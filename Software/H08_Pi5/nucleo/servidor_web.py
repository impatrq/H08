# -*- coding: utf-8 -*-
"""La página web del tablero con http.server, sin internet ni paquetes.

/ es el tablero en vivo para cualquiera; /mando, la botonera del profe; /qr y
/cartel, para proyectar e imprimir. Las órdenes se rechazan acá (403 sin
sesión, 409 sin el mando): esconder botones en la página no protege nada.
"""
import json
import os
import re
import socket
import subprocess
import gzip
import hashlib
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as _ServidorHilos


class ThreadingHTTPServer(_ServidorHilos):
    # un celular que se va de la wifi no deja un error largo: gastaba la SD

    def handle_error(self, pedido, direccion):
        import sys as _sys
        if isinstance(_sys.exc_info()[1], (ConnectionError, TimeoutError, OSError)):
            return
        _ServidorHilos.handle_error(self, pedido, direccion)
from urllib.parse import urlparse, parse_qs

import qr

_AQUI = os.path.dirname(os.path.abspath(__file__))

# lo único que acepta /api/accion/ (los modos van por /api/modo/); lo demás, 400
ACCIONES = ("pausa", "velocidad", "prueba_luces", "piloto_reactivo", "ciclar",
            "activar_falla", "quitar_falla", "activar")
_SCRIPT_AP = os.path.join(_AQUI, "..", "raspberry_pi5", "punto_de_acceso.sh")


def datos_punto_de_acceso():
    """Red, clave e IP del wifi propio, sacados de punto_de_acceso.sh."""
    # leídos del script y no repetidos acá, así el cartel nunca queda viejo
    datos = {"red": "Tablero-H08", "clave": "", "ip": "10.55.0.1"}
    try:
        texto = open(_SCRIPT_AP, encoding="utf-8").read()
    except OSError:
        return datos
    for campo, var in (("red", "RED"), ("clave", "CLAVE"), ("ip", "IP")):
        m = re.search(r'^%s="([^"]*)"' % var, texto, re.M)
        if m:
            datos[campo] = m.group(1)
    return datos


# Cada celular pide el estado 4 veces por segundo (~3 kB); comprimido pesa
# un tercio. Lo grande (three.js) se comprime una sola vez
_COMPRIMIDOS = {}


def comprimir(cuerpo):
    if len(cuerpo) < 64 * 1024:
        return gzip.compress(cuerpo, 5, mtime=0)
    llave = hashlib.md5(cuerpo).hexdigest()
    if llave not in _COMPRIMIDOS:
        if len(_COMPRIMIDOS) > 20:
            _COMPRIMIDOS.clear()
        _COMPRIMIDOS[llave] = gzip.compress(cuerpo, 6, mtime=0)
    return _COMPRIMIDOS[llave]


# el wifi de la Pi acepta unos 8 a la vez, límite del chip
_RED_CACHE = {"t": -99.0, "dato": None}


def celulares_conectados():
    ahora = time.monotonic()
    if ahora - _RED_CACHE["t"] < 5:
        return _RED_CACHE["dato"]
    limite = 8
    try:
        m = re.search(r'^LIMITE_CELULARES=(\d+)', open(_SCRIPT_AP, encoding="utf-8").read(), re.M)
        limite = int(m.group(1)) if m else 8
    except OSError:
        pass
    n = None
    try:
        r = subprocess.run(["iw", "dev", "wlan0", "station", "dump"], capture_output=True,
                           text=True, timeout=2)
        activa = subprocess.run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
                                capture_output=True, text=True, timeout=2).stdout.split()
        if r.returncode == 0 and "tablero-ap" in activa:
            n = r.stdout.count("Station ")
    except (OSError, subprocess.SubprocessError):
        pass
    _RED_CACHE.update(t=ahora, dato={"conectados": n, "limite": limite})
    return _RED_CACHE["dato"]


# Los que desconectó el profe: una MAC por renglón en bloqueados_red.txt.
# punto_de_acceso.sh vigilar (corre como root) los saca del wifi; se borra al reiniciar
ARCH_BLOQUEADOS = os.path.join(_AQUI, "..", "raspberry_pi5", "bloqueados_red.txt")
_MAC = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")
_BLOQ = {"mtime": None, "dato": {}}
_bloq_cerrojo = threading.Lock()


