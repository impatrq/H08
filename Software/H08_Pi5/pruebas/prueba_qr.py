# -*- coding: utf-8 -*-
"""Genera QR con nucleo/qr.py y los decodifica con OpenCV para ver si vuelve el mismo texto.

Mirar el dibujo no alcanza: escribiendo qr.py tuvimos un Reed-Solomon espejado,
faltaba el bloque de versión (7 en adelante) y el contador quedó en 8 bits
cuando desde la versión 10 son 16. Los tres QR se veían perfectos. Por eso se
recorren las diez versiones. Sin OpenCV avisa y no falla (en la Pi no hace falta).
"""
import os
import random
import string
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "nucleo"))

import qr                                                   # noqa: E402


def _imagen(matriz, escala=8, borde=4):
    import numpy as np
    n = len(matriz)
    lado = (n + 2 * borde) * escala
    im = np.full((lado, lado), 255, dtype=np.uint8)
    for y in range(n):
        for x in range(n):
            if matriz[y][x]:
                im[(y + borde) * escala:(y + borde + 1) * escala,
                   (x + borde) * escala:(x + borde + 1) * escala] = 0
    return im


def correr():
    try:
        import cv2                                          # noqa: F401
        import numpy                                        # noqa: F401
    except ImportError:
        print("OpenCV no esta instalado: no se puede comprobar la lectura.")
        print("La prueba no falla, pero tampoco comprueba nada.")
        return 0

    import cv2
    lector = cv2.QRCodeDetector()

    casos = ["http://192.168.1.45:8000/",
             # la del QR de administrador, el más cargado que generamos
             "http://10.0.0.7:8000/mando?k=JXUuz0XJvfjplbVW7QOAqA",
             "http://tablero-h08.local:8000/",
             "WIFI:T:WPA;S:Tablero-H08;P:sikorsky55;;",
             "H-08", "a"]
    random.seed(20260828)
    alfabeto = string.ascii_letters + string.digits + "/:.-_?=&"
    for largo in list(range(1, 60)) + [80, 100, 120, 140, 160, 180, 200, 213]:
        casos.append("".join(random.choice(alfabeto) for _ in range(largo)))

    por_version = {}
    fallados = []
    for texto in casos:
        m = qr.matriz(texto)
        version = (len(m) - 17) // 4
        por_version.setdefault(version, [0, 0])
        try:
            leido, _, _ = lector.detectAndDecode(_imagen(m))
        except cv2.error:
            leido = ""
        if leido == texto:
            por_version[version][0] += 1
        else:
            por_version[version][1] += 1
            fallados.append((len(texto), version, leido[:30]))

    print("=" * 70)
    print("CODIGOS QR - se generan y se DECODIFICAN con un lector de verdad")
    print("=" * 70)
    print("   %d textos, de 1 a 213 caracteres" % len(casos))
    print()
    print("   version   leidos   fallados")
    for v in sorted(por_version):
        ok, mal = por_version[v]
        print("      %2d      %4d     %4d %s" % (v, ok, mal, "" if not mal else "<--"))
    print()
    if fallados:
        print("   NO SE PUDIERON LEER:")
        for largo, v, leido in fallados[:10]:
            print("      %d caracteres, version %d, se leyo %r" % (largo, v, leido))
        print("=" * 70)
        print("HAY %d CODIGO(S) QUE NO SE LEEN" % len(fallados))
        print("=" * 70)
        return 1

    # y que las diez versiones se hayan recorrido de verdad
    faltan = [v for v in range(1, 11) if v not in por_version]
    if faltan:
        print("   OJO: no se probaron las versiones %s" % faltan)
        print("=" * 70)
        return 1

    print("=" * 70)
    print("LOS %d CODIGOS SE LEEN, EN LAS DIEZ VERSIONES" % len(casos))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(correr())
