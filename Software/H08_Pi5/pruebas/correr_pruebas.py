#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corre todas las pruebas automáticas, una detrás de otra.

python3 pruebas/correr_pruebas.py. No hace falta hardware: anda igual en la
Raspberry que en una compu. De cada prueba muestra las últimas líneas.
"""

import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
PRUEBAS = [
    ("banco_de_pruebas.py", ["todo"]),
    ("prueba_hardware.py", []),
    ("prueba_servidor.py", []),
    ("prueba_acceso.py", []),
    ("prueba_qr.py", []),
    ("prueba_pi5.py", []),
]


def main():
    resultados = []
    for archivo, args in PRUEBAS:
        print("=" * 70)
        print(" " + archivo)
        print("=" * 70)
        t0 = time.monotonic()
        # UTF-8 forzado: en Windows la consola usa otra codificación y los
        # acentos y los QR rompían la salida capturada
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, os.path.join(AQUI, archivo)] + args,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env)
        salida = (r.stdout + r.stderr).strip().splitlines()
        print("\n".join(salida[-6:]))
        resultados.append((archivo, r.returncode == 0, time.monotonic() - t0))
        print("")
    print("=" * 70)
    for archivo, ok, seg in resultados:
        print("  %-22s %s   (%.0f s)" % (archivo, "OK" if ok else "FALLÓ", seg))
    malos = [a for a, ok, _ in resultados if not ok]
    print("=" * 70)
    print(" Todas bien." if not malos else " Fallaron: " + ", ".join(malos))
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
