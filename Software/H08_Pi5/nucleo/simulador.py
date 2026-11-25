# -*- coding: utf-8 -*-
"""Orquestador: los tres modos (vuelo normal, escenario, falla puntual), el lazo
de tiempo fijo y la telemetría para la página. Es el único módulo que conoce
a todos los demás.
"""

from utiles import ticks_ms, ticks_diff, limitar
from configuracion import (LIM, LAZO, TABLERO, AERONAVE, ANUNCIADOR,
                           PANEL_VIRTUAL, PANEL_LIENZO, PANEL_ZONAS,
                           PANEL_CONMUTADORES, PANEL_PLACAS, BARRIDO,
                           CENTRO_ESCALA, LED, HORIZONTE)
from senales import BusSenales
from modelo_vuelo import ModeloVuelo, PilotoVirtual, MAG_OFF
from fallas import MotorFallas, CATALOGO, CATALOGO_POR_ID
from escenarios import PERFIL_NORMAL, ESCENARIOS, ESCENARIOS_POR_ID
from mapa_tablero import MapaTablero

MODO_NORMAL = 1
MODO_ESCENARIO = 2
MODO_FALLA = 3
MODO_DETENIDO = 0

NOMBRES_MODO = {
    0: "Detenido",
    1: "Vuelo normal controlado",
    2: "Escenario de emergencia",
    3: "Falla de sistema puntual",
}


# para que las agujas lleguen al cero antes de soltarlas
SEGUNDOS_A_REPOSO = 8.0


