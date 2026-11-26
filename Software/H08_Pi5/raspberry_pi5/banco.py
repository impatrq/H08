# -*- coding: utf-8 -*-
"""Lo que comparten las herramientas de prueba de la Raspberry (probar_canal,
probar_motor, calibrar_instrumento, prueba_general y diagnostico_pi).

Con --simulado se abren placas y motor de mentira, para ver la prueba en la
compu sin hardware.
"""

import datetime
import os
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "nucleo"))

from configuracion import (TABLERO, TABLERO_POR_ID, PLACAS, SERVO, MOTOR, LED,   # noqa: E402
                           BARRIDO, ENGRANAJES, AL_REVES, factor_servo, invertido,
                           recorrido_servo, reduccion)
from utiles import interpolar_tabla                                              # noqa: E402

ARCHIVO_CALIBRACION = os.path.join(AQUI, "calibracion_servos.json")
ARCHIVO_MOTORES = os.path.join(AQUI, "posicion_motores.json")
SERVICIO = "tablero-h08"


def servicio_andando():
    try:
        r = subprocess.run(["systemctl", "is-active", "--quiet", SERVICIO],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def exigir_servicio_detenido():
    if servicio_andando():
        print("\n  El servicio del tablero está andando y usa las mismas placas.")
        print("  Primero:   sudo systemctl stop %s" % SERVICIO)
        print("  Al final:  sudo systemctl start %s\n" % SERVICIO)
        sys.exit(1)


def abrir_placas_reales():
    from actuadores_pca9685 import ActuadoresPCA9685
    try:
        return ActuadoresPCA9685(calibracion=ARCHIVO_CALIBRACION)
    except RuntimeError as e:
        print("\n  %s\n" % e)
        sys.exit(1)


def que_hay_en(destino):
    for it in TABLERO:
        if tuple(it.get("canal") or ()) == tuple(destino):
            return it
    return None


def resolver(palabras):
    """["PCA0", "3"] o ["AIRSPEED"] a (destino, instrumento o None)."""
    if not palabras:
        return None, None
    if palabras[0].upper() in PLACAS:
        if len(palabras) < 2 or not palabras[1].isdigit() \
                or not 0 <= int(palabras[1]) <= 15:
            sys.exit("  Falta el canal (0 a 15):  %s 3" % palabras[0].upper())
        destino = (palabras[0].upper(), int(palabras[1]))
        return destino, que_hay_en(destino)
    it = TABLERO_POR_ID.get(palabras[0].upper())
    if it is None or not it.get("canal"):
        sys.exit("  No existe '%s'. Ver la lista con --listar" % palabras[0])
    return tuple(it["canal"]), it


def nombre_de(destino):
    it = que_hay_en(destino)
    return "%s:%d%s" % (destino[0], destino[1],
                        "  (%s)" % it["id"] if it else "  (libre)")


def carpeta_informes():
    # H08_INFORMES la usan las pruebas automáticas para no ensuciar la carpeta
    # de verdad. Se lee en cada informe, no al importar.
    return os.environ.get("H08_INFORMES") or os.path.join(AQUI, "informes")

# con --simulado no hay nada que mirar, así que las esperas se acortan
_ESCALA_TIEMPO = [1.0]


def acelerar():
    _ESCALA_TIEMPO[0] = 0.02


def dormir(seg):
    time.sleep(seg * _ESCALA_TIEMPO[0])


class Preguntas:
    # auto=True contesta "s" solo: para la prueba simulada o una demo sin nadie al lado

    def __init__(self, auto=False):
        self.auto = auto

    def si_no(self, texto, repetir=False):
        """Devuelve 's', 'n', 'r' (repetir, si se permite) o 'q' (salir)."""
        op = "[Enter=sí / n=no%s / q=terminar]" % (" / r=repetir" if repetir else "")
        if self.auto:
            print("  %s %s  s [auto]" % (texto, op))
            return "s"
        while True:
            try:
                r = input("  %s %s " % (texto, op)).strip().lower()
            except EOFError:
                return "q"
            if r in ("", "s", "si", "sí", "y"):
                return "s"
            if r in ("n", "no"):
                return "n"
            if r == "q":
                return "q"
            if r == "r" and repetir:
                return "r"

    def nota(self, texto="¿Qué pasó? (una línea, Enter para nada)"):
        if self.auto:
            return ""
        try:
            return input("  " + texto + " ").strip()
        except EOFError:
            return ""


class Informe:
    def __init__(self, titulo):
        self.titulo = titulo
        self.inicio = datetime.datetime.now()
        self.filas = []          # (sección, qué, "BIEN"/"MAL"/"SALTEADO", nota)

    def anotar(self, seccion, que, resultado, nota=""):
        self.filas.append((seccion, que, resultado, nota))

    def bien(self, seccion, que, nota=""):
        self.anotar(seccion, que, "BIEN", nota)

    def mal(self, seccion, que, nota=""):
        self.anotar(seccion, que, "MAL", nota)

    def malos(self):
        return [f for f in self.filas if f[2] == "MAL"]

    def texto(self):
        L = ["=" * 72,
             " " + self.titulo,
             " " + self.inicio.strftime("%d/%m/%Y %H:%M"),
             "=" * 72]
        seccion = None
        for s, que, res, nota in self.filas:
            if s != seccion:
                L.append("")
                L.append(" " + s)
                seccion = s
            L.append("   [%-8s] %s%s" % (res, que, ("  -  " + nota) if nota else ""))
        n_mal = len(self.malos())
        L += ["", "-" * 72,
              " %d controles, %d bien, %d mal, %d salteados"
              % (len(self.filas), sum(1 for f in self.filas if f[2] == "BIEN"), n_mal,
                 sum(1 for f in self.filas if f[2] == "SALTEADO")),
              " RESULTADO: " + ("TODO BIEN" if n_mal == 0 else "HAY %d PARA REVISAR" % n_mal),
              "=" * 72]
        return "\n".join(L)

    def guardar(self, nombre):
        carpeta = carpeta_informes()
        os.makedirs(carpeta, exist_ok=True)
        base = os.path.join(carpeta, "%s_%s"
                            % (nombre, self.inicio.strftime("%Y%m%d_%H%M%S")))
        ruta, n = base + ".txt", 1
        while os.path.exists(ruta):          # por si hay dos pruebas en el mismo segundo
            n += 1
            ruta = "%s_%d.txt" % (base, n)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.texto() + "\n")
        return ruta


