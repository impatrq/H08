# -*- coding: utf-8 -*-
"""Todos los números del proyecto: límites del H-19A, instrumentos, canales de
las placas, pines y geometría de la página. Ningún otro módulo tiene constantes
propias, así que recalibrar es editar este archivo.

H-08: Sikorsky H-19A Chickasaw (S-55), c/n 55-135, ex USAF 51-3873, FAA 1962-1968.
"""

# se muestra en la página
AERONAVE = {
    "modelo": "Sikorsky H-19A Chickasaw (S-55)",
    "matricula": "H-08",
    "serie": "c/n 55-135 (ex USAF 51-3873)",
    "operador": "Fuerza Aérea Argentina",
    "servicio": "1962 - 1968",
    "motor": "Pratt & Whitney R-1340-57 Wasp, 600 HP",
    "referencia": "T.O. 1H-19A-1",
    "preservacion": "Taller Regional Quilmes",
}

LIM = {
    # motor R-1340-57: 600 HP a 2250 RPM, 550 HP continuo a 2200
    "rpm_motor_ralenti": 1400.0,
    "rpm_motor_crucero": 2200.0,
    "rpm_motor_despegue": 2250.0,
    "rpm_motor_max": 2400.0,
    "rpm_motor_escala": 3500.0,       # fondo de escala del tacómetro
    "rpm_arranque_corte": 600.0,      # por debajo de esto el motor no sostiene

    # rotor
    "rpm_rotor_min": 170.0,           # arco rojo inferior
    "rpm_rotor_nom": 220.0,
    "rpm_rotor_max": 245.0,           # arco rojo superior
    "rpm_rotor_escala": 350.0,
    # Con el embrague acoplado las dos agujas del tacómetro doble quedan
    # superpuestas; si el motor falla la rueda libre desacopla y se separan
    "reduccion": 10.0,                # motor:rotor

    # Admisión: el manómetro es absoluto. Motor parado marca ~29,9 (la presión
    # del campo) y al arrancar BAJA, por la depresión con la mariposa cerrada
    "map_ambiente": 29.92,            # inHg, ISA a nivel del mar
    "map_min": 10.0,                  # fondo de escala del instrumento
    "map_ralenti": 13.0,              # mariposa cerrada, 1400 RPM
    "map_crucero": 29.0,
    "map_despegue": 36.5,             # R-1340-57 a 2250 RPM
    "map_max": 38.0,                  # línea roja
    "map_escala": 50.0,

    # aceite
    "oil_p_min": 25.0,                # psi, mínimo en ralenti
    "oil_p_nom": 80.0,
    "oil_p_max": 100.0,
    "oil_p_escala": 150.0,
    "oil_t_nom": 70.0,                # C
    "oil_t_min_despegue": 40.0,       # no se despega con el aceite más frío
    "oil_t_max": 85.0,
    "oil_t_escala": 100.0,

    # Culata: en tierra 232 C, porque quieto y sin viento el radial se recalienta
    # rápido. Es la limitación clásica del tipo
    "cht_nom": 200.0,                 # C
    "cht_tierra_max": 232.0,          # 450 F, límite en tierra
    "cht_max": 260.0,                 # 500 F, límite absoluto
    "cht_escala": 350.0,

    "cat_nom": 15.0,                  # C
    "cat_hielo_min": -10.0,           # banda de riesgo de engelamiento
    "cat_hielo_max": 15.0,

    "fuel_p_nom": 16.0,               # psi
    "fuel_p_min": 12.0,
    "fuel_p_escala": 25.0,
    "cap_fwd": 378.0,                 # litros
    "cap_aft": 322.0,
    "aviso_fuel_l": 45.0,             # nivel que enciende la luz ámbar
    "consumo_max_lph": 155.0,         # a potencia de despegue
    "consumo_min_lph": 22.0,          # ralenti

    "xmsn_p_nom": 55.0,               # psi
    "xmsn_p_min": 30.0,
    "xmsn_p_escala": 100.0,
    "xmsn_t_nom": 85.0,               # C
    "xmsn_t_max": 110.0,
    "xmsn_t_escala": 150.0,

    # eléctrico: 24 V CC, generador de 200 A
    "bus_bateria": 24.0,              # V con generador fuera de línea
    "bus_generador": 28.0,            # V con generador en línea
    "bus_min_util": 20.0,             # por debajo los instrumentos eléctricos mueren
    "amp_escala": 200.0,
    "amp_carga_max": 120.0,
    # acelerado: una batería real tarda una hora, no da para una clase
    "factor_bateria": 8.0,

    "vne_kt": 95.0,
    "v_crucero_kt": 74.0,
    "v_escala_kt": 120.0,
    "vs_escala_fpm": 2000.0,
    "alt_escala_ft": 10000.0,
    "techo_ft": 10500.0,
    "viraje_estandar_dps": 3.0,       # 3 grados/s = viraje de 2 minutos

    # ISA a nivel del mar
    "oat_c": 15.0,
    "qnh_hpa": 1013.0,
}

SERVO = "SERVO"          # servo de 180 grados sobre una placa PCA9685
MOTOR = "MOTOR"          # paso a paso 28BYJ-48 de giro continuo, con plaquita ULN2003
LED = "LED"              # luz de alerta, encendida o apagada, sobre PCA9685

# Campos de cada entrada de TABLERO (un actuador físico):
#   n         número en la lista de 33 del anteproyecto
#   senal     variable del modelo que lo alimenta
#   arcos     (desde, hasta, color) para la página
#   cal       [(valor, ángulo)], ver utiles.interpolar_tabla. Para ajustar un
#             instrumento se corrige esta tabla, no el código
#   tau, slew inercia (s) y velocidad máxima (grados/s) de la aguja
#   canal     ("PCA0", 7), ("MOTOR", 1) o None

