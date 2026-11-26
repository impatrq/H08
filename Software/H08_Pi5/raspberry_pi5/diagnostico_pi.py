#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisa conexiones e instalación de la Pi y, para lo que falla, dice el
comando que lo arregla. No mueve ni cambia nada, se puede correr con el
servicio andando. --cableado muestra la tabla de cables.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import socket
import struct
import urllib.error
import urllib.request

import banco
from configuracion import PLACAS, MOTORES, I2C_BUS, LLAVE_APAGADO

AUTOSTART = os.path.expanduser("~/.config/autostart/tablero-pantalla.desktop")
PUERTO = 8000

CABLEADO = """
  CABLEADO RASPBERRY PI 5 -> PLACA MADRE (J1)
  --------------------------------------------------------------------------
   Función          GPIO     Pata del conector de 40 de la Raspberry
   3,3 V (lógica)    -        1
   SDA  (I2C)        GPIO2    3
   SCL  (I2C)        GPIO3    5
   GND               -        6, 9, 14, 20, 25, 30, 34, 39
   Motor IN1         GPIO12   32
   Motor IN2         GPIO16   36
   Motor IN3         GPIO20   38
   Motor IN4         GPIO21   40
   Llave BATERÍA     GPIO26   37   (la otra pata de la llave a GND, pata 39)
   (libre: motor 0)  GPIO6/13/19      31/33/35
  --------------------------------------------------------------------------
  OJO, PLACA ESPEJADA: el cobre de la placa salió en espejo, así que en J1 las
  columnas par e impar quedaron cambiadas y el cable plano NO sirve. Se
  cablea pata por pata con Dupont hembra-hembra siguiendo esta tabla por
  FUNCIÓN (SDA con SDA, IN1 con IN1...), mirando la serigrafía de la placa
  que tienen en la mano. El programa no cambia: las funciones son las mismas.

  PCA9685
   PCA0  0x40  sin puentes        servos de vuelo y motor (canales 0-15)
   PCA1  0x41  puente A0 soldado  MAP, transmisión, eléctricos (0-5), luces (8-13)
   V+ de los dos módulos: 5 V de la fuente de servos (LM2596), NUNCA de la Pi.
   GND de la fuente y GND de la Pi: unidos.
  Luces: ánodo a +5 V (J8), cátodo por 220 ohm (R2..R7) al canal (J7).
"""


class Revision:
    def __init__(self, eco=True):
        self.filas = []            # (ok, texto, arreglo); ok None es solo un dato
        self.eco = eco
        self.seccion = ""

    def titulo(self, t):
        self.seccion = t
        self.filas.append(("T", t, None))
        if self.eco:
            print("\n  " + t)

    def decir(self, ok, texto, arreglo=None):
        self.filas.append((ok, texto, arreglo))
        if self.eco:
            print("   [%s] %s" % ("ok" if ok else "!!", texto))
            if not ok and arreglo:
                print("        -> " + arreglo)

    def dato(self, texto):
        self.filas.append((None, texto, None))
        if self.eco:
            print("        " + texto)

    def problemas(self):
        return [f for f in self.filas if f[0] is False]

    def texto(self):
        L = []
        for ok, t, arr in self.filas:
            if ok == "T":
                L += ["", " " + t]
            elif ok is None:
                L.append("        " + t)
            else:
                L.append("   [%s] %s" % ("ok" if ok else "!!", t))
                if not ok and arr:
                    L.append("        -> " + arr)
        return "\n".join(L)


# como punto de acceso, el wifi de la Pi aguanta unos 8 celulares
LIMITE_CELULARES = 8



