# -*- coding: utf-8 -*-
"""Perfil de vuelo normal (Modo 1) y guiones de emergencia (Modo 2).

Ninguno toca un instrumento: mueven mandos y salud de los sistemas, y las
agujas salen solas.
"""

from modelo_vuelo import MAG_OFF, MAG_L, MAG_R, MAG_BOTH
from modelo_vuelo import TANQUE_FWD, TANQUE_AFT, TANQUE_AMBOS

# Modo 1. Se pasa de fase por tiempo (dur, en s) o por condición física
# (hasta: ("variable", "op", valor)), nunca por dónde está una aguja.
# ctl se fija al entrar; obj es para el piloto virtual (alt_ft, ias_kt, hdg_deg, rpm).

PERFIL_NORMAL = [
    {
        "id": "FRIO", "nombre": "Aeronave fría y apagada", "dur": 6.0, "hasta": None,
        "ctl": {"bateria": False, "generador": False, "magnetos": MAG_OFF,
                "arrancador": False, "bomba_combustible": False, "embrague": False,
                "throttle": 0.0, "colectivo": 0.0, "luces_tablero": 0.0},
        "piloto": False, "obj": None,
        "texto": "Todo el tablero muerto. Ninguna aguja tiene energía: los "
                 "instrumentos eléctricos marcan cero y los neumáticos marcan "
                 "las condiciones ambientales.",
    },
    {
        "id": "BATERIA", "nombre": "Batería conectada", "dur": 8.0, "hasta": None,
        "ctl": {"bateria": True, "luces_tablero": 0.75},
        "piloto": False, "obj": None,
        "texto": "Al conectar la batería la barra sube a 24 V. Se encienden las "
                 "luces del tablero y despiertan los instrumentos eléctricos. "
                 "El amperímetro marca DESCARGA porque todavía no hay generador.",
    },
    {
        "id": "PREARRANQUE", "nombre": "Previo a la puesta en marcha", "dur": 8.0, "hasta": None,
        "ctl": {"bateria": True, "bomba_combustible": True,
                "selector_tanque": TANQUE_AMBOS, "luces_tablero": 0.75,
                "throttle": 0.10, "mezcla": 1.0, "calefaccion_carb": 0.0},
        "piloto": False, "obj": None,
        "texto": "Bomba de combustible conectada: la presión de combustible sube "
                 "al arco verde. Sin esa presión el motor no arranca.",
    },
    {
        "id": "ARRANQUE", "nombre": "Puesta en marcha del motor", "dur": 22.0,
        "hasta": ("n_eng_rpm", ">", 1250.0),
        "ctl": {"bateria": True, "bomba_combustible": True, "luces_tablero": 0.75,
                "magnetos": MAG_BOTH, "arrancador": True, "throttle": 0.14},
        "piloto": False, "obj": None,
        "texto": "Mirar el TACOMETRO: primero el arrancador ARRASTRA el motor "
                 "a unas 200 RPM, y recien despues el motor PRENDE y acelera "
                 "solo. Mientras arrastra, el amperimetro se va al tope de "
                 "descarga y la barra se hunde a 18 V: los aforadores y las "
                 "temperaturas marcan de menos porque son electricos, pero el "
                 "tacometro y el manometro de aceite siguen bien porque no "
                 "dependen de la barra. Y la presion de admision BAJA de 30 a "
                 "16: con el motor parado marcaba la presion atmosferica. Al "
                 "prender, la presion de aceite debe subir en menos de 30 "
                 "segundos o se corta el motor.",
    },
    {
        "id": "RALENTI", "nombre": "Ralenti y calentamiento", "dur": 20.0, "hasta": None,
        "ctl": {"arrancador": False, "generador": True, "throttle": 0.137,
                "embrague": False},
        "piloto": False, "obj": None,
        "texto": "1400 RPM, embrague DESACOPLADO: el rotor está quieto y la "
                 "aguja de ROTOR del tacómetro doble marca cero mientras la de "
                 "MOTOR ya está arriba. El generador entra en línea: el "
                 "voltímetro salta a 28 V y el amperímetro pasa a CARGA.",
    },
    {
        "id": "EMBRAGUE", "nombre": "Acople del embrague", "dur": 45.0,
        "hasta": ("n_rot_rpm", ">", 195.0),
        "ctl": {"embrague": True, "throttle": 0.40},
        "piloto": False, "obj": None,
        "texto": "Se acopla el embrague: la aguja de ROTOR sube hasta alcanzar "
                 "a la de MOTOR. Cuando ambas quedan SUPERPUESTAS, la relación "
                 "10:1 está establecida. La presión de aceite de transmisión "
                 "aparece recien ahora, porque su bomba la mueve el rotor.",
    },
    {
        "id": "RUNUP", "nombre": "Prueba de motor (run-up)", "dur": 30.0, "hasta": None,
        # mariposa donde se queda quieto en 2000 RPM con rotor acoplado y
        # colectivo abajo: la prueba de magnetos compara contra eso
        "ctl": {"throttle": 0.29},
        "piloto": False, "obj": None,
        "texto": "2000 RPM ESTABILIZADAS. Se controla presión y temperatura de "
                 "aceite, presión de admisión y temperaturas de transmisión. "
                 "Con el aceite todavía frío la presión está contra la válvula "
                 "de alivio, arriba de 100 psi, y va a BAJAR sola a medida que "
                 "el aceite afloje. No se despega con el aceite por debajo de "
                 "40 C: aceite frío es aceite que todavía no llegó a todos "
                 "lados. Todas las agujas en arco verde antes de despegar.",
    },
    {
        "id": "MAG_L", "nombre": "Prueba magneto izquierdo", "dur": 14.0, "hasta": None,
        "ctl": {"magnetos": MAG_L},
        "piloto": False, "obj": None,
        "texto": "Solo magneto izquierdo: la caída normal es de 50 a 100 RPM, y "
                 "TARDA unos segundos en establecerse. La cifra del manual es "
                 "de RÉGIMEN, no de potencia: el motor pierde alrededor del "
                 "11% de potencia y eso mueve la aguja un 4%. También sube unos "
                 "grados la culata, porque con una sola bujía por cilindro la "
                 "mezcla termina de quemarse más tarde. "
                 "CERO CAÍDA TAMBIÉN ES DEFECTO: significa que el magneto no se "
                 "está desconectando y el motor queda vivo con la llave en OFF. "
                 "Una caída mayor de 100, bujías sucias o cable flojo.",
    },
    {
        # como en el procedimiento real: si no, el derecho se compara contra
        # un régimen ya caído
        "id": "MAG_BOTH", "nombre": "Vuelta a ambos magnetos", "dur": 20.0,
        "hasta": None,
        "ctl": {"magnetos": MAG_BOTH},
        "piloto": False, "obj": None,
        "texto": "Se vuelve a AMBOS y se espera que el régimen se recupere. "
                 "Recién con la aguja de vuelta en su referencia tiene sentido "
                 "probar el otro magneto: una prueba sin referencia no mide "
                 "nada. La culata también baja de nuevo.",
    },
    {
        "id": "MAG_R", "nombre": "Prueba magneto derecho", "dur": 14.0, "hasta": None,
        "ctl": {"magnetos": MAG_R},
        "piloto": False, "obj": None,
        "texto": "Solo magneto derecho: misma verificación y misma caída. Lo "
                 "que se compara no es solo el valor de cada caída, sino la "
                 "DIFERENCIA entre las dos: una asimetría marcada entre "
                 "magnetos delata el que está fallando. Notar que el motor "
                 "SIGUE funcionando con un solo magneto: es un sistema "
                 "redundante, y para eso está.",
    },
    {
        "id": "DESPEGUE", "nombre": "Despegue al estacionario", "dur": 22.0, "hasta": None,
        "ctl": {"magnetos": MAG_BOTH, "throttle": 0.55},
        "piloto": True, "obj": {"alt": 30.0, "ias": 0.0, "hdg": 90.0, "rpm": 2200.0},
        "texto": "Estacionario a 30 ft. Es la condición de MÁXIMA demanda de "
                 "potencia: la presión de admisión sube al máximo y las "
                 "temperaturas empiezan a trepar porque casi no hay flujo de "
                 "aire de refrigeración.",
    },
    {
        "id": "ASCENSO", "nombre": "Ascenso", "dur": 150.0,
        "hasta": ("alt_ft", ">", 770.0),
        "ctl": {},
        "piloto": True, "obj": {"alt": 800.0, "ias": 55.0, "hdg": 90.0, "rpm": 2200.0},
        "texto": "Ascenso a 55 kt. El variómetro marca positivo, el altímetro "
                 "sube y - detalle importante - las temperaturas BAJAN respecto "
                 "del estacionario porque ahora si hay flujo de aire.",
    },
    {
        "id": "CRUCERO", "nombre": "Crucero", "dur": 70.0, "hasta": None,
        "ctl": {},
        "piloto": True, "obj": {"alt": 800.0, "ias": 74.0, "hdg": 90.0, "rpm": 2200.0},
        "texto": "Crucero estabilizado: 800 ft, 74 kt, rumbo 090. Todas las "
                 "agujas quietas en arco verde. Este es el estado de referencia "
                 "contra el que el alumno va a comparar cualquier falla.",
    },
    {
        "id": "VIRAJE", "nombre": "Viraje estándar a la derecha", "dur": 65.0, "hasta": None,
        "ctl": {},
        "piloto": True, "obj": {"alt": 800.0, "ias": 74.0, "hdg": 270.0, "rpm": 2200.0},
        "texto": "Viraje de 180 grados. Mirar el indicador de viraje y la bola: "
                 "un viraje coordinado mantiene la bola centrada. La brújula "
                 "giroscópica gira y el altímetro NO debe moverse.",
    },
    {
        "id": "DESCENSO", "nombre": "Descenso", "dur": 100.0,
        "hasta": ("alt_ft", "<", 260.0),
        "ctl": {},
        "piloto": True, "obj": {"alt": 250.0, "ias": 65.0, "hdg": 270.0, "rpm": 2200.0},
        "texto": "Descenso a 500 ft/min. El variómetro marca negativo. Baja la "
                 "presión de admisión porque se necesita menos potencia.",
    },
    {
        "id": "APROXIMACION", "nombre": "Aproximacion", "dur": 50.0, "hasta": None,
        "ctl": {},
        "piloto": True, "obj": {"alt": 60.0, "ias": 25.0, "hdg": 270.0, "rpm": 2200.0},
        "texto": "Desaceleración y descenso final. Al perder velocidad se pierde "
                 "el efecto de traslación: hace falta MÁS potencia, no menos.",
    },
    {
        "id": "ESTACIONARIO", "nombre": "Estacionario final", "dur": 22.0, "hasta": None,
        "ctl": {},
        "piloto": True, "obj": {"alt": 15.0, "ias": 0.0, "hdg": 270.0, "rpm": 2200.0},
        "texto": "Estacionario en efecto suelo antes de posar.",
    },
    {
        "id": "ATERRIZAJE", "nombre": "Aterrizaje", "dur": 30.0, "hasta": None,
        "ctl": {},
        "piloto": True, "obj": {"alt": 0.0, "ias": 0.0, "hdg": 270.0, "rpm": 2200.0},
        "texto": "Toma de contacto. El variómetro vuelve a cero y el velocímetro "
                 "queda por debajo del arco.",
    },
    {
        "id": "ENFRIAMIENTO", "nombre": "Enfriamiento", "dur": 25.0, "hasta": None,
        "ctl": {"throttle": 0.14, "colectivo": 0.0},
        "piloto": False, "obj": None,
        "texto": "1200 RPM durante dos minutos reales: un radial NO se corta "
                 "caliente, se agarrotan las válvulas al contraerse. Hay que "
                 "ver bajar la temperatura de culata hasta unos 160 C antes de "
                 "cortar. Sin viento relativo el radial se enfría despacio: es "
                 "la limitación operativa clásica del tipo.",
    },
    {
        "id": "CORTE", "nombre": "Corte de motor", "dur": 25.0, "hasta": None,
        "ctl": {"magnetos": MAG_OFF, "mezcla": 0.0},
        "piloto": False, "obj": None,
        "texto": "Magnetos a OFF. El motor se detiene, el rotor sigue girando por "
                 "inercia y las agujas del tacómetro se SEPARAN de nuevo. "
                 "Recien después se corta batería.",
    },
    {
        "id": "APAGADO", "nombre": "Aeronave asegurada", "dur": 15.0, "hasta": None,
        "ctl": {"embrague": False, "generador": False, "bomba_combustible": False,
                "bateria": False, "luces_tablero": 0.0},
        "piloto": False, "obj": None,
        "texto": "Todo apagado. El ciclo puede repetirse indefinidamente.",
    },
]