# Cuánto barre cada aguja de verdad (valores típicos de la época). De acá salen
# la carátula, los engranajes y el ángulo del servo. Hasta 180 el servo alcanza
# solo; más de 180 lleva un par que multiplica barrido/180.
BARRIDO = {
    # vuelo, bocas de 78 mm
    "AIRSPEED":       300,   # velocímetro de 3 pulgadas, escala larga
    "ALTIMETER":      360,   # millares: una vuelta entera cada 10.000 pies
    "ALTIMETER_100": "CONT", # centenas: da vueltas sin parar, motor continuo
    "VSI":            300,   # variómetro de +-2000 pies por minuto
    "TURN":            60,   # la aguja de viraje se mueve +-30 y nada más
    "SLIP":            70,   # no es una aguja: es el arco que recorre la bola
    "TACH_ENG":       300,   # tacómetro doble
    "TACH_ROT":       300,   # la otra aguja del mismo instrumento
    "MAP":            270,   # manómetro de presión de admisión
    "VOR_CDI":         40,   # aguja de desvío de curso, +-20

    # combustible y culata, 58 mm
    "FUEL_QTY_FWD":   120,   # aforador de flotante: arco corto
    "FUEL_QTY_AFT":   120,
    "CHT":            270,   # termómetro de culata

    # motor, transmisión y eléctricos, 48 mm
    "OIL_TEMP":       270,
    "OIL_PRESS":      270,
    "FUEL_PRESS":     270,
    "CARB_AIR_TEMP":  270,
    "XMSN_OIL_TEMP":  270,
    "XMSN_OIL_PRESS": 270,
    "AMMETER":        120,   # amperímetro de aguja central, arco corto
    "VOLTMETER":      120,

    # las dos de 122 mm
    "COMPASS":       "CONT", # la rosa da la vuelta entera, motor continuo
    "ATT_PITCH":     "MEC",  # el horizonte tiene su propio mecanismo
    "ATT_ROLL":      "MEC",
}

# Medio de la escala en ángulo de dibujo (90 = arriba). El VSI tiene el cero a
# las 9 como el real. Lo usan caratulas.py y la página, por eso está acá
CENTRO_ESCALA = {
    "VSI": 180.0,
}

# (dientes servo, dientes aguja). Módulo 0,5 y 24 en la aguja: entra en la boca
# de 48 mm y todavía sale limpio en la impresora de filamento
ENGRANAJES = {
    1.5:    (36, 24),        # 270 grados de aguja
    5/3.0:  (40, 24),        # 300 grados
    2.0:    (48, 24),        # 360 grados
}
MODULO_ENGRANAJE = 0.5


def reduccion(id_instrumento):
    # 1 = aguja directo al servo
    b = BARRIDO.get(id_instrumento)
    if not isinstance(b, (int, float)):
        return 1.0
    return max(1.0, b / 180.0)


def invertido(id_instrumento):
    """True si hay un par de engranajes exteriores, que invierte el giro."""
    if id_instrumento == "ATT_ROLL":           # sin piñón no hay engranaje que invierta
        return not HORIZONTE.get("alabeo_directo")
    return reduccion(id_instrumento) > 1.0


# Los que quedaron armados al revés (servo del otro lado, un engranaje de más):
# se da vuelta el giro dentro del mismo recorrido. Después de anotar uno,
# python3 calibrar_instrumento.py ESE. Lo elegido al calibrar le gana a esta lista.
AL_REVES = {
    "FUEL_QTY_FWD",     # PCA0 canal 0
    "FUEL_PRESS",       # PCA0 canal 3
    "AIRSPEED",         # PCA0 canal 6
    "TACH_ENG",         # PCA0 canal 7
    "ALTIMETER",        # PCA0 canal 9
    "VSI",              # PCA0 canal 10
    "VOR_CDI",          # PCA0 canal 15
    "MAP",              # PCA1 canal 0
}


def recorrido_servo(id_instrumento):
    return 180.0 * factor_servo(id_instrumento)


def factor_servo(id_instrumento):
    """De ángulo de tabla (0..180) a ángulo de servo.

    Si cambia un barrido cambia este factor y las tablas quedan como están.
    """
    b = BARRIDO.get(id_instrumento)
    if not isinstance(b, (int, float)):
        return 1.0
    return (b / 180.0) / reduccion(id_instrumento)


# Horizonte: dos grados de libertad y sin recta, así que las tablas se calculan
# de la mecánica. Cabeceo: yugo escocés, el disco baja r*sen(servo-90) + 1,2 mm
# (r = 23,1). 0,35 mm por grado, ranuras hasta 8 mm: 1 mm de margen para no
# empujar el tope. El brazo calza cada 18 grados y puede quedar 3,6 mm corrido,
# eso lo arregla calibrar_instrumento.py. Si va al revés, a AL_REVES.
import math as _math

HORIZONTE = {
    "cabeceo_max": 20.0,        # marcas del disco
    "mm_por_grado": 0.35,       # Disco_horizonte_cabeceo_20.pdf
    "radio_perno_mm": 23.1,     # del eje del servo al perno del brazo
    "corrimiento_mm": 1.2,      # perno corrido del centro con el brazo a 90°
    "carrera_max_mm": 8.0,      # largo de las ranuras guía
    "alabeo_max": 60.0,
    "dientes_plato": 70,        # módulo 1, 1,4 a 1: servo +-84 para plato +-60
    "dientes_pinon": 50,
    # armado simple (el actual): True/True; intermedio: True/False; v3: False/False
    "alabeo_directo": True,     # plato pegado al eje del servo: 1 a 1, sin piñón
    "cabeceo_fijo": True,       # sin corredera: el servo de cabeceo no se usa
    "paso_tabla": 5,            # grados
}


def corrimiento_disco(cabeceo, h=HORIZONTE):
    # nariz arriba = el disco baja
    return cabeceo * h["mm_por_grado"]


def _tabla_cabeceo(h=HORIZONTE):
    # cancela el seno del yugo y el corrimiento del perno; queda de ~69 a ~105, no simétrico
    paso = h["paso_tabla"]
    n = int(h["cabeceo_max"] / paso)
    r, c = h["radio_perno_mm"], h["corrimiento_mm"]
    return [(p * paso, round(90.0 + _math.degrees(_math.asin(
                (corrimiento_disco(p * paso, h) - c) / r)), 2))
            for p in range(-n, n + 1)]


