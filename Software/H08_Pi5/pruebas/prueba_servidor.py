#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Levanta el servidor de verdad con un núcleo de mentira y le pega con pedidos HTTP.

Lo que importa es que conteste 403 a las órdenes que no vienen de un
administrador. Esconder los botones no alcanza: cualquiera abre la consola.
"""
import http.client
import json
import os
import sys
import tempfile
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
for _c in (os.path.join(AQUI, "..", "nucleo"), os.path.join(AQUI, "nucleo")):
    if os.path.isdir(_c):
        sys.path.insert(0, os.path.abspath(_c))
        break

import acceso as acceso_mod                                  # noqa: E402
from acceso import Acceso                                    # noqa: E402
import servidor_web                                       # noqa: E402

fallos = []


def igual(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print("  %s %-54s %s" % ("ok  " if ok else "MAL ", nombre,
                             "" if ok else "-> %r (esperaba %r)"
                             % (obtenido, esperado)))
    if not ok:
        fallos.append(nombre)


def cierto(nombre, v):
    igual(nombre, bool(v), True)


class NucleoFalso:
    # lo mínimo que el servidor le pide al núcleo; anota lo que le ordenan

    def __init__(self):
        self.catalogo = {"fases": [], "escenarios": [], "fallas": [],
                         "instrumentos": [], "anunciador": []}
        self.foto = {"modo_nombre": "MODO 1", "t": 1.0, "pausado": False,
                     "fase": "CRUCERO", "fase_texto": "Crucero"}
        self.ordenes = []

    def ordenar(self, que, valor=None):
        self.ordenes.append((que, valor))


class Cliente:

    def __init__(self, puerto):
        self.puerto = puerto
        self.cookie = None

    def _pedir(self, metodo, ruta, datos=None):
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=5)
        cab = {}
        if self.cookie:
            cab["Cookie"] = self.cookie
        cuerpo = None
        if datos is not None:
            cuerpo = json.dumps(datos).encode("utf-8")
            cab["Content-Type"] = "application/json"
        c.request(metodo, ruta, body=cuerpo, headers=cab)
        r = c.getresponse()
        cuerpo = r.read().decode("utf-8", "replace")
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        destino = r.getheader("Location")
        c.close()
        return r.status, cuerpo, destino

    def get(self, ruta):
        return self._pedir("GET", ruta)

    def post(self, ruta, datos=None):
        return self._pedir("POST", ruta, datos)

    def seguir(self, ruta):
        # sigue el redirect, como el navegador con el QR
        cod, cuerpo, destino = self.get(ruta)
        if cod in (301, 302) and destino:
            return self.get(destino)
        return cod, cuerpo, destino


def main():
    tmp = tempfile.mkdtemp()
    web = os.path.join(tmp, "web")
    os.makedirs(web)
    # páginas de mentira, para no depender de las de verdad
    for f, t in (("tablero.html", "<html>TABLERO PUBLICO</html>"),
                 ("mando.html", "<html>BOTONERA</html>"),
                 ("sin_permiso.html", "<html>PEDIR LA CLAVE</html>")):
        open(os.path.join(web, f), "w", encoding="utf-8").write(t)

    acceso = Acceso(os.path.join(tmp, "secreto_admin.json"))
    nucleo = NucleoFalso()
    puerto = servidor_web.puerto_libre(8731)
    srv = servidor_web.crear(nucleo, puerto, web, acceso=acceso)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    time.sleep(0.3)

    print("=" * 76)
    print(" EL SERVIDOR, CON UN VISITANTE Y DOS ADMINISTRADORES")
    print("=" * 76)

    # el visitante
    print("\n  EL VISITANTE (sin clave)")
    v = Cliente(puerto)
    cod, cuerpo, _ = v.get("/")
    igual("puede ver el tablero", cod, 200)
    cierto("y es la pagina publica", "TABLERO PUBLICO" in cuerpo)

    cod, _c, _ = v.get("/api/estado")
    igual("puede leer el estado en vivo", cod, 200)
    cod, cuerpo, _ = v.get("/api/catalogo")
    igual("puede leer el catalogo", cod, 200)
    igual("y el catalogo le dice que no es admin",
          json.loads(cuerpo).get("admin"), False)

    cod, cuerpo, _ = v.get("/mando")
    igual("en /mando le sale que hace falta el QR", cod, 200)
    cierto("y no la botonera", "BOTONERA" not in cuerpo)
    cod, _c, _ = v.get("/tecnico")
    igual("la vista tecnica ya no existe para nadie", cod, 404)

    antes = len(nucleo.ordenes)
    for ruta in ("/api/modo/1", "/api/modo/3?id=OIL_PRESS_LOSS",
                 "/api/accion/pausa?valor=true",
                 "/api/accion/velocidad?valor=4"):
        cod, _c, _ = v.post(ruta)
        igual("POST %s -> prohibido" % ruta[:34], cod, 403)
    igual("y el nucleo no recibio NINGUNA orden", len(nucleo.ordenes), antes)

    cod, _c, _ = v.post("/api/mando/tomar")
    igual("tampoco puede tomar el mando", cod, 403)

    # una clave inventada no sirve
    cod, cuerpo, _ = v.get("/mando?k=" + "x" * 22)
    cierto("con una clave inventada tampoco entra", "BOTONERA" not in cuerpo)

    # la clave interna en la dirección no sirve desde un celular, ya no hay QR
    # de administrador: el profesor entra con su clave
    _local = servidor_web.Manejador._es_local
    servidor_web.Manejador._es_local = lambda self: False
    try:
        r = Cliente(puerto)
        cod, cuerpo, _ = r.get("/mando?k=" + acceso.clave)
        cierto("desde un celular la clave interna en la direccion no entra",
               cod == 200 and "BOTONERA" not in cuerpo and r.cookie is None)
    finally:
        servidor_web.Manejador._es_local = _local

    # el profesor
    print("\n  EL PROFESOR (programa de prueba en la propia Raspberry)")
    p = Cliente(puerto)
    cod, cuerpo, destino = p.get("/mando?k=" + acceso.clave)
    igual("el QR redirige", cod, 302)
    igual("a la direccion sin la clave", destino, "/mando")
    cierto("y deja cookie", p.cookie and p.cookie.startswith("h08="))
    cierto("la clave no quedo en la URL de destino", "k=" not in (destino or ""))

    cod, cuerpo, _ = p.get("/mando")
    cierto("ahora si ve la botonera", "BOTONERA" in cuerpo)
    cod, _c, _ = p.get("/tecnico")
    igual("y para el profesor tampoco", cod, 404)

    antes = len(nucleo.ordenes)
    cod, _c, _ = p.post("/api/modo/3?id=OIL_PRESS_LOSS")
    igual("puede meter una falla", cod, 200)
    igual("y la orden llego al nucleo", len(nucleo.ordenes), antes + 1)
    igual("con lo que corresponde", nucleo.ordenes[-1],
          ("modo_falla", "OIL_PRESS_LOSS"))

    cod, cuerpo, _ = p.get("/api/sesion")
    e = json.loads(cuerpo)
    cierto("se ve como admin", e["admin"])
    cierto("y con el mando", e["mando"])

    # el tablero muestra el atajo a /mando solo si el catalogo dice que si
    cod, cuerpo, _ = p.get("/api/catalogo")
    cierto("el catalogo le avisa al tablero que es admin",
           json.loads(cuerpo).get("admin"))

    # el ayudante
    print("\n  EL AYUDANTE (tambien con el QR)")
    a = Cliente(puerto)
    a.seguir("/mando?k=" + acceso.clave)
    cod, cuerpo, _ = a.get("/api/sesion")
    e = json.loads(cuerpo)
    cierto("es admin", e["admin"])
    igual("pero no tiene el mando", e["mando"], False)
    cierto("y ve que lo tiene otro", e["hay_titular"])

    antes = len(nucleo.ordenes)
    cod, cuerpo, _ = a.post("/api/accion/pausa?valor=true")
    igual("su orden se rechaza con 409", cod, 409)
    cierto("explicando que el mando lo tiene otro",
           "mando" in json.loads(cuerpo).get("motivo", "").lower())
    igual("y el nucleo no la recibio", len(nucleo.ordenes), antes)

    cod, _c, _ = a.post("/api/mando/pedir")
    igual("puede pedir el mando", cod, 200)
    cod, cuerpo, _ = p.get("/api/sesion")
    cierto("el profesor ve el pedido", json.loads(cuerpo)["pedido_ajeno"])

    cod, _c, _ = p.post("/api/mando/ceder")
    igual("el profesor cede", cod, 200)
    cod, cuerpo, _ = a.get("/api/sesion")
    cierto("y el ayudante queda con el mando", json.loads(cuerpo)["mando"])

    antes = len(nucleo.ordenes)
    cod, _c, _ = a.post("/api/accion/pausa?valor=true")
    igual("ahora si le pasan las ordenes", cod, 200)
    igual("y llegan al nucleo", len(nucleo.ordenes), antes + 1)
    cod, _c, _ = a.post("/api/accion/borrar_todo?valor=true")
    igual("una orden que no existe se rechaza con 400", cod, 400)
    igual("y no llega al nucleo", len(nucleo.ordenes), antes + 1)

    cod, _c, _ = p.post("/api/accion/pausa?valor=false")
    igual("y al profesor ya no", cod, 409)

    # salir
    print("\n  CERRAR SESION")
    cod, _c, destino = a.get("/salir")
    igual("redirige al tablero", destino, "/")
    a.cookie = None
    cod, _c, _ = a.post("/api/modo/1")
    igual("y ya no puede mandar", cod, 403)

    # renovar la clave
    print("\n  RENOVAR LA CLAVE")
    vieja = acceso.clave
    nueva = acceso.renovar_clave()
    cod, _c, _ = p.post("/api/modo/1")
    igual("la sesion del profesor se corta", cod, 403)
    z = Cliente(puerto)
    cod, cuerpo, _ = z.get("/mando?k=" + vieja)
    cierto("la clave vieja ya no entra", "BOTONERA" not in cuerpo)
    z2 = Cliente(puerto)
    cod, cuerpo, _ = z2.seguir("/mando?k=" + nueva)
    cierto("la nueva si", "BOTONERA" in cuerpo)

    # la clave del profesor, escrita en la pagina
    print("\n  EL PROFESOR (con la clave escrita)")
    reales = os.path.join(AQUI, "..", "raspberry_pi5", "web")
    with open(os.path.join(reales, "tablero.html"), encoding="utf-8") as f:
        cierto("la pagina publica tiene el boton del profesor",
               "Soy el profesor" in f.read())
    with open(os.path.join(reales, "sin_permiso.html"), encoding="utf-8") as f:
        cierto("la pagina sin permiso pide la clave", "/api/entrar" in f.read())
    w = Cliente(puerto)
    cod, cuerpo, _ = w.get("/mando")
    cierto("sin sesion, /mando muestra donde poner la clave", "PEDIR LA CLAVE" in cuerpo)
    cod, _c, _ = w.post("/api/entrar", {"clave": "equivocada"})
    igual("con una clave equivocada no entra", cod, 403)
    cierto("ni le deja cookie", w.cookie is None)
    cod, cuerpo, _ = w.post("/api/entrar", {"clave": acceso_mod.CLAVE_INICIAL})
    igual("con la inicial entra", cod, 200)
    cierto("y le avisa que tiene que cambiarla", json.loads(cuerpo).get("cambiar"))
    antes = len(nucleo.ordenes)
    cod, _c, _ = w.post("/api/modo/1")
    igual("con la inicial no puede mandar", cod, 403)
    igual("y el nucleo no recibio la orden", len(nucleo.ordenes), antes)
    cod, cuerpo, _ = w.get("/api/sesion")
    cierto("la sesion dice que cambie la clave", json.loads(cuerpo).get("cambiar_clave"))
    cod, _c, _ = w.post("/api/clave", {"nueva": "abc"})
    igual("una clave corta se rechaza", cod, 400)
    cod, _c, _ = w.post("/api/clave", {"nueva": "taller-quilmes"})
    igual("una propia se acepta", cod, 200)
    cod, _c, _ = w.post("/api/modo/1")
    igual("ahora si puede mandar", cod, 200)
    cod, _c, _ = w.post("/api/accion/activar")
    igual("puede activar el tablero", cod, 200)
    igual("y la orden llega al nucleo", nucleo.ordenes[-1][0], "activar")
    cod, _c, _ = Cliente(puerto).post("/api/accion/activar")
    igual("un visitante no puede activarlo", cod, 403)
    q = Cliente(puerto)
    cod, _c, _ = q.post("/api/entrar", {"clave": acceso_mod.CLAVE_INICIAL})
    igual("la inicial ya no entra", cod, 403)
    cod, cuerpo, _ = q.post("/api/entrar", {"clave": "taller-quilmes"})
    igual("la nueva si", cod, 200)
    cierto("sin tener que cambiarla", not json.loads(cuerpo).get("cambiar"))
    cod, cuerpo, _ = q.get("/mando")
    cierto("y ve la botonera", "BOTONERA" in cuerpo)
    cod, _c, _ = Cliente(puerto).post("/api/clave", {"nueva": "hackeada123"})
    igual("sin sesion no se puede cambiar la clave", cod, 403)

    # que la clave no salga nunca por la web
    print("\n  LA CLAVE NO SE SIRVE POR LA WEB")
    for ruta in ("/", "/qr", "/api/catalogo", "/api/estado", "/api/sesion",
                 "/mando"):
        cod, cuerpo, _ = z2.get(ruta)
        igual("la clave no aparece en %s" % ruta, nueva in cuerpo, False)

    srv.shutdown()

    # servidor abierto (compu propia). Se nos había escapado: con acceso=None
    # dejaba mandar pero /mando pedía el QR, y no había forma de llegar a la botonera
    print("\n  EL SERVIDOR ABIERTO (computadora propia, sin clave)")
    n2 = NucleoFalso()
    p2 = servidor_web.puerto_libre(8751)
    srv2 = servidor_web.crear(n2, p2, web, acceso=None)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    time.sleep(0.3)
    c = Cliente(p2)
    cod, cuerpo, _ = c.get("/")
    igual("se ve el tablero", cod, 200)
    cod, cuerpo, _ = c.get("/mando")
    cierto("y TAMBIEN la botonera, sin clave", "BOTONERA" in cuerpo)
    cod, cuerpo, _ = c.get("/api/catalogo")
    cierto("el catalogo dice que es admin (aparece el atajo)",
           json.loads(cuerpo).get("admin"))
    antes = len(n2.ordenes)
    cod, _x, _ = c.post("/api/modo/1")
    igual("y las ordenes pasan", cod, 200)
    igual("y llegan al nucleo", len(n2.ordenes), antes + 1)
    srv2.shutdown()

    # la página que se abre sola al conectarse a la red del tablero
    print("\n  AL CONECTARSE A LA RED DEL TABLERO, LA PAGINA SE ABRE SOLA")
    igual("con el puerto 80 la direccion no lleva numero",
          servidor_web.url_de("10.55.0.1", 80), "http://10.55.0.1/")
    igual("con otro puerto si", servidor_web.url_de("10.55.0.1", 8000), "http://10.55.0.1:8000/")
    igual("escrita para la gente: sin http ni barra",
          servidor_web.sin_http("http://10.55.0.1/"), "10.55.0.1")
    n3 = NucleoFalso()
    p3 = servidor_web.puerto_libre(8771)
    srv3 = servidor_web.crear(n3, p3, web, acceso=None)
    threading.Thread(target=srv3.serve_forever, daemon=True).start()
    time.sleep(0.3)
    M = servidor_web.Manejador
    M._ip_ap = "127.0.0.1"          # el celular de la prueba "esta en la red del tablero"
    M.liberados.clear()

    def pedir(ruta, host):
        c = http.client.HTTPConnection("127.0.0.1", p3, timeout=5)
        c.request("GET", ruta, headers={"Host": host})
        r = c.getresponse()
        cuerpo = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, r.getheader("Location"), cuerpo

    base = "http://127.0.0.1:%d/" % p3
    igual("Android prueba internet: le abre el tablero (con el renglon de ayuda)",
          pedir("/generate_204", "connectivitycheck.gstatic.com")[:2], (302, base + "?bienvenida=1"))
    igual("iPhone prueba internet: tambien",
          pedir("/hotspot-detect.html", "captive.apple.com")[:2], (302, base + "?bienvenida=1"))
    cod, _d, cuerpo = pedir("/?bienvenida=1", "127.0.0.1")
    cierto("la ventana muestra el tablero", cod == 200 and "TABLERO PUBLICO" in cuerpo)
    igual("la direccion vieja de la bienvenida lleva al tablero", pedir("/bienvenida", "127.0.0.1")[:2], (302, "/?bienvenida=1"))
    igual("Entrar lleva al tablero", pedir("/entrar", "127.0.0.1")[:2], (302, "/"))
    igual("a Android nunca se le dice que hay internet (si no, cierra solo la ventana)",
          pedir("/generate_204", "connectivitycheck.gstatic.com")[:2], (302, base + "?bienvenida=1"))
    cod, _d, cuerpo = pedir("/hotspot-detect.html", "captive.apple.com")
    cierto("el iPhone, despues de abrir el tablero, ve internet (muestra OK y no se desconecta)",
           cod == 200 and "Success" in cuerpo)
    # pasa el tiempo sin usar el tablero: al volver a conectarse, otra vez la ventana
    for k in list(M.liberados):
        M.liberados[k] -= M.LIBRE_S + 1
    igual("si no lo usa un rato, al volver a conectarse el iPhone vuelve a ver la ventana",
          pedir("/hotspot-detect.html", "captive.apple.com")[:2], (302, base + "?bienvenida=1"))
    pedir("/", "127.0.0.1")
    # el estado y las páginas van comprimidos si el navegador acepta
    c = http.client.HTTPConnection("127.0.0.1", p3, timeout=5)
    estilo = "body{color:#123456}\n" * 300
    with open(os.path.join(web, "estilo.css"), "w", encoding="utf-8") as f:
        f.write(estilo)
    c.request("GET", "/estilo.css", headers={"Host": "127.0.0.1", "Accept-Encoding": "gzip, deflate"})
    r = c.getresponse(); crudo = r.read(); c.close()
    import gzip as _gz
    cierto("lo que se manda va comprimido (gzip), mas chico, y se descomprime igual",
           r.getheader("Content-Encoding") == "gzip" and len(crudo) < len(estilo) / 3
           and _gz.decompress(crudo).decode("utf-8") == estilo)
    cod, _d, cuerpo = pedir("/api/red", "127.0.0.1")
    d = json.loads(cuerpo)
    cierto("/api/red dice el limite de celulares (y cuantos hay, si se puede saber)",
           cod == 200 and d.get("limite") == 8 and "conectados" in d)
    igual("otro sitio cualquiera lleva al tablero",
          pedir("/", "www.google.com")[:2], (302, base))
    cod, _d, cuerpo = pedir("/", "127.0.0.1:%d" % p3)
    cierto("con la direccion del tablero, el tablero", cod == 200 and "TABLERO PUBLICO" in cuerpo)
    # el profesor desconecta celulares
    tmpb = tempfile.mkdtemp()
    viejo = (servidor_web.ARCH_BLOQUEADOS, servidor_web.celulares_detalle, servidor_web.mac_de_ip)
    servidor_web.ARCH_BLOQUEADOS = os.path.join(tmpb, "bloqueados_red.txt")
    servidor_web.celulares_detalle = lambda: [
        {"mac": "aa:aa:aa:aa:aa:01", "ip": "10.55.0.11", "nombre": "Galaxy-A12", "segundos": 300},
        {"mac": "aa:aa:aa:aa:aa:02", "ip": "10.55.0.12", "nombre": "iPhone", "segundos": 60},
        {"mac": "aa:aa:aa:aa:aa:09", "ip": "127.0.0.1", "nombre": "profe", "segundos": 900}]
    yo_mac = ["aa:aa:aa:aa:aa:09"]
    servidor_web.mac_de_ip = lambda ip: yo_mac[0]

    def post(ruta):
        c = http.client.HTTPConnection("127.0.0.1", p3, timeout=5)
        c.request("POST", ruta, body=b"", headers={"Host": "127.0.0.1"})
        r = c.getresponse(); cuerpo = r.read().decode("utf-8", "replace"); c.close()
        return r.status, cuerpo
    cod, _d, cuerpo = pedir("/api/red/celulares", "127.0.0.1")
    d = json.loads(cuerpo)
    cierto("el profesor ve los celulares conectados y cual es el suyo",
           cod == 200 and len(d["conectados"]) == 3 and [c["yo"] for c in d["conectados"]] == [False, False, True])
    cod, _c = post("/api/red/desconectar?mac=aa:aa:aa:aa:aa:09")
    igual("no se puede desconectar a si mismo", cod, 400)
    cod, _c = post("/api/red/desconectar?mac=aa:aa:aa:aa:aa:01")
    cierto("desconecta a uno: queda anotado con su nombre", cod == 200 and
           open(servidor_web.ARCH_BLOQUEADOS).read() == "aa:aa:aa:aa:aa:01 Galaxy-A12\n")
    d = json.loads(pedir("/api/red/celulares", "127.0.0.1")[2])
    cierto("y aparece en la lista de desconectados, no en la de conectados",
           [c["mac"] for c in d["bloqueados"]] == ["aa:aa:aa:aa:aa:01"]
           and "aa:aa:aa:aa:aa:01" not in [c["mac"] for c in d["conectados"]])
    yo_mac[0] = "aa:aa:aa:aa:aa:01"        # ahora pide el desconectado
    cod, _d, cuerpo = pedir("/", "127.0.0.1")
    cierto("el desconectado no ve el tablero: le dice que el profesor lo desconecto",
           cod == 403 and "desconect" in cuerpo)
    yo_mac[0] = "aa:aa:aa:aa:aa:09"
    cod, _c = post("/api/red/permitir?mac=aa:aa:aa:aa:aa:01")
    cierto("permitir lo saca de la lista", cod == 200 and open(servidor_web.ARCH_BLOQUEADOS).read() == "")
    cod, _c = post("/api/red/desconectar_otros")
    cierto("desconectar a todos menos al profesor",
           cod == 200 and sorted(servidor_web.leer_bloqueados()) == ["aa:aa:aa:aa:aa:01", "aa:aa:aa:aa:aa:02"])
    servidor_web.ARCH_BLOQUEADOS, servidor_web.celulares_detalle, servidor_web.mac_de_ip = viejo

    M._ip_ap = "10.55.0.1"          # ahora el celular NO esta en la red del tablero
    igual("desde la red de la escuela no se toca nada",
          pedir("/generate_204", "connectivitycheck.gstatic.com")[0], 404)
    cod, _d, cuerpo = pedir("/api/catalogo", "127.0.0.1")
    w = json.loads(cuerpo).get("wifi", {})
    cierto("el catalogo trae la clave del wifi (para mostrarla en el proyector)",
           w.get("clave") == servidor_web.datos_punto_de_acceso()["clave"] and w.get("clave"))
    M._ip_ap = None
    M.liberados.clear()
    srv3.shutdown()

    print("")
    print("=" * 76)
    if fallos:
        print(" FALLARON %d:" % len(fallos))
        for f in fallos:
            print("   %s" % f)
    else:
        print(" Todo bien.")
    print("=" * 76)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