def nombre_a_ip(nombre, servidor, espera=2.0, puerto=53):
    """Pide el registro A a un servidor DNS, como haría un celular. IP o None."""
    try:
        q = struct.pack(">HHHHHH", 0x4808, 0x0100, 1, 0, 0, 0)
        q += b"".join(bytes([len(p)]) + p.encode() for p in nombre.split(".")) + b"\0" + struct.pack(">HH", 1, 1)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(espera)
        try:
            s.sendto(q, (servidor, puerto))
            r, _ = s.recvfrom(512)
        finally:
            s.close()
        n = struct.unpack(">H", r[6:8])[0]
        k = len(q)
        for _ in range(n):
            if r[k] & 0xC0 == 0xC0:
                k += 2
            else:
                while r[k]:
                    k += r[k] + 1
                k += 1
            tipo, _c, _ttl, largo = struct.unpack(">HHIH", r[k:k + 10])
            k += 10
            if tipo == 1 and largo == 4:
                return ".".join(str(b) for b in r[k:k + 4])
            k += largo
    except (OSError, IndexError, struct.error):
        pass
    return None


class _SinSeguir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def prueba_android(ip):
    # tiene que contestar 302 a la bienvenida, así el celular abre la página solo
    pedido = urllib.request.Request("http://%s/generate_204" % ip, headers={"Host": "connectivitycheck.gstatic.com"})
    try:
        r = urllib.request.build_opener(_SinSeguir).open(pedido, timeout=3)
        return False if r.status == 204 else "bienvenida" in (r.geturl() or "")
    except urllib.error.HTTPError as e:
        return e.code in (301, 302) and "bienvenida" in (e.headers.get("Location") or "")
    except (OSError, ValueError):
        return False

def datos_red_propia():
    # los lee de punto_de_acceso.sh, igual que el servidor
    datos = {"red": "Tablero-H08", "ip": "10.55.0.1"}
    texto = leer(os.path.join(banco.AQUI, "punto_de_acceso.sh"))
    for campo, var in (("red", "RED"), ("ip", "IP")):
        m = re.search(r'^%s="([^"]*)"' % var, texto, re.M)
        if m:
            datos[campo] = m.group(1)
    return datos


def correr(cmd, t=10):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read().strip("\x00\n ")
    except OSError:
        return ""


def grupos():
    try:
        import grp                  # solo Linux
    except ImportError:
        return []
    g = []
    for gid in os.getgroups():
        try:
            g.append(grp.getgrgid(gid).gr_name)
        except KeyError:
            pass
    return g


