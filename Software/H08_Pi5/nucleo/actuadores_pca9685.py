# -*- coding: utf-8 -*-
"""Servos y luces sobre dos PCA9685 por I2C (/dev/i2c-1, solo biblioteca estándar).

Si el chip se reinicia por una caída de tensión vuelve dormido y con todo en
bajo: cada 2 s leemos MODE1 para darnos cuenta. Un error de bus no frena el
tablero, se cuenta y se reintenta.
"""

try:
    import fcntl            # sólo existe en Linux (la Raspberry)
except ImportError:         # en Windows se puede correr todo en modo simulado
    fcntl = None
import json
import os
import time

from utiles import limitar, interpolar_tabla
from configuracion import (SERVO_CFG, LUCES_ACTIVAS_EN_BAJO, I2C_BUS, PLACAS,
                           TABLERO, LED, SERVO, AL_REVES, invertido,
                           recorrido_servo)
from actuadores_base import ActuadoresBase

MODE1 = 0x00
MODE2 = 0x01
LED0_ON_L = 0x06
PRESCALE = 0xFE

M1_RESTART = 0x80
M1_AI = 0x20            # autoincremento de dirección de registro
M1_SLEEP = 0x10
M2_OUTDRV = 0x04        # salida totem-pole: obligatoria para los servos

# prescale = round(25 MHz / (4096 * f)) - 1, da 121 para 50 Hz.
# A 50 Hz cada cuenta son 4,88 us: 500-2500 us son ~410 pasos, 0,44 grados c/u
OSCILADOR_HZ = 25000000.0

# ON_L, ON_H, OFF_L, OFF_H con el bit 4 de full ON / full OFF (este gana).
# Para las luces, que son todo o nada, y para soltar servos (sin pulso no zumban)
SALIDA_ALTA = (0x00, 0x10, 0x00, 0x00)
SALIDA_BAJA = (0x00, 0x00, 0x00, 0x10)

I2C_SLAVE = 0x0703      # ioctl de linux/i2c-dev.h: elegir el esclavo


class BusI2C:
    # os + fcntl, así no hay que instalar nada

    def __init__(self, numero=I2C_BUS):
        self.nombre = "/dev/i2c-%d" % numero
        if fcntl is None:
            raise RuntimeError("No hay bus I2C en este sistema (sólo en la Raspberry).")
        try:
            self._fd = os.open(self.nombre, os.O_RDWR)
        except FileNotFoundError:
            raise RuntimeError(
                "No existe %s: el I2C está deshabilitado.\n"
                "  sudo raspi-config nonint do_i2c 0   y reiniciar" % self.nombre)
        except PermissionError:
            raise RuntimeError(
                "Sin permiso sobre %s.\n"
                "  sudo usermod -aG i2c $USER   y volver a iniciar sesión"
                % self.nombre)
        self._actual = None

    def _elegir(self, direccion):
        if direccion != self._actual:
            fcntl.ioctl(self._fd, I2C_SLAVE, direccion)
            self._actual = direccion

    def escribir(self, direccion, registro, datos=()):
        self._elegir(direccion)
        os.write(self._fd, bytes([registro]) + bytes(datos))

    def leer(self, direccion, registro, n=1):
        self._elegir(direccion)
        os.write(self._fd, bytes([registro]))
        return os.read(self._fd, n)

    def responde(self, direccion):
        try:
            self.leer(direccion, MODE1, 1)
            return True
        except OSError:
            return False

    def cerrar(self):
        try:
            os.close(self._fd)
        except OSError:
            pass