def _tabla_alabeo(h=HORIZONTE):
    # tres puntos alcanzan: los engranajes son lineales
    rel = 1.0 if h.get("alabeo_directo") else h["dientes_plato"] / float(h["dientes_pinon"])
    tope = round(h["alabeo_max"] * rel, 2)
    return [(-h["alabeo_max"], 90.0 - tope),
            (0.0, 90.0),
            (h["alabeo_max"], 90.0 + tope)]


TABLERO = [

    # grupo motopropulsor
    {
        "id": "FUEL_QTY_FWD", "n": 2,
        "nombre": "Cantidad de combustible - tanque delantero",
        "en": "Fuel Quantity Gage - Fwd Tank",
        "senal": "fuel_fwd_l", "unidad": "L", "escala": (0.0, 378.0),
        "arcos": [(0, 45, "rojo"), (45, 378, "verde")],
        "actuador": SERVO, "tau": 1.2, "slew": 60.0,
        # más resolución en la parte baja del tanque
        "cal": [(0, 0), (45, 30), (95, 60), (190, 105), (285, 145), (378, 180)],
        "canal": ("PCA0", 0),
    },
    {
        "id": "OIL_TEMP", "n": 3,
        "nombre": "Temperatura de aceite de motor",
        "en": "Engine Oil Temperature Gage",
        "senal": "oil_t_c", "unidad": "C", "escala": (0.0, 100.0),
        "arcos": [(0, 40, "amarillo"), (40, 85, "verde"), (85, 100, "rojo")],
        "actuador": SERVO, "tau": 2.0, "slew": 45.0,
        "cal": [(0, 0), (40, 60), (70, 110), (85, 145), (100, 180)],
        "canal": ("PCA0", 1),
    },
    {
        "id": "OIL_PRESS", "n": 4,
        "nombre": "Presión de aceite de motor",
        "en": "Engine Oil Pressure Gage",
        "senal": "oil_p_psi", "unidad": "psi", "escala": (0.0, 150.0),
        "arcos": [(0, 25, "rojo"), (25, 100, "verde"), (100, 150, "rojo")],
        "actuador": SERVO, "tau": 0.4, "slew": 240.0,
        "cal": [(0, 0), (25, 40), (80, 110), (100, 135), (150, 180)],
        "canal": ("PCA0", 2),
    },
    {
        "id": "FUEL_PRESS", "n": 5,
        "nombre": "Presión de combustible",
        "en": "Fuel Pressure Gage",
        "senal": "fuel_p_psi", "unidad": "psi", "escala": (0.0, 25.0),
        "arcos": [(0, 12, "rojo"), (12, 20, "verde"), (20, 25, "amarillo")],
        "actuador": SERVO, "tau": 0.5, "slew": 200.0,
        "cal": [(0, 0), (12, 80), (16, 115), (20, 145), (25, 180)],
        "canal": ("PCA0", 3),
    },
    {
        "id": "CARB_AIR_TEMP", "n": 6,
        "nombre": "Temperatura de aire del carburador",
        "en": "Carburetor Air Temperature Gage",
        "senal": "cat_c", "unidad": "C", "escala": (-50.0, 50.0),
        "arcos": [(-50, -10, "verde"), (-10, 15, "amarillo"), (15, 50, "verde")],
        "actuador": SERVO, "tau": 1.5, "slew": 60.0,
        "cal": [(-50, 0), (-10, 65), (0, 90), (15, 118), (50, 180)],
        "canal": ("PCA0", 4),
    },
    {
        "id": "CHT", "n": 7,
        "nombre": "Temperatura de cabeza de cilindro",
        "en": "Cylinder Head Temperature Gage",
        "senal": "cht_c", "unidad": "C", "escala": (0.0, 350.0),
        "arcos": [(0, 120, "amarillo"), (120, 232, "verde"), (232, 350, "rojo")],
        "actuador": SERVO, "tau": 3.0, "slew": 45.0,
        "cal": [(0, 0), (120, 55), (200, 100), (232, 125), (260, 145), (350, 180)],
        "canal": ("PCA0", 5),
    },

    # vuelo
    {
        "id": "AIRSPEED", "n": 10,
        "nombre": "Velocímetro",
        "en": "Airspeed Indicator",
        "senal": "ias_kt", "unidad": "kt", "escala": (0.0, 120.0),
        "arcos": [(0, 20, "amarillo"), (20, 95, "verde"), (95, 120, "rojo")],
        "actuador": SERVO, "tau": 0.7, "slew": 120.0,
        # presión dinámica con V^2: abajo la esfera va comprimida
        "cal": [(0, 0), (20, 18), (40, 52), (60, 88), (80, 125), (95, 150), (120, 180)],
        "canal": ("PCA0", 6),
    },
    {
        "id": "TACH_ENG", "n": 11,
        "nombre": "Tacómetro doble - aguja de MOTOR",
        "en": "Dual Tachometer - Engine needle",
        "senal": "n_eng_rpm", "unidad": "RPM", "escala": (0.0, 3500.0),
        "arcos": [(0, 1200, "amarillo"), (1200, 2250, "verde"), (2250, 3500, "rojo")],
        "actuador": SERVO, "tau": 0.35, "slew": 300.0,
        "cal": [(0, 0), (1000, 51), (2000, 103), (2200, 113), (2400, 123), (3500, 180)],
        "canal": ("PCA0", 7),
    },
    {
        "id": "TACH_ROT", "n": 11,
        "nombre": "Tacómetro doble - aguja de ROTOR",
        "en": "Dual Tachometer - Rotor needle",
        "senal": "n_rot_rpm", "unidad": "RPM", "escala": (0.0, 350.0),
        "arcos": [(0, 170, "rojo"), (170, 245, "verde"), (245, 350, "rojo")],
        "actuador": SERVO, "tau": 0.35, "slew": 300.0,
        # la del motor dividida por 10, así se superponen
        "cal": [(0, 0), (100, 51), (200, 103), (220, 113), (240, 123), (350, 180)],
        # solo en la página: el físico lleva la de motor y avisa LOW ROTOR. PCA0:8 libre
        "canal": None,
    },
    {
        "id": "ALTIMETER", "n": 18,
        "nombre": "Altímetro (aguja de miles de pies)",
        "en": "Altimeter - thousands pointer",
        "senal": "alt_ind_ft", "unidad": "ft", "escala": (0.0, 10000.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.9, "slew": 90.0,
        "cal": [(0, 0), (2500, 45), (5000, 90), (7500, 135), (10000, 180)],
        "canal": ("PCA0", 9),
    },
    {
        "id": "ALTIMETER_100", "n": 18,
        "nombre": "Altímetro (aguja de centenas de pies)",
        "en": "Altimeter - hundreds pointer",
        "senal": "alt_centenas", "unidad": "ft", "escala": (0.0, 1000.0),
        "arcos": [],
        # solo en la página; el físico tiene la de miles con engranajes 2:1. Motor 0 (U1) libre
        "actuador": MOTOR, "tau": 0.5, "slew": 600.0,
        "cal": [(0, 0), (1000, 360)],
        "canal": None,
    },
    {
        "id": "VSI", "n": 20,
        "nombre": "Variómetro / velocidad vertical",
        "en": "Vertical Velocity Indicator",
        "senal": "vs_ind_fpm", "unidad": "ft/min", "escala": (-2000.0, 2000.0),
        "arcos": [],
        # el real tarda 6 a 9 s (capilar + cápsula)
        "actuador": SERVO, "tau": 2.5, "slew": 90.0,
        "cal": [(-2000, 0), (-1000, 40), (-500, 62), (0, 90),
                (500, 118), (1000, 140), (2000, 180)],
        "canal": ("PCA0", 10),
    },
    {
        "id": "TURN", "n": 19,
        "nombre": "Indicador de viraje (aguja)",
        "en": "Turn Indicator needle",
        "senal": "turn_rate_dps", "unidad": "deg/s", "escala": (-6.0, 6.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.6, "slew": 150.0,
        "cal": [(-6, 45), (-3, 65), (0, 90), (3, 115), (6, 135)],
        "canal": ("PCA0", 11),
    },
    {
        "id": "SLIP", "n": 19,
        "nombre": "Indicador de ladeo (bola)",
        "en": "Slip Indicator ball",
        "senal": "slip", "unidad": "g", "escala": (-1.0, 1.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.8, "slew": 150.0,
        "cal": [(-1, 55), (0, 90), (1, 125)],
        # solo en la página: en el físico la bola va impresa. PCA0:12 libre
        "canal": None,
    },
    {
        "id": "ATT_PITCH", "n": 12,
        "nombre": "Horizonte artificial - cabeceo",
        "en": "Attitude Indicator - pitch",
        "senal": "pitch_ind_deg", "unidad": "deg", "escala": (-20.0, 20.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.5, "slew": 180.0,
        # nueve puntos porque el yugo es un seno
        "cal": _tabla_cabeceo(),
        # armado simple: disco pegado, canal 13 libre y siempre en 0
        "canal": None if HORIZONTE["cabeceo_fijo"] else ("PCA0", 13),
    },
    {
        "id": "ATT_ROLL", "n": 12,
        "nombre": "Horizonte artificial - alabeo",
        "en": "Attitude Indicator - roll",
        "senal": "roll_ind_deg", "unidad": "deg", "escala": (-60.0, 60.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.4, "slew": 240.0,
        "cal": _tabla_alabeo(),
        "canal": ("PCA0", 14),
    },
    {
        "id": "COMPASS", "n": 14,
        "nombre": "Brújula giroscópica esclavizada",
        "en": "Slaved Gyro Magnetic Compass",
        "senal": "hdg_ind_deg", "unidad": "deg", "escala": (0.0, 360.0),
        "arcos": [],
        "actuador": MOTOR, "tau": 1.0, "slew": 180.0,
        "cal": [(0, 0), (360, 360)],
        "canal": ("MOTOR", 1),
    },
    {
        "id": "VOR_CDI", "n": 16,
        "nombre": "Indicador de rumbo del receptor AN/ARN-14",
        "en": "Range Course Indicator",
        "senal": "cdi", "unidad": "pts", "escala": (-5.0, 5.0),
        "arcos": [],
        "actuador": SERVO, "tau": 1.0, "slew": 60.0,
        "cal": [(-5, 60), (0, 90), (5, 120)],
        "canal": ("PCA0", 15),
    },

    # admisión, transmisión y eléctrico
    {
        "id": "MAP", "n": 23,
        "nombre": "Presión de admisión",
        "en": "Manifold Pressure Gage",
        "senal": "map_inhg", "unidad": "inHg", "escala": (10.0, 50.0),
        # motor parado queda en 29,9, dentro del verde: no es falla
        "arcos": [(10, 18, "amarillo"), (18, 36.5, "verde"), (38, 50, "rojo")],
        "actuador": SERVO, "tau": 0.3, "slew": 300.0,
        "cal": [(10, 0), (20, 45), (30, 90), (38, 126), (44, 153), (50, 180)],
        "canal": ("PCA1", 0),
    },
    {
        "id": "XMSN_OIL_TEMP", "n": 26,
        "nombre": "Temperatura de aceite de transmisión",
        "en": "Transmission Oil Temperature Gage",
        "senal": "xmsn_t_c", "unidad": "C", "escala": (0.0, 150.0),
        "arcos": [(0, 50, "amarillo"), (50, 110, "verde"), (110, 150, "rojo")],
        "actuador": SERVO, "tau": 3.5, "slew": 45.0,
        "cal": [(0, 0), (50, 60), (85, 100), (110, 130), (150, 180)],
        "canal": ("PCA1", 1),
    },
    {
        "id": "XMSN_OIL_PRESS", "n": 28,
        "nombre": "Presión de aceite de transmisión",
        "en": "Transmission Oil Pressure Gage",
        "senal": "xmsn_p_psi", "unidad": "psi", "escala": (0.0, 100.0),
        "arcos": [(0, 30, "rojo"), (30, 70, "verde"), (70, 100, "amarillo")],
        "actuador": SERVO, "tau": 0.5, "slew": 200.0,
        "cal": [(0, 0), (30, 60), (55, 100), (70, 128), (100, 180)],
        "canal": ("PCA1", 2),
    },
    {
        "id": "AMMETER", "n": 27,
        "nombre": "Amperímetro",
        "en": "Ammeter",
        "senal": "amp_a", "unidad": "A", "escala": (-50.0, 200.0),
        "arcos": [(-50, 0, "rojo"), (0, 150, "verde"), (150, 200, "amarillo")],
        "actuador": SERVO, "tau": 0.7, "slew": 150.0,
        "cal": [(-50, 20), (0, 45), (100, 120), (200, 180)],
        "canal": ("PCA1", 3),
    },
    {
        "id": "VOLTMETER", "n": 30,
        "nombre": "Voltímetro",
        "en": "Voltmeter",
        "senal": "bus_v", "unidad": "V", "escala": (0.0, 32.0),
        "arcos": [(0, 22, "rojo"), (22, 30, "verde"), (30, 32, "rojo")],
        "actuador": SERVO, "tau": 0.6, "slew": 150.0,
        # expandida entre 20 y 30 V, que es lo que importa
        "cal": [(0, 0), (18, 25), (22, 60), (24, 85), (28, 130), (32, 180)],
        "canal": ("PCA1", 4),
    },
    {
        "id": "FUEL_QTY_AFT", "n": 31,
        "nombre": "Cantidad de combustible - tanque trasero",
        "en": "Fuel Quantity Gage - Aft Tank",
        "senal": "fuel_aft_l", "unidad": "L", "escala": (0.0, 322.0),
        "arcos": [(0, 45, "rojo"), (45, 322, "verde")],
        "actuador": SERVO, "tau": 1.2, "slew": 60.0,
        "cal": [(0, 0), (45, 32), (80, 62), (160, 105), (240, 145), (322, 180)],
        "canal": ("PCA1", 5),
    },

    # luces de alerta
    {
        "id": "LT_FUEL_FWD", "n": 8,
        "nombre": "Luz de advertencia combustible delantero",
        "en": "Fuel Warning Light - Fwd Tank",
        "senal": "lt_fuel_fwd", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "ambar",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 8),
    },
    {
        "id": "LT_FUEL_AFT", "n": 9,
        "nombre": "Luz de advertencia combustible trasero",
        "en": "Fuel Warning Light - Aft Tank",
        "senal": "lt_fuel_aft", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "ambar",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 9),
    },
    {
        "id": "LT_XMSN_PRESS", "n": 24,
        "nombre": "Luz de alerta presión de aceite de transmisión",
        "en": "Transmission Oil Pressure Warning",
        "senal": "lt_xmsn", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "rojo",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 10),
    },
    {
        "id": "LT_GEN", "n": 29,
        "nombre": "Luz de advertencia del generador",
        "en": "Generator Warning Light",
        "senal": "lt_gen", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "rojo",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 11),
    },
    {
        "id": "LT_LOW_ROTOR", "n": 0,
        "nombre": "Luz de RPM de rotor bajo (agregada con fin didáctico)",
        "en": "Low Rotor RPM Warning",
        "senal": "lt_low_rotor", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "rojo",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 12),
    },
    {
        "id": "LT_STARTER", "n": 32,
        "nombre": "Luz de arranque / magnetos activos",
        "en": "Starter / Ignition Light",
        "senal": "lt_starter", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "verde",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 13),
    },
]

