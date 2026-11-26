# -*- coding: utf-8 -*-
"""Catálogo de fallas como datos y el motor que las inyecta.

Una falla no toca agujas: degrada un sistema y el modelo hace el resto. Cortar
el motor es salud.motor = 0, y el tacómetro, el aceite, el generador y la luz
roja reaccionan solos. Las de tipo "ind" dejan la máquina bien y hacen mentir
al instrumento ("¿se cayó el helicóptero o se tapó la estática?").
"""

from utiles import limitar, mezclar
from senales import IND_CONGELADO, IND_FIJO, IND_RUIDO, IND_OSCILA

SEV_LEVE = "LEVE"
SEV_MEDIA = "MEDIA"
SEV_GRAVE = "GRAVE"
SEV_CRITICA = "CRITICA"

# para agrupar en la app
SIS_MOTOR = "MOTOR"
SIS_COMBUSTIBLE = "COMBUSTIBLE"
SIS_LUBRICACION = "LUBRICACION"
SIS_TRANSMISION = "TRANSMISION"
SIS_ELECTRICO = "ELECTRICO"
SIS_ROTORES = "ROTORES"
SIS_INSTRUMENTOS = "INSTRUMENTOS"


# Agregar una falla es sumar una entrada, sin tocar la lógica.
#   desarrollo    segundos hasta el efecto pleno (0 = instantánea)
#   intermitente  va y viene (mal contacto, obstrucción parcial)
#   instr         dónde lo debería ver el alumno
#   proc          procedimiento según el manual del tipo

