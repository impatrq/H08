# -*- coding: utf-8 -*-
"""Quién puede mirar, quién es admin y quién tiene el mando.

Mirar es libre. Admin: clave del profesor o QR de admin. El mando lo tiene un
solo dispositivo a la vez, porque dos metiendo fallas juntos arruinan la demo.
Ojo: es HTTP sin cifrar, frena al alumno curioso, no a alguien decidido en el wifi.
"""
import hashlib
import json
import os
import secrets
import threading
import time

# 8 h sin uso: una jornada de taller
VIDA_SESION = 8 * 3600

# si el titular desaparece (cerró el navegador, sin batería), pasados estos
# segundos otro admin puede tomar el mando
MANDO_ABANDONADO = 45

# tiempo para contestar un pedido de mando; si no contesta, se lo queda el otro
ESPERA_CESION = 30

LARGO_CLAVE = 22   # la del QR; se cambia con --renovar-clave

# Es pública (está en el código): con ella solo se entra a cambiarla.
# Si el profe se olvida la suya: --restablecer-clave
CLAVE_INICIAL = "profesor-h08"
LARGO_MIN_PROFESOR = 6
LARGO_MAX_PROFESOR = 40

# errores seguidos por dirección antes de hacer esperar BLOQUEO segundos
INTENTOS = 5
BLOQUEO = 60

_VUELTAS_HASH = 100000


def _ahora():
    return time.monotonic()