TABLERO_POR_ID = {}
for _it in TABLERO:
    TABLERO_POR_ID[_it["id"]] = _it


LAZO = {
    "hz_fisica": 20,      # alcanza: la aguja más rápida tiene tau 0,3 s
    "hz_salida": 20,
    "hz_telemetria": 20,  # una foto por paso de física
    "banda_muerta": 2,    # cuentas del PCA9685; menos que esto no va por I2C
}

# Arranque de a tandas: un servo pide ~700 mA al arrancar. Con 3 por tanda y
# 0,25 s son ~2,1 A de pico y menos de 2,5 s. Si el tablero se reinicia al
# encender, bajar canales_por_tanda.
ARRANQUE = {
    "canales_por_tanda": 3,
    "segundos_entre_tandas": 0.25,
}

# I2C 1: GPIO2 = SDA, GPIO3 = SCL. La placa 0 sin puentes (0x40), la 1 con A0 soldado (0x41)
I2C_BUS = 1
PLACAS = {"PCA0": 0x40, "PCA1": 0x41}

# Nominales de la hoja de datos del MG90S. Lo medido con calibrar_instrumento.py
# --transportador queda en calibracion_servos.json y pisa esto en ese canal
SERVO_CFG = {
    "pulso_min_us": 500,    # 0 grados
    "pulso_max_us": 2500,   # 180 grados
    "barrido_deg": 180.0,
    "frecuencia_hz": 50,    # 20 ms: 1 cuenta del PCA9685 = 4,88 us
    # tope para las calibraciones: algunos SG90 pasan de 500-2500. Más allá del
    # tope interno el servo zumba y no se acepta
    "pulso_limite_us": (200, 3000),
}