class PCA9685:
    # 16 canales con copia de lo escrito, para mandar solo lo que cambió

    def __init__(self, bus, direccion, frecuencia=50):
        self.bus = bus
        self.dir = direccion
        self.prescale = int(round(OSCILADOR_HZ / (4096.0 * frecuencia))) - 1
        self.frecuencia = OSCILADOR_HZ / (4096.0 * (self.prescale + 1))
        self.reg = [SALIDA_BAJA] * 16      # lo que tiene que haber en el chip
        self.sucio = [True] * 16           # lo que falta mandar
        self.reinicios = 0

    def configurar(self):
        # el prescaler solo se puede escribir con el chip dormido
        self.bus.escribir(self.dir, MODE1, [M1_AI | M1_SLEEP])
        self.bus.escribir(self.dir, PRESCALE, [self.prescale])
        self.bus.escribir(self.dir, MODE2, [M2_OUTDRV])
        self.bus.escribir(self.dir, MODE1, [M1_AI])
        time.sleep(0.001)                  # el oscilador tarda 500 us
        self.bus.escribir(self.dir, MODE1, [M1_AI | M1_RESTART])
        self.sucio = [True] * 16

    def se_reinicio(self):
        # dormido o sin autoincremento = se reinició
        m1 = self.bus.leer(self.dir, MODE1, 1)[0]
        return (m1 & M1_SLEEP) or not (m1 & M1_AI)

    def poner(self, canal, cuatro_bytes):
        # reg None después de un reinicio: cualquier valor es nuevo
        if self.reg[canal] != cuatro_bytes:
            self.reg[canal] = cuatro_bytes
            self.sucio[canal] = True

    def volcar(self):
        # una sola transacción del primer al último canal sucio (autoincremento)
        if True not in self.sucio:
            return 0
        a = self.sucio.index(True)
        b = 15 - self.sucio[::-1].index(True)
        datos = []
        for c in range(a, b + 1):
            # después de un reinicio, un canal todavía sin soltar queda apagado
            datos.extend(self.reg[c] if self.reg[c] is not None else SALIDA_BAJA)
        self.bus.escribir(self.dir, LED0_ON_L + 4 * a, datos)
        for c in range(a, b + 1):
            self.sucio[c] = False
        return b - a + 1


def bytes_pulso(cuentas):
    c = int(limitar(round(cuentas), 0, 4095))
    return (0x00, 0x00, c & 0xFF, c >> 8)


