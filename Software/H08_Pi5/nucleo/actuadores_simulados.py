# -*- coding: utf-8 -*-
"""Salida sin hardware: guarda el último valor de cada canal.

La usamos para correr el tablero en la compu, revisar la calibración antes de
conectar servos y en las pruebas automáticas.
"""

from actuadores_base import ActuadoresBase


class ActuadoresSimulados(ActuadoresBase):

    def __init__(self, verboso=False):
        self.valores = {}
        self.verboso = verboso

    def _clave(self, destino):
        return "%s:%d" % (destino[0], destino[1])

    def escribir_servo(self, destino, angulo_deg):
        self.valores[self._clave(destino)] = round(angulo_deg, 2)
        if self.verboso:
            print("SERVO %s -> %.1f grados" % (self._clave(destino), angulo_deg))

    def escribir_motor(self, destino, angulo_deg):
        self.valores[self._clave(destino)] = round(angulo_deg, 2)

    def escribir_led(self, destino, encendido):
        self.valores[self._clave(destino)] = 1 if encendido else 0
        if self.verboso:
            print("LUZ   %s -> %s" % (self._clave(destino),
                                      "encendida" if encendido else "apagada"))

    def refrescar(self):
        return 0

    def descripcion(self):
        return "simulada, sin hardware"
