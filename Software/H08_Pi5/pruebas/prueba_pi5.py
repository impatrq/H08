#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lo que agregamos para la Raspberry, probado sin la Raspberry.

Luces por falla, carátulas de la página, servidor, pruebas guiadas en
--simulado --auto, sintaxis de los .sh, la llave BATERÍA, el punto de acceso
y actualizar.sh sobre una instalación de mentira.
"""

import http.client
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PI = os.path.join(RAIZ, "raspberry_pi5")
sys.path.insert(0, os.path.join(RAIZ, "nucleo"))
sys.path.insert(0, PI)

from configuracion import TABLERO, PANEL_VIRTUAL, LED, HORIZONTE  # noqa: E402
from actuadores_simulados import ActuadoresSimulados              # noqa: E402
from simulador import Simulador                                   # noqa: E402

fallos = []


def cierto(nombre, v, detalle=""):
    print("  %s %s%s" % ("ok  " if v else "MAL ", nombre, "" if v else "   " + str(detalle)))
    if not v:
        fallos.append(nombre)


def correr(sim, seg, dt=0.05):
    for _ in range(int(seg / dt)):
        sim.paso(dt)
        sim.mapa.escribir()


def luces_encendidas(sim):
    e = sim.estado()["instrumentos"]
    return set(it["id"] for it in TABLERO if it["actuador"] == LED and e[it["id"]]["ang"] >= 0.5)


def probar_camara_lenta():
    """x0,5 y x0,25 tienen que ir a esa velocidad (con int() el x0,5 iba a x0,42)."""
    print("\n CÁMARA LENTA")
    import simulador as S
    for vel in (0.5, 0.25):
        sim = Simulador(ActuadoresSimulados(), semilla=1)
        sim.modo_falla("PITOT_BLOCK")
        sim.velocidad = vel
        reloj = [0]
        orig = S.ticks_ms
        S.ticks_ms = lambda: reloj[0]
        try:
            sim._t_ultimo = 0
            t0 = sim.t_sim
            for _ in range(2000):                 # 10 s reales en vueltas de 5 ms
                reloj[0] += 5
                sim.servicio()
        finally:
            S.ticks_ms = orig
        real = (sim.t_sim - t0) / 10.0
        cierto("con ×%s el tiempo simulado va a ×%s (da ×%.3f)" % (vel, vel, real), abs(real - vel) < 0.02)


def probar_luces():
    print("\n LUCES DE ALERTA")
    for falla, luz, seg in (("GEN_FAIL", "LT_GEN", 10), ("XMSN_PRESS_LOSS", "LT_XMSN_PRESS", 40),
                            ("LOW_ROTOR_RPM", "LT_LOW_ROTOR", 80),
                            ("FUEL_STARVATION", "LT_FUEL_FWD", 10)):
        sim = Simulador(ActuadoresSimulados(), semilla=1)
        sim.modo_falla(falla)
        vista = False
        for _ in range(int(seg / 1.0)):
            correr(sim, 1.0)
            if luz in luces_encendidas(sim):
                vista = True
                break
        cierto("%s enciende %s antes de %d s" % (falla, luz, seg), vista)

    sim = Simulador(ActuadoresSimulados(), semilla=1)
    sim.modo_falla("PITOT_BLOCK")           # crucero; la falla no toca luces
    correr(sim, 20)
    cierto("crucero: sólo IGNITION encendida", luces_encendidas(sim) == {"LT_STARTER"},
           luces_encendidas(sim))

    sim.prueba_luces(True)
    correr(sim, 0.2)
    cierto("prueba de lámparas: la página ve las seis", len(luces_encendidas(sim)) == 6)
    act = sim.mapa.actuadores
    cierto("prueba de lámparas: las seis salidas encendidas",
           all(act.valores.get("%s:%d" % tuple(it["canal"])) == 1
               for it in TABLERO if it["actuador"] == LED))
    sim.prueba_luces(False)
    correr(sim, 0.2)
    cierto("fin de la prueba: vuelve a sólo IGNITION", luces_encendidas(sim) == {"LT_STARTER"})

    sim = Simulador(ActuadoresSimulados(), semilla=1)
    sim.modo_falla("ELEC_TOTAL")
    correr(sim, 120)
    cierto("sin energía eléctrica: todas apagadas", luces_encendidas(sim) == set(),
           luces_encendidas(sim))


def probar_disposicion():
    # chapa del diseño F: todo adentro, nada se pisa, biseles vecinos a la misma distancia
    print("\n DISPOSICIÓN DE LA CHAPA (diseño F)")
    import math
    from configuracion import PANEL_LIENZO, PANEL_ZONAS, ANUNCIADOR
    W, H = PANEL_LIENZO
    inst = [it for it in list(TABLERO) + list(PANEL_VIRTUAL) if it.get("pos") and it.get("dial") != "luz"]
    fuera = [it["id"] for it in inst if it["pos"][0] < 0 or it["pos"][1] < 0
             or it["pos"][0] + it["tam"] > W or it["pos"][1] + it["tam"] > H]
    cierto("todos los instrumentos entran en la chapa", not fuera, fuera)
    pisados = []
    for i, a in enumerate(inst):
        ca = (a["pos"][0] + a["tam"] / 2.0, a["pos"][1] + a["tam"] / 2.0)
        for b in inst[i + 1:]:
            cb = (b["pos"][0] + b["tam"] / 2.0, b["pos"][1] + b["tam"] / 2.0)
            if math.hypot(ca[0] - cb[0], ca[1] - cb[1]) < (a["tam"] + b["tam"]) / 2.0 + 6:
                pisados.append((a["id"], b["id"]))
    cierto("ningún instrumento se pisa con otro", not pisados, pisados)
    rects = [(z["id"], z["pos"], z["tam"]) for z in PANEL_ZONAS]
    contra = []
    for zid, (zx, zy), (zw, zh) in rects:
        for it in inst:
            cx, cy, r = it["pos"][0] + it["tam"] / 2.0, it["pos"][1] + it["tam"] / 2.0, it["tam"] / 2.0
            dx = max(zx - cx, 0, cx - (zx + zw)); dy = max(zy - cy, 0, cy - (zy + zh))
            if math.hypot(dx, dy) < r:
                contra.append((zid, it["id"]))
    cierto("los instrumentos no tapan las llaves, las luces ni la tapa", not contra, contra)
    luces = [a["id"] for a in ANUNCIADOR if not a.get("nombre") or not a.get("pos")]
    cierto("cada luz tiene un nombre simple y su lugar", not luces, luces)
    sin_corto = [it["id"] for it in inst if not it.get("corto")]
    cierto("cada instrumento tiene su nombre corto", not sin_corto, sin_corto)
    # separación pareja: en la columna de motor, 12 entre biseles
    col = sorted((it for it in inst if it["id"] in ("OIL_PRESS", "FUEL_PRESS", "XMSN_OIL_PRESS", "AMMETER")),
                 key=lambda it: it["pos"][1])
    huecos = {round(b["pos"][1] - (a["pos"][1] + a["tam"]), 1) for a, b in zip(col, col[1:])}
    cierto("columna de motor con la misma separación entre biseles", len(huecos) == 1, huecos)


def probar_caratulas():
    print("\n CARÁTULAS DE LA PÁGINA")
    carpeta = os.path.join(PI, "web", "caratulas")
    try:
        with open(os.path.join(carpeta, "indice.json"), encoding="utf-8") as f:
            ind = json.load(f)
    except (OSError, ValueError):
        ind = {}
    cierto("existe web/caratulas/indice.json", bool(ind))
    con_dibujo = [it["id"] for it in list(TABLERO) + list(PANEL_VIRTUAL)
                  if it.get("pos") and it.get("dial") != "horizonte"]
    faltan = [i for i in con_dibujo if i not in ind]
    cierto("hay carátula para los %d instrumentos que se dibujan" % len(con_dibujo),
           not faltan, faltan)
    sucias = []
    for ident, c in ind.items():
        ruta = os.path.join(carpeta, c["archivo"])
        try:
            t = open(ruta, encoding="utf-8").read()
        except OSError:
            sucias.append(c["archivo"] + " (no está)")
            continue
        if 'fill="#FFFFFF"' in t or "stroke-dasharray" in t or 'width="' in t.split(">")[0]:
            sucias.append(c["archivo"])
        if not (0 < c["R"] < c["L"] / 2.0):
            sucias.append(c["archivo"] + " (medidas)")
    cierto("sin fondo blanco, sin líneas de corte, medidas coherentes", not sucias, sucias)


class Cliente:
    def __init__(self, puerto):
        self.puerto = puerto

    def pedir(self, metodo, ruta):
        c = http.client.HTTPConnection("localhost", self.puerto, timeout=5)
        c.request(metodo, ruta, body=b"" if metodo == "POST" else None)
        r = c.getresponse()
        b = r.read()
        c.close()
        return r.status, b, r.getheader("Content-Type") or ""


def probar_servidor():
    print("\n SERVIDOR")
    import servidor_web
    from hilo_simulacion import HiloSimulacion
    nucleo = HiloSimulacion(ActuadoresSimulados(), semilla=1)
    nucleo.start()
    puerto = servidor_web.puerto_libre(8150)
    srv = servidor_web.crear(nucleo, puerto, os.path.join(PI, "web"), acceso=None)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Cliente(puerto)
    try:
        s, b, t = c.pedir("GET", "/caratulas/airspeed.svg")
        cierto("/caratulas/airspeed.svg se sirve como SVG", s == 200 and "svg" in t and b"<svg" in b)
        for malo in ("/caratulas/../secreto_admin.json", "/caratulas/..%2fsecreto_admin.svg",
                     "/caratulas/AIRSPEED.svg", "/caratulas/indice.json", "/caratulas/"):
            s, _, _ = c.pedir("GET", malo)
            cierto("rechaza %s" % malo, s == 404, s)
        # el helicóptero 3D: three.js y el modelo salen de la Pi (sin internet)
        for nombre in ("three.min", "orbit_controls", "room_environment", "sikorsky", "helicoptero", "cine3d", "vuelo3d"):
            s, b, t = c.pedir("GET", "/3d/%s.js" % nombre)
            cierto("/3d/%s.js se sirve como JavaScript" % nombre, s == 200 and "javascript" in t and len(b) > 1000, (s, t))
        for malo in ("/3d/../tablero.html", "/3d/..%2fsecreto_admin.js", "/3d/../../nucleo/acceso.js",
                     "/3d/THREE.js", "/3d/vuelo3d.css", "/3d/", "/3d/no_existe.js"):
            s, _, _ = c.pedir("GET", malo)
            cierto("rechaza %s" % malo, s == 404, s)
        # diseño F: letras, logo y estilo viajan con el programa (sin internet)
        for ruta, tipo in (("/estilo.css", "text/css"), ("/fuentes/inter.woff2", "font/woff2"),
                           ("/fuentes/space-grotesk.woff2", "font/woff2"), ("/logo.png", "image/png")):
            s, b, t = c.pedir("GET", ruta)
            cierto("%s se sirve (%s)" % (ruta, tipo), s == 200 and t.startswith(tipo) and len(b) > 1000, (s, t, len(b)))
        for malo in ("/fuentes/../secreto_admin.json", "/fuentes/inter.ttf", "/fuentes/", "/estilo.css/..",
                     "/fuentes/LICENCIA_Inter.txt"):
            s, _, _ = c.pedir("GET", malo)
            cierto("rechaza %s" % malo, s == 404, s)
        afuera = re.compile(r"""(?:src|href)=["']https?://|url\(\s*["']?https?://|fonts\.googleapis""")
        for pag in ("tablero.html", "mando.html", "sin_permiso.html", "estilo.css"):
            texto = open(os.path.join(PI, "web", pag), encoding="utf-8").read()
            cierto("%s no pide nada a internet" % pag, not afuera.search(texto), afuera.findall(texto)[:3])
            if pag.endswith(".html"):
                cierto("%s usa la guía de estilo común" % pag, 'href="/estilo.css"' in texto)
        s, b, _ = c.pedir("GET", "/api/estado")
        vu = json.loads(b.decode("utf-8")).get("vuelo") or {}
        cierto("el estado trae el vuelo real para el 3D",
               all(k in vu for k in ("alt_ft", "ias_kt", "rumbo", "cabeceo", "alabeo", "rotor_rpm", "motor_rpm")), sorted(vu))
        pag = open(os.path.join(PI, "web", "tablero.html"), encoding="utf-8").read()
        cierto("la página ofrece ver el helicóptero y carga /3d/vuelo3d.js",
               'data-vista="heli"' in pag and "/3d/vuelo3d.js" in pag and "/3d/three.min.js" in pag)
        # la vista 3D le habla al alumno sin jerga, tiene recorrido de espera y pantalla completa
        cine = open(os.path.join(PI, "web", "3d", "cine3d.js"), encoding="utf-8").read()
        vuelo = open(os.path.join(PI, "web", "3d", "vuelo3d.js"), encoding="utf-8").read()
        jerga = re.compile(r"\b(pies|nudos|rpm|colectivo|flare)\b", re.IGNORECASE)
        marcas = ("titulo:", "sub:", "textos:", 'n: "', 'd: "')
        feas = []
        for lin in cine.splitlines():
            if any(m in lin for m in marcas):
                for cadena in re.findall(r'"([^"]*)"', lin):
                    feas += jerga.findall(cadena)
        cierto("los textos del cine 3D no usan palabras técnicas", not feas, feas[:5])
        cierto("cine3d.js tiene el recorrido de espera",
               all(p in cine for p in ("esperaInicio", "esperaPaso", "esperaFin", "enEspera", "PARTES")))
        cierto("vuelo3d.js tiene pantalla completa y mueve el recorrido de espera",
               all(p in vuelo for p in ("requestFullscreen", "pantallaCompleta", "esperaPaso")))
        cierto("cine3d.js no deja la cámara adentro del helicóptero", "function afuera(" in cine)
        pag_t = open(os.path.join(PI, "web", "tablero.html"), encoding="utf-8").read()
        srv_t = open(os.path.join(RAIZ, "nucleo", "servidor_web.py"), encoding="utf-8").read()
        cierto("fluidez: un pedido por vez con corte, agujas interpoladas, sin filtros que se recalculan",
               "AbortController" in pag_t and "objetivoEn" in pag_t and "filter:drop-shadow(0 6px" not in pag_t)
        cierto("servidor: respuestas sin demora (Nagle), conexiones colgadas que se cierran y caché de carátulas",
               "disable_nagle_algorithm = True" in srv_t and "timeout = 20" in srv_t and "If-None-Match" in srv_t)
        cierto("la ventana del celular muestra el tablero con la ayuda y la pantalla cuenta los celulares",
               "ayudaRed" in pag_t and "datos móviles" in pag_t and "/api/red" in pag_t and "Red llena" in pag_t)
        cierto("las cinemáticas siguen al simulador (el 3D, el tablero y la página muestran lo mismo)",
               "ctx.seguir(dt)" in cine and "moverGuion(" not in cine and "seguir: function (dt)" in vuelo)
        v3d = open(os.path.join(PI, "web", "3d", "vuelo3d.js"), encoding="utf-8").read()
        m = re.search(r"PerspectiveCamera\(45, 1, ([0-9.]+),", v3d)
        cierto("3D sin titileo: el helipuerto y el portón van encima con polygonOffset y la cámara no arranca tan pegada",
               v3d.count("polygonOffset: true") >= 2 and m is not None and float(m.group(1)) >= 0.1
               and "0, Math.PI); tg.rotateZ" in v3d)
        heli = open(os.path.join(PI, "web", "3d", "helicoptero.js"), encoding="utf-8").read()
        siko = open(os.path.join(PI, "web", "3d", "sikorsky.js"), encoding="utf-8").read()
        cierto("3D más fluido: chapa con menos triángulos, resolución que se adapta y sombra liviana",
               "opciones.detalle" in siko and "detalle: op.detalle" in heli and "ajustarResolucion" in v3d
               and "sombraFalsa" in v3d and "shadowMap.autoUpdate = false" in v3d)
        cierto("el humo del escape sale del lado del caño (sikorsky.js lo pone en -z)",
               "escape: P(2.72, 0.98, -1.1)" in heli)
        s, b, t = c.pedir("GET", "/qr_wifi.svg")
        cierto("/qr_wifi.svg", s == 200 and b"<svg" in b)
        s, b, _ = c.pedir("GET", "/api/catalogo")
        cat = json.loads(b.decode("utf-8"))
        ins = {i["id"]: i for i in cat["instrumentos"]}
        cierto("el catálogo trae las carátulas", "AIRSPEED" in cat.get("caratulas", {}))
        cierto("el catálogo trae barrido y centro (VSI con el cero a las 9)",
               ins["AIRSPEED"]["barrido"] == 300 and ins["VSI"]["centro"] == 180.0
               and ins["COMPASS"]["barrido"] == "CONT")
        cierto("el catálogo trae la red wifi", cat.get("wifi", {}).get("red") == "Tablero-H08")
        s, b, _ = c.pedir("POST", "/api/mando/tomar")
        cierto("sin clave (--sin-clave): tomar el mando no rompe el servidor",
               s == 200 and json.loads(b.decode("utf-8"))["ok"])
        s, b, _ = c.pedir("GET", "/?pantalla=1")
        cierto("la página de la pantalla se sirve", s == 200 and b"MODO.pantalla" in b)
    finally:
        srv.shutdown()
        srv.server_close()
        nucleo.detener()
        nucleo.join(5)


def probar_guiadas():
    print("\n PRUEBAS GUIADAS DE LA PI (--simulado --auto)")
    tmp = tempfile.mkdtemp(prefix="h08_informes_")
    env = dict(os.environ, H08_INFORMES=tmp, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    for args in (["calibrar_instrumento.py", "AIRSPEED"],
                 ["calibrar_instrumento.py", "ATT_ROLL" if HORIZONTE["cabeceo_fijo"] else "ATT_PITCH"],
                 ["calibrar_instrumento.py", "COMPASS"],
                 ["prueba_general.py", "--solo", "A"]):
        r = subprocess.run([sys.executable, os.path.join(PI, args[0])] + args[1:] +
                           ["--simulado", "--auto"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=240, env=env, cwd=PI)
        cierto(" ".join(args), r.returncode == 0 and "TODO BIEN" in r.stdout,
               (r.stdout + r.stderr)[-400:])
    cierto("los informes van a su carpeta", len(os.listdir(tmp)) == 4, os.listdir(tmp))
    for viejo in ("prueba_instrumento.py", "prueba_luces_motor.py", "calibrar_servo.py"):
        cierto("ya no está %s (lo hacen otras)" % viejo, not os.path.exists(os.path.join(PI, viejo)))
    r = subprocess.run([sys.executable, os.path.join(PI, "diagnostico_pi.py"), "--cableado"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=30, cwd=PI, env=env)
    cierto("diagnostico_pi.py --cableado", r.returncode == 0 and "GPIO12" in r.stdout)


def probar_pasar_instrumento():
    # --todos: pasar uno (antes o en el medio) y seguir
    print("\n CALIBRAR TODOS: PASAR UN INSTRUMENTO Y SEGUIR")
    import builtins
    import contextlib
    import io
    import banco
    import calibrar_instrumento as C
    respuestas = iter(["p",            # AMMETER: se pasa antes de empezar
                       "", "", "p",    # VOLTMETER: se empieza, giro bien, se pasa en la 1a marca
                       "", ""] +       # FUEL_QTY_AFT: se calibra entero (giro bien)
                      [""] * 6 + [""] +  # sus seis marcas y la comprobación
                      ["p"])           # COMPASS (va al final): se pasa
    viejo_input, viejo_consola, viejo_argv = (builtins.input, banco.salir_si_no_hay_consola,
                                              sys.argv)
    builtins.input = lambda *_: next(respuestas)
    banco.salir_si_no_hay_consola = lambda auto: None
    sys.argv = ["calibrar_instrumento.py", "--todos", "--desde", "AMMETER", "--simulado"]
    os.environ["H08_INFORMES"] = tempfile.mkdtemp(prefix="h08_informes_")
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cod = C.main()
    finally:
        builtins.input, banco.salir_si_no_hay_consola, sys.argv = (
            viejo_input, viejo_consola, viejo_argv)
    txt = salida.getvalue()
    cierto("pasar ANTES de empezar: queda salteado", "[SALTEADO] AMMETER" in txt, txt[-600:])
    cierto("pasar en el MEDIO: queda salteado", "[SALTEADO] VOLTMETER" in txt, txt[-600:])
    cierto("y sigue con el resto", "[BIEN    ] FUEL_QTY_AFT" in txt and cod == 0, txt[-600:])
    cierto("al final dice cuáles faltan",
           "Quedaron sin calibrar: AMMETER, VOLTMETER, COMPASS" in txt, txt[-300:])
    cierto("se usaron justo las respuestas previstas", next(respuestas, None) is None)

    sys.argv = ["calibrar_instrumento.py", "--todos", "--saltear", "noexiste", "--simulado"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cod = C.main()
    finally:
        sys.argv = viejo_argv
    cierto("--saltear con un nombre que no existe avisa", cod == 1)


def probar_horizonte_simple():
    """Armado simple: plato pegado al servo de alabeo y disco de cabeceo fijo."""
    print("\n HORIZONTE: ARMADO SIMPLE (SIN TORNILLERÍA)")
    import banco
    import calibrar_instrumento as C
    from configuracion import TABLERO_POR_ID, invertido
    roll = TABLERO_POR_ID["ATT_ROLL"]
    cierto("alabeo directo: el servo gira lo mismo que el plato (±60°)",
           roll["cal"] == [(-60.0, 30.0), (0.0, 90.0), (60.0, 150.0)], roll["cal"])
    cierto("sin piñón no se invierte el giro", not invertido("ATT_ROLL"))
    cierto("el servo de cabeceo queda sin conectar (canal 13 libre)",
           TABLERO_POR_ID["ATT_PITCH"]["canal"] is None)
    cierto("el cabeceo ya no aparece para calibrar",
           "ATT_PITCH" not in [x["id"] for x in C.calibrables()] and banco.buscar("ATT_PITCH") is None)
    cierto("el alabeo sí se calibra", "ATT_ROLL" in [x["id"] for x in C.calibrables()])


def probar_cabeceo():
    # el cabeceo del horizonte es un disco, no una aguja
    if HORIZONTE["cabeceo_fijo"]:
        probar_horizonte_simple()
        return
    print("\n CALIBRAR EL CABECEO DEL HORIZONTE")
    import banco
    import calibrar_instrumento as C
    it = banco.buscar("ATT_PITCH")
    cierto("el cabeceo ya se puede calibrar",
           "ATT_PITCH" in [x["id"] for x in C.calibrables()])
    cierto("las marcas son las líneas del disco: -20, -10, 0, 10, 20",
           banco.puntos_de_prueba(it) == [-20, -10, 0, 10, 20],
           banco.puntos_de_prueba(it))
    cierto("nariz arriba: una línea del CIELO", "línea 10 del CIELO" in C.que_hacer(it, 10),
           C.que_hacer(it, 10))
    cierto("nariz abajo: una línea de la TIERRA", "línea 20 de la TIERRA" in C.que_hacer(it, -20),
           C.que_hacer(it, -20))
    cierto("en 0: la línea del horizonte", "horizonte" in C.que_hacer(it, 0))
    cierto("los demás siguen hablando de la aguja",
           "aguja" in C.que_hacer(banco.buscar("AIRSPEED"), 40))
    cierto("al cabeceo se llega pasándose poquito (tiene tope)",
           C.Aguja(None, it, 1).llegada < C.LLEGADA)

    # brazo corrido: en el 0 hay que subir 50 us, y las otras marcas tienen que
    # arrancar ya corridas (si no van contra el tope)
    import builtins
    import contextlib
    import io
    respuestas = iter([""] + ["++", "++", ""] + [""] * 4 + [""])     # giro bien, marcas
    guardado = {}
    viejo = (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar, C.FLECHAS[0])
    builtins.input = lambda *_: next(respuestas)
    banco.salir_si_no_hay_consola = lambda auto: None
    sys.argv = ["calibrar_instrumento.py", "ATT_PITCH", "--simulado", "--sin-flechas"]
    C.guardar = lambda archivo, datos: guardado.update(datos)
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cod = C.main()
    finally:
        (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar,
         C.FLECHAS[0]) = viejo
    txt = salida.getvalue()
    orden = [ln.split("avioncito")[0] for ln in txt.splitlines() if "Llevá el disco" in ln]
    cierto("empieza por el 0 y después va a cada lado",
           len(orden) == 5 and "horizonte" in orden[0] and "10 del CIELO" in orden[1]
           and "20 de la TIERRA" in orden[4], orden)
    marcas = (guardado.get("PCA0:13") or {}).get("marcas") or []
    act = banco.abrir_placas(True)
    calc = {round(banco.angulo_servo(it, v), 2): act.pulso_us(("PCA0", 13), banco.angulo_servo(it, v))
            for v in banco.puntos_de_prueba(it)}
    act.cerrar()
    corridas = [round(u - calc[a]) for a, u in marcas]
    cierto("lo corregido en el 0 se suma a las demás marcas",
           cod == 0 and len(marcas) == 5 and all(abs(c - 50) <= 1 for c in corridas),
           (cod, corridas, txt[-300:]))


def probar_elegir_giro():
    print("\n CALIBRAR: ELEGIR GIRO NORMAL O AL REVÉS")
    import builtins
    import contextlib
    import io
    import json
    import banco
    import calibrar_instrumento as C
    import actuadores_pca9685 as P9
    it = banco.buscar("AMMETER")          # no está en AL_REVES: arranca normal
    destino = tuple(it["canal"])
    act = banco.abrir_placas(True)
    valores = banco.puntos_de_prueba(it)
    normal = [act.pulso_us(destino, banco.angulo_servo(it, v)) for v in valores]
    act.poner_al_reves(destino, True)
    reves = [act.pulso_us(destino, banco.angulo_servo(it, v)) for v in valores]
    act.cerrar()
    cierto("al revés, la escala va para el otro lado",
           (normal[-1] - normal[0]) * (reves[-1] - reves[0]) < 0, (normal, reves))

    # fue al revés (r), se da vuelta, ahora sí (Enter) y se calibra
    n = len(valores)
    respuestas = iter(["r", ""] + [""] * n + [""])
    guardado = {}
    viejo = (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar, C.FLECHAS[0])
    builtins.input = lambda *_: next(respuestas)
    banco.salir_si_no_hay_consola = lambda auto: None
    sys.argv = ["calibrar_instrumento.py", "AMMETER", "--simulado", "--sin-flechas"]
    C.guardar = lambda archivo, datos: guardado.update(datos)
    os.environ["H08_INFORMES"] = tempfile.mkdtemp(prefix="h08_informes_")
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cod = C.main()
    finally:
        (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar,
         C.FLECHAS[0]) = viejo
    txt = salida.getvalue()
    e = guardado.get("%s:%d" % destino) or {}
    marcas = [u for _a, u in e.get("marcas") or []]
    cierto("elegido al revés: se guarda con las marcas",
           cod == 0 and e.get("al_reves") is True and len(marcas) == n
           and (marcas[-1] - marcas[0]) * (reves[-1] - reves[0]) > 0, (e, txt[-400:]))
    cierto("se usaron justo las respuestas previstas", next(respuestas, None) is None)

    # lo elegido acá pisa a configuracion.AL_REVES al arrancar
    cal = os.path.join(tempfile.mkdtemp(), "cal.json")
    with open(cal, "w") as f:
        json.dump({"PCA1:3": {"al_reves": True}, "PCA0:6": {"al_reves": False}}, f)
    cierto("la calibración dice qué canal va al revés",
           P9.cargar_al_reves(cal) == {"PCA1:3": True, "PCA0:6": False})


def probar_tope():
    # una marca a la que la aguja no llega (t = tope)
    print("\n CALIBRAR: MARCA QUE NO SE ALCANZA (TOPE)")
    import builtins
    import contextlib
    import io
    import banco
    import calibrar_instrumento as C
    from utiles import interpolar_tabla
    it = banco.buscar("VSI")
    valores = banco.puntos_de_prueba(it)          # -2000 ... 2000
    # giro bien; -2000: t y marca -1800; las del medio Enter; 2000: t y marca 1750; comprobación
    respuestas = iter(["", "t", "-1800"] + [""] * (len(valores) - 2) + ["t", "1750", ""])
    guardado = {}
    viejo = (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar, C.FLECHAS[0])
    builtins.input = lambda *_: next(respuestas)
    banco.salir_si_no_hay_consola = lambda auto: None
    sys.argv = ["calibrar_instrumento.py", "VSI", "--simulado", "--sin-flechas"]
    C.guardar = lambda archivo, datos: guardado.update(datos)
    os.environ["H08_INFORMES"] = tempfile.mkdtemp(prefix="h08_informes_")
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cod = C.main()
    finally:
        (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar,
         C.FLECHAS[0]) = viejo
    marcas = (guardado.get("PCA0:10") or {}).get("marcas") or []
    angulos = [a for a, _u in marcas]
    cierto("los topes se guardan con el número que marca la aguja",
           cod == 0 and len(marcas) == len(valores)
           and round(interpolar_tabla(-1800, it["cal"]), 1) == round(min(angulos), 1)
           and round(interpolar_tabla(1750, it["cal"]), 1) == round(max(angulos), 1),
           (marcas, salida.getvalue()[-300:]))
    cierto("se usaron justo las respuestas previstas", next(respuestas, None) is None)


def probar_transportador():
    # --transportador es lo que antes era calibrar_servo.py
    print("\n CALIBRAR: EL SERVO SUELTO (TRANSPORTADOR)")
    import builtins
    import contextlib
    import io
    import banco
    import calibrar_instrumento as C
    cierto("ya no existe calibrar_servo.py: hay un solo método",
           not os.path.exists(os.path.join(PI, "calibrar_servo.py")))
    # brazo puesto, 0° con -- (550 us), 180° con ++ (2450 us), medio bien, guardar
    respuestas = iter(["", "--", "", "", "++", "", "", "", ""])
    guardado = {"PCA0:6": {"marcas": [[0, 600], [180, 2400]], "al_reves": True}}
    viejo = (builtins.input, sys.argv, C.guardar, C.leer)
    builtins.input = lambda *_: next(respuestas)
    sys.argv = ["calibrar_instrumento.py", "PCA0", "6", "--transportador", "--simulado"]
    C.guardar = lambda archivo, datos: (guardado.clear(), guardado.update(datos))
    C.leer = lambda archivo: json.loads(json.dumps(guardado))
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cod = C.main()
    finally:
        builtins.input, sys.argv, C.guardar, C.leer = viejo
    e = guardado.get("PCA0:6", {})
    cierto("guarda el 0° y el 180° del servo",
           cod == 0 and e.get("us_0") == 550 and e.get("us_180") == 2450, (e, salida.getvalue()[-300:]))
    cierto("y no toca las marcas ni el giro elegido",
           e.get("marcas") == [[0, 600], [180, 2400]] and e.get("al_reves") is True, e)
    cierto("se usaron justo las respuestas previstas", next(respuestas, None) is None)
    cierto("--listar muestra lo del transportador", "transportador 0°=550" in C.texto_transportador(e))
    cierto("el pulso se puede llevar más allá de 2700 us (algunos SG90)",
           C.LIMITE[1] >= 2900 and C.LIMITE[0] <= 300, C.LIMITE)


def probar_brujula():
    print("\n CALIBRAR LA BRÚJULA (MOTOR PASO A PASO)")
    import builtins
    import contextlib
    import io
    import json
    import banco
    import calibrar_instrumento as C
    import paso_a_paso as M
    from configuracion import MOTORES
    cierto("la brújula entra en la calibración",
           "COMPASS" in [x["id"] for x in C.calibrables()])

    # dar vuelta el giro no mueve la aguja (pasos x sentido queda igual)
    m = M.MotorContinuo(lambda pines, bits: None, (12, 16, 20, 21), sentido=1)
    m.pos, m.obj_grados = 1019, 90.0
    antes = m.pos * m.sentido
    m.invertir_sentido()
    cierto("invertir el giro deja la aguja donde está",
           m.pos * m.sentido == antes and m.objetivo_pasos() == m.pos and m.sentido == -1)

    tmp = tempfile.mkdtemp()
    cal = os.path.join(tmp, "cal.json")
    with open(cal, "w") as f:
        json.dump({"MOTOR:1": {"invertido": True}, "PCA0:6": {"marcas": [[0, 500]]}}, f)
    g = M.GestorMotores(lambda pines, bits: None, os.path.join(tmp, "pos.json"),
                        archivo_calibracion=cal)
    cierto("el tablero arranca con el giro que guardó la calibración",
           g.motores[1].sentido == -MOTORES[1]["sentido"])
    with open(cal, "w") as f:
        f.write("{roto")
    cierto("calibración dañada: el giro de configuracion.py", M.motores_invertidos(cal) == set())

    # fue a la O (n): se invierte, ahora va a la E y la vuelta da bien
    respuestas = iter(["+", "", "n", "", ""])
    guardado = {}
    viejo = (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar, C.FLECHAS[0])
    builtins.input = lambda *_: next(respuestas)
    banco.salir_si_no_hay_consola = lambda auto: None
    sys.argv = ["calibrar_instrumento.py", "COMPASS", "--simulado", "--sin-flechas"]
    C.guardar = lambda archivo, datos: guardado.update(datos)
    os.environ["H08_INFORMES"] = tempfile.mkdtemp(prefix="h08_informes_")
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cod = C.main()
    finally:
        (builtins.input, banco.salir_si_no_hay_consola, sys.argv, C.guardar,
         C.FLECHAS[0]) = viejo
    txt = salida.getvalue()
    cierto("si va a la O, se invierte el giro y se guarda",
           cod == 0 and guardado.get("MOTOR:1") == {"invertido": True}
           and "[BIEN    ] COMPASS" in txt, (guardado, txt[-400:]))
    cierto("se usaron justo las respuestas previstas", next(respuestas, None) is None)


def probar_vigilancia():
    # avisos a systemd (arrancó, sigue vivo) sin librerías extra
    print("\n VIGILANCIA DEL SERVICIO (systemd)")
    if os.name == "nt" or not hasattr(socket, "AF_UNIX"):
        print("  --   se prueba en Linux, salteado")
        return
    import time
    import tablero_pi5 as T
    carpeta = tempfile.mkdtemp(prefix="h08_sd_")
    ruta = os.path.join(carpeta, "notify")
    oido = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    oido.bind(ruta)
    oido.settimeout(2)
    viejo = os.environ.get("NOTIFY_SOCKET")
    os.environ["NOTIFY_SOCKET"] = ruta
    try:
        cierto("avisa a systemd que arrancó", T.sd_notify("READY=1") and oido.recv(64) == b"READY=1")
    finally:
        if viejo is None:
            os.environ.pop("NOTIFY_SOCKET", None)
        else:
            os.environ["NOTIFY_SOCKET"] = viejo
        oido.close()
    cierto("fuera de systemd no hace nada", T.sd_notify("READY=1") is False or viejo)

    class NucleoFalso:
        latido = time.monotonic()
        def is_alive(self):
            return True
    n = NucleoFalso()
    cierto("si la página no contesta, no dice que está vivo", not T.esta_vivo(n, 9))
    n.latido = time.monotonic() - 60
    cierto("si la simulación se trabó, tampoco", not T.esta_vivo(n, 9))
    unidad = open(os.path.join(PI, "instalar.sh"), encoding="utf-8").read()
    cierto("el servicio se reinicia siempre y tiene vigilancia",
           "Restart=always" in unidad and "WatchdogSec=" in unidad and "Type=notify" in unidad
           and "StartLimitIntervalSec=0" in unidad)


def probar_flechas():
    print("\n CALIBRAR CON FLECHAS")
    import calibrar_instrumento as C
    cierto("las flechas y Enter se reconocen",
           C.separar_teclas("\x1b[C\x1b[D\x1b[A\x1b[B\x1bOC+-s\n") ==
           ["der", "izq", "arr", "aba", "der", "+", "-", "s", "enter"],
           C.separar_teclas("\x1b[C\x1b[D\x1b[A\x1b[B\x1bOC+-s\n"))

    class AgujaFalsa:
        def __init__(self, sentido):
            self.us, self.sentido, self.movidas = 1500.0, sentido, []

        def poner(self, us):
            self.movidas.append(us)
            self.us = us

    def correr(sentido, tandas):
        aguja = AgujaFalsa(sentido)
        cola = iter(tandas)
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            r = C.ajustar_teclas(aguja, lambda: next(cola))
        return r, aguja

    r, ag = correr(1, [["der"], ["der"], ["arr"], ["izq"], ["enter"]])
    cierto("→ → ↑ ← y Enter: 1500 + 5 + 5 + 25 - 5", r == 1530.0, (r, ag.movidas))
    r, ag = correr(-1, [["der"], ["enter"]])
    cierto("si el pulso baja cuando sube la escala, → baja el pulso", r == 1495.0, r)
    r, ag = correr(1, [["arr"] * 12, ["enter"]])
    cierto("tecla apretada: 12 juntas se mueven como mucho 3 pasos", r == 1575.0, r)
    r, ag = correr(1, [["der", "der", "enter"]])
    cierto("las flechas antes del Enter se aplican", r == 1510.0, r)
    r, _ = correr(1, [["s"]])
    cierto("s saltea la marca", r is None)
    r, _ = correr(1, [["p"]])
    cierto("p pasa el instrumento", r == "p")

    def se_termina():
        raise EOFError
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        r = C.ajustar_teclas(AgujaFalsa(1), se_termina)
    cierto("si se cierra el teclado, termina", r == "q")


# Comandos de mentira para probar punto_de_acceso.sh sin placa wifi: anotan
# lo que se les pide y contestan como la Raspberry
_FALSOS = {
    "nmcli": r"""#!/usr/bin/env bash
E="$H08_ESTADO"; echo "nmcli $*" >> "$E/log"
clave() { case "$1" in autoconnect) echo connection.autoconnect ;; ssid) echo 802-11-wireless.ssid ;;
          wifi-sec.*) echo "802-11-wireless-security.${1#wifi-sec.}" ;; *) echo "$1" ;; esac; }
if [ "$1" = "-s" ]; then shift; fi
case "$*" in
  "-t -f DEVICE,TYPE device status") cat "$E/placa" 2>/dev/null ;;
  "-t -f DEVICE,CONNECTION device status") cat "$E/conectada" 2>/dev/null ;;
  "-t -f NAME connection show") [ -f "$E/creada" ] && echo tablero-ap ;;
  "-t -f NAME connection show --active") [ -f "$E/activa" ] && echo tablero-ap ;;
  "-t -f CHAN,SIGNAL device wifi list"*) cat "$E/redes" 2>/dev/null ;;
  "-g "*) cat "$E/p_$2" 2>/dev/null ;;
  "connection add"*) touch "$E/creada"; prev=""; for a in "$@"; do
        [ "$prev" = ssid ] && echo "$a" > "$E/p_802-11-wireless.ssid"; prev="$a"; done ;;
  "connection modify"*) shift 3; while [ $# -ge 2 ]; do echo "$2" > "$E/p_$(clave "$1")"; shift 2; done ;;
  "connection up"*) [ -f "$E/falla_up" ] && { echo "Error: Connection activation failed"; exit 4; }; touch "$E/activa" ;;
  "connection down"*) rm -f "$E/activa" ;;
esac
exit 0
""",
    "ip": "#!/bin/sh\n[ -f \"$H08_ESTADO/activa\" ] && echo '3: wlan0    inet 10.55.0.1/24 brd 10.55.0.255 scope global wlan0'\nexit 0\n",
    "iw": "#!/bin/sh\necho \"iw $*\" >> \"$H08_ESTADO/log\"\ncase \"$*\" in *\"station dump\"*) ;; *) exit 0 ;; esac\n"
          "n=$(cat \"$H08_ESTADO/celulares\" 2>/dev/null || echo 0); i=0\nwhile [ $i -lt $n ]; do echo \"Station aa:bb:cc:00:00:0$i (on wlan0)\"; i=$((i+1)); done\n",
    "systemctl": "#!/bin/sh\necho \"systemctl $*\" >> \"$H08_ESTADO/log\"\n"
                 "case \"$*\" in *is-active*tablero-h08-red*) [ -f \"$H08_ESTADO/vigilante_parado\" ] && exit 3 ;; esac\nexit 0\n",
    "rfkill": "#!/bin/sh\n[ \"$1\" = list ] && echo '0: phy0: Wireless LAN' && echo '\tSoft blocked: no' && echo '\tHard blocked: no'\nexit 0\n",
    "raspi-config": "#!/bin/sh\ncase \"$2\" in get_wifi_country) cat \"$H08_ESTADO/pais\" 2>/dev/null ;; do_wifi_country) echo \"$3\" > \"$H08_ESTADO/pais\" ;; esac\nexit 0\n",
    "id": "#!/bin/sh\nif [ \"$1\" = -u ] && [ -n \"$H08_UID\" ]; then echo \"$H08_UID\"; else exec /usr/bin/id \"$@\"; fi\n",
}


def probar_punto_de_acceso():
    # NetworkManager de mentira, solo en Linux
    print("\n RED WIFI PROPIA (punto_de_acceso.sh, sin placa)")
    if os.name == "nt":
        print("  --   se prueba en Linux, salteado")
        return
    import socket
    import stat
    base = tempfile.mkdtemp(prefix="h08_ap_")
    falsos = os.path.join(base, "bin")
    os.makedirs(falsos)
    for nombre, texto in _FALSOS.items():
        ruta = os.path.join(falsos, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IEXEC)
    original = os.path.join(PI, "punto_de_acceso.sh")
    oyente = socket.socket()
    oyente.bind(("127.0.0.1", 0))
    oyente.listen(5)
    puerto = oyente.getsockname()[1]
    oyente80 = socket.socket()          # el "puerto 80" de la prueba
    oyente80.bind(("127.0.0.1", 0))
    oyente80.listen(5)
    puerto80 = oyente80.getsockname()[1]

    # revisar se conecta muchas veces: hay que atenderlas y cerrarlas, si no
    # se llena la cola y la conexión siguiente se cuelga
    import threading

    def atender(o):
        while True:
            try:
                c, _ = o.accept()
                c.close()
            except OSError:
                return
    for o in (oyente, oyente80):
        threading.Thread(target=atender, args=(o,), daemon=True).start()

    def correr(args, estado, script=original, uid="0", placa=True, dnsmasq=True, web80=True, **extra):
        os.makedirs(estado, exist_ok=True)
        if placa:
            open(os.path.join(estado, "placa"), "w").write("wlan0:wifi\n")
        for k, v in extra.items():
            open(os.path.join(estado, k), "w").write(str(v))
        env = dict(os.environ, PATH=falsos + ":/usr/bin:/bin", H08_ESTADO=estado, H08_UID=uid,
                   TABLERO_PUERTO=str(puerto),
                   TABLERO_PUERTO_WEB=str(puerto80 if web80 else 9),
                   H08_DNSMASQ_DIR=os.path.join(estado, "dnsmasq-shared.d"),
                   H08_SYSTEMD_DIR=os.path.join(estado, "systemd"),
                   H08_VIGILAR_CADA="0", H08_VIGILAR_UNA_VEZ="1", H08_RUN_DIR=os.path.join(estado, "run"), H08_ESPERA_ESCANEO="0", H08_VIGILAR_PASO="0",
                   H08_BLOQUEADOS=os.path.join(estado, "bloqueados_red.txt"),
                   H08_DNSMASQ="/bin/sh" if dnsmasq else "/no/existe")
        r = subprocess.run(["bash", script] + args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30, env=env)
        return r.returncode, r.stdout + r.stderr

    def prop(estado, k):
        try:
            return open(os.path.join(estado, "p_" + k)).read().strip()
        except OSError:
            return None

    try:
        e1 = os.path.join(base, "e1")
        cod, sal = correr(["preparar"], e1)
        cierto("preparar: crea la red con los datos del archivo",
               cod == 0 and prop(e1, "802-11-wireless.ssid") == "Tablero-H08"
               and prop(e1, "802-11-wireless-security.psk") == "sikorsky55"
               and prop(e1, "ipv4.addresses") == "10.55.0.1/24", sal[-300:])
        cierto("preparar: queda para levantarse sola al encender",
               prop(e1, "connection.autoconnect") == "yes")
        cierto("preparar: si falla al encender la reintenta sin límite, antes que otro wifi",
               prop(e1, "connection.autoconnect-retries") == "0"
               and prop(e1, "connection.autoconnect-priority") == "100")
        try:
            unidad = open(os.path.join(e1, "systemd", "tablero-h08-red.service"), encoding="utf-8").read()
        except OSError:
            unidad = ""
        log = open(os.path.join(e1, "log"), encoding="utf-8").read()
        cierto("preparar: instala el servicio que la vuelve a levantar si se cae",
               "punto_de_acceso.sh vigilar" in unidad and "Restart=always" in unidad
               and "systemctl enable tablero-h08-red" in log, unidad + log[-300:])
        cierto("preparar: no la levanta ahora (no corta una conexión por wifi)",
               not os.path.exists(os.path.join(e1, "activa"))
               and "systemctl start tablero-h08-red" not in log, log[-300:])
        cierto("preparar: elige el país si no estaba (la placa viene bloqueada sin país)",
               open(os.path.join(e1, "pais")).read().strip() == "AR")
        try:
            portal = open(os.path.join(e1, "dnsmasq-shared.d", "h08-portal.conf")).read()
        except OSError:
            portal = ""
        cierto("preparar: cualquier nombre lleva a la Raspberry (la página se abre sola)",
               "address=/#/10.55.0.1" in portal, portal)
        cierto("cifrado completo: rsn, ccmp de a pares y de grupo, sin IPv6",
               prop(e1, "802-11-wireless-security.group") == "ccmp"
               and prop(e1, "ipv6.method") == "disabled")

        otro = os.path.join(base, "otro.sh")
        texto = open(original, encoding="utf-8").read().replace('CLAVE="sikorsky55"', 'CLAVE="otraclave9"')
        open(otro, "w", encoding="utf-8").write(texto)
        cod, sal = correr(["encender"], e1, script=otro)
        cierto("si se cambia la clave en el archivo, la red guardada la toma",
               cod == 0 and prop(e1, "802-11-wireless-security.psk") == "otraclave9", sal[-300:])

        e2 = os.path.join(base, "e2")
        cod, sal = correr(["encender"], e2, uid="1000")
        cierto("sin sudo: no toca nada y dice cómo correrlo",
               cod != 0 and "sudo bash" in sal and not os.path.exists(os.path.join(e2, "creada")), sal)
        cod, sal = correr(["preparar"], os.path.join(base, "e3"), dnsmasq=False)
        cierto("sin dnsmasq: avisa en vez de dejar una red que no da direcciones",
               cod != 0 and "dnsmasq-base" in sal, sal)
        cod, sal = correr(["preparar"], os.path.join(base, "e4"), placa=False)
        cierto("sin placa wifi: lo dice", cod != 0 and "placa wifi" in sal, sal)
        cod, sal = correr(["encender"], os.path.join(base, "e5"), falla_up=1)
        cierto("si no levanta: muestra el error y las causas comunes",
               cod != 0 and "activation failed" in sal and "revisar" in sal, sal[-400:])

        e6 = os.path.join(base, "e6")
        correr(["encender"], e6, pais="AR", celulares=3)
        cod, sal = correr(["revisar"], e6)
        cierto("revisar: todo bien con la red levantada", cod == 0 and "Todo bien" in sal
               and "Celulares conectados: 3" in sal and "se abre sola" in sal, sal[-600:])
        cod, sal = correr(["revisar"], e6, web80=False)
        cierto("revisar: avisa si la página no está en el puerto 80 y cómo arreglarlo",
               cod != 0 and "bash instalar.sh" in sal and ":%d" % puerto in sal, sal[-600:])
        open(os.path.join(e6, "p_802-11-wireless-security.psk"), "w").write("vieja123")
        open(os.path.join(e6, "celulares"), "w").write("8")
        cod, sal = correr(["revisar"], e6)
        cierto("revisar: detecta la clave distinta a la del QR", cod != 0 and "clave guardada" in sal, sal[-600:])
        cierto("revisar: avisa cuando llega al límite de celulares", "acepta unos 8" in sal and "[MAL ] Celulares" in sal)
        cod, sal = correr(["estado"], e6, uid="1000")
        cierto("estado: se puede ver sin sudo", cod == 0 and "LEVANTADO" in sal, sal)

        # placa enganchada al wifi de la escuela: la red propia no aparece en
        # los celulares ("red no disponible" con el QR)
        e7 = os.path.join(base, "e7")
        correr(["preparar"], e7, pais="AR")
        cod, sal = correr(["revisar"], e7, conectada="wlan0:Escuela-WiFi\n")
        cierto("revisar: avisa si la placa está conectada a otro wifi",
               cod != 0 and "no la van a ver en la lista" in sal and "“Escuela-WiFi”" in sal, sal[-600:])

        # el vigilante levanta la red si tendría que estar y no está
        def mismo_encendido(estado):
            # la marca que deja el servicio la primera vez en cada encendido
            os.makedirs(os.path.join(estado, "run"), exist_ok=True)
            open(os.path.join(estado, "run", "tablero-h08-red.encendido"), "w").close()

        e8 = os.path.join(base, "e8")
        correr(["preparar"], e8, pais="AR")
        mismo_encendido(e8)
        cod, sal = correr(["vigilar"], e8)
        cierto("vigilar: si la red no está levantada, la levanta",
               cod == 0 and os.path.exists(os.path.join(e8, "activa")) and "de nuevo" in sal, sal)
        cod, sal = correr(["vigilar"], e8, conectada="wlan0:Escuela-WiFi\n")
        cierto("vigilar: si ya está levantada, no hace nada",
               cod == 0 and sal.strip() == "", sal)
        cod, sal = correr(["revisar"], e8, celulares=1)
        cierto("revisar: la red al encender, reintentos sin límite y vigilada",
               cod == 0 and "sin límite" in sal and "Vigilada" in sal, sal[-700:])
        open(os.path.join(e8, "vigilante_parado"), "w").write("1")
        cod, sal = correr(["revisar"], e8)
        cierto("revisar: avisa si el vigilante no está andando y cómo arrancarlo",
               cod != 0 and "enable --now tablero-h08-red" in sal, sal[-700:])
        e9 = os.path.join(base, "e9")
        correr(["preparar"], e9, pais="AR")
        correr(["apagar"], e9)
        mismo_encendido(e9)
        cod, sal = correr(["vigilar"], e9)
        cierto("vigilar: respeta 'apagar' hasta reiniciar (no la levanta mientras se usa el wifi de la escuela)",
               cod == 0 and not os.path.exists(os.path.join(e9, "activa")), sal)
        # reinicio de la Pi (/run vacío): la red vuelve sola
        e12 = os.path.join(base, "e12")
        correr(["preparar"], e12, pais="AR")
        cod, sal = correr(["apagar"], e12)
        cierto("apagar: avisa que dura hasta reiniciar", "reinicie" in sal, sal)
        cod, sal = correr(["vigilar"], e12)
        cierto("al encender: la red vuelve aunque se haya apagado, y se levanta ya",
               cod == 0 and os.path.exists(os.path.join(e12, "activa"))
               and prop(e12, "connection.autoconnect") == "yes" and "Al encender" in sal, sal)
        cierto("al encender: deja la marca para no repetirlo en el mismo encendido",
               os.path.exists(os.path.join(e12, "run", "tablero-h08-red.encendido")))
        cierto("preparar: el wifi sin ahorro de energía (menos demoras y cortes)",
               prop(e1, "802-11-wireless.powersave") == "2")
        # elige el canal con menos wifi alrededor: 1 y 6 ocupados, va al 11
        e14 = os.path.join(base, "e14")
        correr(["preparar"], e14, pais="AR")
        cod, sal = correr(["vigilar"], e14, redes="1:80\n2:60\n6:70\n6:55\n7:40\n")
        cierto("al encender: elige el canal menos ocupado (1 y 6 llenos -> 11)",
               cod == 0 and prop(e14, "802-11-wireless.channel") == "11" and "canal 11" in sal
               and os.path.exists(os.path.join(e14, "activa")), sal)
        # al desconectado por el profesor el vigilante lo saca cada vez que vuelve
        e16 = os.path.join(base, "e16")
        correr(["preparar"], e16, pais="AR")
        mismo_encendido(e16)
        open(os.path.join(e16, "bloqueados_red.txt"), "w").write("aa:bb:cc:00:00:01 Galaxy-A12\n")
        cod, sal = correr(["vigilar"], e16, celulares=3)
        log16 = open(os.path.join(e16, "log")).read()
        cierto("vigilar: saca de la wifi al que el profesor desconectó (y a nadie más)",
               cod == 0 and "station del aa:bb:cc:00:00:01" in log16
               and "station del aa:bb:cc:00:00:00" not in log16 and "station del aa:bb:cc:00:00:02" not in log16, log16[-400:])
        e17 = os.path.join(base, "e17")
        correr(["preparar"], e17, pais="AR")
        open(os.path.join(e17, "bloqueados_red.txt"), "w").write("aa:bb:cc:00:00:01 Galaxy-A12\n")
        correr(["vigilar"], e17)
        cierto("al encender se borra la lista de desconectados (un error no dura para siempre)",
               open(os.path.join(e17, "bloqueados_red.txt")).read() == "")
        e15 = os.path.join(base, "e15")
        correr(["preparar"], e15, pais="AR")
        correr(["vigilar"], e15, redes="")
        cierto("al encender sin redes alrededor: queda en el 6", prop(e15, "802-11-wireless.channel") == "6")
        e13 = os.path.join(base, "e13")
        cod, sal = correr(["vigilar"], e13, pais="AR")
        cierto("al encender sin la red creada: la crea y la levanta",
               cod == 0 and os.path.exists(os.path.join(e13, "activa")), sal)
        inst = open(os.path.join(PI, "instalar.sh"), encoding="utf-8").read()
        act = open(os.path.join(PI, "actualizar.sh"), encoding="utf-8").read()
        cierto("el servicio del tablero arranca solo y pide el de la red",
               "WantedBy=multi-user.target" in inst and "Wants=tablero-h08-red.service" in inst
               and 'systemctl enable "$SERVICIO"' in act)
        e10 = os.path.join(base, "e10")
        correr(["preparar"], e10, pais="AR")
        cod, sal = correr(["vigilar"], e10, falla_up=1)
        cierto("vigilar: si no puede levantarla, avisa y sigue (no se cae)",
               cod == 0 and "no se pudo levantar" in sal and "revisar" in sal, sal)
        cod, sal = correr(["vigilar"], os.path.join(base, "e11"), uid="1000")
        cierto("vigilar: sin sudo no corre", cod != 0 and "sudo bash" in sal, sal)

        import servidor_web
        texto = servidor_web.texto_qr_wifi(servidor_web.datos_punto_de_acceso())
        igual = texto == "WIFI:T:WPA;S:Tablero-H08;P:sikorsky55;;"
        cierto("QR del wifi: el tipo de seguridad primero y los datos del archivo", igual, texto)
        # diagnóstico: la pregunta de nombre que hace un celular, contra un DNS falso
        import importlib.util, struct as _st
        esp = importlib.util.spec_from_file_location("diag_h08", os.path.join(PI, "diagnostico_pi.py"))
        diag = importlib.util.module_from_spec(esp); esp.loader.exec_module(diag)
        dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); dns.bind(("127.0.0.1", 0))

        def contestar():
            q, a = dns.recvfrom(512)
            dns.sendto(q[:2] + b"\x81\x80" + q[4:6] + b"\x00\x01\x00\x00\x00\x00" + q[12:] + b"\xc0\x0c"
                       + _st.pack(">HHIH", 1, 1, 60, 4) + bytes([10, 55, 0, 1]), a)
        threading.Thread(target=contestar, daemon=True).start()
        r = diag.nombre_a_ip("connectivitycheck.gstatic.com", "127.0.0.1", puerto=dns.getsockname()[1])
        dns.close()
        cierto("diagnóstico: pregunta un nombre como el celular y lee la IP", r == "10.55.0.1", r)
    finally:
        oyente.close()
        oyente80.close()


def probar_scripts():
    print("\n SCRIPTS DE LA PI")
    for sh in sorted(f for f in os.listdir(PI) if f.endswith(".sh")):
        # en Windows el bash suele ser el de WSL o Git y no entiende C:\...,
        # así que la sintaxis se revisa en Linux o en la Pi
        if os.name == "nt":
            print("  --   %s: la sintaxis de bash se comprueba en Linux, salteado" % sh)
            continue
        try:
            r = subprocess.run(["bash", "-n", os.path.join(PI, sh)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            print("  --   %s: sin bash en este sistema, salteado" % sh)
            continue
        cierto("%s sin errores de sintaxis" % sh, r.returncode == 0, r.stderr)
    texto = open(os.path.join(PI, "instalar.sh"), encoding="utf-8").read()
    cierto("instalar.sh deja la pantalla, el inicio solo y la red propia",
           all(k in texto for k in ("pantalla.sh\" instalar", "do_boot_behaviour B4", "do_blanking 1",
                                    "punto_de_acceso.sh\" preparar")))
    pan = open(os.path.join(PI, "pantalla.sh"), encoding="utf-8").read()
    cierto("pantalla.sh: agranda según la pantalla (4K como 1080p) o con ESCALA a mano",
           "--force-device-scale-factor=\"$(escala)\"" in pan and "wlr-randr" in pan)
    if os.name != "nt":
        prog = pan[pan.index("ancho_pantalla() {"):pan.index("responde() {")]
        for ancho, esperado in (("3840", "2"), ("2560", "1.25"), ("1920", "1"), ("1280", "1")):
            r = subprocess.run(["bash", "-c", 'ESCALA=""\n%s\nancho_pantalla() { echo %s; }\nescala' % (prog, ancho)],
                               capture_output=True, text=True, timeout=10)
            cierto("pantalla de %s px de ancho: tamaño ×%s" % (ancho, esperado), r.stdout.strip() == esperado, r.stdout + r.stderr)
    cierto("pantalla.sh: Alt + F4 deja el escritorio y un cuelgue la vuelve a abrir",
           '[ "$salida" -eq 0 ] && break' in pan and "?pantalla=1" in pan)
    act = open(os.path.join(PI, "actualizar.sh"), encoding="utf-8").read()
    cierto("actualizar.sh pasa la pantalla al nombre nuevo y borra lo que ya no va",
           'pantalla.sh" instalar' in act and "rsync -a --delete" in act)
    cierto("actualizar.sh deja la red propia vigilada y para cada encendido (sin levantarla ahora), aunque esté apagada",
           'punto_de_acceso.sh" preparar' in act and "grep -qx tablero-ap" in act
           and "connection.autoconnect connection show tablero-ap" not in act)
    cierto("ya no queda el script con el nombre viejo",
           not os.path.exists(os.path.join(PI, "kios" + "co.sh")))
    if os.name != "nt":
        casa = tempfile.mkdtemp(prefix="h08_casa_")
        viejo = os.path.join(casa, ".config", "autostart", "tablero-kios" + "co.desktop")
        os.makedirs(os.path.dirname(viejo)); open(viejo, "w").write("viejo")
        labwc = os.path.join(casa, ".config", "labwc", "autostart")
        os.makedirs(os.path.dirname(labwc))
        open(labwc, "w").write("/bin/bash /x/kios" + "co.sh &\notra cosa\n")
        env = dict(os.environ, HOME=casa, XDG_RUNTIME_DIR=casa)
        try:
            subprocess.run(["bash", os.path.join(PI, "pantalla.sh"), "instalar"], env=env,
                           capture_output=True, timeout=30)
            lw = open(labwc, encoding="utf-8").read()
            cierto("pantalla.sh instalar: arranque, menú y limpia el arranque viejo",
                   os.path.exists(os.path.join(casa, ".config", "autostart", "tablero-pantalla.desktop"))
                   and os.path.exists(os.path.join(casa, ".local", "share", "applications", "tablero-pantalla.desktop"))
                   and not os.path.exists(viejo) and "pantalla.sh" in lw and "otra cosa" in lw
                   and ("kios" + "co") not in lw, lw)
            subprocess.run(["bash", os.path.join(PI, "pantalla.sh"), "quitar"], env=env,
                           capture_output=True, timeout=30)
            cierto("pantalla.sh quitar: ya no arranca sola",
                   not os.path.exists(os.path.join(casa, ".config", "autostart", "tablero-pantalla.desktop"))
                   and "pantalla.sh" not in open(labwc, encoding="utf-8").read())
        except (OSError, subprocess.SubprocessError) as e:
            print("  --   pantalla.sh instalar: sin bash, salteado (%s)" % e)
    cierto("actualizar.sh no pisa la clave, la calibración ni el motor",
           all(re.search(r"--exclude '%s'" % re.escape(n),
                         open(os.path.join(PI, "actualizar.sh"), encoding="utf-8").read())
               for n in ("secreto_admin.json", "calibracion_servos.json",
                         "posicion_motores.json")))


def probar_llave():
    """Lógica de la llave BATERÍA: apaga solo al pasar de ENC a APAG y quedarse ahí."""
    print("\n LLAVE BATERÍA (apagado seguro)")
    from llave_apagado import LlaveApagado
    from configuracion import LLAVE_APAGADO, MOTORES

    def armar(posiciones, falla=None, cuenta=0.0):
        # posiciones: lista de (segundos, apag); devuelve (llave, veces que apagó)
        veces = []
        actual = {"apag": posiciones[0][1]}

        def apagar():
            if falla:
                raise RuntimeError(falla)
            veces.append(1)
        L = LlaveApagado(lambda: actual["apag"], apagar, segundos=2.0, cuenta=cuenta)
        t = 0.0
        for seg, apag in posiciones:
            actual["apag"] = apag
            fin = t + seg
            while t < fin - 1e-9:
                L.paso(t)
                t += 0.1
        return L, len(veces)

    L, n = armar([(1, False), (2.5, True), (3, True)])
    cierto("ENC -> APAG 2 s: apaga una sola vez", n == 1 and L.estado["apagando"], (n, L.estado))
    L, n = armar([(1, False), (1.5, True), (0.5, False), (1.5, True), (1, False)])
    cierto("un golpe (menos de 2 s en APAG) no apaga", n == 0 and not L.estado["apagando"], n)
    L, n = armar([(5, True)])
    cierto("arranca en APAG: no apaga y avisa", n == 0 and "APAG" in L.estado["aviso"], L.estado)
    L, n = armar([(3, True), (1, False), (2.5, True)])
    cierto("arranca en APAG, pasa a ENC y vuelve a APAG: apaga", n == 1, n)
    L, n = armar([(1, False), (3, True)], falla="sin permiso")
    cierto("si no puede apagar, lo dice y no queda 'apagando'",
           n == 0 and not L.estado["apagando"] and "sin permiso" in L.estado["aviso"], L.estado)

    # cuenta regresiva: el cartel sale a los 2 s y ENC lo cancela
    L, n = armar([(1, False), (3.05, True)], cuenta=5.0)
    cierto("cuenta regresiva: a los 2 s en APAG aparece el cartel con lo que falta",
           n == 0 and L.estado["apagando"] and L.estado["cuenta"] == 4, L.estado)
    L, n = armar([(1, False), (4, True), (1, False)], cuenta=5.0)
    cierto("volver a ENC durante la cuenta cancela y saca el cartel",
           n == 0 and not L.estado["apagando"] and L.estado["cuenta"] is None
           and L.estado["aviso"] == "", L.estado)
    L, n = armar([(1, False), (4, True), (1, False), (7.5, True)], cuenta=5.0)
    cierto("después de cancelar, volver a APAG empieza de nuevo y apaga",
           n == 1 and L.estado["cuenta"] == 0, (n, L.estado))
    L, n = armar([(1, False), (6.5, True)], cuenta=5.0)
    cierto("2 s + 5 s de cuenta todavía no apaga (justo antes)", n == 0, (n, L.estado))
    L, n = armar([(1, False), (7.5, True), (2, False)], cuenta=5.0)
    cierto("terminada la cuenta apaga una vez; ENC después ya no lo cancela",
           n == 1 and L.estado["apagando"] and "Ya se está apagando" in L.estado["aviso"], (n, L.estado))
    cierto("la cuenta regresiva del tablero dura unos segundos (configuracion)",
           3.0 <= LLAVE_APAGADO["cuenta_s"] <= 10.0, LLAVE_APAGADO)
    cierto("el tablero usa esa cuenta al armar la llave",
           'cuenta=LLAVE_APAGADO["cuenta_s"]' in open(os.path.join(PI, "tablero_pi5.py"), encoding="utf-8").read())

    def rota():
        raise OSError("pin ocupado")
    L = LlaveApagado(rota, lambda: None)
    cierto("si no se puede leer el pin, no apaga", L.paso(0) is False and L.paso(5) is False
           and L.estado["posicion"] == "sin llave")
    usados = {2, 3} | {p for m in MOTORES.values() for p in m["pines"]}
    cierto("el pin de la llave no lo usa nada más (I2C, motor)",
           LLAVE_APAGADO["gpio"] not in usados, LLAVE_APAGADO)

    import time
    from hilo_simulacion import HiloSimulacion
    h = HiloSimulacion(ActuadoresSimulados(), semilla=1)
    h.llave = LlaveApagado(lambda: True, lambda: None)
    h.llave.paso(0)
    h.start()
    t0 = time.monotonic()
    while "llave" not in h.foto and time.monotonic() - t0 < 3:
        time.sleep(0.05)
    h.detener()
    h.join(3)
    cierto("la foto que lee la página trae la llave", h.foto.get("llave", {}).get("posicion") == "APAG",
           h.foto.get("llave"))
    pag = open(os.path.join(PI, "web", "tablero.html"), encoding="utf-8").read()
    cierto("la página tiene el cartel de apagado y no intenta reconectar",
           'id="apagando"' in pag and "llave(d.llave)" in pag and "!APAGANDO" in pag)
    cierto("la página saca el cartel si se cancela y muestra la cuenta",
           "APAGANDO=!!(L && L.apagando)" in pag and "Para cancelar" in pag and 'id="apagTxt"' in pag)

    import tablero_pi5 as T
    viejo = T.ORDEN_APAGAR
    try:
        T.ORDEN_APAGAR = [sys.executable, "-c", "import sys; sys.exit(1)"]
        try:
            T.apagar_raspberry(espera=0)
            sin_permiso = False
        except RuntimeError as e:
            sin_permiso = "--permiso-apagado" in str(e)
        cierto("sin permiso de apagado, el error dice cómo arreglarlo", sin_permiso)
        T.ORDEN_APAGAR = [sys.executable, "-c", "pass"]
        T.apagar_raspberry(espera=0)
        cierto("con permiso, pide el apagado sin error", True)
    finally:
        T.ORDEN_APAGAR = viejo
    inst = open(os.path.join(PI, "instalar.sh"), encoding="utf-8").read()
    cierto("instalar.sh da SÓLO el permiso de apagar, validado con visudo",
           "NOPASSWD: /usr/bin/systemctl poweroff\"" in inst and "visudo -cf" in inst
           and "--permiso-apagado)" in inst)
    cierto("el programa apaga con el mismo comando que permite instalar.sh",
           viejo == ["sudo", "-n", "/usr/bin/systemctl", "poweroff"])


def probar_actualizar():
    """Corre actualizar.sh de verdad sobre una instalación de mentira (sin sudo ni systemd)."""
    print("\n ACTUALIZAR (instalación de mentira)")
    import shutil
    import time
    if os.name == "nt" or not shutil.which("bash") or not shutil.which("rsync"):
        print("  --   hace falta bash y rsync (Linux o la Pi), salteado")
        return
    base = tempfile.mkdtemp(prefix="h08_act_")
    privados = ("secreto_admin.json", "calibracion_servos.json", "posicion_motores.json")
    fuera = shutil.ignore_patterns("__pycache__", "informes", "dist", ".git", *privados)
    inst = os.path.join(base, "casa", "H08_Pi5")
    nuevo = os.path.join(base, "pendrive", "H08_Pi5")
    shutil.copytree(RAIZ, inst, ignore=fuera)
    shutil.copytree(RAIZ, nuevo, ignore=fuera)
    pi = os.path.join(inst, "raspberry_pi5")
    for n in privados:
        with open(os.path.join(pi, n), "w", encoding="utf-8") as f:
            f.write('{"de": "este tablero"}')
    with open(os.path.join(pi, "programa_viejo.py"), "w") as f:
        f.write("# ya no viene en el paquete")
    os.makedirs(os.path.join(pi, "informes"))
    ahora = time.time()
    for i in range(25):
        r = os.path.join(pi, "informes", "calibracion_%02d.txt" % i)
        open(r, "w").close()
        os.utime(r, (ahora - 1000 + i, ahora - 1000 + i))   # el 24 es el más nuevo
    for f in ("20200101_000000", "20210101_000000", "20220101_000000"):
        os.makedirs(os.path.join(base, "casa", "H08_respaldo_" + f))
    # sudo y systemctl de mentira: anotan lo que les piden y dicen que sí
    falsos = os.path.join(base, "bin")
    os.makedirs(falsos)
    for prog in ("sudo", "systemctl"):
        with open(os.path.join(falsos, prog), "w") as f:
            f.write('#!/bin/sh\necho "%s $*" >> "%s"\nexit 0\n' % (prog, os.path.join(base, "ordenes.txt")))
        os.chmod(os.path.join(falsos, prog), 0o755)
    # y un usuario común (las pruebas pueden correr como root)
    with open(os.path.join(falsos, "id"), "w") as f:
        f.write('#!/bin/sh\ncase "$1" in -u) echo 1000;; -un) echo alumno;; *) exec /usr/bin/id "$@";; esac\n')
    os.chmod(os.path.join(falsos, "id"), 0o755)
    env = dict(os.environ, PATH=falsos + os.pathsep + os.environ.get("PATH", ""),
               HOME=os.path.join(base, "casa"))
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    r = subprocess.run(["bash", os.path.join(pi, "actualizar.sh"), nuevo], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120)
    cierto("actualizar.sh termina bien", r.returncode == 0, r.stdout[-600:] + r.stderr[-600:])
    cierto("conserva la clave, la calibración y la posición del motor",
           all(open(os.path.join(pi, n), encoding="utf-8").read() == '{"de": "este tablero"}'
               for n in privados))
    cierto("borra lo que ya no viene en el paquete",
           not os.path.exists(os.path.join(pi, "programa_viejo.py"))
           and os.path.exists(os.path.join(pi, "tablero_pi5.py")))
    quedan = sorted(os.listdir(os.path.join(pi, "informes")))
    cierto("deja los 20 informes más nuevos",
           len(quedan) == 20 and quedan[0] == "calibracion_05.txt" and quedan[-1] == "calibracion_24.txt",
           quedan[:3])
    resp = sorted(d for d in os.listdir(os.path.join(base, "casa")) if d.startswith("H08_respaldo_"))
    cierto("deja los 2 respaldos más nuevos (uno es el de recién)",
           len(resp) == 2 and "H08_respaldo_2020" not in resp[0] and "H08_respaldo_2021" not in resp[0],
           resp)
    cierto("el respaldo nuevo tiene la calibración de antes",
           os.path.exists(os.path.join(base, "casa", resp[-1], "raspberry_pi5", "calibracion_servos.json")))
    ordenes = open(os.path.join(base, "ordenes.txt"), encoding="utf-8").read()
    cierto("da el permiso de la llave y reinicia el servicio",
           "visudo -cf" in ordenes and "tablero-h08-apagar" in ordenes
           and "systemctl stop tablero-h08" in ordenes and "systemctl start tablero-h08" in ordenes,
           ordenes)
    # el paquete descomprimido DENTRO de la carpeta instalada no se borra a mitad de camino
    adentro = os.path.join(inst, "H08_Pi5")
    shutil.copytree(nuevo, adentro)
    r = subprocess.run(["bash", os.path.join(pi, "actualizar.sh"), adentro], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120)
    cierto("con el paquete adentro de la instalación también anda (y lo saca)",
           r.returncode == 0 and os.path.exists(os.path.join(pi, "tablero_pi5.py"))
           and not os.path.exists(adentro), r.stdout[-400:] + r.stderr[-400:])
    shutil.rmtree(base, ignore_errors=True)


def main():
    probar_camara_lenta()
    probar_luces()
    probar_disposicion()
    probar_caratulas()
    probar_servidor()
    probar_scripts()
    probar_guiadas()
    probar_pasar_instrumento()
    probar_cabeceo()
    probar_elegir_giro()
    probar_tope()
    probar_transportador()
    probar_brujula()
    probar_vigilancia()
    probar_flechas()
    probar_punto_de_acceso()
    probar_llave()
    probar_actualizar()
    print("\n" + ("Todas bien." if not fallos else "FALLARON %d: %s" % (len(fallos), ", ".join(fallos))))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
