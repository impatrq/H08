# -*- coding: utf-8 -*-
"""Agujas de giro continuo (centenas del altímetro y brújula) con 28BYJ-48.

Un servo tiene topes y tendría que desandar la vuelta; el 28BYJ-48 gira sin fin
y trae reducción 63,68:1. Cada uno con su ULN2003 de fábrica: las bobinas piden
~100 mA y un pin de la Pi no da más de 16 mA ni tiene diodos.
"""

import json
import math
import os
import threading
import time

from configuracion import MOTOR_CFG, MOTORES

# medio paso: IN1, IN1+IN2, IN2, IN2+IN3, IN3, IN3+IN4, IN4, IN4+IN1
SECUENCIA = (0b0001, 0b0011, 0b0010, 0b0110,
             0b0100, 0b1100, 0b1000, 0b1001)


def _envolver180(d):
    return (d + 180.0) % 360.0 - 180.0


class MotorContinuo:
    # escribir(pines, bits) pone IN1..IN4 de la plaquita

    def __init__(self, escribir, pines, sentido=1, grados_iniciales=0.0,
                 fase_inicial=0):
        self.escribir = escribir
        self.pines = pines
        self.sentido = 1 if sentido >= 0 else -1
        self.ppv = float(MOTOR_CFG["pasos_por_vuelta"])
        self.v_max = float(MOTOR_CFG["vel_max_pps"])
        self.v_min = float(MOTOR_CFG["vel_arranque_pps"])
        self.acel = float(MOTOR_CFG["aceleracion"])
        self.t_soltar = float(MOTOR_CFG["soltar_tras_s"])
        # desenrollados: pueden pasar de 360 o ser negativos
        g = grados_iniciales % 360.0
        self.pos = int(round(g * self.ppv / 360.0))
        self.obj_grados = g
        self.estado = int(fase_inicial) % 8
        self.vel = 0.0          # pasos/s, siempre >= 0
        self.dir = 0
        self.proximo = 0.0
        self.energizado = False
        self.quieto_desde = time.monotonic()

    # las órdenes vienen de otro hilo, por eso son asignaciones simples
    def ir_a_grados(self, grados):
        # camino corto: de 350 a 10 son 20 para adelante, no 340 para atrás
        actual = self.obj_grados
        self.obj_grados = actual + _envolver180(grados - actual)

    def grados(self):
        return (self.pos * 360.0 / self.ppv) % 360.0

    def objetivo_pasos(self):
        return int(round(self.obj_grados * self.ppv / 360.0))

    def declarar_cero(self):
        self.pos = 0
        self.obj_grados = 0.0

    def invertir_sentido(self):
        """Da vuelta el giro sin mover la aguja (para la calibración)."""
        # la aguja depende de pasos x sentido: cambiando los dos signos queda donde está
        self.sentido = -self.sentido
        self.pos = -self.pos
        self.obj_grados = -self.obj_grados

    def servicio(self, ahora):
        """Da el paso que toque. Devuelve cuándo volver a llamarlo, o None si
        está quieto y suelto.

        Si el hilo se atrasa el motor va más lento, nunca más rápido: no pierde
        pasos y por eso no hace falta sensor de posición.
        """
        falta = self.objetivo_pasos() - self.pos
        if falta == 0 and self.vel <= self.v_min:
            self.vel = 0.0
            self.dir = 0
            if not self.energizado:
                return None
            # energizado se calienta aunque esté quieto; la reducción sostiene la aguja
            soltar_en = self.quieto_desde + self.t_soltar
            if ahora >= soltar_en:
                self.soltar()
                return None
            return soltar_en

        if not self.energizado:
            # fase donde quedó y 5 ms para que el rotor se acomode
            self.escribir(self.pines, SECUENCIA[self.estado])
            self.energizado = True
            self.proximo = ahora + 0.005
            return self.proximo
        if ahora < self.proximo:
            return self.proximo

        # trapezoidal paso a paso: v^2 cambia 2a en cada paso
        if falta == 0:
            deseada = -self.dir          # llegó con velocidad, frena pasándose
        else:
            deseada = 1 if falta > 0 else -1
        a2 = 2.0 * self.acel
        if self.dir == 0:
            self.dir = deseada
            self.vel = self.v_min
        elif self.dir != deseada:
            self.vel = math.sqrt(max(self.vel * self.vel - a2, 0.0))
            if self.vel <= self.v_min:
                self.dir = deseada
                self.vel = self.v_min
        elif abs(falta) <= self.vel * self.vel / a2:
            self.vel = max(self.v_min, math.sqrt(max(self.vel * self.vel - a2, 0.0)))
        else:
            self.vel = min(self.v_max, math.sqrt(self.vel * self.vel + a2))

        self.pos += self.dir
        self.estado = (self.estado + self.dir * self.sentido) % 8
        self.escribir(self.pines, SECUENCIA[self.estado])
        self.quieto_desde = ahora
        self.proximo = ahora + 1.0 / self.vel
        return self.proximo

    def en_objetivo(self):
        return self.objetivo_pasos() == self.pos and self.dir == 0

    def estacionar(self):
        # el cero más cercano, sin desandar vueltas
        self.obj_grados = round(self.obj_grados / 360.0) * 360.0

    def soltar(self):
        self.escribir(self.pines, 0)
        self.energizado = False


