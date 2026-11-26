# -*- coding: utf-8 -*-
"""Interfaz de salida: el núcleo solo conoce estos métodos, así corre igual
sin hardware (actuadores_simulados) o con los servos (actuadores_pca9685).

Destinos: tuplas (placa, canal), por ej. ("PCA0", 7) o ("MOTOR", 1) para la brújula.
"""


class ActuadoresBase:

    def escribir_servo(self, destino, angulo_deg):
        # angulo_deg en [0, 180]
        raise NotImplementedError

    def escribir_motor(self, destino, angulo_deg):
        """Grados de aguja sin tope: el 28BYJ-48 da vueltas enteras, 370 = 10."""
        raise NotImplementedError

    def escribir_led(self, destino, encendido):
        raise NotImplementedError

    def soltar(self, destino):
        # saca el pulso: el servo deja de hacer fuerza
        pass

    def refrescar(self):
        pass

    def cerrar(self):
        pass

    def descripcion(self):
        return self.__class__.__name__
