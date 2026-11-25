#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arma dist/H08_Pi5.zip para llevar a la Raspberry (corre las pruebas antes,
salvo con --sin-pruebas; --salida E:\\ lo deja en el pendrive).

Pasa todo a LF porque con CRLF bash en la Pi falla con "$'\\r': command not
found". Nunca mete los archivos privados de cada tablero.
"""
import argparse
import datetime
import hashlib
import os
import subprocess
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETAS = ("nucleo", "raspberry_pi5", "pruebas")
# los archivos de trabajo del programador no viajan, se quedan en la compu
SUELTOS = ("LEEME.md", "empaquetar.py", ".gitignore", ".gitattributes")
PRIVADOS = {"secreto_admin.json", "calibracion_servos.json", "posicion_motores.json", "bloqueados_red.txt"}
FUERA_DIR = {"__pycache__", "informes", ".venv", ".git", "dist"}
FUERA_EXT = (".pyc", ".tmp", ".log", ".zip")
TEXTO = (".py", ".sh", ".md", ".html", ".svg", ".json", ".txt", ".desktop", ".css", ".js")
RAIZ_ZIP = "H08_Pi5"


def archivos():
    for f in SUELTOS:
        ruta = os.path.join(AQUI, f)
        if os.path.exists(ruta):
            yield ruta, f
    for c in CARPETAS:
        for base, dirs, fs in os.walk(os.path.join(AQUI, c)):
            dirs[:] = sorted(d for d in dirs if d not in FUERA_DIR)
            for f in sorted(fs):
                if f in PRIVADOS or f.endswith(FUERA_EXT):
                    continue
                ruta = os.path.join(base, f)
                yield ruta, os.path.relpath(ruta, AQUI).replace(os.sep, "/")


def leer(ruta, rel):
    with open(ruta, "rb") as f:
        datos = f.read()
    if rel.endswith(TEXTO) or rel in (".gitignore", ".gitattributes"):
        datos = datos.replace(b"\r\n", b"\n")
    return datos


def pruebas():
    print("Corriendo las pruebas antes de empaquetar (1 minuto)...")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(AQUI, "pruebas", "correr_pruebas.py")],
                       env=env)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Arma H08_Pi5.zip para la Raspberry")
    ap.add_argument("--sin-pruebas", action="store_true", dest="sin_pruebas")
    ap.add_argument("--salida", default=os.path.join(AQUI, "dist"))
    a = ap.parse_args()

    if not a.sin_pruebas and not pruebas():
        print("\nHay pruebas que fallan: NO se armó el zip. Arreglarlas primero "
              "(o --sin-pruebas, bajo tu responsabilidad).")
        return 1

    lista = [(ruta, rel, leer(ruta, rel)) for ruta, rel in archivos()]
    h = hashlib.sha256()
    for _, rel, datos in lista:
        h.update(rel.encode("utf-8"))
        h.update(datos)
    ahora = datetime.datetime.now()
    version = ("H08_Pi5 %s  ·  huella %s\n"
               "Tablero didáctico H-08 · Sikorsky S-55 / H-19A · programa de la Raspberry Pi 5\n"
               "archivos  %d\n"
               "Se ve al arrancar el programa y en diagnostico_pi.py.\n"
               % (ahora.strftime("%Y-%m-%d %H:%M"), h.hexdigest()[:12], len(lista) + 1))

    os.makedirs(a.salida, exist_ok=True)
    destino = os.path.join(a.salida, "H08_Pi5.zip")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        def meter(rel, datos, ejecutable=False):
            info = zipfile.ZipInfo(RAIZ_ZIP + "/" + rel, date_time=ahora.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if ejecutable else 0o644) << 16
            z.writestr(info, datos)
        meter("VERSION.txt", version.encode("utf-8"))
        for _, rel, datos in lista:
            meter(rel, datos, ejecutable=rel.endswith(".sh"))

    with zipfile.ZipFile(destino) as z:
        nombres = z.namelist()
    colados = [n for n in nombres if os.path.basename(n) in PRIVADOS]
    if colados:
        os.remove(destino)
        print("SE COLÓ UN ARCHIVO PRIVADO: %s. Zip borrado." % colados)
        return 1
    # la copia local también queda con la versión nueva
    with open(os.path.join(AQUI, "VERSION.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(version)
    print("\nListo: %s  (%d archivos, %.0f kB)" % (destino, len(nombres),
                                                   os.path.getsize(destino) / 1024.0))
    print(version.splitlines()[0])
    print("En la Raspberry:  bash actualizar.sh RUTA/H08_Pi5.zip   (la primera vez: instalar.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