# Ánodo a +5 V (J8), cátodo por 220 ohm (R2..R7) al PCA9685 (J7): prende en BAJO.
# Al dar energía, antes del programa, las seis se prenden: si una no prende,
# está cortado el LED o el cable.
LUCES_ACTIVAS_EN_BAJO = True

# 28BYJ-48: la reducción no es 64, es (32/9)(22/11)(26/9)(31/10) = 63,684.
# Con 4096 la brújula se corría 1,8 grados por vuelta. Para comprobarlo:
# python3 probar_motor.py 1 --vueltas 10 y la aguja tiene que volver al mismo lugar
MOTOR_CFG = {
    "pasos_por_vuelta": 4075.77,  # medio paso, 0,088 grados c/u
    "vel_max_pps": 900,           # ~13 vueltas por minuto
    "vel_arranque_pps": 200,      # arranca sin perder pasos
    "aceleracion": 2000,          # pasos/s^2
    "soltar_tras_s": 0.5,
}

# Queda solo la brújula. pines: GPIO BCM a IN1..IN4, patas 1 a 4 de U2 en la
# placa madre. U1 (motor 0) quedó libre y su GPIO 26 lo usa la llave BATERÍA.
# sentido: la rosa ahora está pegada y se mueve una aguja de 47 mm; con 90 tiene
# que apuntar a la E (horario), por eso pasó de -1 a +1. Se ajusta con probar_motor.py
MOTORES = {
    1: {"id": "COMPASS", "pines": (12, 16, 20, 21), "sentido": 1},
}

