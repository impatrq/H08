# -*- coding: utf-8 -*-
"""La llave BATERÍA del panel apaga la Raspberry en orden, con cuenta regresiva.

No corta corriente: la leemos 10 veces por segundo. La llave va entre el GPIO
(configuracion.LLAVE_APAGADO) y GND y cierra en APAG; con el pull-up interno un
cable suelto lee ENC, así nunca apaga el tablero por accidente.
"""

import math
import threading
import time

SIN_LLAVE = "sin llave"
ENC = "ENC"
APAG = "APAG"


class LlaveApagado(threading.Thread):

    def __init__(self, leer, al_apagar, segundos=2.0, cuenta=0.0, cada=0.1, reloj=time.monotonic):
        # leer() da True en APAG. segundos: espera antes del cartel; cuenta:
        # regresiva en la que volver a ENC cancela
        threading.Thread.__init__(self, daemon=True, name="llave-apagado")
        self.leer = leer
        self.al_apagar = al_apagar
        self.segundos = float(segundos)
        self.cuenta = float(cuenta)
        self.cada = float(cada)
        self.reloj = reloj
        self.armada = None          # None: todavía no leyó nada
        self.desde = None           # desde cuándo está en APAG (armada)
        self.cuenta_desde = None    # desde cuándo corre la cuenta regresiva
        self.pedido = False         # ya se pidió apagar: no se puede cancelar
        self._parar = threading.Event()
        # lo copia hilo_simulacion a la foto; cuenta None = sin cuenta, 0 = ya pedido
        self.estado = {"posicion": SIN_LLAVE, "apagando": False, "cuenta": None, "aviso": ""}

    def paso(self, ahora=None):
        """Una lectura. True si en esta se pidió apagar."""
        ahora = self.reloj() if ahora is None else ahora
        try:
            apag = bool(self.leer())
        except Exception as e:
            self.estado.update(posicion=SIN_LLAVE, aviso="No se pudo leer la llave: %s" % e)
            return False
        self.estado["posicion"] = APAG if apag else ENC

        if self.armada is None:
            # si arranca ya en APAG no apagamos: no se podría volver a prender
            self.armada = not apag
            if apag:
                self.estado["aviso"] = ("La llave BATERÍA está en APAG. Pasala a ENC: "
                                        "después, ponerla en APAG apaga el tablero.")
            return False
        if not apag:
            self.armada = True
            self.desde = None
            if self.pedido:
                self.estado["aviso"] = ("Ya se está apagando: esperá a que la pantalla "
                                        "quede negra.")
            elif self.cuenta_desde is not None:
                # volvió a ENC durante la cuenta: se cancela
                self.cuenta_desde = None
                self.estado.update(apagando=False, cuenta=None, aviso="")
            else:
                self.estado["aviso"] = ""
            return False
        if not self.armada or self.pedido:
            return False
        if self.desde is None:
            self.desde = ahora
        if ahora - self.desde < self.segundos:
            return False

        if self.cuenta_desde is None:
            self.cuenta_desde = ahora
            self.estado.update(apagando=True,
                               aviso="Apagando el tablero. Para cancelar, volvé la "
                                     "llave BATERÍA a ENC.")
        falta = self.cuenta - (ahora - self.cuenta_desde)
        if falta > 1e-9:
            self.estado["cuenta"] = int(math.ceil(falta - 1e-9))
            return False

        self.pedido = True
        self.estado.update(cuenta=0,
                           aviso="Apagando el tablero: esperá a que la pantalla quede "
                                 "negra para apagar la zapatilla.")
        try:
            self.al_apagar()
        except Exception as e:
            # para reintentar hay que pasar la llave por ENC
            self.pedido = False
            self.armada = False
            self.cuenta_desde = None
            self.estado.update(apagando=False, cuenta=None, aviso="No se pudo apagar: %s" % e)
        return True

    def run(self):
        while not self._parar.is_set():
            self.paso()
            self._parar.wait(self.cada)

    def detener(self):
        self._parar.set()


def lector_gpio(pin):
    # gpiozero sobre lgpio en la Pi 5; pull-up interno, APAG lo lleva a GND
    try:
        from gpiozero import Button
    except ImportError:
        raise RuntimeError("Falta gpiozero:  sudo apt install -y python3-gpiozero python3-lgpio")
    boton = Button(pin, pull_up=True, bounce_time=None)
    return lambda: boton.is_pressed