def http_json(ruta, t=3, puerto=PUERTO):
    try:
        with urllib.request.urlopen("http://localhost:%d%s" % (puerto, ruta), timeout=t) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def revisar_llave(R, servicio):
    pin = LLAVE_APAGADO["gpio"]
    R.dato("llave BATERÍA: GPIO %d (pata 37) y GND (pata 39); cierra el contacto en APAG" % pin)
    if servicio:
        L = (http_json("/api/estado") or {}).get("llave")
        R.decir(bool(L) and L.get("posicion") in ("ENC", "APAG"),
                "El tablero vigila la llave BATERÍA (ahora: %s)" % ((L or {}).get("posicion") or "-"),
                "el servicio no pudo abrir el GPIO %d: journalctl -u %s -n 50" % (pin, banco.SERVICIO))
    else:
        try:
            from gpiozero import Button
            b = Button(pin, pull_up=True)
            R.dato("llave BATERÍA ahora: %s" % ("APAG" if b.is_pressed else "ENC"))
            b.close()
        except ImportError:
            pass
        except Exception as e:
            R.decir(False, "Pin de la llave BATERÍA libre",
                    "el GPIO %d lo usa otro programa: %s" % (pin, e))
    R.dato("(sin llave conectada se lee ENC: el tablero no se apaga solo)")
    try:
        permiso = subprocess.run(["sudo", "-n", "-l", "/usr/bin/systemctl", "poweroff"],
                                 capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        permiso = False
    R.decir(permiso, "La llave BATERÍA puede apagar la Raspberry (permiso de sudo)",
            "bash instalar.sh --permiso-apagado")


def revisar(eco=True):
    R = Revision(eco)
    soy_root = getattr(os, "geteuid", lambda: -1)() == 0
    g = grupos()

    R.titulo("1. SISTEMA")
    modelo = leer("/proc/device-tree/model")
    R.decir("Raspberry Pi 5" in modelo, "Placa: %s" % (modelo or "desconocida"),
            "el programa está pensado para la Raspberry Pi 5")
    so = ""
    for linea in leer("/etc/os-release").splitlines():
        if linea.startswith("PRETTY_NAME="):
            so = linea.split("=", 1)[1].strip('"')
    R.decir(any(n in so.lower() for n in ("bookworm", "trixie")),
            "Sistema: %s" % (so or "desconocido"),
            "usar Raspberry Pi OS Bookworm (64 bits) o posterior, CON escritorio")
    escritorio = [n for n in ("labwc", "wayfire", "lxsession") if correr(["which", n])]
    R.decir(bool(escritorio), "Escritorio instalado (%s)" % (", ".join(escritorio) or "ninguno"),
            "hace falta Raspberry Pi OS con escritorio para la pantalla del tablero")
    R.decir(sys.version_info >= (3, 9), "Python %d.%d" % sys.version_info[:2])
    version = leer(os.path.join(os.path.dirname(banco.AQUI), "VERSION.txt")).splitlines()
    R.dato("versión instalada: %s" % (version[0] if version else "sin VERSION.txt"))

    R.titulo("2. ALIMENTACIÓN DE LA RASPBERRY")
    t = correr(["vcgencmd", "get_throttled"])
    if t.startswith("throttled="):
        v = int(t.split("=")[1], 16)
        R.decir(not v & 0x1, "Tensión bien ahora",
                "baja tensión: fuente oficial de 27 W (5,1 V 5 A) y su cable")
        R.decir(not v & 0x10000, "Sin baja tensión desde que arrancó",
                "hubo baja tensión: revisar fuente y cable USB-C. Si pasa cuando se "
                "mueven los servos, la masa de la fuente de servos está mal hecha")
        R.decir(not v & 0x4, "Sin recortes por temperatura", "ventilación de la Pi")
    else:
        R.dato("vcgencmd no disponible")
    adc = correr(["vcgencmd", "pmic_read_adc", "EXT5V_V"])
    m = re.search(r"=([0-9.]+)V", adc)
    if m:
        v5 = float(m.group(1))
        R.decir(v5 >= 4.85, "5 V de entrada de la Pi: %.2f V" % v5,
                "por debajo de 4,85 V: fuente o cable flojos")

    R.titulo("3. BUS I2C Y PLACAS PCA9685")
    dev = "/dev/i2c-%d" % I2C_BUS
    hay = os.path.exists(dev)
    R.decir(hay, "I2C habilitado (%s)" % dev, "sudo raspi-config nonint do_i2c 0   y reiniciar")
    cfg = leer("/boot/firmware/config.txt") or leer("/boot/config.txt")
    m = re.search(r"^dtparam=i2c_arm_baudrate=(\d+)", cfg, re.M)
    R.decir(bool(m), "Velocidad del bus: %s" % ("%s Hz" % m.group(1) if m else "100 kHz (de fábrica)"),
            "bash instalar.sh la deja en 400 kHz (con 100 kHz anda, pero más lento)")
    R.decir(soy_root or "i2c" in g, "Usuario en el grupo i2c",
            "sudo usermod -aG i2c $USER   y volver a iniciar sesión")
    servicio = banco.servicio_andando()
    if hay:
        try:
            from actuadores_pca9685 import BusI2C, MODE1, MODE2, PRESCALE
            bus = BusI2C()
            encontrados = [d for d in range(0x03, 0x78) if bus.responde(d)]
            R.dato("en el bus hay: " + (", ".join("0x%02X" % d for d in encontrados) or "nada"))
            esperadas = set(PLACAS.values())
            for nombre, direccion in sorted(PLACAS.items()):
                ok = direccion in encontrados
                R.decir(ok, "%s responde en 0x%02X" % (nombre, direccion),
                        "revisar VCC 3,3 V, GND, SDA (GPIO2), SCL (GPIO3)%s"
                        % (" y el puente A0 soldado" if direccion == 0x41 else
                           " y que NO tenga puentes soldados"))
                if ok and servicio:
                    try:
                        m1 = bus.leer(direccion, MODE1, 1)[0]
                        m2 = bus.leer(direccion, MODE2, 1)[0]
                        pre = bus.leer(direccion, PRESCALE, 1)[0]
                        R.decir(pre == 121 and (m2 & 0x04) and not (m1 & 0x10),
                                "%s configurada: 50 Hz, salida totem-pole, despierta" % nombre,
                                "el servicio no la pudo configurar: ver journalctl -u %s" % banco.SERVICIO)
                    except OSError:
                        pass
            otras = [d for d in encontrados if d not in esperadas and d != 0x70]
            if 0x70 in encontrados:
                R.dato("0x70 es la dirección 'a todas' del PCA9685: es normal")
            if otras:
                R.dato("OJO, hay algo más en el bus: " + ", ".join("0x%02X" % d for d in otras))
            if encontrados and 0x40 not in encontrados and 0x41 in encontrados:
                R.dato("sólo 0x41: ¿la placa 0 tiene soldado el puente A0 por error?")
            bus.cerrar()
        except RuntimeError as e:
            R.decir(False, "Abrir el bus I2C", str(e).splitlines()[-1].strip())

    R.titulo("4. GPIO: MOTOR PASO A PASO Y LLAVE BATERÍA")
    try:
        import gpiozero                                   # noqa: F401
        R.decir(True, "gpiozero instalado")
    except ImportError:
        R.decir(False, "gpiozero instalado", "sudo apt install -y python3-gpiozero python3-lgpio")
    try:
        import lgpio                                      # noqa: F401
        R.decir(True, "lgpio instalado (la Pi 5 lo necesita)")
    except ImportError:
        R.decir(False, "lgpio instalado", "sudo apt install -y python3-lgpio")
    R.decir(soy_root or "gpio" in g, "Usuario en el grupo gpio",
            "sudo usermod -aG gpio $USER   y volver a iniciar sesión")
    for n, mo in sorted(MOTORES.items()):
        R.dato("motor %d (%s): GPIO %s, sentido %+d"
               % (n, mo["id"], ",".join(str(p) for p in mo["pines"]), mo["sentido"]))
    if not servicio:
        try:
            from gpiozero import DigitalOutputDevice
            ocupados = []
            for mo in MOTORES.values():
                for p in mo["pines"]:
                    try:
                        DigitalOutputDevice(p, initial_value=False).close()
                    except Exception:
                        ocupados.append(p)
            R.decir(not ocupados, "Pines del motor libres",
                    "GPIO ocupados %s: otro programa los usa (¿quedó abierto probar_motor.py?)"
                    % ocupados)
        except ImportError:
            pass
    else:
        R.dato("(pines no revisados: los está usando el servicio, que es lo normal)")
    revisar_llave(R, servicio)

    R.titulo("5. SERVICIO DEL TABLERO")
    R.decir(servicio, "Servicio %s andando" % banco.SERVICIO,
            "sudo systemctl start %s   (errores: journalctl -u %s -n 50)"
            % (banco.SERVICIO, banco.SERVICIO))
    R.decir(correr(["systemctl", "is-enabled", banco.SERVICIO]) == "enabled",
            "Arranca solo al encender", "sudo systemctl enable %s" % banco.SERVICIO)
    est = http_json("/api/estado")
    R.decir(est is not None, "La página contesta en http://localhost:%d/" % PUERTO,
            "el servicio no atiende: journalctl -u %s -n 50" % banco.SERVICIO)
    if est:
        R.decir(http_json("/api/estado", puerto=80) is not None,
                "También en el puerto 80: se entra escribiendo 10.55.0.1 y la página se abre sola",
                "bash instalar.sh   (sin sudo: le da el permiso al servicio) y reiniciar")
        hw = est.get("hardware") or {}
        R.dato("modo: %s   tiempo simulado: %.0f s" % (est.get("modo_nombre", "?"), est.get("t", 0)))
        if "errores_i2c" in hw:
            R.decir(not hw.get("faltan"), "Placas presentes desde el arranque",
                    "faltan %s: el servicio sigue sin ellas" % ", ".join(hw.get("faltan", [])))
            R.decir(hw.get("errores_i2c", 0) == 0,
                    "Errores del bus I2C: %d" % hw.get("errores_i2c", 0),
                    "cables SDA/SCL largos o sueltos, o GND sin unir. Último: %s"
                    % hw.get("ultimo_error", ""))
            R.decir(hw.get("reinicios_pca", 0) == 0,
                    "Reinicios de los PCA9685: %d" % hw.get("reinicios_pca", 0),
                    "se reinician por baja tensión: el 3,3 V del módulo o picos de los servos")
            R.decir(hw.get("errores_motor", 0) == 0,
                    "Errores del motor de la brújula: %d" % hw.get("errores_motor", 0),
                    "revisar los cables de la plaquita ULN2003. Último: %s" % hw.get("error_motor", ""))
        else:
            R.decir(False, "El servicio maneja el hardware",
                    "está en modo simulado o no abrió el I2C: journalctl -u %s -n 50" % banco.SERVICIO)
        R.decir(hw.get("errores_programa", 0) == 0,
                "Errores del programa: %d" % hw.get("errores_programa", 0),
                "journalctl -u %s -n 100" % banco.SERVICIO)

    R.titulo("6. PANTALLA DE LA RASPBERRY")
    nav = [n for n in ("chromium", "chromium-browser") if correr(["which", n])]
    R.decir(bool(nav), "Chromium instalado", "sudo apt install -y chromium")
    auto = leer(AUTOSTART) + leer(os.path.expanduser("~/.config/labwc/autostart"))
    R.decir("pantalla.sh" in auto, "El tablero se abre solo al encender",
            "bash pantalla.sh instalar   (o quitado a propósito con  bash pantalla.sh quitar)")
    lightdm = leer("/etc/lightdm/lightdm.conf")
    R.decir(bool(re.search(r"^autologin-user=\S+", lightdm, re.M)),
            "El escritorio entra solo, sin contraseña",
            "sudo raspi-config nonint do_boot_behaviour B4")
    abierta = correr(["pgrep", "-f", "tablero-pantalla"])
    R.dato("pantalla del tablero abierta ahora: %s" % ("sí" if abierta else "no (normal si se entró por SSH o se cerró con Alt + F4)"))

    R.titulo("7. RED WIFI PROPIA")
    ap = datos_red_propia()
    R.decir(os.path.exists("/usr/sbin/dnsmasq") or bool(correr(["which", "dnsmasq"])),
            "dnsmasq instalado (reparte las direcciones a los celulares)",
            "sudo apt install -y dnsmasq-base")
    if correr(["which", "nmcli"]):
        conex = correr(["nmcli", "-t", "-f", "NAME", "connection", "show"]).splitlines()
        R.decir("tablero-ap" in conex, "Red %s creada" % ap["red"],
                "sudo bash punto_de_acceso.sh preparar   (y reiniciar)")
        if "tablero-ap" in conex:
            ssid = correr(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", "tablero-ap"])
            R.decir(ssid == ap["red"], "Nombre de la red igual al de punto_de_acceso.sh (el del QR)",
                    "sudo bash punto_de_acceso.sh encender   (vuelve a aplicar los datos)")
            ac = correr(["nmcli", "-g", "connection.autoconnect", "connection", "show", "tablero-ap"])
            vig_on = correr(["systemctl", "is-enabled", "tablero-h08-red"]) == "enabled"
            # apagada a propósito está bien, el servicio de la red la levanta al reiniciar
            R.decir(ac == "yes" or vig_on,
                    "Se levanta sola al encender" if ac == "yes" else
                    "Apagada por ahora: vuelve sola al reiniciar la Pi",
                    "sudo bash punto_de_acceso.sh preparar   (y reiniciar)")
            if ac == "yes":
                rein = correr(["nmcli", "-g", "connection.autoconnect-retries", "connection",
                               "show", "tablero-ap"])
                R.decir(rein == "0", "Si falla al encender, la reintenta sin límite",
                        "sudo bash punto_de_acceso.sh preparar   (y reiniciar)")
                vig = correr(["systemctl", "is-active", "tablero-h08-red"])
                R.decir(vig == "active", "Vigilada: si se cae, se vuelve a levantar sola",
                        "sudo bash punto_de_acceso.sh preparar   (y reiniciar)")
            activa = "tablero-ap" in correr(["nmcli", "-t", "-f", "NAME", "connection",
                                             "show", "--active"]).splitlines()
            R.decir(activa, "Levantada ahora", "sudo bash punto_de_acceso.sh encender")
            if activa:
                dirs = correr(["ip", "-4", "-o", "addr", "show", "dev", "wlan0"])
                R.decir((" %s/" % ap["ip"]) in dirs, "La Raspberry tiene la dirección %s" % ap["ip"],
                        "sudo bash punto_de_acceso.sh apagar   y después   encender")
                # Imita al celular: pregunta un nombre (contesta la Pi) y hace la
                # prueba de Android (va a la bienvenida). Si falla, no se abre nada.
                dns = nombre_a_ip("connectivitycheck.gstatic.com", ap["ip"])
                R.decir(dns == ap["ip"], "Los nombres de internet llevan a la Raspberry (%s)" % (dns or "sin respuesta"),
                        "sudo bash punto_de_acceso.sh encender   (rehace el portal) y reiniciar")
                R.decir(prueba_android(ap["ip"]), "La prueba de internet de Android lleva a la bienvenida",
                        "el tablero tiene que atender en el puerto 80: bash instalar.sh y reiniciar")
                n = correr(["iw", "dev", "wlan0", "station", "dump"]).count("Station ")
                R.decir(n < LIMITE_CELULARES,
                        "Celulares conectados: %d (el wifi de la Raspberry acepta unos %d)"
                        % (n, LIMITE_CELULARES),
                        "los que no entran tienen que esperar; para más hace falta un router aparte")
        R.dato("para revisar la red paso a paso:  sudo bash punto_de_acceso.sh revisar")
    else:
        R.decir(False, "NetworkManager (nmcli)", "hace falta Raspberry Pi OS Bookworm o posterior")
    R.dato("direcciones: %s" % (correr(["hostname", "-I"]) or "ninguna"))

    R.titulo("8. ARCHIVOS")
    R.decir(os.access(banco.AQUI, os.W_OK), "Se puede escribir en la carpeta del programa",
            "la clave, la calibración y la posición del motor se guardan ahí")
    R.decir(os.path.exists(os.path.join(banco.AQUI, "secreto_admin.json")),
            "Clave interna generada", "python3 tablero_pi5.py --preparar-clave")
    try:
        with open(banco.ARCHIVO_CALIBRACION, encoding="utf-8") as f:
            ncal = len(json.load(f))
    except (OSError, ValueError):
        ncal = 0
    R.dato("servos calibrados: %d de 20 (los demás usan 500-2500 us)" % ncal)
    R.dato("posición del motor guardada: %s"
           % ("sí" if os.path.exists(banco.ARCHIVO_MOTORES) else "no (arranca en 0°)"))
    ind = os.path.join(banco.AQUI, "web", "caratulas", "indice.json")
    R.decir(os.path.exists(ind), "Carátulas de la página (web/caratulas)",
            "faltan: la página usa sus esferas viejas. Volver a copiar el paquete")
    return R


def main():
    ap = argparse.ArgumentParser(description="Diagnóstico del tablero H-08")
    ap.add_argument("--cableado", action="store_true")
    ap.add_argument("--guardar", action="store_true")
    a = ap.parse_args()
    if a.cableado:
        print(CABLEADO)
        return 0
    print("\n  DIAGNÓSTICO DEL TABLERO H-08")
    R = revisar()
    malos = R.problemas()
    print("\n  %s\n" % ("Todo en orden." if not malos else "%d cosa(s) para revisar." % len(malos)))
    if a.guardar:
        os.makedirs(banco.carpeta_informes(), exist_ok=True)
        ruta = os.path.join(banco.carpeta_informes(), "diagnostico_%s.txt"
                            % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("DIAGNÓSTICO DEL TABLERO H-08  %s\n" %
                    datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
            f.write(R.texto() + "\n")
        print("  Guardado en: %s\n" % ruta)
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
