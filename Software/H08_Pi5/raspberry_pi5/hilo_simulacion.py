# -*- coding: utf-8 -*-
"""Simulación y placas PCA9685 en su propio hilo, a 20 Hz.

El servidor web solo le manda órdenes por una cola y lee la última foto del
estado, que se reemplaza entera de una vez (asignar una referencia es atómico).
Si una vuelta falla, se cuenta el error y el lazo sigue, para que el tablero
no se congele delante del público.
"""

import queue
import threading
import time
import traceback

from simulador import Simulador
from configuracion import LAZO


class HiloSimulacion(threading.Thread):

    def __init__(self, actuadores, semilla=None):
        threading.Thread.__init__(self, daemon=True, name="simulacion")
        self.sim = Simulador(actuadores, semilla=semilla)
        self.actuadores = actuadores
        self.cola = queue.Queue()
        self.foto = self.sim.estado()
        self.catalogo = self.sim.catalogo_estatico()
        self.errores = 0
        self.ultimo_error = ""
        self._parar = threading.Event()
        # lo mira la vigilancia de tablero_pi5.py para saber si el lazo sigue vivo
        self.latido = time.monotonic()
        # llave BATERÍA, si hay; su estado va en la foto para que la página
        # muestre el aviso
        self.llave = None
        self._periodo_foto = 1.0 / LAZO["hz_telemetria"]

    # para el servidor web
    def ordenar(self, accion, valor=None):
        self.cola.put((accion, valor))

    def detener(self):
        self._parar.set()

    def run(self):
        sim = self.sim
        # Arranca en reposo: sin pulso en los servos hasta que el profesor
        # toca "Activar tablero".
        sim.entrar_en_reposo(inmediato=True)
        t_foto = time.monotonic()

        while not self._parar.is_set():
            self.latido = time.monotonic()
            try:
                while True:
                    try:
                        accion, valor = self.cola.get_nowait()
                    except queue.Empty:
                        break
                    self._ejecutar(accion, valor)

                # pasos fijos de 50 ms según el tiempo real que pasó
                sim.servicio()

                ahora = time.monotonic()
                if ahora - t_foto >= self._periodo_foto:
                    t_foto = ahora
                    foto = sim.estado()
                    foto["hardware"] = self._salud()
                    if self.llave is not None:
                        foto["llave"] = dict(self.llave.estado)
                    self.foto = foto
            except Exception as e:
                self.errores += 1
                self.ultimo_error = "%s: %s" % (type(e).__name__, e)
                if self.errores <= 3 or self.errores % 100 == 0:
                    print("[simulación] error %d:" % self.errores)
                    traceback.print_exc()
                time.sleep(0.2)
            time.sleep(0.005)

        # apagado en orden: luces, servos sin pulso, motores a cero
        try:
            sim.mapa.apagar()
        except Exception:
            pass
        try:
            self.actuadores.cerrar()
        except Exception:
            traceback.print_exc()

    def _salud(self):
        d = {"errores_programa": self.errores, "ultimo_error": self.ultimo_error}
        salud = getattr(self.actuadores, "salud", None)
        if salud:
            d.update(salud())
        return d

    # órdenes que no tienen sentido con el tablero quieto: se ignoran con un aviso
    _SOLO_ACTIVO = ("modo_normal", "modo_escenario", "modo_falla", "activar_falla",
                    "quitar_falla", "pausa", "velocidad", "prueba_luces",
                    "piloto_reactivo")

    def _ejecutar(self, accion, valor):
        sim = self.sim
        if accion == "activar":
            sim.activar()
            return
        if accion in self._SOLO_ACTIVO and sim.en_reposo:
            sim._msg("El tablero está en reposo: primero “Activar tablero”.")
            return
        if accion == "modo_normal":
            sim.modo_normal(desde_fase=valor)
        elif accion == "modo_escenario":
            sim.modo_escenario(valor)
        elif accion == "modo_falla":
            sim.modo_falla(valor)
        elif accion == "detener":
            sim.entrar_en_reposo()
        elif accion == "activar_falla":
            sim.activar_falla(valor)
        elif accion == "quitar_falla":
            sim.quitar_falla(valor)
        elif accion == "pausa":
            sim.pausado = bool(valor)
        elif accion == "velocidad":
            try:
                sim.velocidad = max(0.25, min(float(valor), 8.0))
            except (TypeError, ValueError):
                pass
        elif accion == "prueba_luces":
            sim.prueba_luces(bool(valor))
        elif accion == "piloto_reactivo":
            sim.fijar_piloto_reactivo(bool(valor))
        elif accion == "ciclar":
            sim.ciclar = bool(valor)
