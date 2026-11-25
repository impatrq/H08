#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puesta en marcha del paso a paso de la brújula (motor 1, GPIO 12, 16, 20, 21).
El GPIO 26 del lugar del motor 0 lo usa la llave BATERÍA.

Si gira al revés: calibrar_instrumento.py COMPASS. Si tiembla y no gira, están
cruzados IN1..IN4: con --bobinas tienen que prender los LED A, B, C, D en orden.
"""

import argparse
import sys
import time

import banco
from configuracion import MOTORES, MOTOR_CFG


def listar():
    guardado = {}
    try:
        import json
        with open(banco.ARCHIVO_MOTORES, encoding="utf-8") as f:
            guardado = json.load(f)
    except (OSError, ValueError):
        pass
    print("")
    from paso_a_paso import motores_invertidos
    invertidos = motores_invertidos(banco.ARCHIVO_CALIBRACION)
    for n, m in sorted(MOTORES.items()):
        pos = guardado.get(str(n))
        print("  Motor %d  %-14s GPIO %-15s sentido %+d%s   posición %s"
              % (n, m["id"], ",".join(str(p) for p in m["pines"]), m["sentido"],
                 " (invertido por la calibración)" if n in invertidos else "",
                 "%.1f°" % pos[0] if pos else "0° (sin archivo)"))
    print("\n  %.2f pasos por vuelta, hasta %d pasos/s\n"
          % (MOTOR_CFG["pasos_por_vuelta"], MOTOR_CFG["vel_max_pps"]))


def esperar(gestor, limite):
    if not gestor.esperar_quietos(limite):
        print("  (no llegó a tiempo: revisar alimentación y cables)")


def main():
    ap = argparse.ArgumentParser(description="Probar los motores paso a paso")
    ap.add_argument("motor", nargs="?", type=int, choices=sorted(MOTORES))
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--bobinas", action="store_true")
    ap.add_argument("--grados", type=float)
    ap.add_argument("--mover", type=float)
    ap.add_argument("--cero", action="store_true")
    ap.add_argument("--vueltas", type=int)
    a = ap.parse_args()

    if a.listar or a.motor is None:
        listar()
        return 0

    banco.exigir_servicio_detenido()
    from paso_a_paso import GestorMotores, EscritorGPIO, SECUENCIA
    try:
        escritor = EscritorGPIO()
    except RuntimeError as e:
        print("  %s" % e)
        return 1
    gestor = GestorMotores(escritor, banco.ARCHIVO_MOTORES,
                           archivo_calibracion=banco.ARCHIVO_CALIBRACION)
    m = gestor.motores[a.motor]
    print("  Motor %d (%s), aguja en %.1f°" % (a.motor, MOTORES[a.motor]["id"],
                                              m.grados()))

    if a.bobinas:
        for i, letra in enumerate("ABCD"):
            print("    IN%d  (LED %s)" % (i + 1, letra))
            escritor(m.pines, 1 << i)
            time.sleep(1.0)
        escritor(m.pines, SECUENCIA[m.estado])
        time.sleep(0.2)
        m.soltar()
        escritor.cerrar()
        return 0

    if a.cero:
        m.declarar_cero()
        gestor.guardar_ahora()
        escritor.cerrar()
        print("  Listo: esta posición es el cero.")
        return 0

    gestor.start()
    try:
        if a.mover is not None:
            m.obj_grados += a.mover
            esperar(gestor, 10)
            print("  Aguja en %.1f°. Si quedó sobre el cero:  --cero" % m.grados())
            gestor.detener()
            escritor.cerrar()
            return 0

        if a.vueltas:
            inicio = m.obj_grados
            print("  %d vueltas adelante..." % a.vueltas)
            m.obj_grados = inicio + 360.0 * a.vueltas
            esperar(gestor, 5 + 6 * a.vueltas)
            input("  ¿Quedó donde arrancó? Enter para volver...")
            m.obj_grados = inicio
            esperar(gestor, 5 + 6 * a.vueltas)
        elif a.grados is not None:
            m.ir_a_grados(a.grados)
            esperar(gestor, 10)
            input("  Marcando %.0f. Enter para volver a cero..." % a.grados)
    except KeyboardInterrupt:
        print("")
    gestor.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
