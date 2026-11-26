#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Calibra cada aguja sobre los números de su carátula, con el instrumento
armado y el servicio detenido. También trae lo del servo suelto (lo que era
calibrar_servo.py): --transportador, --probar, --explorar, --pulso.

El tablero une las marcas con rectas, así se corrige junto el servo, los
engranajes y cómo quedó pegado el sticker. Por el juego de los engranajes, a
cada marca se llega siempre desde abajo.
"""

import argparse
import json
import os
import sys
import tempfile
import time

import banco
from configuracion import SERVO, MOTOR, MOTORES, SERVO_CFG, invertido

PASO_CHICO = 5        # us por cada + o -; una cuenta del PCA9685 son 4,9 us
PASO_GRANDE = 25      # us por cada ++ o --
LLEGADA = 60          # us de más con los que se llega a una marca desde abajo
# el cabeceo no tiene engranajes y la corredera hace tope a 1 mm de las marcas
# de 20: se pasa poquito (20 us son unos 0,7 mm de disco)
LLEGADA_DE = {"ATT_PITCH": 20}
# Empiezan por el 0. El brazo calza en dientes de 18°, así que el disco puede
# quedar unos mm corrido; lo corregido en el 0 se suma a las otras marcas para
# no llegar a la de 20 contra el tope.
DESDE_EL_MEDIO = {"ATT_PITCH"}
NO_SE_CALIBRAN = {}
SECCION = "CALIBRACIÓN EN EL INSTRUMENTO"

# flechas sin Enter; se apagan con --sin-flechas o sin terminal de verdad
FLECHAS = [True]
FLECHA = {"C": "der", "D": "izq", "A": "arr", "B": "aba"}      # llegan como ESC [ C
MOVIDA = {"der": PASO_CHICO, "+": PASO_CHICO, "izq": -PASO_CHICO, "-": -PASO_CHICO,
          "arr": PASO_GRANDE, "aba": -PASO_GRANDE}
AYUDA_TECLAS = ("    → / ←  un poquito hacia los números más altos / bajos"
                "   ↑ / ↓  más\n"
                "    Enter = está justo en la marca   s = saltear esta marca\n"
                "    t = no llega: la aguja quedó en su tope (decís qué número marca)\n"
                "    p = pasar este instrumento   q = terminar todo")

AYUDA_DADA = [False]

# qué hacer después de cada instrumento
SEGUIR, PASADO, TERMINAR = "seguir", "pasado", "terminar"


def leer(archivo):
    try:
        with open(archivo, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar(archivo, datos):
    tmp = archivo + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=1, sort_keys=True)
    os.replace(tmp, archivo)


def clave_de(it):
    return "%s:%d" % tuple(it["canal"])


def calibrables():
    return [it for it in banco.lista_instrumentos()
            if it["actuador"] in (SERVO, MOTOR) and it["id"] not in NO_SE_CALIBRAN]


def listar(archivo):
    datos = leer(archivo)
    print("\n  %-15s %-8s %s" % ("INSTRUMENTO", "CANAL", "MARCAS MEDIDAS"))
    for it in banco.lista_instrumentos():
        if it["actuador"] not in (SERVO, MOTOR):
            continue
        if it["actuador"] == MOTOR:
            e = datos.get(clave_de(it))
            txt = "-" if not isinstance(e, dict) or "invertido" not in e else (
                "giro invertido" if e["invertido"] else "giro normal")
        elif it["id"] in NO_SE_CALIBRAN:
            txt = "no se calibra: " + NO_SE_CALIBRAN[it["id"]]
        else:
            e = datos.get(clave_de(it)) or {}
            m = e.get("marcas")
            txt = "%d marcas" % len(m) if m else "-"
            if isinstance(e.get("al_reves"), bool):
                txt += ", giro " + ("al revés" if e["al_reves"] else "normal")
            txt += texto_transportador(e)
        print("  %-15s %-8s %s" % (it["id"], clave_de(it), txt))
    print("")


class Aguja:
    """Mueve un servo por pulso, despacio, llegando siempre desde abajo."""

    def __init__(self, act, it, sentido):
        self.act, self.destino = act, tuple(it["canal"])
        self.sentido = sentido        # +1 si el pulso sube cuando sube el valor
        self.llegada = LLEGADA_DE.get(it["id"], LLEGADA)
        self.us = None

    def _ir(self, hasta, seg=0.4):
        desde = hasta if self.us is None else self.us
        pasos = max(2, int(abs(hasta - desde) / 10))
        for i in range(1, pasos + 1):
            self.act.escribir_pulso(self.destino, desde + (hasta - desde) * i / pasos)
            self.act.refrescar()
            banco.dormir(seg / pasos)
        self.us = hasta

    def poner(self, us):
        lo, hi = SERVO_CFG["pulso_limite_us"]
        us = max(float(lo), min(float(hi), us))
        # hacia abajo se pasa y vuelve, así el juego del engranaje queda siempre del mismo lado
        if self.us is None or (us - self.us) * self.sentido < 0:
            self._ir(us - self.sentido * self.llegada)
        self._ir(us)


def fuera_de_lo_normal(us):
    if SERVO_CFG["pulso_min_us"] <= us <= SERVO_CFG["pulso_max_us"]:
        return ""
    return "  (más allá de lo normal: si zumba, volvé atrás)"


def separar_teclas(texto):
    # según la terminal, las flechas llegan como ESC [ C o ESC O C
    teclas, i = [], 0
    while i < len(texto):
        c = texto[i]
        if c == "\x1b" and i + 2 < len(texto) and texto[i + 1] in ("[", "O"):
            teclas.append(FLECHA.get(texto[i + 2], ""))
            i += 3
            continue
        if c in ("\r", "\n"):
            teclas.append("enter")
        elif c != "\x1b":
            teclas.append(c.lower())
        i += 1
    return [t for t in teclas if t]


def lector_de_teclas():
    """(leer, restaurar) para leer tecla por tecla, o None en Windows, sin
    terminal o con --sin-flechas."""
    if not FLECHAS[0] or not sys.stdin.isatty():
        return None
    try:
        import select
        import termios
        import tty
    except ImportError:
        return None
    fd = sys.stdin.fileno()
    try:
        antes = termios.tcgetattr(fd)
        tty.setcbreak(fd)          # sin Enter y sin eco; Ctrl+C sigue andando
    except (termios.error, OSError):
        return None

    def leer():
        # junta las que se acumularon si dejaron la tecla apretada
        datos = os.read(fd, 64)
        if not datos:
            raise EOFError
        while select.select([fd], [], [], 0.03)[0]:
            datos += os.read(fd, 64)
        return separar_teclas(datos.decode("utf-8", "ignore"))

    def restaurar():
        termios.tcsetattr(fd, termios.TCSADRAIN, antes)
    return leer, restaurar


def tope_de_tanda(teclas):
    # Como mucho tres pasos de la más grande: si no, al soltar la tecla la
    # aguja sigue de largo con las que quedaron en cola.
    pasos = [abs(MOVIDA[t]) for t in teclas if t in MOVIDA]
    return 3 * max(pasos) if pasos else 0


def ajustar_teclas(aguja, leer):
    # devuelve lo mismo que ajustar()
    if not AYUDA_DADA[0]:              # la ayuda va solo la primera vez
        print(AYUDA_TECLAS)
        AYUDA_DADA[0] = True
    while True:
        sys.stdout.write("\r    %4.0f us%s   " % (aguja.us, fuera_de_lo_normal(aguja.us)))
        sys.stdout.flush()
        try:
            teclas = leer()
        except (EOFError, OSError):
            print("")
            return "q"
        tope = tope_de_tanda(teclas)
        movida = 0
        for t in teclas:
            if t in MOVIDA:
                movida = max(-tope, min(tope, movida + MOVIDA[t]))
                continue
            if movida:
                aguja.poner(aguja.us + aguja.sentido * movida)
            if t == "enter":
                print("")
                return aguja.us
            if t == "s":
                print("  (marca salteada)")
                return None
            if t == "t":
                print("")
                return ("t", aguja.us)
            if t in ("p", "q"):
                print("")
                return t
            movida = 0
        if movida:
            # tecla apretada: todas las que llegaron juntas, en un solo movimiento
            aguja.poner(aguja.us + aguja.sentido * movida)


def que_hacer(it, valor):
    # en el cabeceo se mueve el disco: nariz arriba es una línea del CIELO sobre el avioncito
    if it["id"] == "ATT_PITCH":
        if valor == 0:
            return "Llevá el disco: la línea del horizonte justo sobre el avioncito"
        lado = "del CIELO" if valor > 0 else "de la TIERRA"
        return ("Llevá el disco: la línea %g %s justo sobre el avioncito (%s)"
                % (abs(valor), lado, banco.fmt_valor(it, valor)))
    return "Llevá la aguja a  %s" % banco.fmt_valor(it, valor)


def ajustar(aguja, it, valor, us, P):
    """Pulso aceptado, None (saltear marca), 'p' (pasar instrumento) o 'q'."""
    aguja.poner(us)
    print("\n  " + que_hacer(it, valor))
    if P.auto:
        print("    %4.0f us > [auto: Enter]" % aguja.us)
        return aguja.us
    lector = lector_de_teclas()
    if lector is not None:
        leer, restaurar = lector
        try:
            return ajustar_teclas(aguja, leer)
        finally:
            restaurar()
    while True:
        try:
            r = input("    %4.0f us%s > " % (aguja.us, fuera_de_lo_normal(aguja.us))).strip().lower()
        except EOFError:
            return "q"
        if r == "":
            return aguja.us
        if r in ("+", "-", "++", "--"):
            paso = PASO_GRANDE if len(r) == 2 else PASO_CHICO
            hacia = 1 if r[0] == "+" else -1
            aguja.poner(aguja.us + hacia * aguja.sentido * paso)
        elif r == "s":
            return None
        elif r == "t":
            return ("t", aguja.us)
        elif r in ("p", "q"):
            return r
        else:
            print("    + / -  corre la aguja un poquito hacia los números más altos / bajos")
            print("    ++ / -- corre más    Enter = está justo en la marca")
            print("    s = saltear esta marca")
            print("    t = no llega: la aguja quedó en su tope (después decís qué número marca)")
            print("    p = pasar este instrumento sin guardarlo y seguir con el siguiente")
            print("    q = terminar todo (este instrumento no se guarda)")


def puntos_de_ensayo(it, valores):
    # los dos valores del movimiento corto que muestra el giro
    if it["id"] in DESDE_EL_MEDIO and 0 in valores:
        arriba = [v for v in valores if v > 0]
        return 0, (min(arriba) if arriba else valores[-1])
    return valores[0], valores[max(1, min(len(valores) - 1, len(valores) // 2))]


def elegir_giro(act, it, P, valores):
    """Movimiento corto para elegir giro normal o al revés. SEGUIR, PASADO o TERMINAR."""
    # el ensayo no usa las marcas viejas; si se da vuelta el giro ya no sirven
    destino, clave = tuple(it["canal"]), clave_de(it)
    if P.auto:
        print("  Giro: %s  [auto]" % ("al revés" if act.esta_al_reves(destino) else "normal"))
        return SEGUIR
    v0, v1 = puntos_de_ensayo(it, valores)
    if it["id"] == "ATT_PITCH":
        pregunta = "¿El disco BAJÓ (como nariz arriba: la línea 10 del CIELO hacia el avioncito)?"
    else:
        pregunta = "¿La aguja fue de %s hacia %s?" % (banco.fmt_valor(it, v0), banco.fmt_valor(it, v1))
    viejas = act.marcas.pop(clave, None)
    cambiado = False
    try:
        while True:
            al_reves = act.esta_al_reves(destino)
            print("\n  Giro: %s. Mirá la %s:" % ("AL REVÉS" if al_reves else "normal",
                                               "disco" if it["id"] == "ATT_PITCH" else "aguja"))
            us0 = act.pulso_us(destino, banco.angulo_servo(it, v0))
            us1 = act.pulso_us(destino, banco.angulo_servo(it, v1))
            ensayo = Aguja(act, it, 1)
            ensayo._ir(us0)
            banco.dormir(0.6)
            ensayo._ir(us1, seg=1.2)
            print("  " + pregunta)
            try:
                r = input("  Enter = sí, está bien   r = no, fue al revés   v = verlo otra vez"
                          "   p = pasar   q = terminar > ").strip().lower()
            except EOFError:
                r = "q"
            if r == "":
                act.soltar(destino)
                act.refrescar()
                print("  Queda: giro %s." % ("al revés" if al_reves else "normal"))
                return SEGUIR
            if r == "r":
                act.poner_al_reves(destino, not al_reves)
                cambiado = not cambiado
                print("  Se da vuelta el giro. Fijate otra vez:")
            elif r in ("p", "q"):
                act.soltar(destino)
                act.refrescar()
                return PASADO if r == "p" else TERMINAR
    finally:
        # las marcas viejas vuelven solo si el giro quedó como estaba
        if viejas is not None and not cambiado:
            act.marcas[clave] = viejas


def valor_en_el_tope(it, objetivo):
    # le pregunta al usuario qué número marca contra el tope; None es saltear
    lo, hi = it["escala"]
    while True:
        try:
            r = input("    La aguja no llega a %s. ¿Qué número marca? (Enter = saltear) > "
                      % banco.fmt_valor(it, objetivo)).strip().replace(",", ".")
        except EOFError:
            return None
        if r == "":
            return None
        try:
            v = float(r)
        except ValueError:
            print("    Escribí sólo el número, por ejemplo 1800.")
            continue
        if not lo <= v <= hi:
            print("    Tiene que estar entre %g y %g." % (lo, hi))
            continue
        return v


def calibrar(act, it, P, archivo, inf):
    destino, clave = tuple(it["canal"]), clave_de(it)
    valores = banco.puntos_de_prueba(it)
    giro_antes = act.esta_al_reves(destino)
    r = elegir_giro(act, it, P, valores)
    if r != SEGUIR:
        act.poner_al_reves(destino, giro_antes)
        if r == PASADO:
            print("\n  %s: pasado, no se guardó nada. Sigue el próximo." % it["id"])
            inf.anotar(SECCION, it["id"], "SALTEADO", "lo pasaste: quedó como estaba")
        else:
            inf.anotar(SECCION, it["id"], "SALTEADO", "se cortó sin guardar")
        return r
    angulos = [banco.angulo_servo(it, v) for v in valores]
    estimados = [act.pulso_us(destino, a) for a in angulos]
    sentido = 1 if estimados[-1] >= estimados[0] else -1

    print("  %s  -  %s" % (it["nombre"], banco.mecanica(it)))
    print("  Marcas: " + ", ".join(banco.fmt_valor(it, v) for v in valores))
    pieza = "el disco" if it["id"] == "ATT_PITCH" else "la aguja"
    print("  Mirá %s de frente, a la altura de los ojos." % pieza)
    if it["id"] == "ATT_PITCH":
        print("  Empieza por el 0. El disco corre en una corredera con tope: si deja de")
        print("  moverse aunque apretes la flecha, llegó al tope. No sigas: el brazo quedó")
        print("  en un diente equivocado (python3 probar_canal.py ATT_PITCH --valor 0 y")
        print("  calzarlo de nuevo).")

    orden = list(range(len(valores)))
    if it["id"] in DESDE_EL_MEDIO and 0 in valores:
        orden.sort(key=lambda k: (valores[k] < 0, abs(valores[k])))
    aguja = Aguja(act, it, sentido)
    medidas = []
    corrido = 0.0               # us que se corrió la marca del 0 contra lo calculado
    try:
        for k in orden:
            v, a, us = valores[k], angulos[k], estimados[k] + corrido
            r = ajustar(aguja, it, v, us, P)
            if r == "p":
                print("\n  %s: pasado, no se guardó nada. Sigue el próximo." % it["id"])
                inf.anotar(SECCION, it["id"], "SALTEADO", "lo pasaste: quedó como estaba")
                return PASADO
            if r == "q":
                inf.anotar(SECCION, it["id"], "SALTEADO", "se cortó sin guardar")
                return TERMINAR
            if isinstance(r, tuple):
                # no llega: se guarda el tope con el número que marca de verdad,
                # así la escala llega hasta donde puede
                real = valor_en_el_tope(it, v)
                if real is not None:
                    medidas.append((round(banco.angulo_servo(it, real), 2), int(round(r[1]))))
                    print("  Tope guardado: en %s." % banco.fmt_valor(it, real))
            elif r is not None:
                medidas.append((round(a, 2), int(round(r))))
                if it["id"] in DESDE_EL_MEDIO and v == 0:
                    corrido = r - estimados[k]
    finally:
        act.soltar(destino)
        act.refrescar()
    medidas.sort()

    if len(medidas) < 2:
        print("\n  Hacen falta al menos dos marcas: no se guarda nada.")
        inf.mal(SECCION, it["id"], "menos de dos marcas")
        return SEGUIR
    saltos = [b[1] - a[1] for a, b in zip(medidas, medidas[1:])]
    if not all(s * sentido > 0 for s in saltos):
        print("\n  Las marcas no avanzan siempre para el mismo lado: no se guarda.")
        if it["id"] == "ATT_PITCH":
            print("  Si el disco iba al revés de las flechas, repetilo y al empezar")
            print("  elegí el giro al revés (r).")
        else:
            print("  Repetilo; si vuelve a pasar, revisá que los engranajes no patinen.")
        inf.mal(SECCION, it["id"], "marcas fuera de orden")
        return SEGUIR

    # comprobación de ida y vuelta con las marcas nuevas
    anteriores = act.marcas.get(clave)
    act.marcas[clave] = sorted((float(a), float(u)) for a, u in medidas)
    print("\n  Comprobación: %s recorre la escala con lo que acabás de medir." % pieza)
    # arranca en la última marca, baja hasta la primera y vuelve
    ang = banco.angulo_servo(it, valores[-1])
    act.escribir_servo(destino, ang)
    act.refrescar()
    for v in valores[-2::-1] + valores[1:]:
        ang = banco.mover_servo(act, it, ang, banco.angulo_servo(it, v), seg=1.0)
        banco.dormir(0.6)
    act.soltar(destino)
    act.refrescar()
    r = P.si_no("¿Cayó en cada número y llegó a las dos puntas?")
    if r == "q":
        act.marcas[clave] = anteriores
        inf.anotar(SECCION, it["id"], "SALTEADO", "se cortó sin guardar")
        return TERMINAR
    if r == "n":
        act.marcas[clave] = anteriores
        print("  No se guardó. Volvé a calibrarlo.")
        inf.mal(SECCION, it["id"], "la comprobación no dio bien")
        return SEGUIR

    datos = leer(archivo)
    entrada = datos.get(clave) or {}
    entrada["marcas"] = [[a, u] for a, u in medidas]
    entrada["al_reves"] = act.esta_al_reves(destino)
    datos[clave] = entrada
    guardar(archivo, datos)
    print("  Guardado: %d marcas, giro %s." % (len(medidas),
                                             "al revés" if entrada["al_reves"] else "normal"))
    inf.bien(SECCION, it["id"], "%d marcas" % len(medidas))
    return SEGUIR


# Servo suelto: transportador, barrido, topes y pulso fijo (era calibrar_servo.py)
LIMITE = SERVO_CFG["pulso_limite_us"]
CLAVES_TRANSPORTADOR = ("us_0", "us_180", "tope_a", "tope_b", "min_us", "max_us")
PASO_T_CHICO = 10     # us por cada + o - en el transportador
PASO_T_GRANDE = 50


def texto_transportador(e):
    if "us_0" in e:
        txt = "   transportador 0°=%d 180°=%d us" % (e["us_0"], e["us_180"])
        if e.get("tope_a") is not None:
            txt += " (topes %d / %d)" % (e["tope_a"], e["tope_b"])
        return txt
    if "min_us" in e:
        return "   transportador %d a %d us (formato viejo)" % (e["min_us"], e["max_us"])
    return ""


def ajustar_transportador(act, destino, us, marca):
    """Brazo con + y - hasta la marca. Devuelve (pulso, ángulo leído)."""
    print("\n  Llevá el brazo a la marca de %d°." % marca)
    print("  +  / -   mueve %d us      ++ / --   mueve %d us" % (PASO_T_CHICO, PASO_T_GRANDE))
    print("  un número (por ejemplo 1480) va a ese pulso;  Enter: el brazo quedó en la marca")
    print("  Si el servo ZUMBA y no se mueve, está contra su tope: volvé con el signo")
    print("  contrario hasta que deje de zumbar y aceptá ahí.")
    while True:
        us = max(LIMITE[0], min(LIMITE[1], us))
        act.escribir_pulso(destino, us)
        act.refrescar()
        r = input("    %4d us%s > " % (us, fuera_de_lo_normal(us))).strip()
        if r == "":
            break
        if r in ("+", "-", "++", "--"):
            paso = PASO_T_GRANDE if len(r) == 2 else PASO_T_CHICO
            us += paso if r[0] == "+" else -paso
        else:
            try:
                us = int(r)
            except ValueError:
                print("    no entendí: + - ++ -- un número o Enter")
    leido = input("    ¿Sobre qué marca quedó el brazo? [Enter = %d°] > " % marca).strip()
    try:
        angulo = float(leido) if leido else float(marca)
    except ValueError:
        angulo = float(marca)
    return us, angulo


def transportador(act, destino, archivo):
    # con el transportador impreso (Transportador_servo.pdf)
    clave = "%s:%d" % destino
    print("\n  ================================================================")
    print("  Transportador: " + banco.nombre_de(destino))
    print("  ================================================================")
    print("  1. Apoyá el servo sobre el transportador, con el eje en la cruz,")
    print("     mirándolo desde el lado del eje.")
    print("  2. El servo va a 1500 us (el medio). Poné el brazo apuntando lo más")
    print("     cerca posible de 90° (arriba). Si queda torcido no importa: sólo")
    print("     tiene que poder llegar a 0° y a 180°.")
    act.escribir_pulso(destino, 1500)
    act.refrescar()
    input("     Enter cuando el brazo esté puesto > ")

    ant = leer(archivo).get(clave) or {}
    u1, a1 = ajustar_transportador(act, destino, int(ant.get("us_0", 600)), 0)
    u2, a2 = ajustar_transportador(act, destino, int(ant.get("us_180", 2400)), 180)
    if abs(a2 - a1) < 90 or abs(u2 - u1) < 500:
        print("\n  Los dos puntos están muy cerca: no se guarda nada. Repetilo.")
        return False

    # recta por los dos puntos; si una marca no se alcanzó se extrapola y el
    # pulso medido queda como tope
    def pulso(ang):
        return u1 + (ang - a1) * (u2 - u1) / (a2 - a1)
    us_0, us_180 = round(pulso(0.0)), round(pulso(180.0))
    medio = round(pulso(90.0))
    act.escribir_pulso(destino, medio)
    act.refrescar()
    print("\n  Comprobación: el brazo tiene que estar en 90° (%d us)." % medio)
    v = input("    ¿En qué marca está? [Enter = 90°] > ").strip()
    try:
        error = float(v) - 90.0 if v else 0.0
    except ValueError:
        error = 0.0
    if abs(error) > 4:
        print("    Error de %.0f° en el medio: el servo no es lineal o se movió el"
              " transportador. Se guarda igual; conviene repetirlo." % error)

    dato = {"us_0": us_0, "us_180": us_180}
    if a1 != 0.0 or a2 != 180.0:
        dato["tope_a"], dato["tope_b"] = u1, u2
    it = banco.que_hay_en(destino)
    if ant.get("marcas"):
        print("\n  Este canal tiene marcas medidas en el instrumento y se mantienen.")
        print("  Si cambiaste el servo, borralas:  python3 calibrar_instrumento.py %s --olvidar"
              % (it["id"] if it else clave))
    print("\n  0° = %d us   180° = %d us%s" % (
        us_0, us_180, "   (topes %d y %d us)" % (u1, u2) if "tope_a" in dato else ""))
    if it is not None and invertido(it["id"]):
        print("  Este canal lleva engranajes: en el instrumento el programa invierte")
        print("  el sentido solo. En el banco, sin engranajes, gira al revés: es correcto.")
    if input("  ¿Guardar? [S/n] > ").strip().lower() in ("", "s", "si", "sí"):
        datos = leer(archivo)
        entrada = {k: v for k, v in (datos.get(clave) or {}).items()
                   if k not in CLAVES_TRANSPORTADOR}
        entrada.update(dato)                 # marcas y giro elegido no se pierden
        datos[clave] = entrada
        guardar(archivo, datos)
        print("  Guardado.")
        return True
    print("  No se guardó.")
    return False


def barrer(act, destino):
    a, b = act.limites_us(destino)
    print("  Barriendo 0° -> 180° -> 0° (%d -> %d us)." % (a, b))
    for i in list(range(0, 181, 2)) + list(range(180, -1, -2)):
        act.escribir_servo(destino, i)
        act.refrescar()
        time.sleep(0.02)


def explorar(act, destino, hacia, inicio, paso, seg):
    paso = -abs(paso) if hacia == "abajo" else abs(paso)
    us = escrito = inicio
    print("  Mirá el brazo: cuando deje de moverse y zumbe, Ctrl+C.")
    try:
        while LIMITE[0] <= us <= LIMITE[1]:
            act.escribir_pulso(destino, us)
            act.refrescar()
            escrito = us
            print("    %4d us%s" % (us, fuera_de_lo_normal(us)))
            time.sleep(seg)
            us += paso
        print("  Llegó al límite del programa (%d a %d us)." % LIMITE)
    except KeyboardInterrupt:
        pass
    print("\n  Último valor bueno: %d us (un paso antes del que zumbó)." % (escrito - paso))


def herramientas_servo(a, archivo):
    if a.transportador and a.todos:
        placa = (a.instrumento[0] if a.instrumento else "PCA0").upper()
        act = banco.abrir_placas(a.simulado)
        try:
            for n in range(16):
                destino = (placa, n)
                it = banco.que_hay_en(destino)
                if it is not None and it["actuador"] != SERVO:
                    continue
                r = input("\n  Canal %s. Enter para calibrar, s para saltar, q para "
                          "terminar > " % banco.nombre_de(destino)).strip().lower()
                if r == "q":
                    break
                if r == "s":
                    continue
                transportador(act, destino, archivo)
                act.soltar(destino)
                act.refrescar()
        except (KeyboardInterrupt, EOFError):
            print("")
        finally:
            act.cerrar()
        return 0

    destino, it = banco.resolver(a.instrumento)
    if destino is None:
        print("  Falta el instrumento o el canal:  AIRSPEED   o   PCA0 6")
        return 1
    if it is not None and it["actuador"] != SERVO:
        print("  %s no es un servo." % banco.nombre_de(destino))
        return 1
    clave = "%s:%d" % destino

    if a.olvidar:                                  # acá siempre viene con --transportador
        datos = leer(archivo)
        entrada = datos.get(clave) or {}
        if any(entrada.pop(k, None) is not None for k in list(CLAVES_TRANSPORTADOR)):
            if entrada:
                datos[clave] = entrada
            else:
                datos.pop(clave, None)
            guardar(archivo, datos)
        print("  %s: sin transportador, vuelve a 500-2500 us." % banco.nombre_de(destino))
        return 0

    act = banco.abrir_placas(a.simulado)
    try:
        if a.transportador:
            transportador(act, destino, archivo)
        elif a.probar:
            barrer(act, destino)
        elif a.explorar:
            explorar(act, destino, a.explorar, a.inicio, a.paso, a.seg)
        else:
            us = max(LIMITE[0], min(LIMITE[1], a.pulso))
            print("  %s: pulso de %d us. Ctrl+C para soltar." % (banco.nombre_de(destino), us))
            act.escribir_pulso(destino, us)
            act.refrescar()
            while True:
                time.sleep(1.0)
    except (KeyboardInterrupt, EOFError):
        print("")
    finally:
        act.soltar(destino)
        act.refrescar()
        act.cerrar()
    return 0


# brújula (paso a paso)
PASO_MOTOR = {"der": 0.5, "+": 0.5, "izq": -0.5, "-": -0.5,
              "arr": 5.0, "++": 5.0, "aba": -5.0, "--": -5.0}
PUNTOS_CARDINALES = ((90, "E"), (180, "S"), (270, "O"), (0, "N"))


def mover_motor(gestor, m, grados=None, corrimiento=0.0):
    # a un ángulo por el camino más corto, o corrido unos grados; espera que llegue
    if grados is not None:
        m.ir_a_grados(grados)
    m.obj_grados += corrimiento
    if not gestor.esperar_quietos(10):
        print("  (la aguja no llegó a tiempo: revisá la alimentación de la plaquita)")


def ajustar_motor(gestor, m, P):
    """Corre la aguja hasta Enter. Devuelve 'enter', 'p' o 'q'."""
    if P.auto:
        print("    [auto: Enter]")
        return "enter"
    lector = lector_de_teclas()
    if lector is not None:
        leer, restaurar = lector
        print("    → / ←  medio grado (horario / antihorario)   ↑ / ↓  5 grados\n"
              "    Enter = está justo sobre la N   p = pasar   q = terminar")
        try:
            while True:
                sys.stdout.write("\r    corrida %+6.1f°   " % m.obj_grados)
                sys.stdout.flush()
                try:
                    teclas = leer()
                except (EOFError, OSError):
                    print("")
                    return "q"
                corre = 0.0
                for t in teclas:
                    if t in PASO_MOTOR:
                        corre += PASO_MOTOR[t]
                    elif t in ("enter", "p", "q"):
                        print("")
                        return t
                corre = max(-15.0, min(15.0, corre))   # con la tecla apretada, que no siga de largo
                if corre:
                    mover_motor(gestor, m, corrimiento=corre)
        finally:
            restaurar()
    while True:
        try:
            r = input("    corrida %+6.1f° > " % m.obj_grados).strip().lower()
        except EOFError:
            return "q"
        if r == "":
            return "enter"
        if r in PASO_MOTOR:
            mover_motor(gestor, m, corrimiento=PASO_MOTOR[r])
        elif r in ("p", "q"):
            return r
        else:
            print("    + / -  medio grado horario / antihorario   ++ / --  5 grados")
            print("    Enter = está justo sobre la N   p = pasar   q = terminar")


def calibrar_brujula(gestor, it, P, archivo, inf):
    n = it["canal"][1]
    m = gestor.motores[n]
    base = 1 if MOTORES[n].get("sentido", 1) >= 0 else -1
    print("  %s  -  %s" % (it["nombre"], banco.mecanica(it)))
    print("  La rosa está pegada y se mueve la aguja. Mirala de frente.")

    mover_motor(gestor, m, 0)
    print("\n  1/3  Llevá la aguja justo sobre la N")
    r = ajustar_motor(gestor, m, P)
    if r == "p":
        inf.anotar(SECCION, it["id"], "SALTEADO", "lo pasaste: quedó como estaba")
        return PASADO
    if r == "q":
        inf.anotar(SECCION, it["id"], "SALTEADO", "se cortó sin guardar")
        return TERMINAR
    m.declarar_cero()
    gestor.guardar_ahora()
    print("  Listo: la N es el cero.")

    # pidiendo 90° tiene que ir a la E, en sentido horario
    print("\n  2/3  Sentido de giro: la aguja va a 90°.")
    for intento in (1, 2):
        mover_motor(gestor, m, 90)
        r = P.si_no("¿Quedó sobre la E (giró como las agujas del reloj)?")
        mover_motor(gestor, m, 0)
        if r == "q":
            inf.anotar(SECCION, it["id"], "SALTEADO", "se cortó sin guardar")
            return TERMINAR
        if r == "s":
            break
        if intento == 1:
            m.invertir_sentido()
            print("  Giró para el otro lado: se da vuelta el giro y se prueba otra vez.")
    else:
        print("  Tampoco al revés. Revisá los cables IN1..IN4:")
        print("      python3 probar_motor.py %d --bobinas" % n)
        m.invertir_sentido()                 # se deshace la segunda vuelta, queda como estaba
        inf.mal(SECCION, it["id"], "no llega a la E para ningún lado (cables IN1..IN4)")
        return SEGUIR

    print("\n  3/3  Comprobación: la aguja pasa por E, S, O y vuelve a la N.")
    for grados, letra in PUNTOS_CARDINALES:
        mover_motor(gestor, m, grados)
        print("    %s" % letra)
        banco.dormir(0.8)
    r = P.si_no("¿Cayó en cada punto y volvió justo a la N?")
    if r == "q":
        inf.anotar(SECCION, it["id"], "SALTEADO", "se cortó sin guardar")
        return TERMINAR
    if r == "n":
        print("  No se guardó el giro. Si se corre de a poco en cada vuelta, revisá que")
        print("  la aguja no patine en el eje:  python3 probar_motor.py %d --vueltas 10" % n)
        inf.mal(SECCION, it["id"], "la comprobación no dio bien")
        return SEGUIR

    invertido = m.sentido != base
    datos = leer(archivo)
    datos[clave_de(it)] = {"invertido": invertido}
    guardar(archivo, datos)
    gestor.guardar_ahora()
    txt = "giro invertido" if invertido else "giro normal"
    print("  Guardado: cero en la N, %s." % txt)
    inf.bien(SECCION, it["id"], "cero en la N, " + txt)
    return SEGUIR


def preguntar_antes(it, P):
    if P.auto:
        return SEGUIR
    while True:
        try:
            r = input("  Enter = calibrarlo   p = pasar al siguiente   q = terminar > ")
        except EOFError:
            return TERMINAR
        r = r.strip().lower()
        if r == "":
            return SEGUIR
        if r == "p":
            return PASADO
        if r == "q":
            return TERMINAR


def main():
    ap = argparse.ArgumentParser(description="Calibrar cada aguja sobre su carátula")
    ap.add_argument("instrumento", nargs="*", help="AIRSPEED, o el canal: PCA0 6")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--desde", help="con --todos: empezar por éste")
    ap.add_argument("--saltear", default="",
                    help="con --todos: no calibrar éstos (separados por coma)")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--olvidar", action="store_true", help="borra las marcas de ese instrumento")
    ap.add_argument("--simulado", action="store_true", help="sin hardware (no toca la calibración)")
    ap.add_argument("--auto", action="store_true", help="acepta todo solo (demostración)")
    ap.add_argument("--sin-flechas", action="store_true", dest="sin_flechas",
                    help="mover con + y - y Enter (si las flechas no andan)")
    ap.add_argument("--transportador", action="store_true",
                    help="el pulso de 0° y 180° del servo, con el transportador")
    ap.add_argument("--probar", action="store_true", help="barre el servo 0° -> 180° -> 0°")
    ap.add_argument("--explorar", choices=("abajo", "arriba"), help="buscar el tope del servo")
    ap.add_argument("--inicio", type=int, default=1500, help="con --explorar: pulso de partida")
    ap.add_argument("--paso", type=int, default=25, help="con --explorar: us por paso")
    ap.add_argument("--seg", type=float, default=0.8, help="con --explorar: segundos por paso")
    ap.add_argument("--pulso", type=int, help="deja ese pulso fijo (Ctrl+C suelta)")
    a = ap.parse_args()
    FLECHAS[0] = not a.sin_flechas

    archivo = banco.ARCHIVO_CALIBRACION
    if a.simulado:
        # trabaja sobre una copia para no tocar lo guardado
        archivo = os.path.join(tempfile.mkdtemp(prefix="h08_cal_"), "calibracion_servos.json")
        if os.path.exists(banco.ARCHIVO_CALIBRACION):
            guardar(archivo, leer(banco.ARCHIVO_CALIBRACION))

    if a.listar:
        listar(archivo)
        return 0

    if a.transportador or a.probar or a.explorar or a.pulso is not None:
        return herramientas_servo(a, archivo)

    if a.instrumento:
        if len(a.instrumento) > 1 or a.instrumento[0].upper() in banco.PLACAS:
            print("  Para calibrar sobre la carátula se nombra el instrumento (ver --listar).")
            return 1
        it = banco.buscar(a.instrumento[0])
        if it is None or it["actuador"] not in (SERVO, MOTOR):
            print("  '%s' no es un instrumento que se calibre (ver --listar)." % a.instrumento[0])
            return 1
        if it["id"] in NO_SE_CALIBRAN:
            print("  %s no se calibra todavía: %s." % (it["id"], NO_SE_CALIBRAN[it["id"]]))
            return 1
        lista = [it]
    elif a.todos:
        lista = calibrables()
        if a.desde:
            ids = [x["id"] for x in lista]
            if a.desde.upper() not in ids:
                print("  No existe '%s' (ver --listar)." % a.desde)
                return 1
            lista = lista[ids.index(a.desde.upper()):]
        saltear = set(x.strip().upper() for x in a.saltear.split(",") if x.strip())
        desconocidos = saltear - set(x["id"] for x in calibrables())
        if desconocidos:
            print("  No existe: %s (ver --listar)." % ", ".join(sorted(desconocidos)))
            return 1
        lista = [x for x in lista if x["id"] not in saltear]
        if saltear:
            print("  Se saltean: " + ", ".join(sorted(saltear)))
    else:
        ap.print_help()
        return 1

    if a.olvidar:
        datos = leer(archivo)
        for it in lista:
            entrada = datos.get(clave_de(it)) or {}
            if entrada.pop("marcas", None) is not None:
                print("  %s: marcas borradas." % it["id"])
            if entrada.pop("al_reves", None) is not None:
                print("  %s: giro elegido borrado (vuelve al de configuracion.py)." % it["id"])
            if entrada.pop("invertido", None) is not None:
                print("  %s: giro calibrado borrado (vuelve al de configuracion.py)." % it["id"])
            if entrada:
                datos[clave_de(it)] = entrada
            else:
                datos.pop(clave_de(it), None)
        guardar(archivo, datos)
        return 0

    banco.salir_si_no_hay_consola(a.auto)
    P = banco.Preguntas(a.auto)
    inf = banco.Informe("CALIBRACIÓN DE INSTRUMENTOS - Tablero H-08" +
                    ("  (SIMULADA)" if a.simulado else ""))
    act = banco.abrir_placas(a.simulado)
    if FLECHAS[0] and sys.stdin.isatty() and os.name != "nt":
        print("\n  Flechas → / ← corren la aguja un poquito, ↑ / ↓ más (se pueden dejar"
              " apretadas).\n  Enter = en la marca")
    else:
        print("\n  + / -  corren la aguja un poquito (++ / -- más)   Enter = en la marca")
    print("  s = saltear una marca   p = pasar al instrumento siguiente   q = terminar")
    pasados = []
    gestor = None
    try:
        for k, it in enumerate(lista, 1):
            print("\n" + "-" * 70)
            print(" %d/%d  %s  (%s)" % (k, len(lista), it["id"], clave_de(it)))
            print("-" * 70)
            if it["actuador"] == MOTOR:
                if len(lista) > 1:
                    antes = preguntar_antes(it, P)
                    if antes == TERMINAR:
                        break
                    if antes == PASADO:
                        inf.anotar(SECCION, it["id"], "SALTEADO", "lo pasaste: quedó como estaba")
                        pasados.append(it["id"])
                        continue
                if gestor is None:
                    gestor = banco.abrir_motor(a.simulado, archivo)
                if gestor is None:
                    inf.anotar(SECCION, it["id"], "SALTEADO", "no se pudo abrir el motor")
                    continue
                r = calibrar_brujula(gestor, it, P, archivo, inf)
                if r == PASADO:
                    pasados.append(it["id"])
                elif r == TERMINAR:
                    break
                continue
            if it["canal"][0] not in act.placas:
                inf.anotar(SECCION, it["id"], "SALTEADO", "%s no responde" % it["canal"][0])
                continue
            if len(lista) > 1:
                antes = preguntar_antes(it, P)
                if antes == TERMINAR:
                    break
                if antes == PASADO:
                    inf.anotar(SECCION, it["id"], "SALTEADO", "lo pasaste: quedó como estaba")
                    pasados.append(it["id"])
                    continue
            r = calibrar(act, it, P, archivo, inf)
            if r == PASADO:
                pasados.append(it["id"])
            elif r == TERMINAR:
                break
    except KeyboardInterrupt:
        print("\n  Cortado: lo que no llegó a guardarse no se guardó.")
    finally:
        act.cerrar()
        if gestor is not None:
            gestor.cerrar()          # vuelve a la N y guarda la posición

    print("\n" + inf.texto())
    if pasados:
        print("\n  Quedaron sin calibrar: " + ", ".join(pasados))
        print("  Para hacerlos después, de a uno:  python3 calibrar_instrumento.py %s"
              % pasados[0])
    if not a.simulado:
        print("\n  El tablero toma la calibración nueva al arrancar:")
        print("    sudo systemctl start tablero-h08")
    print("\n  Informe guardado en: %s\n" % inf.guardar("calibracion"))
    return 1 if inf.malos() else 0


if __name__ == "__main__":
    sys.exit(main())