class EscritorGPIO:
    # gpiozero sobre lgpio: RPi.GPIO no anda con el RP1 de la Pi 5

    def __init__(self):
        try:
            from gpiozero import DigitalOutputDevice
        except ImportError:
            raise RuntimeError("Falta gpiozero:  sudo apt install -y "
                               "python3-gpiozero python3-lgpio")
        self._crear = DigitalOutputDevice
        self.salidas = {}
        self.ultimo = {}

    def __call__(self, pines, bits):
        previo = self.ultimo.get(pines)
        for i, gp in enumerate(pines):
            b = (bits >> i) & 1
            if previo is not None and ((previo >> i) & 1) == b:
                continue
            s = self.salidas.get(gp)
            if s is None:
                s = self._crear(gp, initial_value=False)
                self.salidas[gp] = s
            s.value = b
        self.ultimo[pines] = bits

    def cerrar(self):
        for s in self.salidas.values():
            try:
                s.off()
                s.close()
            except Exception:
                pass
        self.salidas = {}


def motores_invertidos(archivo_calibracion):
    # en calibracion_servos.json como "MOTOR:1": {"invertido": true}
    if not archivo_calibracion:
        return set()
    try:
        with open(archivo_calibracion, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return set()
    if not isinstance(datos, dict):
        return set()
    invertidos = set()
    for clave, entrada in datos.items():
        if clave.startswith("MOTOR:") and isinstance(entrada, dict) and entrada.get("invertido"):
            try:
                invertidos.add(int(clave.split(":", 1)[1]))
            except ValueError:
                pass
    return invertidos


class GestorMotores(threading.Thread):
    """Mueve los motores desde su hilo. Destino ("MOTOR", n), n de configuracion.MOTORES."""

    PERIODO_QUIETO_S = 0.05
    LIMITE_CIERRE_S = 8.0        # para llevar las agujas a cero al cerrar
    GUARDAR_CADA_S = 30.0

    def __init__(self, escritor, archivo_posicion=None, motores=MOTORES,
                 archivo_calibracion=None):
        threading.Thread.__init__(self, daemon=True, name="motores")
        self.escritor = escritor
        self.archivo = archivo_posicion
        guardado = self._leer_posiciones()
        invertidos = motores_invertidos(archivo_calibracion)
        self.motores = {}
        for n, m in motores.items():
            grados, fase = guardado.get(str(n), (0.0, 0))
            sentido = m.get("sentido", 1) * (-1 if n in invertidos else 1)
            self.motores[n] = MotorContinuo(escritor, tuple(m["pines"]),
                                            sentido, grados, fase)
        # si un GPIO arranca con pull-up queda una bobina prendida hasta que se mueva
        for m in self.motores.values():
            m.soltar()
        self._parar = threading.Event()
        self._t_guardado = 0.0
        self._guardado = self._posiciones()

    def escribir_motor(self, destino, angulo_deg):
        m = self.motores.get(destino[1])
        if m is not None:
            m.ir_a_grados(angulo_deg)

    def descripcion(self):
        return "%d motores paso a paso (GPIO %s)" % (
            len(self.motores),
            " / ".join(",".join(str(p) for p in m.pines)
                       for m in self.motores.values()))

    errores = 0
    ultimo_error = ""

    def run(self):
        while not self._parar.is_set():
            try:
                self._vuelta()
            except Exception as e:
                # que no muera el hilo con la brújula congelada; lo muestra diagnostico_pi.py
                self.errores += 1
                self.ultimo_error = "%s: %s" % (type(e).__name__, e)
                if self.errores <= 3 or self.errores % 50 == 0:
                    print("[motor] error %d: %s" % (self.errores, self.ultimo_error))
                for m in self.motores.values():
                    try:
                        m.soltar()
                    except Exception:
                        pass
                self._parar.wait(1.0)

    def _vuelta(self):
        ahora = time.monotonic()
        proximos = [m.servicio(ahora) for m in self.motores.values()]
        pendientes = [p for p in proximos if p is not None]
        if pendientes:
            espera = min(pendientes) - time.monotonic()
        else:
            espera = self.PERIODO_QUIETO_S
            if ahora - self._t_guardado >= self.GUARDAR_CADA_S:
                self._t_guardado = ahora
                self._guardar()
        if espera > 0:
            if pendientes and espera < self.PERIODO_QUIETO_S:
                # time.sleep porque en Windows Event.wait no baja de ~15 ms
                # (solo importa simulando en la PC)
                time.sleep(espera)
            else:
                self._parar.wait(min(espera, self.PERIODO_QUIETO_S))

    def esperar_quietos(self, limite_s=10.0):
        fin = time.monotonic() + limite_s
        while time.monotonic() < fin:
            if all(m.en_objetivo() for m in self.motores.values()):
                return True
            time.sleep(0.02)
        return False

    def detener(self):
        # sin mover las agujas
        self._parar.set()
        if self.is_alive():
            self.join(1.0)
        for m in self.motores.values():
            m.soltar()
        self._guardar(forzar=True)

    def cerrar(self):
        # Apagado en orden: a cero y se guarda. Si hay corte de luz sirve la
        # última posición guardada con el motor quieto.
        if self.is_alive():
            for m in self.motores.values():
                m.estacionar()
            self.esperar_quietos(self.LIMITE_CIERRE_S)
            self._parar.set()
            self.join(1.0)
        for m in self.motores.values():
            m.soltar()
        self._guardar(forzar=True)
        cerrar = getattr(self.escritor, "cerrar", None)
        if cerrar:
            cerrar()

    def _posiciones(self):
        # {"0": [grados, fase], ...}
        return dict((str(n), [round(m.grados(), 2), m.estado])
                    for n, m in self.motores.items())

    def _leer_posiciones(self):
        if not self.archivo:
            return {}
        try:
            with open(self.archivo, encoding="utf-8") as f:
                d = json.load(f)
            return dict((k, (float(v[0]), int(v[1]))) for k, v in d.items())
        except (OSError, ValueError, TypeError, AttributeError, IndexError,
                KeyError):
            return {}

    def _guardar(self, forzar=False):
        if not self.archivo:
            return
        actual = self._posiciones()
        if actual == self._guardado and not forzar:
            return
        tmp = self.archivo + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(actual, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.archivo)      # así nunca queda a medias
            self._guardado = actual
        except OSError:
            pass

    def guardar_ahora(self):
        self._guardar(forzar=True)
