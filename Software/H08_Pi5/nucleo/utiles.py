# -*- coding: utf-8 -*-
"""Reloj, azar reproducible y la matemática que usa todo el núcleo
(filtro de primer orden, rampa e interpolación de las tablas de calibración).
"""

import time as _t

# monotónico y no la hora del sistema: si la Pi corrige la hora en marcha,
# la simulación no salta
_T0 = _t.monotonic()


def ticks_ms():
    return int((_t.monotonic() - _T0) * 1000)


def ticks_diff(a, b):
    return a - b


# Congruencial de 32 bits. Misma semilla, mismo vuelo con las mismas
# vibraciones: la demo sale igual frente al curso y las pruebas comparan exacto.
class Aleatorio:
    __slots__ = ("_s",)

    def __init__(self, semilla=20250819):
        self._s = semilla & 0xFFFFFFFF

    def sembrar(self, semilla):
        self._s = semilla & 0xFFFFFFFF

    def _siguiente(self):
        # constantes de Numerical Recipes
        self._s = (1664525 * self._s + 1013904223) & 0xFFFFFFFF
        return self._s

    def uniforme(self):
        # [0, 1)
        return self._siguiente() / 4294967296.0

    def simetrico(self):
        # [-1, 1)
        return self.uniforme() * 2.0 - 1.0


RNG = Aleatorio()


def limitar(x, minimo, maximo):
    if x < minimo:
        return minimo
    if x > maximo:
        return maximo
    return x


def mezclar(a, b, k):
    return a + (b - a) * k


def aproximar(actual, objetivo, dt, tau):
    """Pasabajos de primer orden con constante tau en segundos.

    tau chico para presión de aceite o RPM, grande para temperaturas. La forma
    dt/(tau+dt) sigue estable aunque dt se agrande.
    """
    if tau <= 0.0:
        return objetivo
    k = dt / (tau + dt)
    return actual + (objetivo - actual) * k


def rampa(actual, objetivo, dt, velocidad):
    """Avanza a velocidad constante (unidades/s) hacia el objetivo."""
    # un servo que cruza la esfera de golpe castiga el engranaje y puede soltar la aguja
    paso = velocidad * dt
    d = objetivo - actual
    if d > paso:
        return actual + paso
    if d < -paso:
        return actual - paso
    return objetivo


def interpolar_tabla(x, tabla):
    """Interpolación lineal a trozos sobre [(x0, y0), (x1, y1), ...], ordenada en x.

    Las esferas no son lineales (velocímetro, aforadores, Bourdon), así que
    medimos dónde cae cada marca y la cargamos en configuracion.py.
    """
    n = len(tabla)
    if n == 0:
        return 0.0
    if x <= tabla[0][0]:
        return tabla[0][1]
    if x >= tabla[n - 1][0]:
        return tabla[n - 1][1]
    # lineal alcanza: las tablas tienen de 3 a 13 puntos
    i = 1
    while i < n and tabla[i][0] < x:
        i += 1
    x0, y0 = tabla[i - 1]
    x1, y1 = tabla[i]
    dx = x1 - x0
    if dx == 0.0:
        return y1
    return y0 + (y1 - y0) * (x - x0) / dx