class ActuadoresPCA9685(ActuadoresBase):
    # los motores paso a paso no van por el PCA: se derivan a paso_a_paso.py

    CADA_VIGILANCIA_S = 2.0
    reinicio_pendiente = False     # una placa se reinició: el mapa reescribe de a tandas

    def __init__(self, placas=PLACAS, bus=None, calibracion=None, motores=None,
                 al_reves=None):
        self.bus = bus if bus is not None else BusI2C()
        self.motores = motores
        self.placas = {}
        self.faltantes = []
        for nombre, direccion in sorted(placas.items()):
            if self.bus.responde(direccion):
                self.placas[nombre] = PCA9685(self.bus, direccion,
                                              SERVO_CFG["frecuencia_hz"])
            else:
                self.faltantes.append("%s (0x%02X)" % (nombre, direccion))

        self.cal = cargar_calibracion(calibracion)
        self.marcas = cargar_marcas(calibracion)
        self.errores = 0
        self.ultimo_error = ""
        self._t_vigilancia = time.monotonic()

        # arranca seguro: servos sin pulso, luces apagadas
        self.luces = set()
        self.invertidos = set()
        self.al_reves = {}               # canal -> grados que usa ese servo
        self._id_de = {}                 # canal -> instrumento
        anotados = AL_REVES if al_reves is None else al_reves
        # lo elegido en calibrar_instrumento.py le gana a configuracion.AL_REVES
        elegidos = cargar_al_reves(calibracion)
        for it in TABLERO:
            if not it.get("canal"):
                continue
            if it["actuador"] == LED:
                self.luces.add(tuple(it["canal"]))
                continue
            if invertido(it["id"]):
                self.invertidos.add(tuple(it["canal"]))
            if it["actuador"] == SERVO:
                canal = tuple(it["canal"])
                self._id_de[canal] = it["id"]
                if elegidos.get("%s:%d" % canal, it["id"] in anotados):
                    self.al_reves[canal] = recorrido_servo(it["id"])
        for nombre, placa in self.placas.items():
            placa.configurar()
            for c in range(16):
                if (nombre, c) in self.luces:
                    placa.poner(c, self._bytes_luz(False))
            placa.volcar()

    def esta_al_reves(self, destino):
        return tuple(destino) in self.al_reves

    def poner_al_reves(self, destino, si):
        canal = tuple(destino)
        if si and canal in self._id_de:
            self.al_reves[canal] = recorrido_servo(self._id_de[canal])
        else:
            self.al_reves.pop(canal, None)

    def limites_us(self, destino):
        """Pulsos para 0 y 180 grados en ese canal.

        Medidos con transportador mirando desde el lado del eje. Con un par de
        engranajes en el medio se dan vuelta (configuracion.invertido).
        """
        c = self.cal.get("%s:%d" % tuple(destino))
        if c is None:
            a, b = SERVO_CFG["pulso_min_us"], SERVO_CFG["pulso_max_us"]
        else:
            a, b = c[0], c[1]
        if tuple(destino) in self.invertidos:
            a, b = b, a
        return a, b

    def topes_us(self, destino):
        # topes medidos, o None
        c = self.cal.get("%s:%d" % tuple(destino))
        return (c[2], c[3]) if c else None

    def _cuentas(self, placa, us):
        return us * 4096.0 * placa.frecuencia / 1e6

    @staticmethod
    def _bytes_luz(encendida):
        if LUCES_ACTIVAS_EN_BAJO:
            return SALIDA_BAJA if encendida else SALIDA_ALTA
        return SALIDA_ALTA if encendida else SALIDA_BAJA

    def pulso_us(self, destino, angulo_deg):
        """Ángulo del programa a pulso: marcas de la carátula si hay, si no la
        recta del transportador, si no la nominal."""
        a = limitar(angulo_deg, 0.0, SERVO_CFG["barrido_deg"])
        marcas = self.marcas.get("%s:%d" % tuple(destino))
        if marcas:
            # las marcas no se dan vuelta por AL_REVES: se midieron con la aguja como está
            return interpolar_tabla(a, marcas)
        recorrido = self.al_reves.get(tuple(destino))
        if recorrido is not None:
            a = limitar(recorrido - a, 0.0, SERVO_CFG["barrido_deg"])
        us_0, us_180 = self.limites_us(destino)
        us = us_0 + (us_180 - us_0) * a / SERVO_CFG["barrido_deg"]
        topes = self.topes_us(destino)
        if topes:
            us = limitar(us, min(topes), max(topes))
        return us

    def escribir_servo(self, destino, angulo_deg):
        placa = self.placas.get(destino[0])
        if placa is None:
            return
        us = self.pulso_us(destino, angulo_deg)
        placa.poner(destino[1], bytes_pulso(self._cuentas(placa, us)))

    def escribir_pulso(self, destino, us):
        # sin calibración, para calibrar_instrumento.py
        placa = self.placas.get(destino[0])
        if placa is not None:
            placa.poner(destino[1], bytes_pulso(self._cuentas(placa, us)))

    def soltar(self, destino):
        placa = self.placas.get(destino[0])
        if placa is not None:
            placa.poner(destino[1], SALIDA_BAJA)

    def escribir_led(self, destino, encendido):
        placa = self.placas.get(destino[0])
        if placa is not None:
            placa.poner(destino[1], self._bytes_luz(encendido))

    def escribir_motor(self, destino, angulo_deg):
        if self.motores is not None:
            self.motores.escribir_motor(destino, angulo_deg)

    def refrescar(self):
        ahora = time.monotonic()
        vigilar = ahora - self._t_vigilancia >= self.CADA_VIGILANCIA_S
        if vigilar:
            self._t_vigilancia = ahora
        n = 0
        for nombre, placa in self.placas.items():
            try:
                if vigilar and placa.se_reinicio():
                    # Casi siempre es baja tensión. Mandar los 16 canales juntos
                    # es el mismo pico que lo reinició, así que no mandamos nada:
                    # mapa_tablero los suelta de a tandas (reinicio_pendiente).
                    placa.reinicios += 1
                    placa.configurar()
                    placa.reg = [None] * 16
                    placa.sucio = [False] * 16
                    self.reinicio_pendiente = True
                    continue
                n += placa.volcar()
            except OSError as e:
                # queda sucio y se reintenta en el próximo ciclo
                self.errores += 1
                self.ultimo_error = "%s: %s" % (nombre, e)
        return n

    def cerrar(self):
        if self.motores is not None:
            self.motores.cerrar()
        for nombre, placa in self.placas.items():
            for c in range(16):
                if (nombre, c) in self.luces:
                    placa.poner(c, self._bytes_luz(False))
                else:
                    placa.poner(c, SALIDA_BAJA)
            try:
                placa.volcar()
            except OSError:
                pass
        self.bus.cerrar()

    def descripcion(self):
        d = "PCA9685: %s" % (", ".join("%s 0x%02X" % (n, p.dir)
                                       for n, p in sorted(self.placas.items()))
                             or "ninguna")
        if self.faltantes:
            d += "  FALTAN: " + ", ".join(self.faltantes)
        if self.cal:
            d += "  (%d servos calibrados)" % len(self.cal)
        if self.motores is not None:
            d += "  + " + self.motores.descripcion()
        return d

    def salud(self):
        return {"errores_i2c": self.errores,
                "ultimo_error": self.ultimo_error,
                "reinicios_pca": sum(p.reinicios for p in self.placas.values()),
                "errores_motor": getattr(self.motores, "errores", 0) if self.motores is not None else 0,
                "error_motor": getattr(self.motores, "ultimo_error", "") if self.motores is not None else "",
                "faltan": self.faltantes}


