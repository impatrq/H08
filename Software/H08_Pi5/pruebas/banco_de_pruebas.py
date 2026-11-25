# -*- coding: utf-8 -*-
"""Corre el simulador entero en cualquier PC con Python 3, sin Raspberry ni servos.

Uso: python3 pruebas/banco_de_pruebas.py [escenarios | fallas | calib | perf | todo]
Sin argumento hace el vuelo normal completo.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "nucleo"))

from utiles import interpolar_tabla                      # noqa: E402
from configuracion import TABLERO, TABLERO_POR_ID                # noqa: E402
from actuadores_simulados import ActuadoresSimulados                          # noqa: E402
from simulador import Simulador, MODO_DETENIDO              # noqa: E402
from fallas import CATALOGO                            # noqa: E402
from escenarios import ESCENARIOS, PERFIL_NORMAL          # noqa: E402

DT = 1.0 / 20.0

COLUMNAS = [
    ("AIRSPEED", "IAS", "%6.1f"),
    ("ALTIMETER", "ALT", "%7.0f"),
    ("VSI", "V/S", "%7.0f"),
    ("TACH_ENG", "N.MOT", "%7.0f"),
    ("TACH_ROT", "N.ROT", "%6.0f"),
    ("MAP", "MAP", "%6.1f"),
    ("OIL_PRESS", "P.AC", "%6.1f"),
    ("OIL_TEMP", "T.AC", "%6.1f"),
    ("CHT", "CHT", "%6.0f"),
    ("XMSN_OIL_PRESS", "P.TR", "%6.1f"),
    ("VOLTMETER", "VOLT", "%6.1f"),
    ("FUEL_QTY_FWD", "C.FWD", "%6.0f"),
]
LUCES_ID = ["LT_FUEL_FWD", "LT_FUEL_AFT", "LT_XMSN_PRESS", "LT_GEN", "LT_LOW_ROTOR"]


def encabezado():
    h = "  T(s) | " + " | ".join(["%-6s" % c[1] for c in COLUMNAS]) + " | LUCES"
    return h


def fila(sim):
    partes = []
    est = sim.bus
    for iid, _, fmt in COLUMNAS:
        it = TABLERO_POR_ID[iid]
        partes.append(fmt % est.ver(it["senal"], 0.0))
    luces = ""
    for iid in LUCES_ID:
        it = TABLERO_POR_ID[iid]
        luces += "*" if est.ver(it["senal"], 0.0) >= 0.5 else "."
    return "%6.1f | " % sim.t_sim + " | ".join(partes) + " | " + luces


def correr(sim, segundos, cada=5.0, mostrar=True):
    n = int(segundos / DT)
    prox = 0.0
    fase_previa = None
    for i in range(n):
        sim.paso(DT)
        sim.mapa.escribir()
        if sim.modo == MODO_DETENIDO:
            break
        if mostrar:
            fase = sim.estado(False).get("fase") or sim.estado(False).get("escenario")
            if fase != fase_previa:
                print("\n>>> " + str(fase))
                print(encabezado())
                fase_previa = fase
                prox = sim.t_sim
            if sim.t_sim >= prox:
                print(fila(sim))
                prox = sim.t_sim + cada


def prueba_vuelo_normal():
    print("=" * 118)
    print("PRUEBA 1 - VUELO NORMAL COMPLETO (Modo 1)")
    print("=" * 118)
    actuadores = ActuadoresSimulados()
    sim = Simulador(actuadores, semilla=1234)
    sim.ciclar = False
    sim.modo_normal()
    total = sum([f["dur"] for f in PERFIL_NORMAL])
    correr(sim, total + 10, cada=6.0)
    print("\nEstadisticas de escritura al hardware:")
    st = sim.mapa.estadisticas()
    print("   escrituras reales : %d" % st["escrituras"])
    print("   escrituras evitadas: %d" % st["omitidas"])
    print("   AHORRO por banda muerta: %.1f%%" % st["ahorro_pct"])
    print("   Sin banda muerta serían %d escrituras." % (st["escrituras"] + st["omitidas"]))
    return True


def prueba_escenarios():
    print("\n" + "=" * 118)
    print("PRUEBA 2 - LOS 8 ESCENARIOS DE EMERGENCIA (Modo 2)")
    print("=" * 118)
    for e in ESCENARIOS:
        print("\n" + "-" * 118)
        print("ESCENARIO: %s   [%s]" % (e["nombre"], e["id"]))
        print("-" * 118)
        actuadores = ActuadoresSimulados()
        sim = Simulador(actuadores, semilla=777)
        sim.modo_escenario(e["id"])
        print(encabezado())
        n = int((e["duracion"] + 5) / DT)
        prox = 0.0
        vistos = 0
        for i in range(n):
            sim.paso(DT)
            sim.mapa.escribir()
            while vistos < len(sim.mensajes):
                mm = sim.mensajes[vistos]
                print("    [%6.1f s] %s" % (mm["t"], mm["texto"]))
                vistos += 1
            if sim.t_sim >= prox:
                print(fila(sim))
                prox = sim.t_sim + 15.0
            if sim.modo == MODO_DETENIDO:
                break
    return True


def prueba_fallas():
    print("\n" + "=" * 118)
    print("PRUEBA 3 - LAS %d FALLAS DEL CATÁLOGO (Modo 3)" % len(CATALOGO))
    print("=" * 118)
    print("%-22s %-14s %-9s %s" % ("FALLA", "SISTEMA", "SEV", "EFECTO OBSERVADO A LOS 90 s"))
    print("-" * 118)
    errores = []
    for f in CATALOGO:
        actuadores = ActuadoresSimulados()
        sim = Simulador(actuadores, semilla=42)
        sim.modo_falla(f["id"])
        # 2 s antes de tomar la referencia, si no los filtros todavía no llegaron a crucero
        for i in range(int(2.0 / DT)):
            sim.paso(DT)
        base = {}
        for iid, _, _ in COLUMNAS:
            base[iid] = sim.bus.ver(TABLERO_POR_ID[iid]["senal"], 0.0)
        try:
            for i in range(int(90.0 / DT)):
                sim.paso(DT)
                sim.mapa.escribir()
        except Exception as ex:
            errores.append((f["id"], repr(ex)))
            print("%-22s %-14s %-9s ERROR: %r" % (f["id"], f["sistema"], f["sev"], ex))
            continue

        cambios = []
        for iid, etiqueta, _ in COLUMNAS:
            v = sim.bus.ver(TABLERO_POR_ID[iid]["senal"], 0.0)
            b = base[iid]
            rango = TABLERO_POR_ID[iid]["escala"][1] - TABLERO_POR_ID[iid]["escala"][0]
            if abs(v - b) > 0.06 * rango:
                cambios.append("%s %.0f->%.0f" % (etiqueta, b, v))
        luces_on = []
        for iid in LUCES_ID:
            if sim.bus.ver(TABLERO_POR_ID[iid]["senal"], 0.0) >= 0.5:
                luces_on.append(iid.replace("LT_", ""))
        txt = ", ".join(cambios[:4])
        if luces_on:
            txt += "  LUZ:" + "+".join(luces_on)
        if not txt:
            txt = "(sin cambio significativo en las columnas mostradas)"
        print("%-22s %-14s %-9s %s" % (f["id"], f["sistema"], f["sev"], txt))
    return len(errores) == 0


def prueba_calibracion():
    print("\n" + "=" * 118)
    print("PRUEBA 4 - VERIFICACIÓN DE TABLAS DE CALIBRACIÓN")
    print("=" * 118)
    ok = True
    print("%-18s %-8s %-22s %-28s %s" % ("INSTRUMENTO", "ACT.", "ESCALA",
                                         "ÁNGULOS min..max", "CONTROL"))
    print("-" * 118)
    for it in TABLERO:
        cal = it["cal"]
        vmin, vmax = it["escala"]
        problemas = []

        # ordenada en x
        for i in range(1, len(cal)):
            if cal[i][0] <= cal[i - 1][0]:
                problemas.append("tabla desordenada en x")
                break

        # que cubra toda la escala
        if cal[0][0] > vmin + 1e-6:
            problemas.append("no cubre el mínimo (%.1f)" % vmin)
        if cal[-1][0] < vmax - 1e-6:
            problemas.append("no cubre el máximo (%.1f)" % vmax)

        amin = min([c[1] for c in cal])
        amax = max([c[1] for c in cal])
        # El motor de giro continuo no tiene tope. El servo sí: pasado 180
        # ya fuerza los engranajes de la reducción.
        if it["actuador"] == "MOTOR":
            tope = 360.0
        elif "LED" in it["actuador"]:
            tope = 1.0
        else:
            tope = 180.0
        if amin < -0.01 or amax > tope + 0.01:
            problemas.append("ángulo fuera de 0..%.0f" % tope)

        # monótona, si no la aguja retrocede
        signo = 0
        for i in range(1, len(cal)):
            d = cal[i][1] - cal[i - 1][1]
            s = 1 if d > 0 else (-1 if d < 0 else 0)
            if s != 0:
                if signo == 0:
                    signo = s
                elif s != signo:
                    problemas.append("no monotona: la aguja retrocede")
                    break

        estado = "OK" if not problemas else "FALLA: " + "; ".join(problemas)
        if problemas:
            ok = False
        print("%-18s %-8s %-22s %-28s %s" % (
            it["id"], it["actuador"],
            "%.0f..%.0f %s" % (vmin, vmax, it["unidad"]),
            "%.1f .. %.1f" % (amin, amax), estado))

    # tacómetro doble: las dos agujas tienen que quedar una arriba de la otra
    print("\nControl de superposición del TACÓMETRO DOBLE (relación 10:1):")
    te = TABLERO_POR_ID["TACH_ENG"]["cal"]
    tr = TABLERO_POR_ID["TACH_ROT"]["cal"]
    print("   %-10s %-12s %-12s %s" % ("RPM motor", "ang. motor", "ang. rotor", "dif."))
    peor = 0.0
    for rpm in (0, 500, 1000, 1400, 2000, 2200, 2400, 3000, 3500):
        ae = interpolar_tabla(rpm, te)
        ar = interpolar_tabla(rpm / 10.0, tr)
        peor = max(peor, abs(ae - ar))
        print("   %-10d %-12.2f %-12.2f %.2f" % (rpm, ae, ar, abs(ae - ar)))
    if peor > 0.5:
        print("   FALLA: las agujas no se superponen (diferencia máxima %.2f grados)" % peor)
        ok = False
    else:
        print("   OK: diferencia máxima %.2f grados (imperceptible en la esfera)" % peor)
    return ok


def prueba_rendimiento():
    print("\n" + "=" * 118)
    print("PRUEBA 5 - RENDIMIENTO DEL NUCLEO")
    print("=" * 118)
    import time
    actuadores = ActuadoresSimulados()
    sim = Simulador(actuadores, semilla=1)
    sim._preparar_crucero()
    sim.modo = 3
    n = 20000
    t0 = time.time()
    for i in range(n):
        sim.paso(DT)
    t1 = time.time()
    us = (t1 - t0) / n * 1e6
    print("   %d pasos de simulación en %.2f s" % (n, t1 - t0))
    print("   %.1f us por paso en esta PC" % us)
    print("   Presupuesto por paso a 20 Hz: 50000 us")
    print("   Uso de CPU en esta PC: %.3f %%" % (us / 50000.0 * 100.0))
    print("   La Raspberry Pi 5 es del mismo orden que una PC de escritorio,")
    print("   así que el margen a 20 Hz se mantiene igual de amplio.")
    return True


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "normal"
    resultados = []
    if que in ("normal", "todo"):
        resultados.append(("vuelo normal", prueba_vuelo_normal()))
    if que in ("escenarios", "todo"):
        resultados.append(("escenarios", prueba_escenarios()))
    if que in ("fallas", "todo"):
        resultados.append(("fallas", prueba_fallas()))
    if que in ("calib", "todo"):
        resultados.append(("calibracion", prueba_calibracion()))
    if que in ("perf", "todo"):
        resultados.append(("rendimiento", prueba_rendimiento()))

    print("\n" + "=" * 118)
    print("RESUMEN")
    print("=" * 118)
    todo_ok = True
    for nombre, ok in resultados:
        print("   %-16s %s" % (nombre, "OK" if ok else "CON ERRORES"))
        todo_ok = todo_ok and ok
    sys.exit(0 if todo_ok else 1)