# Llave BATERÍA, la única del panel que funciona (ver llave_apagado.py).
# Una pata a la 37 (GPIO 26) y la otra a la 39 (GND)
LLAVE_APAGADO = {
    "gpio": 26,           # BCM, sacado del lugar libre del motor 0
    "segundos": 2.0,      # en APAG antes del cartel, filtra un golpe
    "cuenta_s": 5.0,      # volver a ENC la cancela
}


# Geometría para dibujar el panel en la página; la simulación no la usa.
# La ubicación sale de una foto de cabina de un S-55; el contenido (escalas,
# arcos, canales) del reporte de aviónica del H-08 y del T.O. 1H-19A-1. Si no
# coinciden manda el reporte: no sabemos si la foto es de esta célula.
# pos: esquina sup. izq. en el lienzo; tam: diámetro con bisel. Las bocas de
# 122, 78, 58 y 48 mm quedan en 257, 168, 123 y 107, con 12 entre biseles.

# unidades de diseño, no píxeles: la app lo escala a la ventana
PANEL_LIENZO = (1209, 725)

# partes de la chapa negra; "tapa" es la tapa ciega donde iba el intercomunicador
PANEL_ZONAS = [
    {"id": "SW", "estilo": "llaves", "pos": (20, 20), "tam": (212, 464),
     "titulo": "PANEL PRINCIPAL"},
    # las luces pasaron al Main Switch Panel; acá van los mandos del motor
    {"id": "MOTOR", "estilo": "llaves", "pos": (976, 468.5), "tam": (213, 168),
     "titulo": "MANDOS DEL MOTOR"},
    {"id": "TAPA", "estilo": "tapa", "pos": (373.5, 623), "tam": (86, 86),
     "titulo": ""},
]

PANEL = {
    # columna de motor, transmisión y combustible (48 y 58 mm)
    "AMMETER":         {"zona": "MOTOR",  "dial": "aguja",     "pos": (244, 20),  "tam": 107, "corto": "Amperímetro",
                        "desc": "Muestra la corriente eléctrica de carga o descarga de la "
                                "batería. Negativo significa que la batería se está gastando."},
    "VOLTMETER":       {"zona": "MOTOR",  "dial": "aguja",     "pos": (363, 20), "tam": 107, "corto": "Voltímetro",
                        "desc": "Monitorea la tensión del barra eléctrica: 24 V con batería "
                                "sola, 28 V con el generador en línea."},

    "MAP":             {"zona": "VUELO", "dial": "aguja",     "pos": (796, 468.5),  "tam": 168, "corto": "Presión de admisión",
                        "desc": "Presión de admisión. Es la medida directa de la "
                                "POTENCIA que está entregando el motor."},
    "OIL_PRESS":       {"zona": "MOTOR", "dial": "aguja",     "pos": (363, 377),  "tam": 107, "corto": "Presión de aceite",
                        "desc": "Mide la presión de lubricación del motor. Es el instrumento "
                                "que primero avisa que un motor a pistón se está muriendo."},
    "OIL_TEMP":        {"zona": "MOTOR", "dial": "aguja",     "pos": (244, 377), "tam": 107, "corto": "Temp. de aceite",
                        "desc": "Monitorea la temperatura del aceite lubricante del motor "
                                "principal. Sube despacio: es una tendencia, no un evento."},
    "CHT":             {"zona": "MOTOR", "dial": "aguja",     "pos": (661, 491), "tam": 123, "corto": "Temp. de culata",
                        "desc": "Temperatura de cabeza de cilindro. Crucial para evitar el "
                                "sobrecalentamiento del motor radial a pistón."},
    "FUEL_PRESS":      {"zona": "MOTOR", "dial": "aguja",     "pos": (244, 258), "tam": 107, "corto": "Presión de combustible",
                        "desc": "Mide la presión del combustible suministrado al carburador. "
                                "Sin ella el motor no arranca ni se sostiene."},
    "CARB_AIR_TEMP":   {"zona": "MOTOR", "dial": "aguja",     "pos": (363, 258), "tam": 107, "corto": "Aire del carburador",
                        "desc": "Temperatura del aire en el carburador. Permite monitorear y "
                                "prevenir la formación de hielo en la inducción."},
    "XMSN_OIL_PRESS":  {"zona": "MOTOR", "dial": "aguja",     "pos": (363, 139), "tam": 107, "corto": "Presión transmisión",
                        "desc": "Lectura en tiempo real de la presión en la caja de "
                                "transmisión principal. Su bomba la mueve el rotor."},
    "XMSN_OIL_TEMP":   {"zona": "MOTOR", "dial": "aguja",     "pos": (244, 139), "tam": 107, "corto": "Temp. transmisión",
                        "desc": "Monitorea que la transmisión principal no sufra "
                                "sobrecalentamiento."},
    "FUEL_QTY_FWD":    {"zona": "MOTOR", "dial": "aguja",     "pos": (93, 496), "tam": 123, "corto": "Tanque delantero",
                        "desc": "Nivel de combustible disponible en el tanque delantero "
                                "(378 litros de capacidad)."},
    "FUEL_QTY_AFT":    {"zona": "MOTOR", "dial": "aguja",     "pos": (228, 496), "tam": 123, "corto": "Tanque trasero",
                        "desc": "Nivel de combustible disponible en el tanque trasero "
                                "(322 litros de capacidad)."},

    # sub-panel de vuelo (78 y 122 mm), en el orden de la chapa real
    "AIRSPEED":        {"zona": "VUELO", "dial": "aguja",     "pos": (482, 64.5),  "tam": 168, "corto": "Velocímetro",
                        "desc": "Indica la velocidad del helicóptero respecto al aire. "
                                "Vne del H-19A: 95 nudos. Es un instrumento NEUMÁTICO: "
                                "sigue funcionando sin energía eléctrica."},
    "ATT_ROLL":        {"zona": "VUELO", "dial": "horizonte", "pos": (662, 20),  "tam": 257, "corto": "Horizonte",
                        "desc": "Horizonte artificial. Instrumento giroscópico que muestra la "
                                "orientación en cabeceo y alabeo respecto del horizonte real."},
    "ALTIMETER":       {"zona": "VUELO", "dial": "altimetro", "pos": (482, 244.5),  "tam": 168, "corto": "Altímetro",
                        "desc": "Mide la altitud barométrica mediante presión estática. "
                                "Aguja larga: centenas de pies. Aguja corta: miles."},
    "TURN":            {"zona": "VUELO", "dial": "viraje",    "pos": (841, 288.5), "tam": 168, "corto": "Viraje",
                        "desc": "Indicador de viraje y ladeo. La aguja muestra el régimen de "
                                "giro; la bola, si el viraje está coordinado."},
    "TACH_ENG":        {"zona": "VUELO", "dial": "tacometro", "pos": (661, 288.5), "tam": 168, "corto": "Tacómetro",
                        "desc": "Tacómetro DOBLE. Aguja larga: RPM del motor (escala x100). "
                                "Aguja corta: RPM del rotor. Con el embrague acoplado la "
                                "relación es 10:1 y las agujas quedan SUPERPUESTAS. Si se "
                                "separan, la rueda libre desacopló: autorrotación."},
    "VSI":             {"zona": "VUELO", "dial": "aguja",     "pos": (482, 424.5), "tam": 168, "corto": "Variómetro",
                        "desc": "Variómetro. Indica la tasa de ascenso o descenso en pies por "
                                "minuto. Tiene un retardo propio de varios segundos."},

    "COMPASS":         {"zona": "VUELO", "dial": "brujula",   "pos": (931, 20), "tam": 257, "corto": "Brújula",
                        "desc": "Brújula giroscópica esclavizada. Proporciona el rumbo "
                                "magnético estabilizado del helicóptero."},
    "CLOCK":           {"zona": "MOTOR", "dial": "reloj",     "pos": (363, 504), "tam": 107, "corto": "Reloj",
                        "desc": "Reloj de cabina. Cronometraje para navegación, estimación de "
                                "tiempo y control de vuelo."},
    "VOR_CDI":         {"zona": "VUELO",   "dial": "cdi",       "pos": (1021, 288.5), "tam": 168, "corto": "Rumbo AN/ARN-14",
                        "desc": "Indicador de rumbo del receptor AN/ARN-14. Radionavegación: "
                                "la aguja vertical muestra el desvio respecto del radial."},
}

