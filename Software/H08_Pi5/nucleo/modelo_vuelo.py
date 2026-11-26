# -*- coding: utf-8 -*-
"""Modelo físico del H-19A y piloto virtual.

Cuasi-estático con retardos: cada magnitud calcula su objetivo y lo persigue
con su tau. Seis grados de libertad sería caro y no hace falta para mover agujas.
La única ecuación que se integra de verdad es la del rotor (ver _paso_rotor).
"""

from utiles import limitar, aproximar, mezclar, rampa
from configuracion import LIM

MAG_OFF = 0
MAG_L = 1
MAG_R = 2
MAG_BOTH = 3

TANQUE_FWD = 0
TANQUE_AFT = 1
TANQUE_AMBOS = 2


class Controles:
    # los escribe el piloto virtual o un escenario

    def __init__(self):
        self.colectivo = 0.0        # 0..1
        self.throttle = 0.0         # 0..1 (correlado al colectivo en vuelo)
        self.ciclico_lon = 0.0      # -1..1 (adelante = negativo = picar)
        self.ciclico_lat = 0.0      # -1..1
        self.pedal = 0.0            # -1..1
        self.calefaccion_carb = 0.0  # 0..1
        self.mezcla = 1.0           # 0..1 (1 = rica)

        self.bateria = False
        self.generador = False
        self.magnetos = MAG_OFF
        self.arrancador = False
        self.bomba_combustible = False
        self.embrague = False        # embrague principal acoplado
        self.selector_tanque = TANQUE_AMBOS
        self.luces_tablero = 0.0     # 0..1


class SaludSistemas:
    """Salud de cada sistema, de 0.0 (roto) a 1.0.

    La escribe el motor de fallas y el modelo solo la lee: no se truca ninguna aguja.
    """

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.motor = 1.0            # potencia disponible
        self.magneto_l = 1.0
        self.magneto_r = 1.0
        self.bomba_aceite = 1.0
        self.refrigeracion = 1.0    # de culata (deflectores, ventilador)
        # el aceite tiene su propio radiador: con una sola salud, enfriador tapado y
        # deflectores daban el mismo tablero y no se distinguían
        self.refrigeracion_aceite = 1.0
        self.carburador = 1.0       # 1.0 = limpio, 0.0 = obstruido por hielo
        self.bomba_combustible = 1.0
        self.fuga_combustible_lph = 0.0
        self.transmision_bomba = 1.0
        self.transmision_refrig = 1.0
        self.rotor_cola = 1.0
        self.generador = 1.0
        self.bateria = 1.0
        self.embrague = 1.0         # <1.0 = patina
        self.vacio_giro = 1.0       # giróscopos
        self.estatica = 1.0


