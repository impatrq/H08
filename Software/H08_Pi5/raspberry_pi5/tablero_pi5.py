#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Programa principal del tablero en la Raspberry Pi 5 (lo arranca el servicio
tablero-h08). --simulado anda sin hardware, en cualquier compu.

Servidor web en el 8000 y también en el 80 si hay permiso: así la dirección
queda 10.55.0.1 sin puerto y la página se abre sola al conectarse.
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "nucleo"))
sys.path.insert(0, AQUI)

from configuracion import AERONAVE, TABLERO, MOTOR_CFG, LLAVE_APAGADO  # noqa: E402
from fallas import CATALOGO                                  # noqa: E402
from escenarios import ESCENARIOS                            # noqa: E402
from acceso import Acceso, CLAVE_INICIAL                     # noqa: E402
from hilo_simulacion import HiloSimulacion                   # noqa: E402
import servidor_web                                          # noqa: E402

ARCHIVO_CLAVE = os.path.join(AQUI, "secreto_admin.json")
ARCHIVO_CALIBRACION = os.path.join(AQUI, "calibracion_servos.json")
ARCHIVO_MOTORES = os.path.join(AQUI, "posicion_motores.json")


def version():
    # VERSION.txt lo escribe empaquetar.py
    try:
        with open(os.path.join(os.path.dirname(AQUI), "VERSION.txt"),
                  encoding="utf-8") as f:
            return f.readline().strip()
    except OSError:
        return "versión de desarrollo"


def construir_actuadores(simulado, con_motores):
    # Único lugar donde se decide sobre qué se escribe. Si falta el hardware
    # sigue con la página sola, que es lo que ve el público.
    from actuadores_simulados import ActuadoresSimulados
    if simulado:
        return ActuadoresSimulados()
    try:
        from actuadores_pca9685 import ActuadoresPCA9685
        actuadores = ActuadoresPCA9685(calibracion=ARCHIVO_CALIBRACION)
    except (RuntimeError, OSError) as e:
        print("\n  NO SE PUDO ABRIR EL BUS I2C: %s" % e)
        print("  El tablero sigue sólo con la página web.\n")
        return ActuadoresSimulados()
    if con_motores:
        try:
            from paso_a_paso import GestorMotores, EscritorGPIO
            motores = GestorMotores(EscritorGPIO(), ARCHIVO_MOTORES,
                                    archivo_calibracion=ARCHIVO_CALIBRACION)
            motores.start()
            actuadores.motores = motores
        except Exception as e:
            print("\n  SIN MOTORES PASO A PASO: %s\n" % e)
    return actuadores


# el servicio no es root: instalar.sh le deja permiso de sudo solo para
# systemctl poweroff (/etc/sudoers.d/tablero-h08-apagar)
ORDEN_APAGAR = ["sudo", "-n", "/usr/bin/systemctl", "poweroff"]