def leer_bloqueados():
    # con caché por mtime: se consulta en cada pedido
    try:
        mt = os.stat(ARCH_BLOQUEADOS).st_mtime_ns
    except OSError:
        _BLOQ.update(mtime=None, dato={})
        return {}
    if mt != _BLOQ["mtime"]:
        d = {}
        try:
            with open(ARCH_BLOQUEADOS, encoding="utf-8") as f:
                for renglon in f:
                    partes = renglon.strip().split(" ", 1)
                    if partes and _MAC.match(partes[0].lower()):
                        d[partes[0].lower()] = partes[1] if len(partes) > 1 else ""
        except OSError:
            pass
        _BLOQ.update(mtime=mt, dato=d)
    return _BLOQ["dato"]


def guardar_bloqueados(d):
    with _bloq_cerrojo:
        tmp = ARCH_BLOQUEADOS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for mac, nombre in sorted(d.items()):
                f.write("%s %s\n" % (mac, re.sub(r"[\r\n]", " ", nombre or "")[:40]))
        os.replace(tmp, ARCH_BLOQUEADOS)


def mac_de_ip(ip):
    # /proc/net/arp se lee sin permisos
    try:
        with open("/proc/net/arp", encoding="ascii") as f:
            for renglon in f.readlines()[1:]:
                c = renglon.split()
                if len(c) >= 4 and c[0] == ip and c[3] != "00:00:00:00:00:00":
                    return c[3].lower()
    except OSError:
        pass
    return None


def _arriendos():
    d = {}
    import glob
    for arch in glob.glob("/var/lib/NetworkManager/dnsmasq-*.leases"):
        try:
            with open(arch, encoding="utf-8", errors="replace") as f:
                for renglon in f:
                    c = renglon.split()
                    if len(c) >= 4:
                        d[c[1].lower()] = (c[2], "" if c[3] == "*" else c[3])
        except OSError:
            pass
    return d