PERFIL_POR_ID = {}
for _f in PERFIL_NORMAL:
    PERFIL_POR_ID[_f["id"]] = _f


# Modo 2. Guion: lista de (segundo, acción). Acciones:
#   {"falla": "ID"} / {"quitar": "ID"}   del catálogo de fallas
#   {"amb": {"humedad": 0.9}}            ambiente
#   {"piloto": False}                    el piloto virtual deja de reaccionar
#   {"obj": {"alt": 600}}, {"ctl": {...}}, {"msg": "texto"}, {"fin": True}

ESCENARIOS = [
    {
        "id": "ESC_AUTORROTACION",
        "nombre": "Falla total de motor y autorrotación",
        "sistema": "MOTOR",
        "duracion": 150,
        "resumen": "La emergencia fundamental del helicóptero. Muestra el "
                   "'needle split' del tacómetro doble y como la autorrotación "
                   "mantiene el rotor girando sin motor.",
        "guion": [
            (0, {"msg": "Crucero estabilizado: 1500 ft, 74 kt. Memorizar la "
                        "posición de todas las agujas."}),
            (20, {"msg": "Atención al tacómetro doble en los próximos segundos."}),
            (25, {"falla": "ENG_FAIL_TOTAL",
                  "msg": "FALLA TOTAL DE MOTOR. Silencio."}),
            (27, {"msg": "NEEDLE SPLIT: la aguja de MOTOR cae y la de ROTOR "
                         "queda arriba. La rueda libre desacopló."}),
            (30, {"msg": "La presión de aceite del MOTOR se desploma a cero. "
                         "La aguja de admisión hace lo contrario de lo que uno "
                         "espera: SUBE hasta unas 30 inHg. Es un manómetro "
                         "ABSOLUTO, y sin mariposa aspirando marca la presión "
                         "atmosférica del lugar."}),
            (34, {"msg": "El generador salió de línea: luz roja, voltímetro a "
                         "23 V bajando, amperímetro en descarga."}),
            (40, {"msg": "MIRAR LA PRESIÓN DE TRANSMISIÓN: NO SE MUEVE, sigue "
                         "en 54 psi con el motor parado. Su bomba la mueve el "
                         "ROTOR, no el motor, y el rotor sigue girando. Por eso "
                         "la caja queda lubricada y la autorrotación es viable. "
                         "Si esa aguja también cayera, no habría maniobra que "
                         "sirviera."}),
            (45, {"msg": "Autorrotación estabilizada: paso colectivo abajo, 52 kt, "
                         "rotor dentro del arco verde 170-245 RPM."}),
            (55, {"msg": "El termómetro de aire de carburador sube hasta la "
                         "temperatura exterior: ya no pasa aire por el venturi, "
                         "así que se terminó el enfriamiento por evaporación."}),
            (70, {"msg": "El variómetro marca unos -1500 ft/min y ahí se queda. "
                         "No es un planeo: son 25 pies por segundo. Desde 1500 "
                         "ft quedan menos de 60 segundos para elegir dónde "
                         "aterrizar."}),
            (95, {"msg": "La culata se enfría rápido y la aguja baja sola. El "
                         "instrumento sigue vivo aunque no haya energía: es una "
                         "termocupla, fabrica su propia señal."}),
            (130, {"msg": "Fin del escenario."}),
            (135, {"fin": True}),
        ],
    },
    {
        "id": "ESC_HIELO_CARB",
        "nombre": "Engelamiento de carburador y recuperación",
        "sistema": "MOTOR",
        "duracion": 290,
        "resumen": "La falla más frecuente del R-1340, en la fase en que "
                   "realmente ocurre -el DESCENSO- y con el final que la hace "
                   "peligrosa: el tablero se ve normal hasta que se pide "
                   "potencia y no está.",
        # En descenso y no en crucero: con la mariposa casi cerrada el hielo se
        # forma más rápido, y en crucero el gobernador abría mariposa y
        # tapaba todo. Lo probamos así y eran dos minutos de tablero normal.
        "guion": [
            (0, {"obj": {"alt": 600.0, "ias": 65.0},
                 "msg": "Descenso hacia 600 ft en aire húmedo y frío, con la "
                        "mariposa casi cerrada. Es la fase de riesgo: vigilar "
                        "el termómetro de aire de carburador."}),
            (30, {"msg": "Descenso estabilizado. ANOTAR ESTOS DOS NÚMEROS: la "
                         "presión de admisión y las RPM. Todo lo que viene se "
                         "mide contra ellos."}),
            (40, {"falla": "CARB_ICE",
                  "msg": "PRIMER INSTRUMENTO QUE AVISA: la temperatura de aire "
                         "de carburador entró en la banda de riesgo, entre -10 "
                         "y +15 C. Todavía no pasó nada más, y esa es la "
                         "ventaja: avisa antes que ningún otro."}),
            (70, {"msg": "Por qué justo acá: con la mariposa cerrada la "
                         "depresión en el venturi es MÁXIMA, y el aire que "
                         "entra al carburador se enfría más que en crucero. "
                         "El engelamiento es un fenómeno de descenso y de "
                         "aproximación, no de despegue."}),
            (105, {"msg": "AHORA VIENE LA PARTE INCÓMODA: mirar el tablero. "
                          "La admisión no bajó, las RPM no bajaron, la presión "
                          "de aceite está bien, la culata está bien. TODO "
                          "NORMAL, con el carburador tapándose de hielo."}),
            (135, {"msg": "Lo que pasó es que el gobernador fue abriendo la "
                          "mariposa solo, a medida que el hielo estrangulaba, y "
                          "sostuvo el régimen. La aeronave está volando con la "
                          "mariposa CASI AL TOPE para dar la misma potencia que "
                          "antes daba a un tercio. El margen de potencia se "
                          "gastó, y ninguna aguja lo dice."}),
            (155, {"obj": {"alt": 1400.0, "ias": 74.0},
                   "msg": "SE PIDE POTENCIA para abandonar el descenso, que es "
                          "lo que uno haría al final de una aproximación."}),
            (175, {"msg": "Y NO HAY. La mariposa ya estaba al tope: las RPM de "
                          "motor y de rotor se caen, se enciende la luz de RPM "
                          "bajas y la aeronave no sube. ASÍ MATA el engelamiento "
                          "de carburador: no cuando se forma, sino cuando hace "
                          "falta la potencia que se llevó."}),
            (195, {"ctl": {"calefaccion_carb": 1.0},
                   "msg": "CALEFACCIÓN DE CARBURADOR CONECTADA, que era lo que "
                          "había que hacer 150 segundos antes. Ojo: la admisión "
                          "baja un poco MÁS al principio, porque el aire "
                          "caliente es menos denso. Empeora antes de mejorar, y "
                          "ahí es donde muchos la desconectan."}),
            (215, {"msg": "La temperatura de aire de carburador sube fuera de "
                          "la banda de riesgo. ATENCIÓN: al derretirse el hielo "
                          "con la mariposa al tope, las RPM SUBEN DE GOLPE y el "
                          "rotor se pasa del arco verde. Hay que cerrar "
                          "mariposa a tiempo."}),
            (240, {"quitar": "CARB_ICE",
                   "msg": "El hielo se derritió: la admisión se recupera y el "
                          "motor vuelve a marcha suave."}),
            (265, {"ctl": {"calefaccion_carb": 0.0},
                   "msg": "Calefacción a OFF. La temperatura de aire de "
                          "carburador vuelve a bajar: si se siguiera "
                          "descendiendo en las mismas condiciones, todo el "
                          "ciclo empezaría de nuevo. Por eso la calefacción se "
                          "aplica ANTES de descender, no después."}),
            (285, {"fin": True}),
        ],
    },
    {
        "id": "ESC_TRANSMISION",
        "nombre": "Pérdida de presión de transmisión",
        "sistema": "TRANSMISION",
        "duracion": 170,
        "resumen": "La falla más temida en helicópteros: la autorrotación NO "
                   "salva una caja principal agarrotada. Enseña urgencia.",
        "guion": [
            (0, {"msg": "Crucero normal. Observar presión y temperatura de "
                        "transmisión en arco verde."}),
            (20, {"falla": "XMSN_PRESS_LOSS",
                  "msg": "Comienza la pérdida de presión de aceite de la "
                         "transmisión principal."}),
            (32, {"msg": "La aguja de presión de transmisión sale del arco "
                         "verde y sigue cayendo."}),
            (42, {"msg": "LUZ ROJA de presión de transmisión encendida "
                         "(umbral 30 psi). A los 50 segundos la aguja está "
                         "prácticamente en cero."}),
            (60, {"msg": "COMPARAR CON EL MANÓMETRO DE ACEITE DEL MOTOR: sigue "
                         "en 80 psi, y la culata en su temperatura de siempre. "
                         "Son DOS CIRCUITOS DE ACEITE DISTINTOS. Confundirlos "
                         "lleva a cortar el motor, que acá es lo peor que se "
                         "puede hacer: sin motor tampoco hay rotor que mueva la "
                         "bomba de la caja."}),
            (80, {"msg": "La temperatura de transmisión empieza a subir, y de "
                         "ahí no vuelve: la caja está trabajando sin "
                         "lubricación y el calor lo genera la propia fricción."}),
            (110, {"msg": "Temperatura en arco rojo, pasando los 110 C. "
                          "ATERRIZAR YA. No hay procedimiento en vuelo que "
                          "resuelva esto: la autorrotación salva una falla de "
                          "motor, no una caja agarrotada."}),
            (140, {"msg": "La aguja de temperatura sigue trepando hacia el "
                          "fondo de escala. Todo el resto del tablero está "
                          "impecable, y esa es la trampa del escenario: dos "
                          "agujas en un rincón contra veintiocho que dicen que "
                          "está todo bien."}),
            (155, {"msg": "Fin del escenario."}),
            (160, {"fin": True}),
        ],
    },
    {
        "id": "ESC_ELECTRICO",
        "nombre": "Falla eléctrica progresiva",
        "sistema": "ELECTRICO",
        "duracion": 200,
        "resumen": "Enseña qué instrumento sobrevive a una falla eléctrica y "
                   "cuál miente en lugar de apagarse.",
        "guion": [
            (0, {"msg": "Crucero normal. Voltímetro en 28 V, amperímetro en carga."}),
            (15, {"falla": "GEN_FAIL",
                  "msg": "FALLA DE GENERADOR. Luz roja encendida."}),
            (20, {"msg": "El voltímetro cae de 28 a 24 V. El amperímetro pasa "
                         "a DESCARGA: la batería alimenta sola todo el avión."}),
            (60, {"msg": "La tensión sigue bajando lentamente. Autonomía de "
                         "batería limitada."}),
            (100, {"falla": "ELEC_TOTAL",
                   "msg": "La batería se agoto. FALLA ELÉCTRICA TOTAL."}),
            (110, {"msg": "Mueren los instrumentos ELÉCTRICOS: aforadores de "
                          "combustible, temperatura de aceite, aire de "
                          "carburador, presión y temperatura de transmisión."}),
            (118, {"msg": "SOBREVIVEN velocímetro, altímetro y variómetro, que "
                          "son NEUMÁTICOS. Y también el tacómetro doble, que "
                          "tiene generador propio, los manómetros de tubo "
                          "Bourdon y la termocupla de culata."}),
            (128, {"msg": "OJO con las luces de alerta: también son eléctricas. "
                          "La luz roja de GENERATOR se APAGA. Un tablero sin "
                          "luces encendidas no significa que no haya fallas."}),
            (142, {"msg": "Mirar el horizonte artificial y el indicador de "
                          "rumbo: NO se congelan ni se ponen en cero. Los "
                          "giróscopos se van cayendo y siguen indicando una "
                          "actitud y un rumbo que ya no son los reales."}),
            (162, {"msg": "Ese es el peligro: el instrumento no avisa que dejó "
                          "de servir. Es el argumento histórico para conservar "
                          "instrumentos de presión como respaldo."}),
            (190, {"fin": True}),
        ],
    },
    {
        "id": "ESC_COMBUSTIBLE",
        "nombre": "Mala gestión de combustible",
        "sistema": "COMBUSTIBLE",
        "duracion": 210,
        "resumen": "Cadena de eventos: pérdida, aviso ignorado, agotamiento del "
                   "tanque y apagado del motor. Enseña a leer los avisos.",
        "guion": [
            (0, {"ctl": {"selector_tanque": TANQUE_FWD},
                 "msg": "Crucero alimentando desde el tanque DELANTERO."}),
            (10, {"falla": "FUEL_LEAK",
                  "msg": "Pérdida de combustible en el tanque delantero."}),
            (35, {"msg": "COMPARAR LOS DOS AFORADORES. El DELANTERO baja mucho "
                         "más rápido de lo que corresponde al consumo; el "
                         "TRASERO no se mueve. Esa asimetría es toda la falla: "
                         "un motor consume parejo, una cañería rota pierde de "
                         "un tanque solo."}),
            (65, {"msg": "Ya se fueron unos 25 litros del delantero contra "
                         "cero del trasero. Con esa diferencia alcanza para "
                         "identificar el tanque afectado y cerrarlo, que es "
                         "todo lo que había que hacer."}),
            (95, {"msg": "Nadie cambió de tanque. Ningún instrumento de motor "
                         "acusa nada todavía: presión de combustible en arco "
                         "verde, RPM normales, admisión normal. El tablero "
                         "avisa por un solo lado y hay que estar mirándolo."}),
            (115, {"falla": "FUEL_STARVATION",
                   "msg": "TANQUE DELANTERO AGOTADO. Se enciende la luz ámbar, "
                          "la presión de combustible se desploma a cero -la "
                          "bomba está chupando aire- y el motor se para."}),
            (122, {"msg": "Needle split otra vez: la aguja de MOTOR se cae y la "
                          "de ROTOR queda arriba. Y el aforador TRASERO sigue "
                          "marcando 320 litros. Había combustible de sobra a "
                          "bordo, solo que no en el tanque seleccionado."}),
            (130, {"ctl": {"selector_tanque": TANQUE_AFT},
                   "quitar": "FUEL_STARVATION",
                   "msg": "SELECTOR AL TANQUE TRASERO."}),
            (134, {"ctl": {"arrancador": True},
                   "msg": "REARRANQUE EN VUELO: hace falta el ARRANCADOR. La rueda "
                          "libre impide que el rotor arrastre al motor, así que el "
                          "molinete no alcanza para volver a encenderlo."}),
            (150, {"ctl": {"arrancador": False}, "quitar": "FUEL_LEAK",
                   "msg": "Motor recuperado. Las agujas del tacómetro vuelven "
                          "a superponerse."}),
            (200, {"fin": True}),
        ],
    },
    {
        "id": "ESC_ROTOR_COLA",
        "nombre": "Pérdida de rotor de cola",
        "sistema": "ROTORES",
        "duracion": 130,
        "resumen": "Emergencia crítica y muy visual: la brújula gira sin parar "
                   "y la bola se va al tope.",
        "guion": [
            (0, {"msg": "Crucero normal, bola centrada, rumbo estable. "
                        "Memorizar dónde está la bola."}),
            (25, {"falla": "TAIL_ROTOR_LOSS",
                  "msg": "PÉRDIDA DE ROTOR DE COLA. Guiñada incontrolada."}),
            (31, {"msg": "LA BOLA SE VA AL TOPE Y SE QUEDA AHÍ. Es el "
                         "instrumento más barato del tablero y el que más "
                         "grita: un tubo curvo con líquido y una bola adentro, "
                         "sin un solo cable."}),
            (38, {"msg": "El indicador de rumbo gira sin detenerse, unos 5 "
                         "grados por segundo. La aguja de viraje marca un "
                         "viraje permanente de dos tercios de escala: no llega "
                         "al tope porque a velocidad de traslación el "
                         "estabilizador vertical aguanta parte del par."}),
            (46, {"msg": "Todos los instrumentos de motor siguen normales. El "
                         "motor está perfecto: lo que se perdió es el control "
                         "de guiñada, y ningún manómetro lo va a decir."}),
            (55, {"falla": "ENG_FAIL_TOTAL",
                  "msg": "PROCEDIMIENTO: entrar en AUTORROTACIÓN. Al desacoplar "
                         "la rueda libre, el árbol deja de transmitir par y la "
                         "reacción sobre el fuselaje DESAPARECE."}),
            (66, {"msg": "MIRAR LOS TRES INSTRUMENTOS JUNTOS: la aguja de "
                         "viraje volvió a cero, la bola se centró sola y el "
                         "rumbo se quedó quieto. La guiñada se detuvo sin tocar "
                         "el pedal, porque el par que la causaba ya no existe."}),
            (85, {"msg": "El precio es que ahora se está en autorrotación de "
                         "verdad, bajando a 1500 ft/min. Se cambia una "
                         "emergencia por otra, y esa segunda sí tiene "
                         "procedimiento conocido."}),
            (120, {"fin": True}),
        ],
    },
    {
        "id": "ESC_ACEITE",
        "nombre": "Pérdida de presión de aceite de motor",
        "sistema": "LUBRICACION",
        "duracion": 170,
        "resumen": "Falla de sistema REAL, para contrastarla después con la "
                   "falla de INDICACIÓN del mismo instrumento.",
        "guion": [
            (0, {"msg": "Crucero normal. Presión de aceite 80 psi."}),
            (20, {"falla": "OIL_PRESS_LOSS",
                  "msg": "Comienza la pérdida de presión de aceite."}),
            (40, {"msg": "La aguja BAJA, y baja despacio: tarda casi un minuto "
                         "en irse de 80 psi a menos de 10. Un instrumento roto "
                         "se va de golpe; un sistema que falla se degrada."}),
            (65, {"msg": "CLAVE: LA CULATA EMPIEZA A SUBIR. Ese es el segundo "
                         "testigo, y sin él no hay diagnóstico. Sin aceite no "
                         "hay película entre las piezas, la fricción calienta y "
                         "la termocupla lo cuenta."}),
            (100, {"msg": "La culata pasó los 232 C de límite en tierra y va "
                          "camino al rojo de 260 C. La temperatura de ACEITE, "
                          "en cambio, casi no se movió: el aceite es una masa "
                          "térmica grande y su aguja va siempre atrasada. No "
                          "esperarla para decidir."}),
            (130, {"msg": "Comparar con el escenario de falla de INDICACIÓN: "
                          "allá la aguja marca cero desde el primer segundo y "
                          "las temperaturas no se mueven NUNCA. Acá la aguja "
                          "tardó un minuto y arrastró a la culata con ella."}),
            (155, {"fin": True}),
        ],
    },
    {
        "id": "ESC_INSTRUMENTO_MIENTE",
        "nombre": "El instrumento miente (falla de indicación)",
        "sistema": "INSTRUMENTOS",
        "duracion": 215,
        "resumen": "El ejercicio diagnóstico más valioso del simulador: "
                   "distinguir una falla de sistema de una falla de instrumento.",
        "guion": [
            (0, {"msg": "Crucero normal. Todo en arco verde."}),
            (20, {"falla": "OILP_GAGE_FAIL",
                  "msg": "La presión de aceite cayó a CERO DE GOLPE, en un "
                         "segundo, y la aguja quedó quieta ahí, sin temblar."}),
            (26, {"msg": "PREGUNTA: hay que cortar el motor?"}),
            (45, {"msg": "PISTA: mirar la temperatura de aceite y la culata. "
                         "Siguen exactamente donde estaban."}),
            (62, {"msg": "Si la presión fuera REALMENTE cero, la culata ya "
                         "estaría subiendo: en el escenario de pérdida REAL "
                         "arranca a subir a los 45 segundos y no para hasta el "
                         "arco rojo. Acá pasó un minuto y no se movió un grado."}),
            (78, {"msg": "DIAGNÓSTICO: falló el TRANSDUCTOR, no el motor. Se "
                         "continúa el vuelo y se anota en el libro. La regla: "
                         "una aguja que cae SOLA es un instrumento roto; un "
                         "sistema que falla se lleva puestos a sus vecinos."}),
            (100, {"falla": "PITOT_BLOCK",
                   "msg": "SEGUNDA FALLA: se tapó el tubo pitot. Por ahora no "
                          "se nota nada, porque la aeronave va a velocidad "
                          "constante y la aguja está clavada en el valor "
                          "correcto."}),
            (120, {"obj": {"ias": 50.0},
                   "msg": "Se reduce velocidad a 50 kt. Acá se ve: el "
                          "velocímetro NO SE MUEVE, sigue marcando 74 kt."}),
            (145, {"msg": "El resto del tablero cuenta la verdad: bajó la "
                          "admisión, cambió la actitud, el variómetro se movió. "
                          "Un solo instrumento contra todos los demás."}),
            (165, {"obj": {"ias": 85.0},
                   "msg": "Se acelera a 85 kt y la aguja sigue clavada en 74. "
                          "El altímetro y el variómetro andan perfectos, así "
                          "que la toma estática está bien: lo que se tapó es "
                          "el PITOT, que es del velocímetro solo."}),
            (195, {"msg": "Las dos fallas del escenario tienen la misma "
                          "enseñanza: antes de creerle a una aguja, buscarle "
                          "un testigo."}),
            (208, {"fin": True}),
        ],
    },
]

ESCENARIOS_POR_ID = {}
for _e in ESCENARIOS:
    ESCENARIOS_POR_ID[_e["id"]] = _e