def cargar_calibracion(archivo):
    """Lee calibracion_servos.json: {"PCA0:3": (us_0, us_180, tope_a, tope_b), ...}.

    us_0 y us_180 pueden estar extrapolados si el servo no llega; los topes son
    los extremos alcanzables. Acepta también el formato viejo min_us/max_us.
    """
    if not archivo or not os.path.exists(archivo):
        return {}
    try:
        with open(archivo, encoding="utf-8") as f:
            crudo = json.load(f)
    except (OSError, ValueError):
        return {}
    cal = {}
    for clave, v in crudo.items():
        try:
            if "us_0" in v:
                a, b = float(v["us_0"]), float(v["us_180"])
                ta = float(v.get("tope_a", a))
                tb = float(v.get("tope_b", b))
            else:
                a, b = float(v["min_us"]), float(v["max_us"])
                ta, tb = a, b
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        lo, hi = SERVO_CFG["pulso_limite_us"]
        if all(lo - 100 <= x <= hi + 200 for x in (a, b)) and abs(b - a) >= 500 \
                and all(lo <= x <= hi for x in (ta, tb)):
            cal[clave] = (a, b, ta, tb)
    return cal


def cargar_al_reves(archivo):
    # {"PCA0:6": True, ...} solo de los canales donde se eligió algo
    if not archivo or not os.path.exists(archivo):
        return {}
    try:
        with open(archivo, encoding="utf-8") as f:
            crudo = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(crudo, dict):
        return {}
    return {clave: v["al_reves"] for clave, v in crudo.items()
            if isinstance(v, dict) and isinstance(v.get("al_reves"), bool)}


def cargar_marcas(archivo):
    """Marcas medidas en la carátula: {"PCA0:6": [(ángulo, pulso), ...]}.

    Descarta la tabla con menos de dos marcas, pulsos fuera de rango o que no
    van todos para el mismo lado.
    """
    if not archivo or not os.path.exists(archivo):
        return {}
    try:
        with open(archivo, encoding="utf-8") as f:
            crudo = json.load(f)
    except (OSError, ValueError):
        return {}
    marcas = {}
    for clave, v in crudo.items():
        try:
            pares = sorted((float(a), float(us)) for a, us in v["marcas"])
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        lo, hi = SERVO_CFG["pulso_limite_us"]
        if len(pares) < 2 or not all(lo <= us <= hi for _a, us in pares):
            continue
        angulos = [a for a, _us in pares]
        saltos = [b[1] - a[1] for a, b in zip(pares, pares[1:])]
        if len(set(angulos)) != len(angulos):
            continue
        if not (all(s > 0 for s in saltos) or all(s < 0 for s in saltos)):
            continue
        marcas[clave] = pares
    return marcas