def celulares_detalle():
    """Conectados (mac, ip, nombre, segundos), o None si no se sabe."""
    try:
        r = subprocess.run(["iw", "dev", "wlan0", "station", "dump"], capture_output=True,
                           text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    lista, actual = [], None
    for renglon in r.stdout.splitlines():
        m = re.match(r"^Station ([0-9a-fA-F:]{17})", renglon)
        if m:
            actual = {"mac": m.group(1).lower(), "segundos": 0}
            lista.append(actual)
            continue
        m = re.search(r"connected time:\s*(\d+)", renglon)
        if m and actual is not None:
            actual["segundos"] = int(m.group(1))
    arr = _arriendos()
    for c in lista:
        ip, nombre = arr.get(c["mac"], (None, ""))
        c["ip"] = ip
        c["nombre"] = nombre
    return lista


def texto_qr_wifi(ap):
    # T primero: algunos Samsung viejos no lo leen si no
    return "WIFI:T:WPA;S:%s;P:%s;;" % (ap["red"], ap["clave"])


def puerto_libre(preferido, intentos=20):
    for p in range(preferido, preferido + intentos):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return None


def ip_de_red():
    """La IP para entrar desde el celular. Se calcula en cada pedido porque el
    servicio puede arrancar antes que la red."""
    # connect en UDP no manda nada, solo consulta la tabla de rutas
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        s.close()

    # sin salida afuera (la Pi como punto de acceso): gana la IP del AP
    try:
        salida = subprocess.run(["hostname", "-I"], capture_output=True,
                                text=True, timeout=2).stdout.split()
    except (OSError, subprocess.SubprocessError):
        salida = []
    ips = [x for x in salida if x.count(".") == 3 and not x.startswith("127.")]
    ip_ap = datos_punto_de_acceso()["ip"]
    if ip_ap in ips:
        return ip_ap
    return ips[0] if ips else None


def url_de(ip, puerto):
    # sin puerto si es 80: a mano alcanza con 10.55.0.1
    return "http://%s/" % ip if puerto == 80 else "http://%s:%d/" % (ip, puerto)


def sin_http(url):
    return re.sub(r"^http://", "", url).rstrip("/")


def direccion(puerto):
    return url_de(ip_de_red() or "localhost", puerto)


# se arman en el momento porque llevan el QR de la dirección actual
_PAGINA_QR = """<!doctype html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tablero H-08 &middot; entrar desde el celular</title>
<style>
 html,body{margin:0;height:100%%;background:#111;color:#eee;
   font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
 .caja{min-height:100%%;display:flex;flex-direction:column;
   align-items:center;justify-content:center;gap:1.4rem;padding:2rem;
   box-sizing:border-box;text-align:center}
 h1{font-size:1.5rem;font-weight:600;margin:0;letter-spacing:.02em}
 .qr{background:#fff;padding:18px;border-radius:14px;line-height:0}
 .url{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
   font-size:clamp(1.1rem,4vw,2rem);color:#7ec8ff;word-break:break-all}
 p{margin:0;color:#9aa4ae;max-width:34rem;line-height:1.5}
 a{color:#7ec8ff;text-decoration:none;border-bottom:1px solid #35505f;
   padding-bottom:2px}
</style></head><body><div class="caja">
<h1>Tablero did&aacute;ctico H-08</h1>
<div class="qr">%(svg)s</div>
<div class="url">%(url)s</div>
<p>Apunt&aacute; la c&aacute;mara del celular al c&oacute;digo. Ten&eacute;s que estar
en la misma red que %(donde)s.</p>
<p><a href="/">Ir al tablero</a> &nbsp;&middot;&nbsp; <a href="/cartel">Cartel para imprimir</a></p>
</div></body></html>"""

_PAGINA_CARTEL = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Cartel &middot; Tablero H-08</title>
<style>
 @page{size:A4;margin:16mm}
 body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:0}
 .hoja{max-width:178mm;margin:0 auto;text-align:center}
 h1{font-size:30pt;margin:6mm 0 1mm;color:#1F3864}
 .sub{font-size:12pt;color:#555;margin:0 0 3mm}
 .lema{font-size:13pt;color:#2E75B6;font-weight:bold;margin:0 0 7mm}
 .paso{display:inline-block;width:80mm;vertical-align:top;margin:0 3mm}
 .paso h2{font-size:15pt;margin:0 0 3mm}
 .qr{width:62mm;margin:0 auto 3mm}
 .qr svg{width:100%%;height:auto}
 .dato{font-size:14pt;font-weight:bold}
 .dato2{font-size:11pt;color:#555}
 .pie{margin-top:9mm;font-size:10pt;color:#666;line-height:1.6}
 .no-imprimir{margin:6mm 0;font-size:11pt}
 @media print{.no-imprimir{display:none}}
</style></head><body><div class="hoja">
<p class="no-imprimir">Para imprimir: Ctrl+P (en el celular, Compartir &rarr; Imprimir).</p>
<h1>TABLERO DEL H-08</h1>
<p class="sub">Sikorsky S-55 / H-19A &middot; EEST N&deg; 7 &middot; Taller Regional Quilmes</p>
<p class="lema">Miralo funcionar desde tu celular</p>
<div class="paso"><h2>1. Conectate a la red</h2>
 <div class="qr">%(qr_wifi)s</div>
 <div class="dato">%(red)s</div><div class="dato2">clave: %(clave)s</div></div>
<div class="paso"><h2>2. Abr&iacute; la p&aacute;gina</h2>
 <div class="qr">%(qr_url)s</div>
 <div class="dato">%(url)s</div><div class="dato2">s&oacute;lo para mirar &middot; se escribe as&iacute; en el navegador</div></div>
<p class="pie">La red del tablero no tiene internet: es normal. Si el celular pregunta, toc&aacute; "Mantener conexi&oacute;n".<br>
En muchos celulares la p&aacute;gina se abre sola al conectarse. Si no, us&aacute; el segundo c&oacute;digo.</p>
</div></body></html>"""


# Respuestas de "hay internet" para el que ya entró, así el iPhone no se
# desconecta al cerrar la ventana. A Android nunca: cierra solo la ventana del
# tablero apenas carga y el chico se queda sin nada.
_PRUEBAS_ANDROID = ("/generate_204", "/gen_204")
_PRUEBAS_DE_INTERNET = {
    "/hotspot-detect.html": (200, "text/html",                      # iPhone, Mac
                             "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"),
    "/library/test/success.html": (200, "text/html",
                                   "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"),
    "/connecttest.txt": (200, "text/plain", "Microsoft Connect Test"),   # Windows
    "/ncsi.txt": (200, "text/plain", "Microsoft NCSI"),
    "/success.txt": (200, "text/plain", "success\n"),                  # Firefox
}


class Manejador(BaseHTTPRequestHandler):
    # un hilo por pedido; la simulación va en el suyo y nadie la frena

    protocol_version = "HTTP/1.1"
    # sin esto cada respuesta tardaba ~40 ms más por Nagle
    disable_nagle_algorithm = True
    # que un celular que se fue sin cerrar no deje un hilo colgado
    timeout = 20
    nucleo = None                 # HiloSimulacion, lo pone crear()
    estaticos = None              # carpeta con las páginas .html
    puerto = 8000
    puerto_publico = 8000         # 80 si se pudo abrir
    donde = "esta computadora"
    acceso = None                 # None = sin clave

    # corto y sin decir de qué es
    COOKIE = "h08"

    def _es_local(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def _url_publica(self):
        return direccion(self.puerto_publico)

    # El AP contesta cualquier nombre con la IP de la Pi, así la prueba de
    # internet del celular llega acá y abre la página sola, como en un aeropuerto.
    # liberados: IPs que ya entraron. Vencen a los LIBRE_S sin pedidos; antes
    # duraban para siempre y el que volvía otro día con la misma IP no veía nada
    liberados = {}
    LIBRE_S = 300
    _cerrojo = threading.Lock()

    _ip_ap = None                 # se lee una vez

    def _red_del_tablero(self):
        if Manejador._ip_ap is None:
            Manejador._ip_ap = datos_punto_de_acceso()["ip"]
        ip_ap = Manejador._ip_ap
        prefijo = ip_ap.rsplit(".", 1)[0] + "."
        return ip_ap, self.client_address[0].startswith(prefijo)

    def _liberar(self):
        with self._cerrojo:
            self.liberados[self.client_address[0]] = time.monotonic()

    def _liberado(self):
        # y renueva la hora
        ip, ahora = self.client_address[0], time.monotonic()
        with self._cerrojo:
            t = self.liberados.get(ip)
            if t is None:
                return False
            if ahora - t > self.LIBRE_S:
                del self.liberados[ip]
                return False
            self.liberados[ip] = ahora
            return True

    def _desconectado(self):
        # True si ya se le contestó "desconectado"
        bloq = leer_bloqueados()
        if not bloq or not self._red_del_tablero()[1]:
            return False
        mac = mac_de_ip(self.client_address[0])
        if not mac or mac not in bloq:
            return False
        self._responder("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                        "<body style='font-family:sans-serif;background:#0b0e12;color:#e8edf2;padding:2rem'>"
                        "<h2>Desconectado</h2><p>El profesor te desconectó del tablero.</p></body>",
                        "text/html; charset=utf-8", 403)
        return True

    def _red_orden(self, ruta, consulta):
        bloq = dict(leer_bloqueados())
        yo = mac_de_ip(self.client_address[0])
        lista = celulares_detalle() or []
        nombres = {c["mac"]: c.get("nombre") or "" for c in lista}
        if ruta.endswith("/desconectar_otros"):
            nuevos = [c["mac"] for c in lista if c["mac"] != yo]
        else:
            mac = ((consulta.get("mac") or [""])[0]).strip().lower()
            if not _MAC.match(mac):
                self._prohibido("Falta el celular.", 400)
                return
            if ruta.endswith("/permitir"):
                bloq.pop(mac, None)
                guardar_bloqueados(bloq)
                self._json({"ok": True, "bloqueados": len(bloq)})
                return
            if mac == yo:
                self._prohibido("No te podés desconectar a vos mismo.", 400)
                return
            nuevos = [mac]
        for mac in nuevos:
            bloq[mac] = nombres.get(mac) or bloq.get(mac) or ""
        guardar_bloqueados(bloq)
        self._json({"ok": True, "desconectados": len(nuevos), "bloqueados": len(bloq)})

    def _portal(self, ruta):
        # True si era para otro sitio y ya se contestó; desde la red de la escuela no hace nada
        ip_ap, en_red = self._red_del_tablero()
        if not en_red:
            return False
        host = (self.headers.get("Host") or "").split(":")[0].strip().lower()
        if not host or host == ip_ap:
            self._liberado()              # renueva la hora
            return False
        if ruta in _PRUEBAS_ANDROID:
            self._ir_a(url_de(ip_ap, self.puerto_publico) + "?bienvenida=1")
            return True
        if self._liberado():
            prueba = _PRUEBAS_DE_INTERNET.get(ruta)
            if prueba:
                codigo, tipo, cuerpo = prueba
                self._responder(cuerpo, tipo + "; charset=utf-8", codigo)
            else:
                self._ir_a(url_de(ip_ap, self.puerto_publico))
            return True
        self._ir_a(url_de(ip_ap, self.puerto_publico) + "?bienvenida=1")
        return True

    def _ir_a(self, destino):
        self.send_response(302)
        self.send_header("Location", destino)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _responder(self, cuerpo, tipo="application/json; charset=utf-8", codigo=200,
                   cache=None):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        comprimido = False
        if (len(cuerpo) > 1024 and not tipo.startswith(("image/png", "font/"))
                and "gzip" in (self.headers.get("Accept-Encoding") or "")):
            cuerpo = comprimir(cuerpo); comprimido = True
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        if comprimido:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", cache or "no-store")
        if self._etag:
            self.send_header("ETag", self._etag)
        self.end_headers()
        try:
            self.wfile.write(cuerpo)
        except OSError:                    # el celular se fue: no es un error nuestro
            pass

    def _con_etag(self, archivo, tipo):
        # etiqueta fecha-tamaño: 304 si ya la tiene, y al actualizar se baja la nueva
        st = os.fstat(archivo.fileno())
        etiqueta = '"%x-%x"' % (int(st.st_mtime), st.st_size)
        if (self.headers.get("If-None-Match") or "").strip() == etiqueta:
            self.send_response(304)
            self.send_header("ETag", etiqueta)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        cuerpo = archivo.read()
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self._etag = etiqueta
        try:
            self._responder(cuerpo, tipo, cache="no-cache")
        finally:
            self._etag = None

    _etag = None

    def _json(self, dato):
        self._responder(json.dumps(dato))

    def _sid(self):
        crudo = self.headers.get("Cookie") or ""
        for parte in crudo.split(";"):
            k, _, v = parte.strip().partition("=")
            if k == self.COOKIE:
                return v.strip()
        return None

    def _cookie(self, sid):
        return ("%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d"
                % (self.COOKIE, sid, 8 * 3600))

    def _json_con_cookie(self, dato, sid):
        cuerpo = json.dumps(dato).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", self._cookie(sid))
        self.end_headers()
        try:
            self.wfile.write(cuerpo)
        except OSError:                    # el celular se fue: no es un error nuestro
            pass

    def _dar_cookie(self, sid, destino="/mando"):
        """Canjea la clave de la URL por la cookie y redirige a la dirección limpia."""
        # si no, la clave queda en el historial y a la vista del curso.
        # HttpOnly: el js no la lee. SameSite=Lax: otra página no manda órdenes
        self.send_response(302)
        self.send_header("Location", destino)
        self.send_header("Set-Cookie", self._cookie(sid))
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _borrar_cookie(self):
        self.send_response(302)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", "%s=; Path=/; Max-Age=0" % self.COOKIE)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _es_admin(self):
        # acceso None (en la compu propia): todos son admin
        if self.acceso is None:
            return True
        return self.acceso.es_admin(self._sid())

    def _prohibido(self, motivo, codigo=403):
        # 409 = el mando lo tiene otro; la página ofrece pedirlo
        self._responder(json.dumps({"ok": False, "motivo": motivo}),
                        "application/json; charset=utf-8", codigo)

    def _pagina(self, nombre):
        try:
            with open(os.path.join(self.estaticos, nombre), "rb") as f:
                self._responder(f.read(), "text/html; charset=utf-8")
        except OSError:
            self._responder("No se encontró web/" + nombre,
                            "text/plain; charset=utf-8", 500)

    # nombres simples, para que no se pueda salir de la carpeta
    _NOMBRE_CARATULA = re.compile(r"^/caratulas/([a-z0-9_]{1,40})\.svg$")

    def _caratula(self, ruta):
        m = self._NOMBRE_CARATULA.match(ruta)
        if not m:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)
            return
        try:
            with open(os.path.join(self.estaticos, "caratulas", m.group(1) + ".svg"),
                      "rb") as f:
                # no-cache: después de actualizar nadie se queda con la carátula vieja
                self._con_etag(f, "image/svg+xml; charset=utf-8")
        except OSError:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)

    # three.js y el modelo 3D desde web/3d/, porque en la wifi no hay internet
    _NOMBRE_3D = re.compile(r"^/3d/([a-z0-9_.]{1,40})\.js$")

    def _archivo_3d(self, ruta):
        m = self._NOMBRE_3D.match(ruta)
        if not m or ".." in m.group(1):
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)
            return
        try:
            with open(os.path.join(self.estaticos, "3d", m.group(1) + ".js"), "rb") as f:
                # three.js pesa 600 kB y no cambia: una hora de caché
                self._responder(f.read(), "text/javascript; charset=utf-8",
                                cache="max-age=3600")
        except OSError:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)

    # letras y logo van con el programa: sin internet no hay Google Fonts
    _NOMBRE_ESTATICO = re.compile(r"^/(fuentes/[a-z0-9-]{1,40}\.woff2|logo\.png|estilo\.css)$")
    _TIPO = {".woff2": "font/woff2", ".png": "image/png", ".css": "text/css; charset=utf-8"}

    def _estatico(self, ruta):
        m = self._NOMBRE_ESTATICO.match(ruta)
        if not m:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)
            return
        nombre = m.group(1)
        try:
            with open(os.path.join(self.estaticos, *nombre.split("/")), "rb") as f:
                ext = os.path.splitext(nombre)[1]
                # el estilo cambia con cada versión: ETag para que pregunte siempre
                if ext == ".css":
                    self._con_etag(f, self._TIPO[ext])
                else:
                    self._responder(f.read(), self._TIPO[ext], cache="max-age=86400")
        except OSError:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)

    def log_message(self, formato, *args):
        # cinco pedidos por segundo por celular: la consola sería ilegible
        pass

    def do_GET(self):
        u = urlparse(self.path)
        ruta = u.path
        consulta = parse_qs(u.query)

        if self._desconectado() or self._portal(ruta):
            return

        # para mirar: abierto para cualquiera
        if ruta in ("/", "/panel", "/tablero"):
            if self._red_del_tablero()[1]:
                self._liberar()
            self._pagina("tablero.html")

        elif ruta in ("/bienvenida", "/entrar"):
            # las direcciones viejas: ahora la bienvenida es el tablero mismo
            if self._red_del_tablero()[1]:
                self._liberar()
            self._ir_a("/?bienvenida=1" if ruta == "/bienvenida" else "/")

        elif ruta == "/api/red":
            self._json(celulares_conectados())

        elif ruta == "/api/red/celulares":
            if not self._es_admin():
                self._prohibido("Hace falta entrar con la clave del profesor.")
                return
            lista = celulares_detalle()
            yo = mac_de_ip(self.client_address[0])
            bloq = leer_bloqueados()
            for c in lista or []:
                c["yo"] = c["mac"] == yo
            self._json({"disponible": lista is not None,
                        "conectados": [c for c in (lista or []) if c["mac"] not in bloq],
                        "bloqueados": [{"mac": m, "nombre": n} for m, n in sorted(bloq.items())],
                        "limite": celulares_conectados()["limite"]})

        # para mandar: hace falta la clave del profesor
        elif ruta in ("/mando", "/mando/"):
            # la clave interna en la URL vale solo desde la misma Pi (programas de prueba)
            clave = (consulta.get("k") or [""])[0] if self._es_local() else ""
            if clave and self.acceso:
                sid = self.acceso.entrar(clave)
                if sid:
                    self._dar_cookie(sid, "/mando")
                    return
                self._pagina("sin_permiso.html")
                return
            if self._es_admin():
                self._pagina("mando.html")
            else:
                self._pagina("sin_permiso.html")

        elif ruta == "/salir":
            if self.acceso:
                self.acceso.salir(self._sid())
                # el último que sale deja el tablero en reposo
                if not self.acceso.hay_sesiones():
                    self.nucleo.ordenar("detener")
            self._borrar_cookie()

        elif ruta == "/api/sesion":
            self._json(self.acceso.estado(self._sid()) if self.acceso
                       else {"admin": True, "mando": True, "mando_libre": True,
                             "hay_titular": False, "pedido_ajeno": False,
                             "pedido_mio": False, "admins": 0})

        elif ruta in ("/qr", "/qr/"):
            url = self._url_publica()
            self._responder(
                _PAGINA_QR % {"svg": qr.svg(url, 380), "url": url,
                              "donde": self.donde},
                "text/html; charset=utf-8")

        elif ruta == "/qr.svg":
            self._responder(qr.svg(self._url_publica(), 380),
                            "image/svg+xml; charset=utf-8")

        elif ruta == "/qr_wifi.svg":
            # la red de los visitantes, la misma del cartel; no la de la escuela
            ap = datos_punto_de_acceso()
            wifi = texto_qr_wifi(ap)
            self._responder(qr.svg(wifi, 300), "image/svg+xml; charset=utf-8")

        elif ruta.startswith("/caratulas/"):
            self._caratula(ruta)

        elif ruta.startswith("/3d/"):
            self._archivo_3d(ruta)

        elif ruta.startswith("/fuentes/") or ruta in ("/logo.png", "/estilo.css"):
            self._estatico(ruta)

        elif ruta in ("/cartel", "/cartel/"):
            ap = datos_punto_de_acceso()
            # la del AP: el que lo lee se acaba de conectar con el primer código
            url = url_de(ap["ip"], self.puerto_publico)
            wifi = texto_qr_wifi(ap)
            self._responder(
                _PAGINA_CARTEL % {"qr_wifi": qr.svg(wifi, 300),
                                  "qr_url": qr.svg(url, 300),
                                  "red": ap["red"], "clave": ap["clave"],
                                  "url": sin_http(url)},
                "text/html; charset=utf-8")

        elif ruta == "/api/catalogo":
            ap = datos_punto_de_acceso()
            self._json(dict(self.nucleo.catalogo,
                            url_publica=self._url_publica(),
                            admin=self._es_admin(),
                            caratulas=indice_caratulas(self.estaticos),
                            wifi={"red": ap["red"], "clave": ap["clave"],
                                  "url": url_de(ap["ip"], self.puerto_publico)}))

        elif ruta == "/api/estado":
            self._json(self.nucleo.foto)

        else:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)

    def do_POST(self):
        u = urlparse(self.path)
        ruta = u.path
        consulta = parse_qs(u.query)

        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = 0
        cuerpo = self.rfile.read(largo) if largo > 0 else b""
        datos = {}
        if 0 < largo <= 2048:
            try:
                datos = json.loads(cuerpo.decode("utf-8")) or {}
            except (ValueError, UnicodeDecodeError):
                datos = {}
        if not isinstance(datos, dict):
            datos = {}
        if self._desconectado():
            return

        sid = self._sid()

        # entrar con la clave del profesor
        if ruta == "/api/entrar":
            if self.acceso is None:
                self._json({"ok": True, "cambiar": False})
                return
            nuevo, motivo = self.acceso.entrar_profesor(
                str(datos.get("clave") or ""), origen=self.client_address[0])
            if not nuevo:
                self._prohibido(motivo)
                return
            self._json_con_cookie(
                {"ok": True, "cambiar": self.acceso.debe_cambiar(nuevo)}, nuevo)
            return

        # cambiar la clave del profesor
        if ruta == "/api/clave":
            if self.acceso is None:
                self._prohibido("Este tablero corre sin clave.")
                return
            if not self.acceso.es_admin(sid):
                self._prohibido("La sesión venció. Volvé a entrar.")
                return
            ok, motivo = self.acceso.cambiar_clave_profesor(
                sid, str(datos.get("actual") or ""), str(datos.get("nueva") or ""))
            if ok:
                self._json({"ok": True, "motivo": motivo})
            else:
                self._prohibido(motivo, 400)
            return

        # el mando: pedirlo, cederlo, tomarlo
        if ruta.startswith("/api/mando/"):
            if not self._es_admin():
                self._prohibido("Hace falta entrar con la clave del profesor.")
                return
            que = ruta.rsplit("/", 1)[-1]
            if self.acceso is None:
                # --sin-clave: el mando es de todos
                self._json({"ok": True, "motivo": ""})
                return
            if que == "tomar":
                ok, motivo = self.acceso.tomar_mando(sid)
                self._json({"ok": ok, "motivo": motivo})
            elif que == "pedir":
                self._json({"ok": self.acceso.pedir_mando(sid)})
            elif que == "ceder":
                self._json({"ok": self.acceso.ceder_mando(sid)})
            elif que == "rechazar":
                self._json({"ok": self.acceso.rechazar_pedido(sid)})
            elif que == "nombre":
                self.acceso.nombrar(sid, (consulta.get("valor") or [""])[0])
                self._json({"ok": True})
            else:
                self._responder("no encontrado",
                                "text/plain; charset=utf-8", 404)
            return

        # de acá para abajo, órdenes al tablero
        if self.acceso is not None:
            if not self.acceso.es_admin(sid):
                self._prohibido("Esta página es para mirar. Para operar el "
                                "tablero hace falta la clave del profesor.")
                return
            if self.acceso.debe_cambiar(sid):
                self._prohibido("Primero cambiá la clave inicial.")
                return
            if not self.acceso.puede_mandar(sid):
                self._prohibido("El mando lo tiene otro dispositivo.", 409)
                return

        if ruta in ("/api/red/desconectar", "/api/red/permitir", "/api/red/desconectar_otros"):
            self._red_orden(ruta, consulta)
            return

        if ruta.startswith("/api/modo/"):
            modo = ruta.rsplit("/", 1)[-1]
            ident = (consulta.get("id") or [""])[0]
            if modo == "1":
                self.nucleo.ordenar("modo_normal", ident or None)
            elif modo == "2":
                self.nucleo.ordenar("modo_escenario", ident)
            elif modo == "3":
                self.nucleo.ordenar("modo_falla", ident)
            else:
                self.nucleo.ordenar("detener")
            self._json({"ok": True})

        elif ruta.startswith("/api/accion/"):
            accion = ruta.rsplit("/", 1)[-1]
            if accion not in ACCIONES:
                self._responder("acción desconocida", "text/plain; charset=utf-8", 400)
                return
            crudo = (consulta.get("valor") or [""])[0]
            if crudo in ("true", "false"):
                valor = (crudo == "true")
            elif crudo == "":
                valor = None
            else:
                try:
                    valor = float(crudo)
                except ValueError:
                    valor = crudo
            self.nucleo.ordenar(accion, valor)
            self._json({"ok": True})

        else:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)


_INDICE = {}


def indice_caratulas(estaticos):
    """{instrumento: {archivo, L, R}} de web/caratulas/indice.json, o {}."""
    # sin la carpeta (instalación vieja) la página dibuja sus esferas de antes
    if estaticos not in _INDICE:
        try:
            with open(os.path.join(estaticos, "caratulas", "indice.json"),
                      encoding="utf-8") as f:
                _INDICE[estaticos] = json.load(f)
        except (OSError, ValueError, TypeError):
            _INDICE[estaticos] = {}
    return _INDICE[estaticos]


def crear(nucleo, puerto, estaticos, donde="esta computadora", acceso=None):
    """Deja el servidor listo, sin bloquear.

    acceso=None: cualquiera manda. Solo para la compu propia; en la Pi siempre va un Acceso.
    """
    Manejador.nucleo = nucleo
    Manejador.estaticos = estaticos
    Manejador.puerto = puerto
    Manejador.puerto_publico = puerto
    Manejador.donde = donde
    Manejador.acceso = acceso
    s = ThreadingHTTPServer(("0.0.0.0", puerto), Manejador)
    s.daemon_threads = True
    return s


def abrir_puerto_extra(puerto=80):
    """También el 80, para que la dirección sea corta y la página se abra sola.

    Necesita CAP_NET_BIND_SERVICE (lo da instalar.sh). Si no puede, devuelve None.
    """
    try:
        s = ThreadingHTTPServer(("0.0.0.0", puerto), Manejador)
    except OSError:
        return None
    s.daemon_threads = True
    Manejador.puerto_publico = puerto
    threading.Thread(target=s.serve_forever, name="web-%d" % puerto, daemon=True).start()
    return s


def cartel_de_acceso(puerto, ancho=68):
    url = direccion(puerto)
    lineas = ["-" * ancho,
              " ENTRAR DESDE CUALQUIER CELULAR, TABLET O COMPUTADORA",
              "",
              "     %s" % url,
              "",
              " Escaneando este código con la cámara del teléfono:",
              ""]
    lineas.append(qr.texto_consola(url, borde=1))
    lineas += ["",
               " El mismo código, grande, para proyectar:  %sqr" % url,
               " Cartel A4 para imprimir y pegar:          %scartel" % url,
               "-" * ancho]
    return "\n".join(lineas)