class PlacasDeMentira:
    """Imita ActuadoresPCA9685 sin bus: anota lo último de cada canal."""

    def __init__(self):
        self.placas = {"PCA0": None, "PCA1": None}
        self.faltantes = []
        self.errores = 0
        self.ultimo_error = ""
        self.valores = {}
        self.motores = None
        self.marcas = {}
        self.al_reves_elegido = {}      # canal: True/False, lo que se eligió al calibrar

    def esta_al_reves(self, destino):
        canal = tuple(destino)
        if canal in self.al_reves_elegido:
            return self.al_reves_elegido[canal]
        it = que_hay_en(destino)
        return it is not None and it["actuador"] == SERVO and it["id"] in AL_REVES

    def poner_al_reves(self, destino, si):
        self.al_reves_elegido[tuple(destino)] = bool(si)

    def limites_us(self, destino):
        a, b = 500, 2500
        it = que_hay_en(destino)
        if it is not None and it["actuador"] == SERVO and invertido(it["id"]):
            a, b = b, a
        return a, b

    def pulso_us(self, destino, ang):
        marcas = self.marcas.get("%s:%d" % tuple(destino))
        if marcas:
            return interpolar_tabla(ang, marcas)
        ang = max(0.0, min(ang, 180.0))
        it = que_hay_en(destino)
        if it is not None and it["actuador"] == SERVO and self.esta_al_reves(destino):
            ang = max(0.0, min(recorrido_servo(it["id"]) - ang, 180.0))
        a, b = self.limites_us(destino)
        return a + (b - a) * ang / 180.0

    def escribir_servo(self, destino, ang):
        self.valores[tuple(destino)] = round(ang, 2)

    def escribir_pulso(self, destino, us):
        self.valores[tuple(destino)] = ("us", us)

    def escribir_led(self, destino, encendida):
        self.valores[tuple(destino)] = bool(encendida)

    def soltar(self, destino):
        self.valores[tuple(destino)] = None

    def refrescar(self):
        return 0

    def cerrar(self):
        pass

    def descripcion(self):
        return "de mentira (--simulado)"