CATALOGO = [

    # motor
    {
        "id": "ENG_FAIL_TOTAL",
        "nombre": "Falla total de motor",
        "sistema": SIS_MOTOR, "sev": SEV_CRITICA, "desarrollo": 0.6,
        "efectos": [{"t": "salud", "obj": "motor", "a": 0.0}],
        "instr": ["TACH_ENG", "TACH_ROT", "MAP", "OIL_PRESS", "CARB_AIR_TEMP",
                  "XMSN_OIL_PRESS", "VSI", "VOLTMETER", "AMMETER", "LT_GEN"],
        "sintomas": [
            "La aguja de MOTOR del tacómetro cae; la de ROTOR queda arriba: NEEDLE SPLIT",
            "La presión de admisión SUBE hasta la presión del campo, unas 30 inHg: "
            "sin mariposa aspirando, el manómetro absoluto marca la atmósfera",
            "La presión de aceite del MOTOR se desploma a cero en pocos segundos",
            "La presión de aceite de la TRANSMISIÓN se mantiene: la bomba de la caja "
            "la mueve el rotor, que sigue girando. Por eso la autorrotación es viable",
            "El termómetro de aire de carburador sube hasta la temperatura exterior: "
            "sin aire pasando por el venturi ya no hay enfriamiento",
            "El generador sale de línea: luz roja, voltímetro a 23 V bajando y "
            "amperímetro en descarga",
            "El variómetro se clava en 1500-1800 ft/min de descenso",
        ],
        "proc": "Colectivo abajo INMEDIATAMENTE para entrar en autorrotación. "
                "Mantener 170-245 RPM de rotor. Velocidad de mínimo descenso "
                "aprox. 52 kt. Buscar zona de aterrizaje sobre la nariz.",
    },
    {
        "id": "ENG_FAIL_PARTIAL",
        "nombre": "Pérdida parcial de potencia",
        "sistema": SIS_MOTOR, "sev": SEV_GRAVE, "desarrollo": 25.0,
        "efectos": [{"t": "salud", "obj": "motor", "a": 0.45}],
        "instr": ["MAP", "TACH_ENG", "TACH_ROT", "LT_LOW_ROTOR", "VSI"],
        "sintomas": [
            "MUCHA ADMISIÓN Y POCA POTENCIA: el gobernador abre la mariposa "
            "buscando régimen y la presión de admisión SUBE de 23 a 35 inHg, "
            "pero las RPM igual se caen. Es al revés de lo que uno espera",
            "Las dos agujas del tacómetro bajan JUNTAS, sin separarse: el "
            "embrague sigue tomando, lo que falta es potencia",
            "El rotor entra al arco rojo y se enciende la luz de RPM bajas",
            "El helicóptero no sostiene la altura ni el estacionario",
        ],
        "proc": "Reducir demanda de potencia, ganar velocidad de traslación, "
                "planificar aterrizaje con potencia parcial. No exigir colectivo. "
                "La combinación admisión alta + RPM bajas es la firma del motor "
                "enfermo, y distingue esta falla del patinaje de embrague.",
    },
    {
        "id": "MAG_L_FAIL",
        "nombre": "Falla del magneto izquierdo",
        "sistema": SIS_MOTOR, "sev": SEV_MEDIA, "desarrollo": 0.3,
        "efectos": [{"t": "salud", "obj": "magneto_l", "a": 0.0}],
        "instr": ["TACH_ENG", "MAP", "CHT"],
        "sintomas": [
            "EN TIERRA, con la mariposa fija: caída de unas 80-90 RPM (4%). "
            "Es la prueba de magnetos del run-up y es donde se detecta",
            "EN VUELO, con el gobernador manteniendo régimen: las RPM NO bajan. "
            "El gobernador abre la mariposa y lo que sube es la presión de "
            "admisión. La falla se esconde detrás del gobernador",
            "La temperatura de culata sube unos 15 C: con una sola bujía por "
            "cilindro la mezcla termina de quemarse más tarde",
            "Marcha áspera perceptible",
        ],
        "proc": "Verificable en la prueba de magnetos del run-up. "
                "Con un solo magneto el motor funciona: no cortar, regresar. "
                "Vigilar la culata, que es el instrumento que delata la falla "
                "cuando el gobernador tapa la caída de RPM.",
    },
    {
        "id": "CARB_ICE",
        "nombre": "Engelamiento de carburador",
        "sistema": SIS_MOTOR, "sev": SEV_GRAVE, "desarrollo": 1.0,
        "efectos": [
            {"t": "amb", "obj": "humedad", "a": 0.95},
            {"t": "amb", "obj": "oat_c", "a": 6.0},
        ],
        "instr": ["MAP", "CARB_AIR_TEMP", "TACH_ENG", "TACH_ROT", "LT_LOW_ROTOR"],
        "sintomas": [
            "El termómetro de aire de carburador cae a la banda de riesgo, "
            "entre -10 y +15 C. Es el PRIMER instrumento que avisa, minutos "
            "antes que cualquier otro",
            "Durante uno o dos minutos NO PASA NADA MÁS: el gobernador va "
            "abriendo la mariposa a medida que el hielo estrangula, y sostiene "
            "el régimen. La aguja de admisión se queda quieta y engaña",
            "Cuando la mariposa se queda sin recorrido, todo se cae junto: "
            "admisión, RPM de motor y RPM de rotor, en menos de un minuto",
            "El engelamiento es un fenómeno de BAJA potencia: la depresión del "
            "venturi es máxima con la mariposa casi cerrada. Por eso aparece en "
            "descenso y en aproximación, no en el despegue",
        ],
        "proc": "Aplicar CALEFACCIÓN DE CARBURADOR completa. La MAP baja un poco "
                "más al principio (aire caliente menos denso) y luego se recupera "
                "al derretirse el hielo. Falla clásica del R-1340.",
    },
    {
        "id": "ENG_ROUGH",
        "nombre": "Marcha áspera / detonación",
        "sistema": SIS_MOTOR, "sev": SEV_MEDIA, "desarrollo": 8.0,
        "intermitente": True,
        "efectos": [
            {"t": "salud", "obj": "motor", "a": 0.80},
            {"t": "salud", "obj": "refrigeracion", "a": 0.78},
            {"t": "ind", "obj": "n_eng_rpm", "modo": IND_RUIDO, "a": 55.0},
            {"t": "ind", "obj": "map_inhg", "modo": IND_OSCILA, "a": 1.2},
        ],
        "instr": ["TACH_ENG", "MAP", "CHT"],
        "sintomas": [
            "Las agujas de RPM y de admisión tiemblan y oscilan: el temblor "
            "es del MOTOR, no del instrumento",
            "La temperatura de culata sube despacio pero no para: la "
            "detonación quema mal y calienta la cabeza del cilindro",
            "Es intermitente. Aparece y desaparece, y esa es la trampa: "
            "invita a seguir volando",
        ],
        "proc": "Enriquecer mezcla, verificar calefacción de carburador, "
                "reducir potencia y aterrizar en cuanto sea practicable. "
                "Comparar con la falla de INDICACIÓN del tacómetro: si tiemblan "
                "las agujas pero la culata no se mueve, es el instrumento.",
    },

    # lubricación
    {
        "id": "OIL_PRESS_LOSS",
        "nombre": "Pérdida de presión de aceite de motor",
        "sistema": SIS_LUBRICACION, "sev": SEV_CRITICA, "desarrollo": 45.0,
        "efectos": [
            {"t": "salud", "obj": "bomba_aceite", "a": 0.08},
            {"t": "salud", "obj": "refrigeracion", "a": 0.65},
        ],
        "instr": ["OIL_PRESS", "OIL_TEMP", "CHT"],
        "sintomas": [
            "La presión de aceite cae por debajo del arco verde y sigue: "
            "de 78 psi a menos de 10 psi en menos de un minuto",
            "El ORDEN importa: primero cae la presión, y RECIÉN DESPUÉS suben "
            "la culata y la temperatura de aceite. Esa demora de medio minuto "
            "es la que distingue esta falla de la del instrumento",
            "La culata se va al arco rojo y pasa los 260 C",
            "La transmisión NO se entera: tiene su propio circuito de aceite",
        ],
        "proc": "Aterrizar cuanto antes. La pérdida de presión de aceite en un "
                "radial lleva a agarrotamiento en minutos. Reducir potencia.",
    },
    {
        "id": "OIL_OVERHEAT",
        "nombre": "Sobretemperatura de aceite",
        "sistema": SIS_LUBRICACION, "sev": SEV_MEDIA, "desarrollo": 90.0,
        # se tapa el enfriador, no los deflectores: sube el aceite y la culata
        # casi no se entera. Así se distingue del sobrecalentamiento de cilindros
        "efectos": [{"t": "salud", "obj": "refrigeracion_aceite", "a": 0.40}],
        "instr": ["OIL_TEMP", "CHT", "OIL_PRESS"],
        "sintomas": [
            "La temperatura de aceite pasa el máximo de 85 C y sigue subiendo "
            "hacia el fondo de escala",
            "LA CULATA CASI NO SE MUEVE. El aceite tiene su propio radiador, "
            "separado del aire que refrigera los cilindros: acá lo que se tapó "
            "es ese radiador. Aceite alto con culata normal es problema del "
            "enfriador de aceite; las dos altas juntas es problema de "
            "refrigeración general",
            "La presión de aceite BAJA a medida que sube la temperatura. "
            "El aceite caliente es más fluido y se escurre por los mismos "
            "huecos: es el mismo efecto que hace que en el arranque en frío "
            "la aguja se clave arriba, pero al revés",
        ],
        "proc": "Aumentar velocidad de traslación para mejorar la refrigeración, "
                "reducir potencia, evitar el vuelo estacionario prolongado. "
                "Aguja de temperatura arriba Y aguja de presión abajo, las dos "
                "a la vez, es sobretemperatura; presión abajo con temperatura "
                "normal es pérdida de presión.",
    },
    {
        "id": "CHT_OVERHEAT",
        "nombre": "Sobrecalentamiento de cabezas de cilindro",
        "sistema": SIS_MOTOR, "sev": SEV_GRAVE, "desarrollo": 70.0,
        "efectos": [
            {"t": "salud", "obj": "refrigeracion", "a": 0.30},
            {"t": "salud", "obj": "motor", "a": 0.85},
        ],
        "instr": ["CHT", "OIL_TEMP", "MAP", "TACH_ENG"],
        "sintomas": [
            "La culata pasa los 232 C de límite en tierra, después los 260 C "
            "de límite absoluto, y termina apoyada contra el fondo de escala",
            "La temperatura de aceite la sigue de atrás, más despacio",
            "Pasado el límite aparece la DETONACIÓN: el motor pierde fuerza, "
            "el gobernador abre mariposa, sube la admisión y las RPM igual no "
            "vuelven. La aguja de culata deja de subir porque el motor ya no "
            "está dando la potencia que la calentaba",
            "Una aguja de culata contra el tope no dice cuánto: dice que se acabó",
        ],
        "proc": "Enriquecer mezcla, bajar colectivo, ganar velocidad. "
                "Si no baja, aterrizar de inmediato: riesgo de incendio.",
    },

    # combustible
    {
        "id": "FUEL_PUMP_FAIL",
        "nombre": "Falla de bomba de combustible",
        "sistema": SIS_COMBUSTIBLE, "sev": SEV_GRAVE, "desarrollo": 3.0,
        "efectos": [{"t": "salud", "obj": "bomba_combustible", "a": 0.55}],
        "instr": ["FUEL_PRESS", "MAP", "TACH_ENG", "TACH_ROT"],
        "sintomas": [
            "La presión de combustible cae de 16 psi a menos de 9 y se queda "
            "ahí: por debajo del mínimo de 12 psi, fuera del arco verde",
            "El motor NO se para. Se queda sin fuerza: el carburador recibe "
            "menos caudal del que pide y la potencia disponible se recorta",
            "En crucero el motor SIGUE ANDANDO Y MANTIENE EL RÉGIMEN. Lo único "
            "que cambia es que el gobernador tiene que abrir más mariposa: la "
            "admisión sube de 23 a 27 inHg para dar la misma potencia",
            "Esa es toda la evidencia en vuelo nivelado: una aguja de presión "
            "de combustible baja y una de admisión un poco alta. Se nota "
            "recién cuando se pide potencia -en un ascenso o en un "
            "estacionario-, que es donde más caudal hace falta y donde el "
            "motor no va a responder",
        ],
        "proc": "Conectar bomba de emergencia. Reducir potencia. "
                "Aterrizar tan pronto como sea practicable.",
    },
    {
        "id": "FUEL_LEAK",
        "nombre": "Pérdida de combustible",
        "sistema": SIS_COMBUSTIBLE, "sev": SEV_GRAVE, "desarrollo": 5.0,
        "efectos": [{"t": "suma", "obj": "fuga_combustible_lph", "a": 1500.0}],
        "instr": ["FUEL_QTY_FWD", "FUEL_QTY_AFT", "LT_FUEL_FWD"],
        "sintomas": [
            "LOS DOS AFORADORES SE SEPARAN. El de adelante se desploma; el de "
            "atrás sigue bajando al ritmo normal de consumo",
            "Esa asimetría es toda la falla: un motor consume de los dos por "
            "igual, una cañería rota pierde de UNO solo. Por eso se puede "
            "identificar el tanque y cerrarlo",
            "El tanque delantero se vacía en unos 15 minutos en vez de las "
            "2 horas y media que le corresponden: unos 80 litros cada tres "
            "minutos, contra 4 del trasero",
            "Más adelante se enciende la luz ambar del tanque delantero mucho "
            "antes de lo calculado, y la del trasero no",
            "Ningún instrumento de motor se entera hasta que el tanque se seca",
        ],
        "proc": "Identificar el tanque afectado y seleccionar el otro. "
                "Recalcular autonomía. Aterrizaje precautorio. "
                "La comparación entre los dos aforadores es el diagnóstico: "
                "un solo aforador no dice nada, los dos juntos dicen todo.",
    },
    {
        "id": "FUEL_STARVATION",
        "nombre": "Agotamiento del tanque seleccionado",
        "sistema": SIS_COMBUSTIBLE, "sev": SEV_CRITICA, "desarrollo": 0.5,
        "efectos": [
            {"t": "estado", "obj": "fuel_fwd_l", "a": 0.0},
            {"t": "ctl", "obj": "selector_tanque", "a": 0},
        ],
        "instr": ["FUEL_QTY_FWD", "FUEL_QTY_AFT", "LT_FUEL_FWD", "FUEL_PRESS",
                  "TACH_ENG", "TACH_ROT", "OIL_PRESS"],
        "sintomas": [
            "El aforador delantero en cero y su luz ambar encendida, con el "
            "TRASERO LLENO: hay combustible a bordo, pero no en el tanque "
            "que está seleccionado",
            "La presión de combustible se desploma a cero: la bomba está "
            "chupando aire",
            "Unos segundos después el motor se para, y aparece el needle "
            "split de la autorrotación",
            "Es la falla más evitable de todas: la información estaba en el "
            "tablero mucho antes de que pasara nada",
        ],
        "proc": "CAMBIAR DE TANQUE inmediatamente. Bomba de refuerzo conectada. "
                "El motor rearranca solo si las RPM de rotor se mantienen.",
    },

    # transmisión
    {
        "id": "XMSN_PRESS_LOSS",
        "nombre": "Pérdida de presión de aceite de transmisión",
        "sistema": SIS_TRANSMISION, "sev": SEV_CRITICA, "desarrollo": 30.0,
        "efectos": [{"t": "salud", "obj": "transmision_bomba", "a": 0.10}],
        "instr": ["XMSN_OIL_PRESS", "XMSN_OIL_TEMP", "LT_XMSN_PRESS", "OIL_PRESS"],
        "sintomas": [
            "La presión de transmisión cae de 54 psi a menos de 30 y se "
            "enciende la luz roja",
            "La temperatura de transmisión empieza a subir DESPUÉS, y no para: "
            "de 85 C pasa el rojo de 110 C en poco más de un minuto",
            "La presión de aceite del MOTOR sigue perfecta, y la culata "
            "también. Son dos circuitos de aceite distintos y esta falla toca "
            "uno solo. Confundirlos manda a cortar el motor, que es lo peor "
            "que se puede hacer acá",
        ],
        "proc": "ATERRIZAR CUANTO ANTES. La caja principal sin lubricación es "
                "la falla más peligrosa de un helicóptero: no hay autorrotación "
                "que salve una transmisión agarrotada.",
    },
    {
        "id": "XMSN_OVERHEAT",
        "nombre": "Sobretemperatura de transmisión",
        "sistema": SIS_TRANSMISION, "sev": SEV_GRAVE, "desarrollo": 100.0,
        "efectos": [{"t": "salud", "obj": "transmision_refrig", "a": 0.28}],
        "instr": ["XMSN_OIL_TEMP", "XMSN_OIL_PRESS", "TACH_ROT"],
        "sintomas": [
            "La temperatura de transmisión sube despacio y sin pausa hacia el "
            "arco rojo de 110 C, y termina contra el fondo de escala",
            "La PRESIÓN de transmisión no se mueve: la bomba está sana, lo que "
            "falla es la refrigeración. Presión buena con temperatura alta es "
            "el problema de enfriamiento; presión mala con temperatura alta es "
            "la bomba",
            "Ningún instrumento de motor acusa recibo",
        ],
        "proc": "Reducir potencia, aumentar velocidad, aterrizaje precautorio.",
    },
    {
        "id": "CLUTCH_SLIP",
        "nombre": "Patinaje del embrague principal",
        "sistema": SIS_TRANSMISION, "sev": SEV_GRAVE, "desarrollo": 15.0,
        "efectos": [{"t": "salud", "obj": "embrague", "a": 0.25}],
        "instr": ["TACH_ENG", "TACH_ROT", "XMSN_OIL_TEMP", "MAP", "LT_LOW_ROTOR"],
        "sintomas": [
            "LAS DOS AGUJAS DEL TACÓMETRO SE SEPARAN CON EL MOTOR ANDANDO. "
            "El motor arriba, incluso pasado de vueltas; el rotor abajo",
            "Es el needle split AL REVÉS del de la autorrotación: allá cae la "
            "aguja de motor y queda arriba la de rotor. Acá pasa lo contrario, "
            "y por eso las dos agujas en una sola esfera valen tanto",
            "La temperatura de transmisión sube y no para: toda la potencia "
            "que el embrague no transmite se está convirtiendo en calor ahí "
            "adentro. Es la confirmación de que lo que patina es el embrague",
            "La presión de transmisión ACOMPAÑA la caída del rotor, porque la "
            "bomba de la caja gira con el rotor",
        ],
        "proc": "Reducir potencia suavemente. Evitar cambios bruscos de colectivo. "
                "Aterrizar de inmediato.",
    },

    # rotores
    {
        "id": "LOW_ROTOR_RPM",
        "nombre": "RPM de rotor bajas",
        "sistema": SIS_ROTORES, "sev": SEV_CRITICA, "desarrollo": 6.0,
        "efectos": [{"t": "salud", "obj": "motor", "a": 0.30}],
        "instr": ["TACH_ROT", "TACH_ENG", "LT_LOW_ROTOR", "MAP", "VSI",
                  "XMSN_OIL_PRESS"],
        "sintomas": [
            "La aguja de ROTOR baja del arco verde de 170-245 RPM y entra al "
            "arco rojo. Se enciende la luz de RPM bajas",
            "Las dos agujas bajan JUNTAS: el embrague sigue tomando, así que "
            "el motor cae con el rotor. No hay separación",
            "La presión de admisión sube al tope, porque el gobernador abre "
            "todo lo que tiene buscando régimen",
            "La presión de aceite de TRANSMISIÓN baja también: su bomba la "
            "mueve el rotor, y el rotor está lento",
            "El variómetro pasa a descenso: sin RPM no hay sustentación",
        ],
        "proc": "COLECTIVO ABAJO y mariposa adelante. Recuperar RPM antes que "
                "altura. Un rotor por debajo del límite no se recupera.",
    },
    {
        "id": "TAIL_ROTOR_LOSS",
        "nombre": "Pérdida de efectividad del rotor de cola",
        "sistema": SIS_ROTORES, "sev": SEV_CRITICA, "desarrollo": 2.0,
        "efectos": [{"t": "salud", "obj": "rotor_cola", "a": 0.05}],
        "instr": ["SLIP", "COMPASS", "TURN", "ATT_ROLL"],
        "sintomas": [
            "LA BOLA SE VA A UN COSTADO Y SE QUEDA AHÍ, contra el tope. Es el "
            "instrumento que más grita, y es el más barato del tablero",
            "El indicador de rumbo gira sin parar y no vuelve nunca: la "
            "aeronave está guiñando de forma permanente",
            "La aguja de viraje NO se va al tope: marca un viraje permanente "
            "de unos 4 a 5 grados por segundo, dos tercios de escala. A "
            "velocidad de traslación el estabilizador vertical aguanta parte "
            "del par, y la guiñada queda rápida pero incontenible. Por eso el "
            "procedimiento es mantener velocidad, no frenar",
            "ENTRAR EN AUTORROTACIÓN DETIENE LA GUIÑADA: sin par transmitido "
            "por el árbol no hay reacción sobre el fuselaje. Las tres agujas "
            "vuelven solas -viraje a cero, bola al centro, rumbo quieto- sin "
            "tocar el pedal",
            "El horizonte artificial muestra un alabeo que el piloto no pidió",
            "Todos los instrumentos de motor siguen normales: el motor está "
            "perfecto, lo que se perdió es el control de guiñada",
        ],
        "proc": "Entrar en autorrotación para eliminar el par del rotor principal. "
                "Aterrizaje con recorrida a velocidad de traslación. "
                "NO frenar en el aire: cuanto menos velocidad, menos ayuda el "
                "estabilizador vertical y más rápido gira.",
    },

    # eléctrico
    {
        "id": "GEN_FAIL",
        "nombre": "Falla del generador",
        "sistema": SIS_ELECTRICO, "sev": SEV_MEDIA, "desarrollo": 1.5,
        "efectos": [{"t": "salud", "obj": "generador", "a": 0.0}],
        "instr": ["VOLTMETER", "AMMETER", "LT_GEN", "FUEL_QTY_FWD", "XMSN_OIL_TEMP"],
        "sintomas": [
            "Luz roja de generador y disyuntor saltado en el panel izquierdo",
            "El voltímetro cae de 28 V a 23 V de golpe -que es la tensión de "
            "la batería sola- y a partir de ahí sigue bajando despacio",
            "El amperímetro pasa de carga a DESCARGA y se queda ahí: es la "
            "aguja que dice cuánto tiempo queda",
            "Al principio no muere ningún otro instrumento. La falla no se "
            "siente: se lee. Ese es todo el ejercicio",
            "Recién cuando la barra baja de 20 V empiezan a caerse los "
            "instrumentos eléctricos, y ahí ya es tarde",
        ],
        "proc": "Desconectar cargas no esenciales. Autonomía de batería limitada. "
                "Aterrizar antes de perder los instrumentos eléctricos.",
    },
    {
        "id": "BATTERY_WEAK",
        "nombre": "Batería degradada",
        "sistema": SIS_ELECTRICO, "sev": SEV_MEDIA, "desarrollo": 4.0,
        "efectos": [
            {"t": "salud", "obj": "bateria", "a": 0.62},
            {"t": "estado", "obj": "bateria_ah", "a": 6.0},
        ],
        "instr": ["AMMETER", "VOLTMETER"],
        "sintomas": [
            "EN VUELO, con el generador en línea, el único instrumento que "
            "acusa la falla es el AMPERÍMETRO: marca una corriente de carga "
            "alta -80 a 120 A en vez de los 25 A normales- y no baja nunca",
            "Una batería sana toma mucha corriente un rato y después se "
            "aquieta. Una batería sulfatada sigue pidiendo para siempre, "
            "porque no llega a cargarse",
            "El voltímetro NO avisa: mientras el generador esté en línea, "
            "sostiene la barra en 28 V y tapa el problema",
            "La falla aparece recién cuando el generador sale de línea, o en "
            "el próximo arranque: la aguja se desploma y el arrancador no da",
        ],
        "proc": "No apagar el generador. Evitar rearranques en vuelo. "
                "Es el caso donde el amperímetro -el instrumento más ignorado "
                "del tablero- es el único que está informando algo.",
    },
    {
        "id": "ELEC_TOTAL",
        "nombre": "Falla eléctrica total",
        "sistema": SIS_ELECTRICO, "sev": SEV_CRITICA, "desarrollo": 3.0,
        "efectos": [
            {"t": "salud", "obj": "generador", "a": 0.0},
            {"t": "salud", "obj": "bateria", "a": 0.05},
        ],
        "instr": ["VOLTMETER", "AMMETER", "FUEL_QTY_FWD", "FUEL_QTY_AFT",
                  "OIL_TEMP", "XMSN_OIL_PRESS", "XMSN_OIL_TEMP", "CARB_AIR_TEMP",
                  "ATT_ROLL", "COMPASS",
                  "TACH_ENG", "TACH_ROT", "OIL_PRESS", "MAP", "CHT",
                  "AIRSPEED", "ALTIMETER", "VSI"],
        "sintomas": [
            "SE CAEN: los dos aforadores de combustible, la temperatura de "
            "aceite, la de aire de carburador, y la presión y la temperatura "
            "de transmisión. Todos van a cero en pocos segundos",
            "SOBREVIVEN: velocímetro, altímetro y variómetro, que son "
            "NEUMÁTICOS; el tacómetro doble, que tiene su propio generador; "
            "los manómetros de aceite, combustible y admisión, que son de tubo "
            "Bourdon; la culata, que es una termocupla; y el reloj, que es a "
            "cuerda. Con eso se vuela y se aterriza",
            "SE APAGAN TAMBIÉN TODAS LAS LUCES DE ALERTA, incluida la del "
            "generador que causó todo. El tablero queda sin una sola luz roja "
            "en la peor emergencia eléctrica posible. Es lo más contraintuitivo "
            "del ejercicio y hay que mostrarlo",
            "EL HORIZONTE Y EL INDICADOR DE RUMBO NO SE APAGAN: SE CAEN. "
            "Siguen indicando durante uno o dos minutos mientras el giro pierde "
            "vueltas, mostrando un alabeo y un rumbo que ya no existen. Un "
            "instrumento apagado avisa; uno que miente, no",
            "La presión de combustible baja de 16 a 9 psi -se cayó la bomba de "
            "refuerzo, queda la mecánica del motor- pero el motor sigue andando",
        ],
        "proc": "Vuelo visual con los instrumentos que quedan. Aterrizar de "
                "inmediato, mientras los giróscopos todavía conserven inercia. "
                "Excelente ejercicio para explicar por qué un tablero mezcla "
                "instrumentos eléctricos, neumáticos y mecánicos: no es "
                "desprolijidad, es redundancia.",
    },

    # instrumentos (fallas de indicación)
    {
        "id": "PITOT_BLOCK",
        "nombre": "Obstrucción del tubo pitot",
        "sistema": SIS_INSTRUMENTOS, "sev": SEV_MEDIA, "desarrollo": 4.0,
        "efectos": [
            {"t": "ind", "obj": "ias_kt", "modo": IND_CONGELADO},
        ],
        "instr": ["AIRSPEED", "ALTIMETER", "VSI"],
        "sintomas": [
            "El velocímetro queda CLAVADO en el último valor y no se mueve "
            "más, aunque cambien la actitud, la potencia y la altura",
            "El altímetro y el variómetro siguen andando perfectos: comparten "
            "la toma estática, pero el pitot es solo del velocímetro",
            "TODO el resto del tablero es coherente y normal. Ese es el dato: "
            "una aeronave que de verdad perdiera velocidad tendría el rotor "
            "cayendo, la admisión moviéndose y el variómetro en descenso",
            "Un instrumento que no coincide con ningún otro es un instrumento "
            "roto, no una aeronave rota",
        ],
        "proc": "Reconocer que la falla es del INSTRUMENTO, no de la aeronave. "
                "Volar por actitud y potencia. Aplicar calefacción de pitot.",
    },
    {
        "id": "STATIC_BLOCK",
        "nombre": "Obstrucción de la toma estática",
        "sistema": SIS_INSTRUMENTOS, "sev": SEV_GRAVE, "desarrollo": 4.0,
        # el error del velocímetro lo calcula el modelo (ias_ind_kt): depende
        # de cuánto se aleje de la altura en que se tapó
        "efectos": [
            {"t": "salud", "obj": "estatica", "a": 0.0},
            {"t": "ind", "obj": "alt_ind_ft", "modo": IND_CONGELADO},
            {"t": "ind", "obj": "alt_centenas", "modo": IND_CONGELADO},
            {"t": "ind", "obj": "vs_ind_fpm", "modo": IND_FIJO, "a": 0.0},
        ],
        "instr": ["ALTIMETER", "VSI", "AIRSPEED"],
        "sintomas": [
            "El altímetro se congela en la altura que había cuando se tapó la "
            "toma, y ahí se queda",
            "El variómetro cae a cero y se queda en cero: la aeronave puede "
            "estar subiendo o bajando y la aguja marca vuelo nivelado",
            "EL VELOCÍMETRO ES EL PEOR DE LOS TRES, porque no se congela: "
            "MIENTE, y miente cada vez más. Mientras se vuele a la misma "
            "altura no hay ningún error. Al subir indica DE MENOS, al bajar "
            "indica DE MÁS, y el error crece con la diferencia de altura",
            "El error en el ascenso es el peligroso: hace creer que se está "
            "lento, e invita a bajar la nariz para ganar una velocidad que en "
            "realidad ya se tiene",
            "Los tres comparten la misma toma estática. Tres instrumentos "
            "raros al mismo tiempo apuntan a la cañería, no a los instrumentos",
        ],
        "proc": "Usar la fuente estática alternativa. Los tres instrumentos "
                "afectados comparten la misma toma: eso explica la falla común. "
                "Mientras tanto, volar por actitud y potencia, y desconfiar del "
                "velocímetro cada vez que se cambie de altura.",
    },
    {
        "id": "GYRO_FAIL",
        "nombre": "Falla giroscópica (horizonte y brújula)",
        "sistema": SIS_INSTRUMENTOS, "sev": SEV_GRAVE, "desarrollo": 20.0,
        # la deriva la hace _paso_giroscopos, con los topes del instrumento real
        "efectos": [
            {"t": "salud", "obj": "vacio_giro", "a": 0.0},
        ],
        "instr": ["ATT_PITCH", "ATT_ROLL", "COMPASS", "TURN", "SLIP"],
        "sintomas": [
            "NO HAY BANDERA, NO HAY LUZ, NO HAY RUIDO. Los dos instrumentos "
            "siguen indicando como si nada",
            "El horizonte artificial tarda cerca de un minuto en caerse, y "
            "mientras se cae va inclinando la barra: termina mostrando un "
            "alabeo de 20 a 30 grados con la aeronave perfectamente nivelada",
            "El indicador de rumbo se va girando solo, unos 2 grados por "
            "segundo, sin que la aeronave vire",
            "EL INDICADOR DE VIRAJE Y LA BOLA SIGUEN BIEN: el de viraje es un "
            "giróscopo distinto y la bola no es más que un peso en un tubo con "
            "líquido. Son el respaldo, y son los dos instrumentos más baratos "
            "del tablero",
            "El contraste es el diagnóstico: horizonte inclinado con bola "
            "centrada y aguja de viraje en cero significa que el que miente es "
            "el horizonte",
        ],
        "proc": "Falla insidiosa: no hay bandera. Contrastar con el indicador "
                "de viraje y con la brújula magnética de respaldo. "
                "Un giróscopo que se queda sin alimentación no se apaga ni se "
                "congela: se vuelca despacio, y sigue indicando.",
    },
    {
        "id": "OILP_GAGE_FAIL",
        "nombre": "Falla del INDICADOR de presión de aceite",
        "sistema": SIS_INSTRUMENTOS, "sev": SEV_LEVE, "desarrollo": 1.0,
        "efectos": [{"t": "ind", "obj": "oil_p_psi", "modo": IND_FIJO, "a": 0.0}],
        "instr": ["OIL_PRESS", "OIL_TEMP", "CHT", "TACH_ENG", "MAP"],
        "sintomas": [
            "La aguja de presión de aceite cae a cero en un segundo y se queda "
            "ahí, quieta y sin temblar",
            "PERO la temperatura de aceite y la de culata siguen exactamente "
            "donde estaban, y ahí no se mueven",
            "Las RPM, la admisión y el sonido del motor, normales",
            "COMPARAR CON LA PÉRDIDA REAL DE PRESIÓN: allá la aguja BAJA en "
            "unos 45 segundos, y a los 30 segundos siguientes empiezan a subir "
            "la culata y el aceite. Acá la aguja se va de golpe y no la "
            "acompaña nadie",
            "Una aguja que cae sola es un instrumento roto. Un sistema que "
            "falla arrastra a sus vecinos",
        ],
        "proc": "EJERCICIO CLAVE: fallo el motor o fallo el instrumento? "
                "Si la presión fuera realmente cero, la temperatura subiría en "
                "segundos. Como no sube, la falla es del transductor.",
    },
    {
        "id": "TACH_GAGE_FAIL",
        "nombre": "Falla del tacómetro (indicación errática)",
        "sistema": SIS_INSTRUMENTOS, "sev": SEV_LEVE, "desarrollo": 1.0,
        "intermitente": True,
        "efectos": [
            {"t": "ind", "obj": "n_eng_rpm", "modo": IND_RUIDO, "a": 220.0},
            {"t": "ind", "obj": "n_rot_rpm", "modo": IND_OSCILA, "a": 18.0},
        ],
        "instr": ["TACH_ENG", "TACH_ROT", "MAP", "XMSN_OIL_PRESS", "CHT"],
        "sintomas": [
            "Las dos agujas saltan y oscilan sin que cambie nada más",
            "El sonido del motor, la admisión, la culata y la presión de "
            "transmisión están todos quietos y normales. Si las RPM se "
            "movieran de verdad, se moverían con ellas",
            "SALTAN LAS DOS AGUJAS A LA VEZ, y eso es el diagnóstico: cada "
            "aguja tiene su propio generador tacométrico -una en el motor, "
            "otra en la transmisión-. Que fallen las dos juntas apunta al "
            "instrumento o a su alimentación, no a los generadores",
            "Si saltara UNA SOLA, la falla estaría en el generador "
            "tacométrico de esa aguja o en su cableado",
        ],
        "proc": "Verificar el generador tacométrico y su cableado. "
                "Volar por sonido y por presión de admisión. "
                "Es una falla LEVE que parece grave: el tacómetro es el "
                "instrumento más mirado de un helicóptero y verlo saltar "
                "asusta más de lo que corresponde.",
    },
]