class ModeloVuelo:

    K_INERCIA_ROTOR = 850.0     # rigidez de la ecuación del rotor
    K_VERT = 900.0              # ft/min de aceleración vertical por unidad de empuje
    TAU_IAS = 6.0               # inercia longitudinal del helicóptero
    # Calibrado para descender ~1500 ft/min como el S-55 real. Más alto, planeaba
    # a 500 y le daba al alumno una idea peligrosamente optimista del tiempo que tiene
    K_AUTOROT = 0.145

    def __init__(self):
        self.ctl = Controles()
        self.salud = SaludSistemas()
        self.reiniciar()

    def reiniciar(self, en_frio=True):
        self.t = 0.0
        self.salud.reiniciar()

        # la exterior es el piso de todas las demás temperaturas
        self.oat_c = LIM["oat_c"]
        self.qnh_hpa = LIM["qnh_hpa"]
        self.humedad = 0.45          # 0..1 - alimenta el riesgo de engelamiento

        self.n_eng_rpm = 0.0
        self.n_rot_rpm = 0.0
        self.map_inhg = LIM["map_ambiente"]
        self.pot_requerida = 0.0     # 0..1.2  carga del rotor
        self.pot_entregada = 0.0     # 0..1.2  potencia del motor
        self.acoplado = False        # rueda libre transmitiendo motor -> rotor

        self.oil_p_psi = 0.0
        self.oil_t_c = self.oat_c
        self.cht_c = self.oat_c
        self.cat_c = self.oat_c
        self.fuel_p_psi = 0.0
        self.fuel_fwd_l = LIM["cap_fwd"]
        self.fuel_aft_l = LIM["cap_aft"]
        self.flujo_lph = 0.0
        self.hielo_carb = 0.0        # 0..1 acumulación de hielo

        self.xmsn_p_psi = 0.0
        self.xmsn_t_c = self.oat_c

        # En el H-19 horizonte y rumbo son eléctricos, por el inversor desde la barra.
        # 0 = detenido, 1 = a régimen
        self.giro_att = 0.0         # régimen del giro del horizonte
        self.giro_dg = 0.0          # régimen del giro de rumbo
        self.deriva_dg_deg = 0.0    # error acumulado del indicador de rumbo
        self.deriva_att_deg = 0.0   # error acumulado del horizonte artificial

        # None = toma despejada
        self.alt_estatica_ft = None

        self.bus_v = 0.0
        self.amp_a = 0.0
        self.bateria_ah_max = 34.0   # capacidad típica de batería de plomo 24 V
        self.bateria_ah = 34.0
        self.gen_en_linea = False
        self.motor_vivo = False
        self.arranque_activo = False
        self.empuje = 0.0

        self.alt_ft = 0.0
        self.alt_terreno_ft = 0.0
        self.ias_kt = 0.0
        self.vs_fpm = 0.0
        self.hdg_deg = 90.0
        self.pitch_deg = 0.0
        self.roll_deg = 0.0
        self.turn_rate_dps = 0.0
        self.slip = 0.0
        self.cdi = 0.0
        self.en_tierra = True

        if not en_frio:
            self._precalentar()

    def _precalentar(self):
        """Arranque en caliente, listo para volar."""
        # Se reponen todos los mandos: viven fuera de reiniciar(). Si se venía
        # del corte (mezcla 0, magnetos OFF) el motor no volvía a arrancar
        self.ctl.bateria = True
        self.ctl.generador = True
        self.ctl.magnetos = MAG_BOTH
        self.ctl.arrancador = False
        self.ctl.bomba_combustible = True
        self.ctl.embrague = True
        self.ctl.mezcla = 1.0
        self.ctl.calefaccion_carb = 0.0
        self.ctl.selector_tanque = TANQUE_AMBOS
        self.ctl.luces_tablero = 0.7
        self.ctl.pedal = 0.0
        self.ctl.ciclico_lat = 0.0
        self.ctl.throttle = 0.48
        self.ctl.colectivo = 0.552
        self.n_eng_rpm = LIM["rpm_motor_crucero"]
        self.n_rot_rpm = LIM["rpm_rotor_nom"]
        self.map_inhg = LIM["map_crucero"]
        self.cat_c = self.oat_c - 18.0 * (1.0 - 0.72 * 0.48)
        self.fuel_p_psi = LIM["fuel_p_nom"]
        self.acoplado = True
        self.oil_p_psi = LIM["oil_p_nom"]
        self.oil_t_c = LIM["oil_t_nom"]
        self.cht_c = LIM["cht_nom"]
        self.xmsn_p_psi = LIM["xmsn_p_nom"]
        self.xmsn_t_c = LIM["xmsn_t_nom"]
        self.bus_v = LIM["bus_generador"]
        self.gen_en_linea = True
        self.giro_att = 1.0
        self.giro_dg = 1.0
        self.deriva_dg_deg = 0.0
        self.deriva_att_deg = 0.0
        self.alt_estatica_ft = None
        self.en_tierra = False

    def paso(self, dt):
        self.t += dt
        self._paso_aire(dt)
        self._paso_electrico(dt)
        self._paso_motor(dt)
        self._paso_rotor(dt)
        self._paso_fluidos(dt)
        self._paso_transmision(dt)
        self._paso_combustible(dt)
        self._paso_vuelo(dt)

    def _paso_aire(self, dt):
        # ISA: 15 °C al nivel del mar, -1,98 °C cada 1000 ft. Todas las temperaturas
        # del motor parten de acá
        del dt
        self.oat_c = LIM["oat_c"] - 1.98 * (self.alt_ft / 1000.0)

    def _paso_electrico(self, dt):
        s = self.salud
        if not self.ctl.bateria:
            self.bus_v = aproximar(self.bus_v, 0.0, dt, 0.25)
            self.amp_a = aproximar(self.amp_a, 0.0, dt, 0.3)
            self.gen_en_linea = False
            return

        # el generador entra recién con el motor girando con fuerza
        quiere_gen = (self.ctl.generador and s.generador > 0.25
                      and self.n_eng_rpm > 1200.0)
        self.gen_en_linea = quiere_gen

        consumo_a = 18.0                       # instrumentos, radios, luces
        consumo_a += 12.0 * self.ctl.luces_tablero
        if self.ctl.arrancador:
            # cientos de amperes: el amperímetro va al tope de descarga y la barra se cae
            consumo_a += 180.0

        if quiere_gen:
            v_obj = LIM["bus_generador"] * mezclar(0.8, 1.0, s.generador)
            # corriente de carga: alta si la batería está baja, decae al llenarse
            deficit = limitar((self.bateria_ah_max - self.bateria_ah)
                              / self.bateria_ah_max, 0.0, 1.0)
            carga = LIM["amp_carga_max"] * deficit
            self.amp_a = aproximar(self.amp_a, consumo_a + carga, dt, 0.8)
            # acelerado con factor_bateria para que se vea en clase
            self.bateria_ah = limitar(self.bateria_ah + carga * dt / 3600.0 * LIM["factor_bateria"],
                                      0.0, self.bateria_ah_max)
        else:
            carga_rel = limitar(self.bateria_ah / self.bateria_ah_max, 0.0, 1.0)
            v_obj = LIM["bus_bateria"] * (0.72 + 0.28 * carga_rel) * s.bateria
            # resistencia interna: con 20 A ni se nota, con los ~200 A del arrancador la
            # barra cae a 18-20 V y el tablero se apaga a medias
            v_obj -= 0.021 * consumo_a * (2.0 - carga_rel)
            v_obj = max(v_obj, 0.0)
            self.amp_a = aproximar(self.amp_a, -consumo_a, dt, 0.8)
            self.bateria_ah = limitar(self.bateria_ah - consumo_a * dt / 3600.0 * LIM["factor_bateria"],
                                      0.0, self.bateria_ah_max)

        self.bus_v = aproximar(self.bus_v, v_obj, dt, 0.35)
        self._paso_giroscopos(dt)
        self._paso_pitot_estatica()

    def _paso_pitot_estatica(self):
        # se anota la altura al taparse y el error del velocímetro sale solo (ias_ind_kt)
        if self.salud.estatica < 0.5:
            if self.alt_estatica_ft is None:
                self.alt_estatica_ft = self.alt_ft
        else:
            self.alt_estatica_ft = None

    def _paso_giroscopos(self, dt):
        s = self.salud
        # el inversor no alcanza con menos de 20 V
        alimentado = self.bus_v >= LIM["bus_min_util"]

        # erigirse lleva cerca de un minuto; caer, varios, porque sigue por inercia
        obj_att = 1.0 if alimentado else 0.0
        obj_dg = 1.0 if alimentado else 0.0
        tau_att = 22.0 if alimentado else 70.0
        tau_dg = 28.0 if alimentado else 90.0
        self.giro_att = aproximar(self.giro_att, obj_att * s.vacio_giro, dt, tau_att)
        self.giro_dg = aproximar(self.giro_dg, obj_dg * s.vacio_giro, dt, tau_dg)

        # sano, el de rumbo se corrige solo (esclavizado a la válvula de flujo)
        if self.giro_dg > 0.97:
            self.deriva_dg_deg = aproximar(self.deriva_dg_deg, 0.0, dt, 25.0)
        else:
            self.deriva_dg_deg += (1.0 - self.giro_dg) * 2.6 * dt

        # El horizonte que se cae no se congela: se vuelca despacio y muestra una
        # actitud que no existe, sin avisar. Por eso es tan peligrosa la falla eléctrica
        # volando por instrumentos
        if self.giro_att > 0.97:
            self.deriva_att_deg = aproximar(self.deriva_att_deg, 0.0, dt, 20.0)
        else:
            self.deriva_att_deg += (1.0 - self.giro_att) * 1.9 * dt
            self.deriva_att_deg = limitar(self.deriva_att_deg, -30.0, 30.0)

    @property
    def pitch_ind_deg(self):
        return self.pitch_deg * self.giro_att + 0.55 * self.deriva_att_deg

    @property
    def roll_ind_deg(self):
        return self.roll_deg * self.giro_att + self.deriva_att_deg

    @property
    def hdg_giro_deg(self):
        return (self.hdg_deg + self.deriva_dg_deg) % 360.0

    # Estática tapada: queda encerrada la presión de esa altura. Nivelado no hay
    # error, subiendo indica de menos y bajando de más. Lo peligroso es el ascenso:
    # parece que vas lento y bajás la nariz
    @property
    def ias_ind_kt(self):
        if self.alt_estatica_ft is None:
            return self.ias_kt
        # ~1 kt cada 100 ft, a velocidad de crucero
        d_ft = self.alt_ft - self.alt_estatica_ft
        return max(0.0, self.ias_kt - d_ft * 0.010 * limitar(
            self.ias_kt / 74.0, 0.25, 1.5))

    @property
    def energia_ok(self):
        return self.bus_v >= LIM["bus_min_util"]

    def _paso_motor(self, dt):
        s = self.salud
        ctl = self.ctl

        # Con un magneto pierde ~11 % de potencia. El manual da 50-100 RPM de caída:
        # como el rotor pide potencia con el cubo de la velocidad, 11 % de potencia
        # son ~4 % de RPM, las 80-90 que se miden en el run-up
        n_mag = 0
        if ctl.magnetos in (MAG_L, MAG_BOTH) and s.magneto_l > 0.5:
            n_mag += 1
        if ctl.magnetos in (MAG_R, MAG_BOTH) and s.magneto_r > 0.5:
            n_mag += 1
        if n_mag == 0:
            factor_mag = 0.0
        elif n_mag == 1:
            factor_mag = 0.89
        else:
            factor_mag = 1.0
        # para la culata: con una bujía la combustión termina más tarde
        self.n_magnetos = n_mag

        hay_combustible = self._combustible_disponible() > 0.5
        presion_ok = self.fuel_p_psi > 4.0 or self.n_eng_rpm < 300.0

        # Con poca presión el motor no se para de golpe: se queda sin fuerza y anda
        # áspero, primero a alta potencia. Fuera del verde es aviso, no emergencia
        if self.n_eng_rpm > 300.0 and self.fuel_p_psi < LIM["fuel_p_min"]:
            factor_fuel = limitar(
                (self.fuel_p_psi - 3.0) / (LIM["fuel_p_min"] - 3.0), 0.0, 1.0)
            factor_fuel = 0.30 + 0.70 * factor_fuel
        else:
            factor_fuel = 1.0

        self._paso_hielo_carburador(dt)
        factor_carb = s.carburador * (1.0 - 0.85 * self.hielo_carb)

        # absoluta: parado marca ~29,9 y al arrancar baja a ~13. Es lo primero raro
        # que ve el alumno y lo que le hace entender qué mide
        perdida_alt = self.alt_ft * 0.001        # ~1 inHg por cada 1000 ft
        map_ambiente = LIM["map_ambiente"] - perdida_alt
        if self.n_eng_rpm < 200.0:
            map_obj = map_ambiente
        else:
            map_obj = mezclar(LIM["map_ralenti"], LIM["map_despegue"], ctl.throttle)
            map_obj -= perdida_alt
            # el hielo baja la MAP sin tocar la mariposa: así se delata
            map_obj *= mezclar(0.35, 1.0, factor_carb)
            # aire caliente, menos denso: 1 a 2 inHg menos aunque no haya hielo
            map_obj -= 1.8 * ctl.calefaccion_carb
            map_obj = limitar(map_obj, LIM["map_min"], LIM["map_max"])
        self.map_inhg = aproximar(self.map_inhg, map_obj, dt, 0.25)

        # 1.0 = potencia continua máxima (550 HP)
        rel_map = limitar((self.map_inhg - LIM["map_ralenti"]) /
                          (LIM["map_despegue"] - LIM["map_ralenti"]), 0.0, 1.2)
        # por debajo de 200 RPM no se sostiene solo, hay que arrastrarlo
        motor_vivo = (factor_mag > 0.0 and hay_combustible and presion_ok
                      and s.motor > 0.02 and ctl.mezcla > 0.15
                      and self.n_eng_rpm > 200.0)

        if motor_vivo:
            # A mariposa fija la potencia sube con las RPM hasta ~900 y se aplana. Con la
            # fricción que crece con RPM^2 da un equilibrio estable; sin esto se embalaba
            factor_rpm = limitar(self.n_eng_rpm / 900.0, 0.0, 1.0)
            self.pot_entregada = (rel_map * factor_mag * s.motor * ctl.mezcla
                                  * factor_rpm * factor_fuel)
            # detonación pasado cht_max: pierde fuerza y así la culata deja de subir.
            # Sin esto la temperatura crecía sin freno
            if self.cht_c > LIM["cht_max"]:
                castigo = limitar((self.cht_c - LIM["cht_max"]) / 60.0, 0.0, 1.0)
                self.pot_entregada *= mezclar(1.0, 0.55, castigo)
        else:
            self.pot_entregada = 0.0

        # rotor (solo acoplado) + accesorios + fricción con RPM^2
        carga = (self.pot_requerida if self.acoplado else 0.04)
        carga += 0.04 + 0.14 * (self.n_eng_rpm / 2200.0) ** 2

        # Se desengrana solo arriba de 900 RPM. Sigue andando con la barra en 18 V,
        # como en la realidad; recién a 15 V deja de dar
        self.arranque_activo = (ctl.arrancador and self.bus_v > 15.0
                                and self.n_eng_rpm < 900.0)
        # motor serie: el equilibrio queda en ~230 RPM, el arrastre real del R-1340.
        # Primero arrastra y la aguja sube despacio, después prende
        if self.arranque_activo:
            p_arrancador = 0.055 + 0.30 * limitar(1.0 - self.n_eng_rpm / 250.0, 0.0, 1.0)
        else:
            p_arrancador = 0.0

        # No hay tabla mariposa-RPM: salen del balance de par. Por eso la MAP de
        # crucero da la que corresponde, y subir colectivo solo ya frena el rotor
        if motor_vivo or self.arranque_activo:
            exceso = self.pot_entregada + p_arrancador - carga
            rpm_obj = self.n_eng_rpm + exceso * 1800.0
            rpm_obj = limitar(rpm_obj, 0.0, LIM["rpm_motor_max"] + 200.0)
            self.n_eng_rpm = aproximar(self.n_eng_rpm, rpm_obj, dt, 0.9)
        else:
            if self.acoplado and self.n_rot_rpm > 20.0:
                self.n_eng_rpm = aproximar(self.n_eng_rpm,
                                           self.n_rot_rpm * LIM["reduccion"] * 0.15,
                                           dt, 2.5)
            else:
                self.n_eng_rpm = aproximar(self.n_eng_rpm, 0.0, dt, 3.5)

        self.n_eng_rpm = limitar(self.n_eng_rpm, 0.0, 3200.0)
        self.motor_vivo = motor_vivo

    def _paso_hielo_carburador(self, dt):
        # La falla clásica del R-1340: el venturi enfría el aire ~15 C y, en la
        # banda de riesgo y con humedad, el hielo estrangula la admisión.
        # La depresión es máxima con la mariposa casi cerrada: el hielo es cosa de
        # descenso y aproximación, no de despegue. Sin motor girando no hay venturi y
        # el termómetro lee la exterior
        aspirando = limitar(self.n_eng_rpm / 400.0, 0.0, 1.0)
        caida_venturi = 18.0 * (1.0 - 0.72 * self.ctl.throttle) * aspirando
        self.cat_c = aproximar(
            self.cat_c,
            self.oat_c - caida_venturi + 55.0 * self.ctl.calefaccion_carb,
            dt, 1.2)

        rel_baja_pot = 0.4 + 1.2 * (1.0 - self.ctl.throttle)
        en_banda = (LIM["cat_hielo_min"] <= self.cat_c <= LIM["cat_hielo_max"])
        if en_banda and self.humedad > 0.55 and self.n_eng_rpm > 500.0:
            self.hielo_carb = limitar(
                self.hielo_carb + (self.humedad - 0.5) * 0.020 * rel_baja_pot * dt,
                0.0, 1.0)
        else:
            # con calefacción se derrite rápido, sin ella lentísimo
            k = 0.12 if self.ctl.calefaccion_carb > 0.5 else 0.012
            self.hielo_carb = limitar(self.hielo_carb - k * dt, 0.0, 1.0)

    def _paso_rotor(self, dt):
        ctl = self.ctl
        s = self.salud

        # Curva en U: inducida (grande en estacionario), perfil casi fija y parásita
        # con V^3. El mínimo en 45-55 kt es la mejor velocidad de autorrotación
        v = self.ias_kt
        induc = 0.47 * (1.0 - limitar(v / 50.0, 0.0, 1.0)) ** 2
        parasita = 0.31 * (v / 95.0) ** 3
        perfil = 0.24
        req = perfil + induc + parasita
        req *= (0.35 + 1.05 * ctl.colectivo)
        req *= (1.0 + self.alt_ft / 22000.0)          # menos densidad, más potencia
        # arrastre de palas con RPM^2: a régimen vale 1, pero fuera de banda deja
        # que el rotor encuentre equilibrio en vez de caer a cero de golpe
        rel_rot = limitar(self.n_rot_rpm / LIM["rpm_rotor_nom"], 0.0, 1.25)
        req *= mezclar(0.30, 1.0, rel_rot * rel_rot)
        self.pot_requerida = limitar(req, 0.0, 1.6)

        # el rotor nunca arrastra al motor: si va más rápido que motor/10, desacopla
        # (autorrotación y needle split)
        n_rot_motor = self.n_eng_rpm / LIM["reduccion"]
        # histéresis: sin esto oscilaba en crucero y arrastraba todo lo demás
        margen = 2.5 if self.acoplado else -0.4
        self.acoplado = bool(ctl.embrague and s.embrague > 0.1
                             and self.motor_vivo
                             and n_rot_motor >= self.n_rot_rpm - margen)

        # Embrague gastado: tiene un techo de par, arriba de eso patina. El rotor baja
        # hasta igualar y las dos agujas quedan separadas estables
        if self.acoplado:
            p_in = min(self.pot_entregada, s.embrague * 1.25)
        else:
            p_in = 0.0

        if not self.acoplado and self.vs_fpm < 0.0:
            p_in += self.K_AUTOROT * limitar(-self.vs_fpm / 1800.0, 0.0, 1.2)

        # dOmega/dt = (P_in - P_req) / (I * Omega)
        # De acá salen solos la caída de RPM por exceso de colectivo, el needle split y
        # que en autorrotación bajar colectivo haga subir las RPM
        omega = max(self.n_rot_rpm, 12.0)
        d_omega = (p_in - self.pot_requerida) * self.K_INERCIA_ROTOR / omega
        # un rotor de 16 m no cambia de régimen de golpe
        d_omega = limitar(d_omega, -55.0, 45.0)
        self.n_rot_rpm = limitar(self.n_rot_rpm + d_omega * dt, 0.0, 300.0)

        # Sano, el embrague impone 10:1 y las agujas van superpuestas. Gastado, el
        # rotor se atrasa con el motor andando: distinto del needle split, donde cae
        # la de motor. Por eso el H-19 tiene las dos agujas en una esfera
        if self.acoplado and s.embrague >= 0.98 and self.n_rot_rpm < n_rot_motor:
            self.n_rot_rpm = aproximar(self.n_rot_rpm, n_rot_motor, dt, 0.5)

        if not ctl.embrague:
            self.n_rot_rpm = aproximar(self.n_rot_rpm, 0.0, dt, 25.0)

    def _paso_fluidos(self, dt):
        s = self.salud
        rel_rpm = self.n_eng_rpm / LIM["rpm_motor_crucero"]

        # Bomba de engranajes: depende del régimen y de la viscosidad. Frío va al tope y
        # baja solo al calentarse. Regla del radial: si a los 30 s no se movió, se corta
        if self.n_eng_rpm < 100.0:
            p_obj = 0.0
        else:
            # caliente y fluido se escurre y baja: una sobretemperatura también se ve acá
            viscosidad = 1.0 + 1.05 * limitar((45.0 - self.oil_t_c) / 45.0, 0.0, 1.0)
            viscosidad -= 0.45 * limitar(
                (self.oil_t_c - LIM["oil_t_max"]) / 35.0, 0.0, 1.0)
            p_obj = LIM["oil_p_nom"] * (limitar(rel_rpm, 0.0, 1.3) ** 1.15)
            p_obj *= s.bomba_aceite * viscosidad
            # válvula de alivio
            p_obj = limitar(p_obj, 0.0, LIM["oil_p_max"] * 1.02)
        self.oil_p_psi = aproximar(self.oil_p_psi, p_obj, dt, 0.55)

        # El H-19 tiene ventilador movido por el motor, pero en estacionario largo igual
        # se recalienta. Exponente 0,42: la culata sube mucho más lento que la potencia
        flujo_ias = limitar(self.ias_kt / 70.0, 0.0, 1.0)
        pot = limitar(self.pot_entregada, 0.0, 1.4)
        vivo = limitar(self.n_eng_rpm / 700.0, 0.0, 1.0)

        cht_obj = self.oat_c + vivo * (245.0 * (pot ** 0.42) + 25.0 * (1.0 - flujo_ias))
        # un magneto: ~15 C más de culata, por eso la prueba de magnetos es corta
        if self.n_magnetos == 1:
            cht_obj += 15.0 * vivo
        if s.refrigeracion < 1.0:
            cht_obj = self.oat_c + (cht_obj - self.oat_c) / max(s.refrigeracion, 0.20)
        # techo en el fondo de escala: sin esto daba 500-600 C, que no existen
        cht_obj = limitar(cht_obj, self.oat_c, LIM["cht_escala"])
        self.cht_c = aproximar(self.cht_c, cht_obj, dt, 55.0)

        # el aceite sigue a la culata, más bajo y con mucho retardo: es la última
        # aguja en moverse y en volver
        oil_obj = self.oat_c + 0.28 * (self.cht_c - self.oat_c)
        if s.refrigeracion_aceite < 1.0:
            oil_obj = self.oat_c + (oil_obj - self.oat_c) / max(
                s.refrigeracion_aceite, 0.25)
        oil_obj = limitar(oil_obj, self.oat_c, LIM["oil_t_escala"])
        self.oil_t_c = aproximar(self.oil_t_c, oil_obj, dt, 95.0)

        # La bomba eléctrica sigue a la barra; sin ella queda la mecánica, que
        # necesita motor girando
        rel_bus = limitar((self.bus_v - 14.0) / (LIM["bus_min_util"] - 14.0), 0.0, 1.0)
        if self.ctl.bomba_combustible and rel_bus > 0.05:
            base = LIM["fuel_p_nom"] * mezclar(0.60, 1.0, rel_bus)
        else:
            base = LIM["fuel_p_nom"] * 0.55 * limitar(rel_rpm, 0.0, 1.0)
        if self._combustible_disponible() <= 0.5:
            base = 0.0
        self.fuel_p_psi = aproximar(self.fuel_p_psi,
                                    base * s.bomba_combustible, dt, 0.45)

    def _paso_transmision(self, dt):
        s = self.salud
        rel = self.n_rot_rpm / LIM["rpm_rotor_nom"]
        p_obj = LIM["xmsn_p_nom"] * (limitar(rel, 0.0, 1.3) ** 0.8) * s.transmision_bomba
        self.xmsn_p_psi = aproximar(self.xmsn_p_psi, p_obj, dt, 0.7)

        flujo_ias = limitar(self.ias_kt / 70.0, 0.0, 1.0)
        pot = limitar(self.pot_requerida, 0.0, 1.5)
        girando = limitar(self.n_rot_rpm / 120.0, 0.0, 1.0)
        t_obj = self.oat_c + girando * (115.0 * (pot ** 0.5) + 20.0 * (1.0 - flujo_ias))
        if s.transmision_refrig < 1.0:
            t_obj = self.oat_c + (t_obj - self.oat_c) / max(s.transmision_refrig, 0.20)
        # sin aceite la caja se calienta rapidísimo por fricción
        if self.xmsn_p_psi < LIM["xmsn_p_min"] and self.n_rot_rpm > 60.0:
            t_obj += 70.0 * (1.0 - self.xmsn_p_psi / LIM["xmsn_p_min"])
        # lo que el embrague no transmite es calor, y el bulbo de la caja es lo único
        # que lo delata: confirma que la separación de agujas es por patinaje
        if self.acoplado and s.embrague < 0.98:
            t_obj += 130.0 * (1.0 - s.embrague) * limitar(pot, 0.0, 1.2)
        t_obj = limitar(t_obj, self.oat_c, LIM["xmsn_t_escala"])
        self.xmsn_t_c = aproximar(self.xmsn_t_c, t_obj, dt, 110.0)

    def _combustible_disponible(self):
        sel = self.ctl.selector_tanque
        if sel == TANQUE_FWD:
            return self.fuel_fwd_l
        if sel == TANQUE_AFT:
            return self.fuel_aft_l
        return self.fuel_fwd_l + self.fuel_aft_l

    def _paso_combustible(self, dt):
        if self.n_eng_rpm > 200.0:
            self.flujo_lph = mezclar(LIM["consumo_min_lph"], LIM["consumo_max_lph"],
                                     limitar(self.pot_entregada, 0.0, 1.2))
        else:
            self.flujo_lph = 0.0

        # La fuga sale del tanque roto aunque no esté seleccionado: los aforadores se
        # separan y así se identifica qué tanque cerrar
        fuga = self.salud.fuga_combustible_lph * dt / 3600.0
        if fuga > 0.0:
            self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - fuga)

        consumo = self.flujo_lph * dt / 3600.0
        sel = self.ctl.selector_tanque
        if sel == TANQUE_FWD:
            self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - consumo)
        elif sel == TANQUE_AFT:
            self.fuel_aft_l = max(0.0, self.fuel_aft_l - consumo)
        else:
            # de a mitades; si uno se agota, el otro toma todo
            if self.fuel_fwd_l > 0.0 and self.fuel_aft_l > 0.0:
                self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - consumo * 0.5)
                self.fuel_aft_l = max(0.0, self.fuel_aft_l - consumo * 0.5)
            elif self.fuel_fwd_l > 0.0:
                self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - consumo)
            else:
                self.fuel_aft_l = max(0.0, self.fuel_aft_l - consumo)

    def _paso_vuelo(self, dt):
        ctl = self.ctl
        s = self.salud

        # Empuje con RPM^2, por eso perder rotor es tan grave. Escalado para que el
        # estacionario quede a mitad de colectivo (1,0 con col = 0,552)
        rel_rpm = self.n_rot_rpm / LIM["rpm_rotor_nom"]
        empuje = (rel_rpm ** 2) * (0.42 + 1.05 * ctl.colectivo)
        empuje *= (1.0 - self.alt_ft / 30000.0)
        self.empuje = empuje

        # el exceso de empuje fija la vertical de régimen; se llega con tau 1,4 s
        vs_obj = limitar(self.K_VERT * (empuje - 1.0), -2400.0, 1600.0)

        # En autorrotación manda el balance de energía: 1500-1800 ft/min en el S-55.
        # Desde 800 ft a 1600 ft/min son 30 s para elegir dónde bajar
        autorrotando = ((not self.acoplado) and (not self.en_tierra)
                        and self.n_rot_rpm > 60.0
                        and self.pot_entregada < 0.08)
        if autorrotando:
            vs_auto = -(self.pot_requerida / max(self.K_AUTOROT, 0.05)) * 1800.0
            vs_obj = limitar(min(vs_obj, vs_auto), -2400.0, 0.0)

        # apoyado, el VSI tiene que marcar cero aunque el motor esté apagado
        if self.alt_ft <= self.alt_terreno_ft + 0.05 and vs_obj < 0.0:
            vs_obj = 0.0
            self.vs_fpm = aproximar(self.vs_fpm, 0.0, dt, 0.5)
        else:
            self.vs_fpm = aproximar(self.vs_fpm, vs_obj, dt, 1.4)

        self.alt_ft += self.vs_fpm / 60.0 * dt
        if self.alt_ft <= self.alt_terreno_ft:
            self.alt_ft = self.alt_terreno_ft
            if self.vs_fpm < 0.0:
                self.vs_fpm = 0.0
            self.en_tierra = True
        else:
            self.en_tierra = False

        # el cíclico fija una actitud y la actitud una velocidad.
        # ciclico_lon > 0: nariz abajo, acelera
        pitch_obj = -12.0 * ctl.ciclico_lon
        self.pitch_deg = aproximar(self.pitch_deg, pitch_obj, dt, 0.9)
        v_obj = limitar(-self.pitch_deg * 8.5, 0.0, 115.0)
        if self.en_tierra and empuje < 0.95:
            v_obj = 0.0
        self.ias_kt = aproximar(self.ias_kt, v_obj, dt, self.TAU_IAS)
        self.ias_kt = limitar(self.ias_kt, 0.0, 130.0)

        roll_obj = 30.0 * ctl.ciclico_lat
        self.roll_deg = aproximar(self.roll_deg, roll_obj, dt, 0.8)
        if self.ias_kt > 8.0:
            # grados/s, V en kt
            self.turn_rate_dps = 1091.0 * _tan_grados(self.roll_deg) / max(self.ias_kt, 15.0)
        else:
            # en estacionario hace guiñar el rotor de cola
            self.turn_rate_dps = 12.0 * ctl.pedal * s.rotor_cola

        # Pérdida de rotor de cola: guiñada a la derecha. El par que la causa es el que
        # entrega la transmisión, no el que consume el rotor: en autorrotación no hay
        # par y la guiñada para sola, que es el procedimiento. Con potencia requerida no
        # paraba nunca. La deriva vertical la frena a velocidad: mantener velocidad
        if s.rotor_cola < 0.95:
            par_motor = self.pot_entregada if self.acoplado else 0.0
            ayuda_deriva = 1.0 - 0.45 * limitar(self.ias_kt / 74.0, 0.0, 1.0)
            par_no_compensado = ((1.0 - s.rotor_cola) * par_motor
                                 * 26.0 * ayuda_deriva)
            self.turn_rate_dps += par_no_compensado
            self.slip = aproximar(
                self.slip,
                limitar((1.0 - s.rotor_cola) * 1.4 * limitar(par_motor / 0.45, 0.0, 1.0),
                        -1.0, 1.0),
                dt, 1.0)
        else:
            slip_obj = limitar(ctl.pedal * 0.35 - self.roll_deg * 0.006, -1.0, 1.0)
            self.slip = aproximar(self.slip, slip_obj, dt, 1.2)

        self.hdg_deg = (self.hdg_deg + self.turn_rate_dps * dt) % 360.0

        # radial de referencia 090
        err = ((self.hdg_deg - 90.0 + 180.0) % 360.0) - 180.0
        self.cdi = limitar(err / 12.0, -5.0, 5.0)


