# -*- coding: utf-8 -*-
"""Del valor de ingeniería (psi, kt, RPM, °C) al actuador: calibración con la
tabla de configuracion.TABLERO, inercia de aguja, banda muerta y despacho al
servo, luz o paso a paso, sin saber qué placa hay abajo.
"""

from utiles import aproximar, rampa, interpolar_tabla
from configuracion import (TABLERO, LAZO, MOTOR, LED, ARRANQUE, BARRIDO,
                           factor_servo)
from senales import envolver


class Canal:
    __slots__ = ("id", "senal", "tipo", "cal", "tau", "slew", "factor",
                 "ang", "ang_escrito", "destino", "activo", "nombre", "circular",
                 "cero")

    def __init__(self, d):
        self.id = d["id"]
        self.nombre = d["nombre"]
        self.senal = d["senal"]
        self.tipo = d["actuador"]
        self.cal = d["cal"]
        self.tau = d.get("tau", 0.4)
        self.slew = d.get("slew", 180.0)
        self.destino = d.get("canal")
        self.activo = self.destino is not None
        # La tabla está escrita como si la esfera fuera de 180 grados. Con
        # barrido 270 o 300 da 1 (el resto lo hacen los engranajes); con 120, 0,667
        self.factor = factor_servo(self.id)
        # altímetro de centenas y brújula: 0..360, camino corto
        self.circular = BARRIDO.get(self.id) == "CONT"
        self.ang = self.cal[0][1]
        self.ang_escrito = -9999.0
        # reposo: 0, o el extremo de escala más cerca de 0
        valores = [p[0] for p in self.cal]
        self.cero = min(max(0.0, min(valores)), max(valores))


class MapaTablero:
    def __init__(self, actuadores):
        self.actuadores = actuadores
        self.canales = []
        self.por_id = {}
        self.test_luces = False
        self.reposo = False            # tablero quieto hasta que el profe lo active
        self._t = 0.0
        self._escrituras = 0
        self._omitidas = 0

        for d in TABLERO:
            c = Canal(d)
            self.canales.append(c)
            self.por_id[c.id] = c

        # Banda muerta: en crucero casi nada cambia y el I2C baja a una fracción.
        # 180 grados del servo son unas 410 cuentas del PCA9685
        cuentas = LAZO["banda_muerta"]
        self.banda_deg = max(0.15, 180.0 * cuentas / 410.0)

        self.arranque_grupo = ARRANQUE["canales_por_tanda"]
        self.arranque_paso = ARRANQUE["segundos_entre_tandas"]
        self._encolar_arranque()

    def _encolar_arranque(self):
        # Un servo pide ~700 mA al arrancar: los 22 juntos tiran la fuente y
        # reinician los PCA9685. Por eso se sueltan de a tandas (configuracion.ARRANQUE).
        def peso(c):
            # luces y paso a paso primero (miliamperes), servos después
            return (0 if c.tipo in (LED, MOTOR) else 1,
                    self.canales.index(c))
        self._cola = sorted([c for c in self.canales if c.activo], key=peso)
        self._sueltos = set()
        self._prox_tanda = 0.0

    def _soltar_tanda(self):
        while self._cola and self._t >= self._prox_tanda:
            for _ in range(self.arranque_grupo):
                if not self._cola:
                    break
                self._sueltos.add(id(self._cola.pop(0)))
            self._prox_tanda = self._t + self.arranque_paso

    def actualizar(self, bus, dt):
        self._t += dt
        for c in self.canales:
            valor = c.cero if self.reposo else bus.ver(c.senal, 0.0)

            if c.tipo == LED and self.reposo:
                c.ang = 0.0
                continue
            if c.tipo == LED:
                # La prueba de lámparas existe en la cabina real y nos sirve
                # para revisar el cableado antes de la clase
                c.ang = 1.0 if (self.test_luces or valor >= 0.5) else 0.0
                continue

            # sin inercia la aguja salta de 0 a 180 en un ciclo, con pico de corriente
            objetivo = interpolar_tabla(valor, c.cal)
            if c.circular:
                objetivo = c.ang + envolver(objetivo - c.ang, 360.0)
            suave = aproximar(c.ang, objetivo, dt, c.tau)
            c.ang = rampa(c.ang, suave, dt, c.slew)
            if c.circular:
                c.ang %= 360.0

    def escribir(self):
        actuadores = self.actuadores
        if getattr(actuadores, "reinicio_pendiente", False):
            # una placa se reinició: reescribir todo de a tandas, sin pico
            actuadores.reinicio_pendiente = False
            for c in self.canales:
                c.ang_escrito = -9999.0
            self._encolar_arranque()
        self._soltar_tanda()
        for c in self.canales:
            if not c.activo:
                continue
            if self._cola and id(c) not in self._sueltos:
                continue

            if c.tipo == LED:
                if c.ang != c.ang_escrito:
                    actuadores.escribir_led(c.destino, c.ang >= 0.5)
                    c.ang_escrito = c.ang
                    self._escrituras += 1
                else:
                    self._omitidas += 1
                continue

            # banda muerta sobre el ángulo del actuador, no el de la tabla
            objetivo = c.ang * c.factor
            cambio = objetivo - c.ang_escrito
            if c.circular and c.ang_escrito > -1000.0:
                cambio = envolver(cambio, 360.0)
            if abs(cambio) >= self.banda_deg * c.factor:
                if c.tipo == MOTOR:
                    actuadores.escribir_motor(c.destino, objetivo)
                else:
                    actuadores.escribir_servo(c.destino, objetivo)
                c.ang_escrito = objetivo
                self._escrituras += 1
            else:
                self._omitidas += 1

        actuadores.refrescar()

    def estadisticas(self):
        total = self._escrituras + self._omitidas
        ahorro = 0.0 if total == 0 else 100.0 * self._omitidas / total
        return {"escrituras": self._escrituras,
                "omitidas": self._omitidas,
                "ahorro_pct": round(ahorro, 1)}

    def angulos(self):
        d = {}
        for c in self.canales:
            d[c.id] = round(c.ang, 2)
        return d

    def soltar_todo(self):
        for c in self.canales:
            if not c.activo:
                continue
            if c.tipo == LED:
                self.actuadores.escribir_led(c.destino, False)
            elif c.tipo != MOTOR:
                self.actuadores.soltar(c.destino)
            c.ang_escrito = -9999.0
        self._encolar_arranque()
        self.actuadores.refrescar()

    def apagar(self):
        for c in self.canales:
            if not c.activo:
                continue
            if c.tipo == LED:
                self.actuadores.escribir_led(c.destino, False)
            c.ang_escrito = -9999.0
        self._encolar_arranque()       # al reanudar también va de a tandas
        self.actuadores.refrescar()