# se dibujan pero no llevan actuador: el reloj es mecánico, de cuerda
PANEL_VIRTUAL = [
    {"id": "CLOCK", "n": 21, "nombre": "Reloj de cabina",
     "en": "Cockpit clock, 8-day mechanical",
     "unidad": "h:mm:ss", "escala": (0.0, 43200.0), "arcos": [],
     "actuador": "MECANICO", "senal": "t_sim", "cal": []},
]

# En el orden del anunciador. leyenda en inglés como en cabina; pos/tam en las
# dos filas de arriba de la zona SW, igual que el sticker
ANUNCIADOR = [
    {"id": "LT_STARTER", "pos": (30, 100), "tam": (64, 20),     "leyenda": "IGNITION",   "color": "verde",
     "nombre": "Encendido",
     "desc": "Magnetos activos. Indica que el circuito de encendido está energizado."},
    {"id": "LT_GEN", "pos": (95, 100), "tam": (64, 20),      "leyenda": "GENERATOR",  "color": "rojo",
     "nombre": "Generador",
     "desc": "El generador principal dejó de suministrar energía. El avión queda "
             "alimentado solo por batería, con autonomía limitada."},
    {"id": "LT_XMSN_PRESS", "pos": (160, 100), "tam": (64, 20), "leyenda": "XMSN PRESS", "color": "rojo",
     "nombre": "Pres. transm.",
     "desc": "Baja presión de aceite en la caja de transmisión del rotor principal. Es la "
             "falla más peligrosa de un helicóptero: la autorrotación NO salva una "
             "transmisión agarrotada. Aterrizar cuanto antes."},
    {"id": "LT_LOW_ROTOR", "pos": (30, 124), "tam": (64, 20),    "leyenda": "LOW ROTOR",  "color": "rojo",
     "nombre": "Rotor bajo",
     "desc": "Régimen de rotor por debajo de 170. El empuje va con el CUADRADO de las RPM: "
             "por debajo del límite el rotor ya no sostiene la aeronave. Colectivo abajo."},
    {"id": "LT_FUEL_FWD", "pos": (95, 124), "tam": (64, 20),  "leyenda": "FUEL FWD",   "color": "ambar",
     "nombre": "Comb. del.",
     "desc": "Bajo nivel de combustible en el tanque DELANTERO. Se enciende por debajo "
             "de 45 litros. Hay que cambiar de tanque."},
    {"id": "LT_FUEL_AFT", "pos": (160, 124), "tam": (64, 20),    "leyenda": "FUEL AFT",   "color": "ambar",
     "nombre": "Comb. tras.",
     "desc": "Bajo nivel de combustible en el tanque TRASERO. Mismo umbral de 45 litros."},
]

