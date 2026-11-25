#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba nucleo/acceso.py sin levantar el servidor: claves, sesiones y turno del mando.

Son las reglas que deciden quién le puede meter una falla al tablero delante
del curso, así que preferimos tenerlas probadas y no "se ve que anda".
"""
import os
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
for _c in (os.path.join(AQUI, "..", "nucleo"), os.path.join(AQUI, "nucleo")):
    if os.path.isdir(_c):
        sys.path.insert(0, os.path.abspath(_c))
        break

import acceso                                                # noqa: E402
from acceso import Acceso                                    # noqa: E402

fallos = []


def igual(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print("  %s %-52s %s" % ("ok  " if ok else "MAL ", nombre,
                             "" if ok else "-> %r (esperaba %r)"
                             % (obtenido, esperado)))
    if not ok:
        fallos.append(nombre)


def cierto(nombre, valor):
    igual(nombre, bool(valor), True)


def falso(nombre, valor):
    igual(nombre, bool(valor), False)


def nuevo():
    d = tempfile.mkdtemp()
    return Acceso(os.path.join(d, "secreto_admin.json"))


def clave_y_sesiones():
    print("\n  LA CLAVE Y LAS SESIONES")
    a = nuevo()
    igual("la clave se genera sola", len(a.clave) >= 12, True)
    cierto("el archivo quedo escrito", os.path.exists(a.archivo))
    if os.name == "nt":
        # Windows no tiene permisos de dueño/grupo/otros, esto se ve en la Pi
        print("  --   el archivo es solo del duenio: no aplica en Windows")
    else:
        modo = os.stat(a.archivo).st_mode & 0o777
        igual("el archivo es solo del duenio", oct(modo), oct(0o600))

    igual("sin clave no se entra", a.entrar(""), None)
    igual("con clave equivocada no se entra", a.entrar("cualquiera"), None)
    sid = a.entrar(a.clave)
    cierto("con la clave correcta se entra", sid)
    cierto("y queda como admin", a.es_admin(sid))
    falso("un sid inventado no es admin", a.es_admin("inventado"))
    falso("sin sid no es admin", a.es_admin(None))

    # la clave que se relee del archivo es la misma
    b = Acceso(a.archivo)
    igual("la clave sobrevive al reinicio", b.clave, a.clave)

    vieja = a.clave
    nueva = a.renovar_clave()
    cierto("renovar da una clave distinta", nueva != vieja)
    falso("la sesion vieja ya no vale", a.es_admin(sid))
    igual("la clave vieja ya no entra", a.entrar(vieja), None)
    cierto("la nueva si", a.entrar(nueva))


def el_visitante_no_manda():
    print("\n  EL VISITANTE")
    a = nuevo()
    falso("un visitante no es admin", a.es_admin(None))
    falso("un visitante no puede mandar", a.puede_mandar(None))
    falso("con un sid inventado tampoco", a.puede_mandar("robado"))
    e = a.estado(None)
    falso("y su estado dice que no es admin", e["admin"])
    falso("ni tiene el mando", e["mando"])


def un_solo_mando():
    print("\n  UN SOLO MANDO")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    q = a.entrar(a.clave, "ayudante")
    cierto("los dos son admin", a.es_admin(p) and a.es_admin(q))

    cierto("el primero que ordena toma el mando", a.puede_mandar(p))
    falso("el segundo NO puede mandar", a.puede_mandar(q))
    cierto("el primero sigue mandando", a.puede_mandar(p))

    e = a.estado(q)
    cierto("el segundo ve que es admin", e["admin"])
    falso("pero que no tiene el mando", e["mando"])
    cierto("y que lo tiene alguien", e["hay_titular"])
    igual("y con que nombre", e["titular_nombre"], "profesor")

    ok, _m = a.tomar_mando(q)
    falso("no se lo puede arrebatar sin mas", ok)

    cierto("puede pedirlo", a.pedir_mando(q))
    e = a.estado(p)
    cierto("el titular ve el pedido", e["pedido_ajeno"])
    igual("y de quien es", e["pedido_nombre"], "ayudante")

    cierto("el titular puede rechazar", a.rechazar_pedido(p))
    e = a.estado(p)
    falso("y el pedido desaparece", e["pedido_ajeno"])
    falso("el que pidio sigue sin mandar", a.puede_mandar(q))

    cierto("pide de nuevo", a.pedir_mando(q))
    cierto("el titular cede", a.ceder_mando(p))
    cierto("y el mando pasa al que pidio", a.estado(q)["mando"])
    falso("el que cedio ya no manda", a.puede_mandar(p))


def el_que_se_fue():
    print("\n  EL QUE SE FUE CON LA PAGINA ABIERTA")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    q = a.entrar(a.clave, "ayudante")
    cierto("el profesor toma el mando", a.puede_mandar(p))

    # atrasamos el reloj en vez de esperar 45 s de verdad
    a.visto_titular -= acceso.MANDO_ABANDONADO + 1
    cierto("pasado el abandono, el mando se considera libre",
           a.estado(q)["mando_libre"])
    ok, _m = a.tomar_mando(q)
    cierto("y el otro lo puede tomar", ok)
    cierto("ahora manda el ayudante", a.puede_mandar(q))
    falso("y el que se fue ya no", a.puede_mandar(p))


def el_que_no_contesta():
    print("\n  EL QUE NO CONTESTA EL PEDIDO")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    q = a.entrar(a.clave, "ayudante")
    a.puede_mandar(p)
    a.pedir_mando(q)
    ok, _m = a.tomar_mando(q)
    falso("recien pedido, todavia no se lo puede quedar", ok)

    a.pedido["cuando"] -= acceso.ESPERA_CESION + 1
    e = a.estado(q)
    igual("la cuenta regresiva llego a cero", e["pedido_resta"], 0)
    ok, motivo = a.tomar_mando(q)
    cierto("pasada la espera, se lo queda", ok)
    igual("y dice por que", motivo, "tomado por falta de respuesta")


def la_sesion_vence():
    print("\n  LA SESION QUE VENCE")
    d = tempfile.mkdtemp()
    a = Acceso(os.path.join(d, "s.json"), vida_sesion=0.2)
    sid = a.entrar(a.clave)
    cierto("recien entrado es admin", a.es_admin(sid))
    time.sleep(0.35)
    falso("pasada la vida de la sesion, ya no", a.es_admin(sid))
    falso("y no puede mandar", a.puede_mandar(sid))


def hay_sesiones():
    print("\n  QUEDAN SESIONES")
    a = nuevo()
    falso("sin nadie, no hay sesiones", a.hay_sesiones())
    s1 = a.entrar(a.clave)
    s2 = a.entrar(a.clave)
    a.salir(s1)
    cierto("si sale uno, queda el otro", a.hay_sesiones())
    a.salir(s2)
    falso("si salen todos, no queda ninguna", a.hay_sesiones())


def salir_libera():
    print("\n  SALIR")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    a.puede_mandar(p)
    a.salir(p)
    falso("el que salio no es admin", a.es_admin(p))
    q = a.entrar(a.clave, "otro")
    cierto("y el mando quedo libre", a.estado(q)["mando_libre"])


def la_clave_del_profesor():
    print("\n  LA CLAVE DEL PROFESOR")
    a = nuevo()
    cierto("arranca con la inicial", a.clave_inicial)
    with open(a.archivo, encoding="utf-8") as f:
        texto = f.read()
    falso("el archivo no guarda la clave escrita", acceso.CLAVE_INICIAL in texto)

    sid, _m = a.entrar_profesor("otra cosa", origen="1")
    igual("con una clave equivocada no se entra", sid, None)
    sid, _m = a.entrar_profesor(acceso.CLAVE_INICIAL, origen="1")
    cierto("con la inicial se entra", sid)
    cierto("pero tiene que cambiarla", a.debe_cambiar(sid))
    falso("y mientras tanto no puede mandar", a.puede_mandar(sid))
    ok, _m = a.tomar_mando(sid)
    falso("ni tomar el mando", ok)
    cierto("su estado lo avisa", a.estado(sid)["cambiar_clave"])

    ok, _m = a.cambiar_clave_profesor(sid, "", "corta")
    falso("una clave de menos de 6 no sirve", ok)
    ok, _m = a.cambiar_clave_profesor(sid, "", acceso.CLAVE_INICIAL)
    falso("la inicial no sirve como nueva", ok)
    otro = a.entrar(a.clave, "ayudante")
    ok, _m = a.cambiar_clave_profesor(sid, "", "aula7avionica")
    cierto("una clave propia si", ok)
    falso("ya no es la inicial", a.clave_inicial)
    falso("ya no tiene que cambiarla", a.debe_cambiar(sid))
    cierto("y puede mandar", a.puede_mandar(sid))
    falso("las otras sesiones se cerraron", a.es_admin(otro))

    sid2, _m = a.entrar_profesor(acceso.CLAVE_INICIAL, origen="2")
    igual("la inicial ya no entra", sid2, None)
    sid2, _m = a.entrar_profesor("aula7avionica", origen="2")
    cierto("la nueva si", sid2)
    falso("y entra sin tener que cambiarla", a.debe_cambiar(sid2))
    sid3, _m = a.entrar_profesor(a.clave, origen="2")
    cierto("la clave del QR tambien entra escrita", sid3)

    ok, _m = a.cambiar_clave_profesor(sid2, "equivocada", "otraclave99")
    falso("para cambiarla hay que saber la actual", ok)
    ok, _m = a.cambiar_clave_profesor(sid2, "aula7avionica", "otraclave99")
    cierto("sabiendo la actual se cambia", ok)

    b = Acceso(a.archivo)
    sid4, _m = b.entrar_profesor("otraclave99", origen="3")
    cierto("la clave sobrevive al reinicio", sid4)

    a.restablecer_clave_profesor()
    cierto("restablecer vuelve a la inicial", a.clave_inicial)
    sid5, _m = a.entrar_profesor(acceso.CLAVE_INICIAL, origen="4")
    cierto("y se entra con la inicial", sid5 and a.debe_cambiar(sid5))

    # otro proceso (la terminal) la restablece con el tablero andando
    c = Acceso(a.archivo)
    s6, _m = c.entrar_profesor(acceso.CLAVE_INICIAL, origen="5")
    ok, _m = c.cambiar_clave_profesor(s6, "", "definitiva1")
    Acceso(a.archivo).restablecer_clave_profesor()
    s7, _m = c.entrar_profesor(acceso.CLAVE_INICIAL, origen="5")
    cierto("el tablero andando toma la clave restablecida", s7)


def demasiados_intentos():
    print("\n  DEMASIADOS INTENTOS")
    a = nuevo()
    for _ in range(acceso.INTENTOS):
        sid, motivo = a.entrar_profesor("mal", origen="9.9.9.9")
    cierto("despues de %d errores avisa que espere" % acceso.INTENTOS,
           "Esperá" in motivo)
    sid, motivo = a.entrar_profesor(acceso.CLAVE_INICIAL, origen="9.9.9.9")
    igual("ni con la clave buena entra mientras espera", sid, None)
    sid, motivo = a.entrar_profesor(acceso.CLAVE_INICIAL, origen="8.8.8.8")
    cierto("otro celular si puede", sid)
    a.fallos["9.9.9.9"][1] = 0
    sid, motivo = a.entrar_profesor(acceso.CLAVE_INICIAL, origen="9.9.9.9")
    cierto("pasado el minuto vuelve a poder", sid)


if __name__ == "__main__":
    print("=" * 74)
    print(" ACCESO: quien mira, quien puede mandar, quien manda ahora")
    print("=" * 74)
    clave_y_sesiones()
    el_visitante_no_manda()
    un_solo_mando()
    el_que_se_fue()
    el_que_no_contesta()
    la_sesion_vence()
    salir_libera()
    hay_sesiones()
    la_clave_del_profesor()
    demasiados_intentos()
    print("")
    print("=" * 74)
    if fallos:
        print(" FALLARON %d:" % len(fallos))
        for f in fallos:
            print("   %s" % f)
    else:
        print(" Todo bien.")
    print("=" * 74)
    sys.exit(1 if fallos else 0)