class Acceso:
    """Sesiones y mando en memoria (reiniciar los libera); las claves, en archivo.

    Lleva candado porque el servidor atiende cada pedido en su hilo.
    """

    def __init__(self, archivo_clave, vida_sesion=VIDA_SESION):
        self.archivo = archivo_clave
        self.vida = vida_sesion
        self._candado = threading.Lock()
        self.sesiones = {}          # sid -> {"desde":, "visto":, "nombre":}
        self.titular = None         # sid del que tiene el mando
        self.visto_titular = 0.0
        self.pedido = None          # {"sid":, "nombre":, "cuando":}
        self.fallos = {}            # origen -> [errores seguidos, bloqueado hasta]
        self.clave = ""
        self.profesor = {}          # {"sal":, "hash":, "inicial":}
        self._leer_o_crear_claves()

    def _leer_o_crear_claves(self):
        datos = {}
        try:
            with open(self.archivo, encoding="utf-8") as f:
                datos = json.load(f) or {}
        except (OSError, ValueError):
            datos = {}
        c = datos.get("clave") or ""
        p = datos.get("profesor") or {}
        cambio = False
        if len(c) < 12:
            c = secrets.token_urlsafe(16)[:LARGO_CLAVE]
            cambio = True
        if not (p.get("sal") and p.get("hash")):
            # instalación vieja con solo la clave del QR: el profe arranca con
            # la inicial y el QR impreso sigue andando
            p = self._hash_nuevo(CLAVE_INICIAL, inicial=True)
            cambio = True
        self.clave, self.profesor = c, p
        if cambio:
            self._guardar()
        self._marca = self._fecha_archivo()

    def _fecha_archivo(self):
        try:
            return os.stat(self.archivo).st_mtime_ns
        except OSError:
            return None

    def _releer_si_cambio(self):
        # por si corrieron --restablecer-clave o --renovar-clave con el tablero andando
        if self._fecha_archivo() != self._marca:
            with self._candado:
                self._leer_o_crear_claves()

    @staticmethod
    def _hash(texto, sal_hex):
        return hashlib.pbkdf2_hmac("sha256", texto.encode("utf-8"),
                                   bytes.fromhex(sal_hex), _VUELTAS_HASH).hex()

    def _hash_nuevo(self, texto, inicial):
        sal = secrets.token_hex(16)
        return {"sal": sal, "hash": self._hash(texto, sal), "inicial": inicial}

    def _es_la_del_profesor(self, texto):
        p = self.profesor
        return secrets.compare_digest(self._hash(texto, p["sal"]), p["hash"])

    def _escribir_clave(self, clave):
        self.clave = clave
        self._guardar()
        return clave

    def _guardar(self):
        d = os.path.dirname(os.path.abspath(self.archivo))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump({"clave": self.clave, "profesor": self.profesor}, f)
        self._marca = self._fecha_archivo()
        try:
            # solo el dueño; no frena a nadie con sudo
            os.chmod(self.archivo, 0o600)
        except OSError:
            pass

    def renovar_clave(self):
        """Clave del QR nueva: el QR anterior deja de servir y se cierran las sesiones."""
        with self._candado:
            self.clave = self._escribir_clave(
                secrets.token_urlsafe(16)[:LARGO_CLAVE])
            self.sesiones.clear()
            self.titular = None
            self.pedido = None
            return self.clave

    def restablecer_clave_profesor(self):
        with self._candado:
            self.profesor = self._hash_nuevo(CLAVE_INICIAL, inicial=True)
            self._guardar()
            self.sesiones.clear()
            self.titular = None
            self.pedido = None

    @property
    def clave_inicial(self):
        return bool(self.profesor.get("inicial"))

    def cambiar_clave_profesor(self, sid, actual, nueva):
        """Devuelve (ok, motivo). Cierra las demás sesiones."""
        nueva = (nueva or "").strip()
        with self._candado:
            self._limpiar()
            d = self.sesiones.get(sid)
            if d is None:
                return False, "La sesión venció. Volvé a entrar."
            # el que entró con la inicial ya la escribió para entrar
            if not d.get("cambiar") and not self._es_la_del_profesor(actual or ""):
                return False, "La clave actual no es correcta."
            if len(nueva) < LARGO_MIN_PROFESOR:
                return False, "La clave nueva tiene que tener al menos %d caracteres." % LARGO_MIN_PROFESOR
            if len(nueva) > LARGO_MAX_PROFESOR:
                return False, "La clave nueva es demasiado larga."
            if nueva == CLAVE_INICIAL:
                return False, "La clave nueva no puede ser la inicial."
            self.profesor = self._hash_nuevo(nueva, inicial=False)
            self._guardar()
            for s in [s for s in self.sesiones if s != sid]:
                del self.sesiones[s]
            d["cambiar"] = False
            if self.titular != sid:
                self.titular = None
            self.pedido = None
            return True, "Listo. La clave quedó cambiada."

    def _limpiar(self):
        # con el candado tomado
        t = _ahora()
        muertas = [s for s, d in self.sesiones.items()
                   if t - d["visto"] > self.vida]
        for s in muertas:
            del self.sesiones[s]
        if self.titular and self.titular not in self.sesiones:
            self.titular = None
        if self.pedido and self.pedido["sid"] not in self.sesiones:
            self.pedido = None

    def _nueva_sesion(self, nombre, cambiar=False):
        sid = secrets.token_urlsafe(18)
        with self._candado:
            self._limpiar()
            self.sesiones[sid] = {"desde": _ahora(), "visto": _ahora(),
                                  "nombre": (nombre or "")[:24],
                                  "cambiar": cambiar}
        return sid

    def entrar(self, clave, nombre=""):
        """Canjea la clave del QR por un sid, o None."""
        if not clave:
            return None
        self._releer_si_cambio()
        # tiempo constante, para no dar pistas por la demora
        if not secrets.compare_digest(str(clave), self.clave):
            return None
        return self._nueva_sesion(nombre)

    def entrar_profesor(self, clave, origen="", nombre=""):
        """Clave escrita a mano (también vale la del QR). Devuelve (sid o None, motivo).

        Con la clave inicial la sesión solo sirve para cambiarla.
        """
        self._releer_si_cambio()
        t = _ahora()
        with self._candado:
            f = self.fallos.get(origen)
            if f and f[1] > t:
                return None, "Demasiados intentos. Esperá un minuto y probá de nuevo."
        clave = (clave or "").strip()
        bien = bool(clave) and len(clave) <= 64 and (
            self._es_la_del_profesor(clave)
            or secrets.compare_digest(clave, self.clave))
        with self._candado:
            if not bien:
                f = self.fallos.setdefault(origen, [0, 0.0])
                f[0] += 1
                if f[0] >= INTENTOS:
                    f[0], f[1] = 0, t + BLOQUEO
                    return None, "Demasiados intentos. Esperá un minuto y probá de nuevo."
                return None, "La clave no es correcta."
            self.fallos.pop(origen, None)
        cambiar = self.clave_inicial and clave == CLAVE_INICIAL
        return self._nueva_sesion(nombre, cambiar), ""

    def debe_cambiar(self, sid):
        with self._candado:
            d = self.sesiones.get(sid)
            return bool(d and d.get("cambiar"))

    def es_admin(self, sid):
        if not sid:
            return False
        with self._candado:
            self._limpiar()
            d = self.sesiones.get(sid)
            if d is None:
                return False
            d["visto"] = _ahora()
            return True

    def hay_sesiones(self):
        with self._candado:
            self._limpiar()
            return bool(self.sesiones)

    def salir(self, sid):
        with self._candado:
            if self.titular == sid:
                self.titular = None
            if self.pedido and self.pedido["sid"] == sid:
                self.pedido = None
            self.sesiones.pop(sid, None)

    def nombrar(self, sid, nombre):
        with self._candado:
            if sid in self.sesiones:
                self.sesiones[sid]["nombre"] = (nombre or "")[:24]

    def _mando_libre(self):
        # con el candado tomado
        if self.titular is None:
            return True
        if self.titular not in self.sesiones:
            return True
        return (_ahora() - self.visto_titular) > MANDO_ABANDONADO

    def tomar_mando(self, sid):
        with self._candado:
            self._limpiar()
            if sid not in self.sesiones:
                return False, "sesión vencida"
            if self.sesiones[sid].get("cambiar"):
                return False, "primero hay que cambiar la clave inicial"
            if self.titular == sid:
                self.visto_titular = _ahora()
                return True, "ya lo tenías"
            if self._mando_libre():
                self.titular = sid
                self.visto_titular = _ahora()
                self.pedido = None
                return True, "tomado"
            # no está libre: sólo se lo queda el que lo pidió y esperó
            p = self.pedido
            if (p and p["sid"] == sid
                    and _ahora() - p["cuando"] >= ESPERA_CESION):
                self.titular = sid
                self.visto_titular = _ahora()
                self.pedido = None
                return True, "tomado por falta de respuesta"
            return False, "lo tiene otro dispositivo"

    def pedir_mando(self, sid):
        with self._candado:
            self._limpiar()
            if sid not in self.sesiones:
                return False
            if self.titular == sid or self._mando_libre():
                return False
            self.pedido = {"sid": sid, "cuando": _ahora(),
                           "nombre": self.sesiones[sid].get("nombre", "")}
            return True

    def ceder_mando(self, sid):
        # si alguien lo había pedido, pasa a ese
        with self._candado:
            if self.titular != sid:
                return False
            p = self.pedido
            if p and p["sid"] in self.sesiones:
                self.titular = p["sid"]
                self.visto_titular = _ahora()
            else:
                self.titular = None
            self.pedido = None
            return True

    def rechazar_pedido(self, sid):
        with self._candado:
            if self.titular != sid:
                return False
            self.pedido = None
            self.visto_titular = _ahora()
            return True

    def puede_mandar(self, sid):
        with self._candado:
            self._limpiar()
            if sid not in self.sesiones:
                return False
            if self.sesiones[sid].get("cambiar"):
                return False
            self.sesiones[sid]["visto"] = _ahora()
            if self.titular is None and not self.sesiones:
                return False
            if self.titular == sid:
                self.visto_titular = _ahora()
                return True
            # nadie manda todavía: el primero que ordena algo toma el mando
            if self._mando_libre():
                self.titular = sid
                self.visto_titular = _ahora()
                self.pedido = None
                return True
            return False

    def estado(self, sid):
        with self._candado:
            self._limpiar()
            soy_admin = sid in self.sesiones
            if soy_admin:
                self.sesiones[sid]["visto"] = _ahora()
                if self.titular == sid:
                    self.visto_titular = _ahora()
            libre = self._mando_libre()
            p = self.pedido
            resta = 0
            if p:
                resta = max(0, int(ESPERA_CESION - (_ahora() - p["cuando"])))
            return {
                "admin": soy_admin,
                "mando": bool(soy_admin and self.titular == sid),
                "mando_libre": libre,
                "hay_titular": bool(self.titular and not libre),
                "titular_nombre": (self.sesiones.get(self.titular, {})
                                   .get("nombre", "") if self.titular else ""),
                "pedido_mio": bool(p and p["sid"] == sid),
                "pedido_ajeno": bool(p and p["sid"] != sid
                                     and self.titular == sid),
                "pedido_nombre": (p or {}).get("nombre", ""),
                "pedido_resta": resta,
                "admins": len(self.sesiones),
                "cambiar_clave": bool(soy_admin
                                      and self.sesiones[sid].get("cambiar")),
            }