CATALOGO_POR_ID = {}
for _f in CATALOGO:
    CATALOGO_POR_ID[_f["id"]] = _f


class MotorFallas:
    """Antes de la física, en cada ciclo: salud a 1.0, sin anomalías, y se
    reaplican las fallas activas escaladas por su progreso.

    Reaplicar en vez de acumular hace que quitar una falla sea limpio y que el
    estado no quede sucio después de muchos cambios de modo.
    """

    def __init__(self, modelo, bus):
        self.m = modelo
        self.bus = bus
        self.activas = {}          # id -> {"t": s desde que se activó, "def": dict}
        self._fase = 0.0

    def activar(self, id_falla):
        d = CATALOGO_POR_ID.get(id_falla)
        if d is None:
            return False
        if id_falla not in self.activas:
            # unicas: efectos de una vez ya aplicados, uno por uno (agotar un
            # tanque lo vacía y además mueve el selector)
            self.activas[id_falla] = {"t": 0.0, "def": d, "unicas": {}}
        return True

    def desactivar(self, id_falla):
        if id_falla in self.activas:
            del self.activas[id_falla]
            return True
        return False

    def limpiar(self):
        self.activas = {}

    def lista_activas(self):
        return list(self.activas.keys())

    def paso(self, dt):
        m = self.m
        m.salud.reiniciar()
        self.bus.limpiar_anomalias()
        self._fase += dt

        if not self.activas:
            return

        for id_falla in self.activas:
            st = self.activas[id_falla]
            st["t"] += dt
            d = st["def"]

            desarrollo = d.get("desarrollo", 0.0)
            p = 1.0 if desarrollo <= 0.0 else limitar(st["t"] / desarrollo, 0.0, 1.0)

            # onda cuadrada de ~1,4 s
            if d.get("intermitente"):
                if int(self._fase * 1.4) % 2 == 0:
                    p *= 0.15

            for ef in d["efectos"]:
                self._aplicar(ef, p, st)

    def _aplicar(self, ef, p, st):
        m = self.m
        tipo = ef["t"]
        obj = ef["obj"]
        clave = tipo + ":" + obj

        if tipo == "salud":
            # multiplicativa: dos fallas al mismo sistema dan 0.5 * 0.5 = 0.25
            actual = getattr(m.salud, obj)
            setattr(m.salud, obj, actual * mezclar(1.0, ef["a"], p))

        elif tipo == "suma":
            actual = getattr(m.salud, obj, None)
            if actual is not None:
                setattr(m.salud, obj, actual + ef["a"] * p)
            else:
                setattr(m, obj, getattr(m, obj) + ef["a"] * p)

        elif tipo == "estado":
            # una sola vez; si se reaplicara cada ciclo congelaría la variable
            if clave not in st["unicas"] and p >= 1.0:
                setattr(m, obj, ef["a"])
                st["unicas"][clave] = True

        elif tipo == "amb":
            setattr(m, obj, ef["a"])

        elif tipo == "ctl":
            if clave not in st["unicas"] and p >= 1.0:
                setattr(m.ctl, obj, ef["a"])
                st["unicas"][clave] = True

        elif tipo == "ind":
            if p > 0.5:
                self.bus.agregar_anomalia(obj, ef["modo"], ef.get("a", 0.0))