class Simulador:
    """El vuelo, las fallas y las agujas.

    En la Pi arranca en reposo (servos sin pulso) hasta que el profe toca
    "Activar tablero". Creado a mano, como en las pruebas, arranca activo.
    """

    def __init__(self, actuadores, semilla=None):
        self.modelo = ModeloVuelo()
        self.piloto = PilotoVirtual(self.modelo)
        self.bus = BusSenales()
        self.fallas = MotorFallas(self.modelo, self.bus)
        self.mapa = MapaTablero(actuadores)
        self.actuadores = actuadores

        self.dt = 1.0 / LAZO["hz_fisica"]
        self.modo = MODO_DETENIDO
        self.pausado = False
        self.velocidad = 1.0          # 0.5 = cámara lenta

        self.fase_idx = 0
        self.fase_t = 0.0
        self.ciclar = True

        self.escenario = None
        self.escenario_t = 0.0
        self.escenario_paso = 0

        self.mensajes = []
        self.t_sim = 0.0

        if semilla is not None:
            from utiles import RNG
            RNG.sembrar(semilla)

        self.activo = True
        self._a_reposo = None         # s que faltan para soltar las agujas

        self._t_ultimo = ticks_ms()
        self._acum_ms = 0
        self._t_salida = 0.0
        self.per_salida = 1.0 / LAZO["hz_salida"]

    # si el profe salta a una de estas desde la página, arranca con el motor en
    # marcha; si no, el tablero queda en cero con el nombre de una fase de vuelo
    FASES_CON_MOTOR = ("RALENTI", "EMBRAGUE", "RUNUP", "MAG_L", "MAG_BOTH", "MAG_R",
                       "DESPEGUE", "ASCENSO", "CRUCERO", "VIRAJE", "DESCENSO",
                       "APROXIMACION", "ESTACIONARIO", "ATERRIZAJE",
                       "ENFRIAMIENTO", "CORTE")

    def modo_normal(self, desde_fase=None):
        # de aeronave fría a aeronave fría
        self.modo = MODO_NORMAL
        self.fallas.limpiar()
        self.modelo.reiniciar(en_frio=True)
        self.piloto.activo = False
        self.piloto.reacciona_a_fallas = True
        self.fase_idx = 0
        self.fase_t = 0.0
        self.mensajes = []

        if desde_fase is not None:
            for i in range(len(PERFIL_NORMAL)):
                if PERFIL_NORMAL[i]["id"] == desde_fase:
                    self.fase_idx = i
                    break
            self._condiciones_iniciales_de_fase(PERFIL_NORMAL[self.fase_idx])

        self._entrar_fase()
        self._msg("MODO 1 - Vuelo normal: " + PERFIL_NORMAL[self.fase_idx]["nombre"])

    def _condiciones_iniciales_de_fase(self, f):
        if f["id"] not in self.FASES_CON_MOTOR:
            return

        m = self.modelo
        m.reiniciar(en_frio=False)
        obj = f.get("obj")

        if f.get("piloto") and obj:
            # se entra ya volando
            m.alt_ft = obj.get("alt", 800.0)
            m.ias_kt = obj.get("ias", 74.0)
            m.hdg_deg = obj.get("hdg", 90.0)
            m.en_tierra = m.alt_ft < 5.0
            self.piloto.objetivos(alt=m.alt_ft, ias=m.ias_kt, hdg=m.hdg_deg,
                                  rpm=obj.get("rpm", LIM["rpm_motor_crucero"]))
            self.piloto._i_thr = 0.50
        else:
            # en tierra con motor en marcha
            m.alt_ft = 0.0
            m.ias_kt = 0.0
            m.vs_fpm = 0.0
            m.en_tierra = True
            m.ctl.colectivo = 0.0
            if f["id"] in ("RALENTI",):
                m.n_eng_rpm = LIM["rpm_motor_ralenti"]
                m.n_rot_rpm = 0.0
                m.acoplado = False
                m.ctl.embrague = False
            m.cht_c = LIM["cht_nom"] * 0.6
            m.oil_t_c = 45.0

        self.piloto._i_alt = 0.0
        self.piloto._i_ias = 0.0

    def modo_escenario(self, id_escenario):
        esc = ESCENARIOS_POR_ID.get(id_escenario)
        if esc is None:
            return False
        self.modo = MODO_ESCENARIO
        self.escenario = esc
        self.escenario_t = 0.0
        self.escenario_paso = 0
        self.mensajes = []
        self.fallas.limpiar()
        self._preparar_crucero()
        self._msg("MODO 2 - " + esc["nombre"])
        return True

    def modo_falla(self, id_falla):
        d = CATALOGO_POR_ID.get(id_falla)
        if d is None:
            return False
        self.modo = MODO_FALLA
        self.mensajes = []
        self.fallas.limpiar()
        self._preparar_crucero()
        self.fallas.activar(id_falla)
        self._msg("MODO 3 - " + d["nombre"] + " (" + d["sistema"] + ")")
        for s in d.get("sintomas", []):
            self._msg("Síntoma: " + s)
        self._msg("Procedimiento: " + d.get("proc", ""))
        return True

    def detener(self):
        self.modo = MODO_DETENIDO
        self.fallas.limpiar()
        self.modelo.reiniciar(en_frio=True)
        self._msg("Simulación detenida. Tablero a cero.")

    @property
    def en_reposo(self):
        # quieto o volviendo: no acepta órdenes de vuelo
        return (not self.activo) or self._a_reposo is not None

    def estado_tablero(self):
        if not self.activo:
            return "reposo"
        return "volviendo" if self._a_reposo is not None else "activo"

    def entrar_en_reposo(self, inmediato=False):
        # inmediato: al arrancar, cuando todavía no recibieron pulso
        if self.en_reposo and not inmediato:
            return
        if self.modo != MODO_DETENIDO:
            self.detener()
        self.pausado = False
        self.velocidad = 1.0
        self.mapa.test_luces = False
        self.mapa.reposo = True
        if inmediato:
            self._a_reposo = None
            self.activo = False
            self.mapa.soltar_todo()
            self._msg("Tablero en reposo. Lo activa el profesor.")
        else:
            self._a_reposo = SEGUNDOS_A_REPOSO
            self._msg("Volviendo al reposo: las agujas van al cero.")

    def activar(self):
        if self.activo and self._a_reposo is None:
            return
        self._a_reposo = None
        self.activo = True
        self.mapa.reposo = False
        self.mapa.apagar()            # reescribe todo, de a tandas
        self._msg("Tablero activado por el profesor.")
        self.modo_normal()

    def _preparar_crucero(self):
        self.modelo.reiniciar(en_frio=False)
        self.modelo.alt_ft = 1500.0
        self.modelo.ias_kt = 74.0
        self.modelo.hdg_deg = 90.0
        self.piloto.activo = True
        self.piloto.reacciona_a_fallas = True
        self.piloto.objetivos(alt=1500.0, ias=74.0, hdg=90.0,
                              rpm=LIM["rpm_motor_crucero"])
        # integrador precargado: si no, hay 20 s de transitorio antes del escenario
        self.piloto._i_thr = 0.45
        self.piloto._i_alt = 0.0
        self.piloto._i_ias = 0.0
        self.modelo.ctl.luces_tablero = 0.7

    def activar_falla(self, id_falla):
        return self.fallas.activar(id_falla)

    def quitar_falla(self, id_falla):
        return self.fallas.desactivar(id_falla)

    def prueba_luces(self, encendido):
        self.mapa.test_luces = bool(encendido)

    def fijar_piloto_reactivo(self, valor):
        # para mostrar qué pasa si nadie reacciona a la falla
        self.piloto.reacciona_a_fallas = bool(valor)

    def servicio(self):
        """Llamar lo más seguido posible. True si hubo al menos un paso.

        Paso fijo: corre tantos pasos como tiempo real pasó. Así la física no se
        acelera en una máquina rápida y las tres tasas quedan desacopladas.
        """
        ahora = ticks_ms()
        transcurrido = ticks_diff(ahora, self._t_ultimo)
        self._t_ultimo = ahora
        if transcurrido < 0:
            transcurrido = 0
        # en float: con int() se perdían decimales y x0,5 en realidad iba a x0,42
        self._acum_ms += transcurrido * self.velocidad

        paso_ms = int(self.dt * 1000)
        max_pasos = 5                 # que una demora del SO no dispare una avalancha
        n = 0
        while self._acum_ms >= paso_ms and n < max_pasos:
            self._acum_ms -= paso_ms
            if not self.pausado:
                self.paso(self.dt)
            n += 1
        if self._acum_ms > paso_ms * max_pasos:
            self._acum_ms = 0

        if n == 0:
            return False

        # en reposo no se escribe nada, los servos quedan sin pulso
        if not self.activo:
            return True
        self._t_salida += n * self.dt
        if self._t_salida >= self.per_salida:
            self._t_salida = 0.0
            self.mapa.escribir()
        if self._a_reposo is not None:
            self._a_reposo -= n * self.dt
            if self._a_reposo <= 0:
                self._a_reposo = None
                self.activo = False
                self.mapa.soltar_todo()
                self._msg("Tablero en reposo. Lo activa el profesor.")
        return True

    def paso(self, dt):
        self.t_sim += dt

        if self.modo == MODO_NORMAL:
            self._paso_fases(dt)
        elif self.modo == MODO_ESCENARIO:
            self._paso_escenario(dt)

        # restablece la salud y reaplica lo activo, antes del piloto y la física
        self.fallas.paso(dt)

        self.piloto.paso(dt)

        self.modelo.paso(dt)

        self._publicar_senales()

        # el radial escala el ruido de todas las agujas; motor parado, tablero quieto
        vibracion = limitar(self.modelo.n_eng_rpm / 2200.0, 0.0, 1.2)
        # 24 V indican bien, 18 V (arranque) de menos, bajo 12 V nada
        factor_e = limitar((self.modelo.bus_v - 12.0) /
                           (LIM["bus_min_util"] - 12.0), 0.0, 1.0)
        self.bus.actualizar_indicaciones(dt, factor_e, vibracion)

        self.mapa.actualizar(self.bus, dt)

    def _entrar_fase(self):
        f = PERFIL_NORMAL[self.fase_idx]
        ctl = self.modelo.ctl
        for k in f.get("ctl", {}):
            setattr(ctl, k, f["ctl"][k])
        activo_antes = self.piloto.activo
        self.piloto.activo = bool(f.get("piloto"))
        if self.piloto.activo and not activo_antes:
            # desde la mariposa actual, si no salta la RPM al tomar el mando
            self.piloto._i_thr = self.modelo.ctl.throttle
            self.piloto._i_alt = 0.0
            self.piloto._i_ias = 0.0
        obj = f.get("obj")
        if obj:
            self.piloto.objetivos(alt=obj.get("alt"), ias=obj.get("ias"),
                                  hdg=obj.get("hdg"), rpm=obj.get("rpm"))
        self.fase_t = 0.0
        self._msg("[FASE] " + f["nombre"])

    def _paso_fases(self, dt):
        self.fase_t += dt
        f = PERFIL_NORMAL[self.fase_idx]

        salir = self.fase_t >= f["dur"]
        cond = f.get("hasta")
        if (not salir) and cond:
            var, op, val = cond
            actual = getattr(self.modelo, var, 0.0)
            if op == ">" and actual > val:
                salir = True
            elif op == "<" and actual < val:
                salir = True
            elif op == ">=" and actual >= val:
                salir = True
            elif op == "<=" and actual <= val:
                salir = True

        if salir:
            self.fase_idx += 1
            if self.fase_idx >= len(PERFIL_NORMAL):
                if self.ciclar:
                    self.fase_idx = 0
                    self.modelo.reiniciar(en_frio=True)
                else:
                    self.fase_idx = len(PERFIL_NORMAL) - 1
                    self.modo = MODO_DETENIDO
                    return
            self._entrar_fase()

    def _paso_escenario(self, dt):
        self.escenario_t += dt
        guion = self.escenario["guion"]
        while self.escenario_paso < len(guion):
            t_evt, accion = guion[self.escenario_paso]
            if self.escenario_t < t_evt:
                break
            self.escenario_paso += 1
            self._ejecutar_accion(accion)

    def _ejecutar_accion(self, a):
        if "falla" in a:
            self.fallas.activar(a["falla"])
        if "quitar" in a:
            self.fallas.desactivar(a["quitar"])
        if "amb" in a:
            for k in a["amb"]:
                setattr(self.modelo, k, a["amb"][k])
        if "ctl" in a:
            for k in a["ctl"]:
                setattr(self.modelo.ctl, k, a["ctl"][k])
        if "obj" in a:
            # para fallas que solo se ven en una fase, como el hielo de
            # carburador en descenso
            o = a["obj"]
            self.piloto.objetivos(alt=o.get("alt"), ias=o.get("ias"),
                                  hdg=o.get("hdg"), rpm=o.get("rpm"))
        if "piloto" in a:
            self.piloto.reacciona_a_fallas = bool(a["piloto"])
        if "msg" in a:
            self._msg(a["msg"])
        if a.get("fin"):
            self._msg("--- Escenario finalizado ---")
            self.modo = MODO_DETENIDO

    def _publicar_senales(self):
        m = self.modelo
        p = self.bus.poner

        # la que deduce el instrumento de pitot-estática, no la real
        p("ias_kt", m.ias_ind_kt)
        # corrección barométrica: 1 hPa = 27 ft
        alt_ind = m.alt_ft + (m.qnh_hpa - LIM["qnh_hpa"]) * 27.0
        p("alt_ind_ft", alt_ind)
        p("alt_centenas", alt_ind % 1000.0)
        p("vs_ind_fpm", m.vs_fpm)
        # actitud filtrada por el giróscopo: con el giro cayendo, el horizonte
        # se atrasa y la brújula deriva
        p("hdg_ind_deg", m.hdg_giro_deg)
        p("pitch_ind_deg", m.pitch_ind_deg)
        p("roll_ind_deg", m.roll_ind_deg)
        p("turn_rate_dps", m.turn_rate_dps)
        p("slip", m.slip)
        p("cdi", m.cdi)

        p("n_eng_rpm", m.n_eng_rpm)
        p("n_rot_rpm", m.n_rot_rpm)
        p("map_inhg", m.map_inhg)
        p("oil_p_psi", m.oil_p_psi)
        p("oil_t_c", m.oil_t_c)
        p("cht_c", m.cht_c)
        p("cat_c", m.cat_c)
        p("fuel_p_psi", m.fuel_p_psi)

        p("fuel_fwd_l", m.fuel_fwd_l)
        p("fuel_aft_l", m.fuel_aft_l)
        p("xmsn_p_psi", m.xmsn_p_psi)
        p("xmsn_t_c", m.xmsn_t_c)

        p("bus_v", m.bus_v)
        p("amp_a", m.amp_a)

        # Luces de alerta: lógica de aviso, no física. Bajo 20 V se apagan
        # todas aunque la alarma siga.
        vivo = 1.0 if m.energia_ok else 0.0

        p("lt_fuel_fwd", vivo if m.fuel_fwd_l < LIM["aviso_fuel_l"] else 0.0)
        p("lt_fuel_aft", vivo if m.fuel_aft_l < LIM["aviso_fuel_l"] else 0.0)

        alarma_xmsn = (m.xmsn_p_psi < LIM["xmsn_p_min"] and m.n_rot_rpm > 60.0)
        p("lt_xmsn", vivo if alarma_xmsn else 0.0)

        alarma_gen = (m.ctl.bateria and not m.gen_en_linea)
        p("lt_gen", vivo if alarma_gen else 0.0)

        alarma_rotor = (40.0 < m.n_rot_rpm < LIM["rpm_rotor_min"])
        p("lt_low_rotor", vivo if alarma_rotor else 0.0)

        p("lt_starter", vivo if m.ctl.magnetos != MAG_OFF else 0.0)

    def _msg(self, texto):
        self.mensajes.append({"t": round(self.t_sim, 1), "texto": texto})
        if len(self.mensajes) > 40:
            del self.mensajes[0]

    def estado(self, con_instrumentos=True):
        """Todo lo que necesita la página, listo para JSON."""
        m = self.modelo
        d = {
            "t": round(self.t_sim, 2),
            "tablero": self.estado_tablero(),
            "modo": self.modo,
            "modo_nombre": NOMBRES_MODO.get(self.modo, "?"),
            "pausado": self.pausado,
            "velocidad": self.velocidad,
            "fase": None,
            "fase_texto": None,
            "escenario": None,
            "fallas": self.fallas.lista_activas(),
            "mensajes": self.mensajes[-12:],
            "energia_ok": m.energia_ok,
            "acoplado": m.acoplado,
            "en_tierra": m.en_tierra,
            "motor_vivo": bool(getattr(m, "motor_vivo", False)),
            "hielo_carb": round(m.hielo_carb, 2),
            "mandos": {
                "colectivo": round(m.ctl.colectivo, 3),
                "throttle": round(m.ctl.throttle, 3),
                "calefaccion_carb": round(m.ctl.calefaccion_carb, 2),
                "magnetos": m.ctl.magnetos,
                "generador": m.ctl.generador,
                "bateria": m.ctl.bateria,
                "embrague": m.ctl.embrague,
                "tanque": m.ctl.selector_tanque,
                # para que la página mueva las llaves como el piloto virtual
                "arrancador": m.ctl.arrancador,
                "bomba": m.ctl.bomba_combustible,
                "luces": round(m.ctl.luces_tablero, 2),
                "mezcla": round(m.ctl.mezcla, 2),
                "gen_en_linea": bool(m.gen_en_linea),
            },
            "stats": self.mapa.estadisticas(),
            # para el helicóptero 3D: lo real, aunque una aguja mienta
            "vuelo": {
                "alt_ft": round(getattr(m, "alt_ft", 0.0), 1),
                "terreno_ft": round(getattr(m, "alt_terreno_ft", 0.0), 1),
                "ias_kt": round(getattr(m, "ias_kt", 0.0), 1),
                "vs_fpm": round(getattr(m, "vs_fpm", 0.0)),
                "rumbo": round(getattr(m, "hdg_deg", 0.0), 1),
                "cabeceo": round(getattr(m, "pitch_deg", 0.0), 2),
                "alabeo": round(getattr(m, "roll_deg", 0.0), 2),
                "giro_dps": round(getattr(m, "turn_rate_dps", 0.0), 2),
                "rotor_rpm": round(getattr(m, "n_rot_rpm", 0.0), 1),
                "motor_rpm": round(getattr(m, "n_eng_rpm", 0.0)),
            },
        }

        if self.modo == MODO_NORMAL:
            f = PERFIL_NORMAL[self.fase_idx]
            d["fase"] = f["nombre"]
            d["fase_texto"] = f["texto"]
            d["fase_id"] = f["id"]
            d["fase_progreso"] = round(min(self.fase_t / f["dur"], 1.0), 2)
        elif self.modo == MODO_ESCENARIO and self.escenario:
            d["escenario"] = self.escenario["nombre"]
            d["escenario_id"] = self.escenario["id"]
            d["fase_texto"] = self.escenario["resumen"]
            d["fase_progreso"] = round(
                min(self.escenario_t / self.escenario["duracion"], 1.0), 2)

        if self.en_reposo:
            d["modo_nombre"] = "En reposo"
            d["fase"] = ("Esperando al profesor" if not self.activo
                         else "Volviendo al reposo")
            d["fase_texto"] = ("El tablero está quieto. Lo activa el profesor "
                               "desde el modo profesor.")

        if con_instrumentos:
            inst = {}
            angulos = self.mapa.angulos()
            for it in TABLERO:
                iid = it["id"]
                if self.en_reposo:
                    # la página muestra lo mismo que van a marcar las agujas
                    c = self.mapa.por_id[iid]
                    cero = 0.0 if it["actuador"] == LED else round(c.cero, 2)
                    inst[iid] = {"v": cero, "real": cero,
                                 "ang": angulos.get(iid, 0.0), "anom": False}
                    continue
                inst[iid] = {
                    "v": round(self.bus.ver(it["senal"], 0.0), 2),
                    "real": round(self.bus.obtener(it["senal"], 0.0), 2),
                    "ang": angulos.get(iid, 0.0),
                    "anom": self.bus.tiene_anomalia(it["senal"]),
                }
            d["instrumentos"] = inst
        return d

    # se manda una sola vez a la página
    def catalogo_estatico(self):
        instrumentos = []
        # PANEL_VIRTUAL: el reloj es mecánico, sin canal, pero se dibuja
        for it in list(TABLERO) + list(PANEL_VIRTUAL):
            instrumentos.append({
                "id": it["id"], "n": it["n"], "nombre": it["nombre"],
                "en": it["en"], "unidad": it["unidad"],
                "min": it["escala"][0], "max": it["escala"][1],
                "arcos": it.get("arcos", []),
                "tipo": it["actuador"], "color": it.get("color", ""),
                "canal": it.get("canal"),
                "desc": it.get("desc", ""),
                "zona": it.get("zona", ""),
                "dial": it.get("dial", ""),
                "pos": it.get("pos"),
                "tam": it.get("tam", 104),
                "leyenda": it.get("leyenda", ""),
                "corto": it.get("corto", it["nombre"]),
                # así la página dibuja la esfera con la misma no linealidad
                "cal": it.get("cal", []),
                # mismo ángulo que el servo sobre la carátula (caratulas.ang_dibujo)
                "barrido": BARRIDO.get(it["id"]),
                "centro": CENTRO_ESCALA.get(it["id"], 90.0),
            })
        fallas = []
        orden_sis = ("MOTOR", "LUBRICACION", "COMBUSTIBLE", "TRANSMISION",
                     "ROTORES", "ELECTRICO", "INSTRUMENTOS")
        catalogo_ordenado = sorted(
            CATALOGO,
            key=lambda f: (orden_sis.index(f["sistema"])
                           if f["sistema"] in orden_sis else 99))
        for f in catalogo_ordenado:
            fallas.append({
                "id": f["id"], "nombre": f["nombre"], "sistema": f["sistema"],
                "sev": f["sev"], "desarrollo": f.get("desarrollo", 0),
                "instr": f.get("instr", []), "sintomas": f.get("sintomas", []),
                "proc": f.get("proc", ""),
            })
        escenarios = []
        for e in ESCENARIOS:
            escenarios.append({
                "id": e["id"], "nombre": e["nombre"], "sistema": e["sistema"],
                "duracion": e["duracion"], "resumen": e["resumen"],
            })
        fases = []
        for f in PERFIL_NORMAL:
            fases.append({"id": f["id"], "nombre": f["nombre"],
                          "dur": f["dur"], "texto": f["texto"]})
        return {"aeronave": AERONAVE, "instrumentos": instrumentos,
                "fallas": fallas, "escenarios": escenarios, "fases": fases,
                "anunciador": ANUNCIADOR,
                # horizonte simple sin cabeceo: la página lo avisa
                "cabeceo_fijo": bool(HORIZONTE.get("cabeceo_fijo")),
                # geometría desde configuracion.py, así la página no repite números
                "lienzo": PANEL_LIENZO,
                "zonas": PANEL_ZONAS,
                "conmutadores": PANEL_CONMUTADORES,
                "placas": PANEL_PLACAS,
                "actuadores": self.actuadores.descripcion()}