def apagar_raspberry(espera=0.5):
    # La cuenta regresiva ya pasó. La espera es para que la página llegue a
    # mostrar "esperá a que la pantalla quede negra".
    time.sleep(espera)
    print("\nLlave BATERÍA en APAG: apagando la Raspberry...")
    r = subprocess.run(ORDEN_APAGAR, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError("no tengo permiso para apagar la Raspberry. "
                           "Se arregla con  bash instalar.sh --permiso-apagado")


def construir_llave(nucleo):
    # si no se puede (no es una Pi, falta gpiozero, pin ocupado) avisa y sigue sin llave
    from llave_apagado import LlaveApagado, lector_gpio
    try:
        leer = lector_gpio(LLAVE_APAGADO["gpio"])
    except Exception as e:
        print("  SIN LLAVE DE APAGADO (GPIO %d): %s" % (LLAVE_APAGADO["gpio"], e))
        return None
    llave = LlaveApagado(leer, apagar_raspberry, segundos=LLAVE_APAGADO["segundos"],
                         cuenta=LLAVE_APAGADO["cuenta_s"])
    nucleo.llave = llave
    llave.start()
    return llave


# Watchdog de systemd: READY=1 al arrancar y WATCHDOG=1 cada 5 s. Si pasan
# 30 s sin aviso, systemd lo reinicia (sirve cuando se cuelga sin cerrarse).
# Solo se avisa si el lazo anda y la página contesta.
def sd_notify(mensaje):
    destino = os.environ.get("NOTIFY_SOCKET")
    if not destino or not hasattr(socket, "AF_UNIX"):
        return False
    if destino.startswith("@"):
        destino = "\0" + destino[1:]
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            s.connect(destino)
            s.sendall(mensaje.encode("ascii"))
        finally:
            s.close()
        return True
    except OSError:
        return False


def esta_vivo(nucleo, puerto, margen=10.0):
    if not nucleo.is_alive() or time.monotonic() - nucleo.latido > margen:
        return False
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/estado" % puerto, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def vigilar(nucleo, puerto, cada=5.0):
    if not os.environ.get("NOTIFY_SOCKET"):
        return None

    def latir():
        while True:
            time.sleep(cada)
            if esta_vivo(nucleo, puerto):
                sd_notify("WATCHDOG=1")
    h = threading.Thread(target=latir, name="vigilancia", daemon=True)
    h.start()
    return h


def main():
    ap = argparse.ArgumentParser(description="Tablero didáctico Sikorsky S-55 H-08")
    ap.add_argument("--simulado", action="store_true",
                    help="sin hardware: sólo la página web")
    ap.add_argument("--sin-motores", action="store_true", dest="sin_motores",
                    help="no usar los motores paso a paso")
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--semilla", type=int, default=20250819,
                    help="semilla del ruido de las agujas")
    ap.add_argument("--sin-clave", action="store_true", dest="sin_clave",
                    help="cualquiera que abra la página puede operar "
                         "(sólo para probar en una computadora propia)")
    ap.add_argument("--renovar-clave", action="store_true", dest="renovar",
                    help="cambia la clave interna (la de los programas de prueba) y sale")
    ap.add_argument("--preparar-clave", action="store_true", dest="preparar",
                    help="crea la clave interna si no existe y sale (lo usa instalar.sh)")
    ap.add_argument("--restablecer-clave", action="store_true", dest="restablecer",
                    help="vuelve la clave del profesor a la inicial y sale")
    args = ap.parse_args()
    # en la consola de Windows el QR no entra en la codificación: se reemplaza en vez de cortar
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    acceso = Acceso(ARCHIVO_CLAVE)

    # La clave interna es para prueba_general.py y el servidor la acepta solo
    # desde la misma Raspberry. El profesor entra con la suya.
    if args.preparar:
        print("  Clave interna lista (%s)." % ARCHIVO_CLAVE)
        return 0
    if args.renovar:
        acceso.renovar_clave()
        print("\n  Clave interna nueva. La del profesor no cambió.\n")
        return 0

    if args.restablecer:
        acceso.restablecer_clave_profesor()
        print("\n  La clave del profesor volvió a la inicial: %s" % CLAVE_INICIAL)
        print("  El profesor entra con esa y la página le pide elegir una nueva.\n")
        return 0

    print("=" * 70)
    print(" TABLERO DIDÁCTICO " + AERONAVE["modelo"] + "   " + version())
    print(" Matrícula %s  -  %s" % (AERONAVE["matricula"], AERONAVE["serie"]))
    print("=" * 70)

    actuadores = construir_actuadores(args.simulado, not args.sin_motores)

    print(" Salida       : " + actuadores.descripcion())
    print(" Instrumentos : %d canales" % len(TABLERO))
    print(" Fallas       : %d   Escenarios: %d" % (len(CATALOGO), len(ESCENARIOS)))
    if getattr(actuadores, "motores", None) is not None:
        print(" Paso a paso  : 28BYJ-48, %.2f pasos por vuelta, hasta %d pasos/s"
              % (MOTOR_CFG["pasos_por_vuelta"], MOTOR_CFG["vel_max_pps"]))

    nucleo = HiloSimulacion(actuadores, semilla=args.semilla)
    nucleo.start()
    # llave BATERÍA solo en el tablero de verdad
    if not args.simulado and construir_llave(nucleo) is not None:
        print(" Llave BATERÍA: GPIO %d (pata 37) y GND (pata 39); en APAG apaga la Raspberry"
              % LLAVE_APAGADO["gpio"])

    servidor = servidor_web.crear(nucleo, args.puerto, os.path.join(AQUI, "web"),
                                  donde="la Raspberry",
                                  acceso=None if args.sin_clave else acceso)
    publico = args.puerto
    if args.puerto != 80 and servidor_web.abrir_puerto_extra(80):
        publico = 80
    elif args.puerto != 80:
        print("  (el puerto 80 no se pudo abrir: la dirección lleva :%d y la página no"
              " se abre sola al conectarse. Se arregla con  bash instalar.sh)" % args.puerto)
    print(servidor_web.cartel_de_acceso(publico, ancho=70))
    if args.sin_clave:
        print("\n  ATENCIÓN: --sin-clave. Cualquiera que abra la página puede operar.")
    else:
        print("\n  El tablero arranca en reposo: nada se mueve hasta “Activar tablero”.")
        print("  Para mirar : la dirección de arriba, sin clave.")
        print("  Para operar: “Soy el profesor” en la página, con la clave del profesor")
        if acceso.clave_inicial:
            print("               (todavía es la inicial: %s)" % CLAVE_INICIAL)

    # SIGTERM de systemd igual que Ctrl+C, así el apagado es siempre ordenado
    def _parar(_sig, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _parar)

    sd_notify("READY=1")
    vigilar(nucleo, args.puerto)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nApagando el tablero (luces, servos y motores a cero)...")
        servidor.server_close()
        nucleo.detener()
        nucleo.join(timeout=12.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