# Panel principal del sticker de la chapa (20,5 x 24 cm), achicado a lo justo.
# En el tablero físico las llaves son decorativas, sin cablear; en la página
# se animan con el estado, así se ve qué hace el piloto virtual en cada fase.
#   tipo   tog, perilla, guardam, lampara, boton, texto, cartel, placa,
#          rotulo, palanca, guarda, rotativo, disyuntor, nota
#   senal  qué campo del estado lo mueve; inv: arriba cuando la señal es False
PANEL_CONMUTADORES = [
    # zona SW: las 6 luces (los LED reales) y la parte eléctrica
    {"tipo": "placa",  "pos": (50, 30), "tam": (152, 18), "texto": "PANEL PRINCIPAL", "sub": ""},
    {"tipo": "rotulo", "pos": (28, 78), "tam": (196, 12), "texto": "LUCES DE ALERTA"},

    {"tipo": "rotulo", "pos": (28, 170), "tam": (196, 12), "texto": "ELÉCTRICO"},
    {"tipo": "palanca", "id": "SW_BATT", "pos": (41, 208), "tam": (64, 78),
     "rot": "BATERÍA", "sub": "", "senal": "bateria",
     "desc": "Llave general de batería. Es la primera que se toca en el arranque y la "
             "última en el corte. Sin ella no hay barra eléctrica."},
    {"tipo": "guarda", "id": "GU_GEN", "pos": (94, 204), "tam": (64, 80),
     "rot": "GENERADOR", "sub": "", "senal": "generador",
     "desc": "Generador, con guarda roja para no apagarlo sin querer. Entra en línea cuando "
             "el motor pasa las 1000 RPM. Si falla, se enciende la luz GENERADOR."},
    {"tipo": "palanca", "id": "SW_INV", "pos": (147, 208), "tam": (64, 78),
     "rot": "INVERSOR", "sub": "", "senal": "energia",
     "desc": "Inversor de corriente alterna. Alimenta los giróscopos del horizonte "
             "artificial y de la brújula. Sigue a la barra principal."},

    {"tipo": "rotulo", "pos": (28, 322), "tam": (196, 12), "texto": "MOTOR E INSTRUMENTOS"},
    {"tipo": "palanca", "id": "SW_PRIME", "pos": (41, 359), "tam": (64, 78),
     "rot": "CEBADOR", "sub": "", "senal": "arrancador",
     "desc": "Cebador: inyecta nafta en los cilindros para el arranque. Se usa mientras "
             "gira el arrancador."},
    {"tipo": "palanca", "id": "SW_PUMP", "pos": (94, 359), "tam": (64, 78),
     "rot": "BOMBA", "rot2": "COMBUSTIBLE", "sub": "", "senal": "bomba",
     "desc": "Bomba eléctrica de combustible. Respalda a la bomba mecánica del motor en "
             "arranque, despegue y aterrizaje."},
    {"tipo": "palanca", "id": "SW_PITOT", "pos": (147, 359), "tam": (64, 78),
     "rot": "CALEFACCIÓN", "rot2": "PITOT", "sub": "", "senal": "bateria",
     "desc": "Calefacción del tubo pitot: evita que se tape con hielo y deje al velocímetro "
             "sin presión dinámica."},

    # Mandos del motor: en el H-19A están en el tablero y la consola, no en el
    # Main Switch Panel. Van acá porque los mueve el piloto virtual
    {"tipo": "rotulo", "pos": (984, 500), "tam": (196, 12), "texto": "MANDOS DEL MOTOR"},
    {"tipo": "rotativo", "id": "SEL_MAG", "pos": (984, 520), "tam": (49, 80),
     "rot": "MAGNETOS", "senal": "magnetos",
     "opciones": [["APAG", 0], ["IZQ", 1], ["DER", 2], ["AMB", 3]],
     "desc": "Llave de encendido (magnetos). En la prueba de run-up se pasa a IZQ y a DER para "
             "verificar que cada magneto sostiene el motor por si solo. La caida "
             "normal de RPM al aislar uno es de 50 a 100 RPM."},
    {"tipo": "guarda", "id": "SW_START", "pos": (1033, 520), "tam": (49, 80),
     "rot": "ARRANQUE", "sub": "", "senal": "arrancador",
     "desc": "Arranque, protegido con guarda roja para que no se accione por error. "
             "Mueve el motor con energía de batería hasta que enciende solo."},
    {"tipo": "guarda", "id": "SW_CLUTCH", "pos": (1082, 520), "tam": (49, 80),
     "rot": "EMBRAGUE", "sub": "", "senal": "embrague",
     "desc": "Embrague del rotor. Se acopla con el motor en ralentí para que el rotor "
             "empiece a girar. La rueda libre separa las dos agujas del tacómetro en autorrotación."},
    {"tipo": "rotativo", "id": "SEL_TANQUE", "pos": (1131, 520), "tam": (49, 80),
     "rot": "TANQUE", "senal": "tanque",
     "opciones": [["DEL", 0], ["AMB", 2], ["TRA", 1]],
     "desc": "Selector de tanque: delantero (378 L), ambos, o trasero (322 L). Una mala "
             "gestión de este selector es una causa clásica de corte de motor con "
             "combustible todavía a bordo."},
]

# vacía a propósito: la ficha y las limitaciones van en la memoria técnica
PANEL_PLACAS = []

# se vuelca todo en la tabla principal
for _it in list(TABLERO) + PANEL_VIRTUAL:
    _p = PANEL.get(_it["id"])
    if _p:
        _it["desc"] = _p["desc"]
        _it["zona"] = _p["zona"]
        _it["dial"] = _p["dial"]
        _it["pos"] = _p["pos"]
        _it["tam"] = _p["tam"]
        _it["corto"] = _p.get("corto", _it["nombre"])
for _a in ANUNCIADOR:
    _t = TABLERO_POR_ID.get(_a["id"])
    if _t:
        _t["desc"] = _a["desc"]
        _t["leyenda"] = _a["leyenda"]
        _t["dial"] = "luz"