def abrir_placas(simulado):
    if simulado:
        acelerar()
        return PlacasDeMentira()
    exigir_servicio_detenido()
    act = abrir_placas_reales()
    if act.faltantes:
        print("  ATENCIÓN, no responden: " + ", ".join(act.faltantes))
    return act


def abrir_motor(simulado, archivo_calibracion=None):
    """GestorMotores ya arrancado. Simulado: pines de mentira y posición en un
    temporal, así no se pisa la guardada."""
    from paso_a_paso import GestorMotores
    if simulado:
        acelerar()
        archivo = os.path.join(tempfile.gettempdir(), "h08_motor_simulado.json")
        g = GestorMotores(lambda pines, bits: None, archivo,
                          archivo_calibracion=archivo_calibracion)
    else:
        from paso_a_paso import EscritorGPIO
        exigir_servicio_detenido()
        try:
            g = GestorMotores(EscritorGPIO(), ARCHIVO_MOTORES,
                              archivo_calibracion=archivo_calibracion or ARCHIVO_CALIBRACION)
        except RuntimeError as e:
            print("  %s" % e)
            return None
    g.start()
    return g


def angulo_servo(it, valor):
    """Valor de la escala a ángulo del servo, misma cuenta que mapa_tablero."""
    return interpolar_tabla(valor, it["cal"]) * factor_servo(it["id"])


def mover_servo(act, it, desde, hasta, seg=1.2):
    # despacio, como se mueve la aguja de verdad
    pasos = max(2, int(seg * 40))
    for i in range(pasos + 1):
        act.escribir_servo(it["canal"], desde + (hasta - desde) * i / pasos)
        act.refrescar()
        dormir(seg / pasos)
    return hasta


def puntos_de_prueba(it):
    # los de la tabla de calibración: son los números grandes de la carátula,
    # los únicos ubicados con precisión
    vistos, pts = set(), []
    for v, _ in it["cal"]:
        if v not in vistos:
            vistos.add(v)
            pts.append(v)
    # el cabeceo del horizonte tiene una tabla de muchos puntos; alcanza con
    # extremos, medio y cuartos
    if len(pts) > 7:
        n = len(pts) - 1
        pts = [pts[round(n * k / 4.0)] for k in range(5)]
    return pts


def mecanica(it):
    b = BARRIDO.get(it["id"])
    if it["actuador"] == MOTOR:
        return "paso a paso, giro continuo"
    if b == "MEC":
        return "mecanismo del horizonte"
    if isinstance(b, (int, float)):
        r = reduccion(it["id"])
        if r > 1.0:
            par = ENGRANAJES.get(min(ENGRANAJES, key=lambda k: abs(k - r)))
            return "barre %g°, engranajes %d/%d (el servo gira al revés)" % (b, par[0], par[1])
        return "barre %g°, aguja directa en el servo" % b
    return ""


def fmt_valor(it, v):
    return "%g %s" % (v, it["unidad"])


def lista_instrumentos():
    # orden del tablero: servos, motor, luces
    orden = {SERVO: 0, MOTOR: 1, LED: 2}
    return sorted([it for it in TABLERO if it.get("canal")],
                  key=lambda it: (orden.get(it["actuador"], 9),
                                  str(it["canal"][0]), it["canal"][1]))


def buscar(nombre):
    it = TABLERO_POR_ID.get(nombre.upper())
    if it and it.get("canal"):
        return it
    return None


def salir_si_no_hay_consola(auto):
    if not auto and not sys.stdin.isatty():
        print("  Esta prueba hace preguntas: correrla en una terminal "
              "(o con --auto para que conteste sola).")
        sys.exit(1)