def _tan_grados(g):
    r = g * 0.017453292519943295
    # Taylor, bien hasta ~60 grados; así no hace falta math
    r2 = r * r
    return r * (1.0 + r2 / 3.0 + 2.0 * r2 * r2 / 15.0)


class PilotoVirtual:
    """Mueve los mandos para cumplir un objetivo; los instrumentos los decide la física.

    Si se apaga durante una falla se ve qué pasa cuando nadie reacciona.
    """

    def __init__(self, modelo):
        self.m = modelo
        self.activo = True
        self.reacciona_a_fallas = True

        self.alt_obj_ft = 0.0
        self.ias_obj_kt = 0.0
        self.hdg_obj_deg = 90.0
        self.rpm_obj = LIM["rpm_motor_crucero"]

        self._i_alt = 0.0
        self._i_ias = 0.0
        self._i_thr = 0.5

    def objetivos(self, alt=None, ias=None, hdg=None, rpm=None):
        if alt is not None:
            self.alt_obj_ft = alt
        if ias is not None:
            self.ias_obj_kt = ias
        if hdg is not None:
            self.hdg_obj_deg = hdg
        if rpm is not None:
            self.rpm_obj = rpm

    def paso(self, dt):
        if not self.activo:
            return
        m = self.m
        ctl = m.ctl

        # motor caído en vuelo
        emergencia = (self.reacciona_a_fallas and not m.en_tierra
                      and m.pot_entregada < 0.12 and m.n_rot_rpm > 40.0)

        if emergencia:
            # colectivo abajo para cuidar las RPM y a la velocidad de mínimo descenso
            ctl.colectivo = rampa(ctl.colectivo, 0.06, dt, 0.9)
            objetivo_v = 52.0
            ctl.ciclico_lon = rampa(ctl.ciclico_lon,
                                    limitar(objetivo_v / 8.5 / 12.0, -1.0, 1.0),
                                    dt, 0.4)
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, 0.0, dt, 0.5)
            return

        # cascada altura, vertical deseada, colectivo: como vuela una persona
        err_alt = self.alt_obj_ft - m.alt_ft
        vs_deseada = limitar(err_alt * 0.9, -700.0, 700.0)
        err_vs = vs_deseada - m.vs_fpm
        self._i_alt = limitar(self._i_alt + err_vs * dt * 0.000060, -0.35, 0.35)
        col_obj = 0.55 + err_vs * 0.00025 + self._i_alt
        # con el rotor frenándose, más paso es peor: se afloja
        if m.n_rot_rpm < LIM["rpm_rotor_min"]:
            col_obj -= 0.30
        ctl.colectivo = rampa(ctl.colectivo, limitar(col_obj, 0.0, 1.0), dt, 0.55)

        # PI sobre RPM; el integral es la mariposa de reposo, así encuentra solo el
        # punto en estacionario y en crucero
        err_rpm = self.rpm_obj - m.n_eng_rpm
        self._i_thr = limitar(self._i_thr + err_rpm * dt * 0.00018, 0.05, 1.0)
        thr_obj = limitar(self._i_thr + err_rpm * 0.00009, 0.05, 1.0)
        ctl.throttle = rampa(ctl.throttle, thr_obj, dt, 0.6)

        err_ias = self.ias_obj_kt - m.ias_kt
        self._i_ias = limitar(self._i_ias + err_ias * dt * 0.0010, -0.30, 0.30)
        lon_obj = (self.ias_obj_kt / 8.5) / 12.0 + err_ias * 0.0030 + self._i_ias
        ctl.ciclico_lon = rampa(ctl.ciclico_lon, limitar(lon_obj, -1.0, 1.0), dt, 0.35)

        # Sin rotor de cola no persigue el rumbo: corrigiendo con cíclico tapaba la
        # guiñada y el tablero mostraba lo contrario de lo que hay que enseñar
        if m.salud.rotor_cola < 0.95:
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, 0.0, dt, 0.5)
            ctl.pedal = rampa(ctl.pedal, 0.0, dt, 0.8)
            return

        err_hdg = ((self.hdg_obj_deg - m.hdg_deg + 180.0) % 360.0) - 180.0
        lat_obj = limitar(err_hdg * 0.035, -1.0, 1.0)
        if m.ias_kt < 12.0:
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, 0.0, dt, 0.5)
            ctl.pedal = rampa(ctl.pedal, limitar(err_hdg * 0.06, -1.0, 1.0), dt, 1.0)
        else:
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, lat_obj, dt, 0.5)
            ctl.pedal = rampa(ctl.pedal, 0.0, dt, 0.8)
