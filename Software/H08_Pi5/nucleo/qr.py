# -*- coding: utf-8 -*-
"""Generador de QR con la biblioteca estándar, porque la Pi arranca sin internet.

Modo byte, corrección M, versiones 1 a 10 (hasta 213 caracteres). La prueba
pruebas/prueba_qr.py los decodifica de verdad con OpenCV.
"""

# GF(256) para Reed-Solomon
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:                 # polinomio del campo 0x11D
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _poli_generador(grado):
    # (x-1)(x-a)(x-a^2)...
    g = [1]
    for i in range(grado):
        # g va con el coeficiente de mayor grado primero: x deja cada uno en
        # su índice y a lo baja al siguiente.
        # Ojo: estas dos líneas estaban al revés. El QR se veía perfecto y
        # ningún celular lo leía, por eso la prueba decodifica en serio.
        nuevo = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            nuevo[j] ^= c
            nuevo[j + 1] ^= _mul(c, _EXP[i])
        g = nuevo
    return g


def _correccion(datos, n_ec):
    g = _poli_generador(n_ec)
    resto = list(datos) + [0] * n_ec
    for i in range(len(datos)):
        coef = resto[i]
        if coef:
            for j, gc in enumerate(g):
                resto[i + j] ^= _mul(gc, coef)
    return resto[len(datos):]


# tablas del estándar, corrección M. version: (datos totales, corrección por
# bloque, bloques g1, datos por bloque g1, bloques g2, datos por bloque g2)
_TABLA_M = {
    1:  (16,  10, 1, 16, 0, 0),
    2:  (28,  16, 1, 28, 0, 0),
    3:  (44,  26, 1, 44, 0, 0),
    4:  (64,  18, 2, 32, 0, 0),
    5:  (86,  24, 2, 43, 0, 0),
    6:  (108, 16, 4, 27, 0, 0),
    7:  (124, 18, 4, 31, 0, 0),
    8:  (154, 22, 2, 38, 2, 39),
    9:  (182, 22, 3, 36, 2, 37),
    10: (216, 26, 4, 43, 1, 44),
}

# centros de alineación
_ALINEACION = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46],
    10: [6, 28, 50],
}

# nivel M con su BCH, por máscara
_FORMATO_M = [
    0x5412, 0x5125, 0x5E7C, 0x5B4B, 0x45F9, 0x40CE, 0x4F97, 0x4AA0,
]


def _bits_cuenta(version):
    return 8 if version < 10 else 16


def _version_para(n_bytes):
    for v in range(1, 11):
        if _TABLA_M[v][0] * 8 >= 4 + _bits_cuenta(v) + n_bytes * 8:
            return v
    raise ValueError("el texto no entra en un QR version 10 "
                     "(el maximo son 213 caracteres)")


def _bits_de(texto, version):
    datos = texto.encode("utf-8")
    cap = _TABLA_M[version][0]
    bits = [0, 1, 0, 0]                                  # modo byte
    nb = _bits_cuenta(version)
    for k in range(nb - 1, -1, -1):                      # 8 bits hasta v9, 16 en v10
        bits.append((len(datos) >> k) & 1)
    for b in datos:
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)
    for _ in range(min(4, cap * 8 - len(bits))):
        bits.append(0)
    while len(bits) % 8:
        bits.append(0)
    relleno = (0xEC, 0x11)
    i = 0
    while len(bits) < cap * 8:
        b = relleno[i % 2]
        i += 1
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)
    return bits


def _bytes_finales(texto, version):
    # datos y corrección intercalados por bloque, como pide el estándar
    bits = _bits_de(texto, version)
    crudos = [int("".join(str(b) for b in bits[i:i + 8]), 2)
              for i in range(0, len(bits), 8)]

    _tot, n_ec, g1, d1, g2, d2 = _TABLA_M[version]
    bloques, i = [], 0
    for _ in range(g1):
        bloques.append(crudos[i:i + d1]); i += d1
    for _ in range(g2):
        bloques.append(crudos[i:i + d2]); i += d2
    ecs = [_correccion(b, n_ec) for b in bloques]

    salida = []
    for k in range(max(len(b) for b in bloques)):
        for b in bloques:
            if k < len(b):
                salida.append(b[k])
    for k in range(n_ec):
        for e in ecs:
            salida.append(e[k])
    return salida


def _armar(version):
    # patrones fijos y casillas reservadas; None = libre para datos
    n = version * 4 + 17
    m = [[None] * n for _ in range(n)]

    def cuadro(fx, fy):
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                x, y = fx + dx, fy + dy
                if not (0 <= x < n and 0 <= y < n):
                    continue
                borde = dx in (0, 6) and 0 <= dy <= 6
                borde = borde or (dy in (0, 6) and 0 <= dx <= 6)
                centro = 2 <= dx <= 4 and 2 <= dy <= 4
                m[y][x] = 1 if (borde or centro) else 0

    cuadro(0, 0); cuadro(n - 7, 0); cuadro(0, n - 7)

    for i in range(8, n - 8):                            # tiempo
        v = 1 - (i % 2)
        m[6][i] = v
        m[i][6] = v

    ejes = _ALINEACION[version]
    for cy in ejes:
        for cx in ejes:
            if (cx, cy) in ((6, 6), (6, n - 7), (n - 7, 6)):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    m[cy + dy][cx + dx] = 1 if (max(abs(dx), abs(dy)) != 1) else 0

    m[n - 8][8] = 1                                      # módulo oscuro fijo

    # Desde v7 va la versión: 18 bits en dos bloques de 6x3 (arriba a la
    # derecha y abajo a la izquierda). Antes el lector la saca del tamaño.
    if version >= 7:
        for i in range(18):
            if m[n - 11 + (i % 3)][i // 3] is None:
                m[n - 11 + (i % 3)][i // 3] = 0
            if m[i // 3][n - 11 + (i % 3)] is None:
                m[i // 3][n - 11 + (i % 3)] = 0

    for i in range(9):                                   # formato
        if m[8][i] is None: m[8][i] = 0
        if m[i][8] is None: m[i][8] = 0
    for i in range(8):
        if m[8][n - 1 - i] is None: m[8][n - 1 - i] = 0
        if m[n - 1 - i][8] is None: m[n - 1 - i][8] = 0
    return m, n


def _bits_version(version):
    # 6 bits de versión + 12 de BCH (generador 0x1F25)
    resto = version << 12
    # división en GF(2): restar es XOR
    while resto.bit_length() >= 13:
        resto ^= 0x1F25 << (resto.bit_length() - 13)
    return (version << 12) | resto


def _poner_version(m, n, version):
    if version < 7:
        return
    bits = _bits_version(version)
    for i in range(18):
        b = (bits >> i) & 1
        m[n - 11 + (i % 3)][i // 3] = b
        m[i // 3][n - 11 + (i % 3)] = b


def _mascara(k, x, y):
    if k == 0: return (x + y) % 2 == 0
    if k == 1: return y % 2 == 0
    if k == 2: return x % 3 == 0
    if k == 3: return (x + y) % 3 == 0
    if k == 4: return (y // 2 + x // 3) % 2 == 0
    if k == 5: return (x * y) % 2 + (x * y) % 3 == 0
    if k == 6: return ((x * y) % 2 + (x * y) % 3) % 2 == 0
    return ((x + y) % 2 + (x * y) % 3) % 2 == 0


def _penalidad(m, n):
    p = 0
    # 1: cinco o más iguales seguidos
    for linea in list(m) + [list(c) for c in zip(*m)]:
        run, ant = 1, linea[0]
        for v in linea[1:]:
            if v == ant:
                run += 1
            else:
                if run >= 5: p += 3 + (run - 5)
                run, ant = 1, v
        if run >= 5: p += 3 + (run - 5)
    # 2: bloques de 2x2
    for y in range(n - 1):
        for x in range(n - 1):
            if m[y][x] == m[y][x+1] == m[y+1][x] == m[y+1][x+1]:
                p += 3
    # 3: 1011101 con cuatro claros de un lado
    pat1 = [1,0,1,1,1,0,1,0,0,0,0]
    pat2 = [0,0,0,0,1,0,1,1,1,0,1]
    for linea in list(m) + [list(c) for c in zip(*m)]:
        for i in range(n - 10):
            if linea[i:i+11] == pat1 or linea[i:i+11] == pat2:
                p += 40
    # 4: desbalance de oscuros
    oscuros = sum(sum(f) for f in m)
    porc = oscuros * 100.0 / (n * n)
    p += 10 * int(abs(porc - 50) / 5)
    return p


def matriz(texto):
    """Matriz del QR: lista de filas de 0 y 1."""
    version = _version_para(len(texto.encode("utf-8")))
    datos = _bytes_finales(texto, version)
    base, n = _armar(version)

    # zigzag desde abajo a la derecha
    bits = []
    for b in datos:
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)

    lleno = [[0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if base[y][x] is not None:
                lleno[y][x] = base[y][x]

    i = 0
    col = n - 1
    arriba = True
    while col > 0:
        if col == 6:                    # se saltea la columna de tiempo
            col -= 1
        filas = range(n - 1, -1, -1) if arriba else range(n)
        for y in filas:
            for x in (col, col - 1):
                if base[y][x] is None:
                    lleno[y][x] = bits[i] if i < len(bits) else 0
                    i += 1
        arriba = not arriba
        col -= 2

    # la máscara con menos penalidad
    mejor, mejor_p = None, None
    for k in range(8):
        m = [fila[:] for fila in lleno]
        for y in range(n):
            for x in range(n):
                if base[y][x] is None and _mascara(k, x, y):
                    m[y][x] ^= 1
        _poner_formato(m, n, k)
        _poner_version(m, n, version)
        p = _penalidad(m, n)
        if mejor_p is None or p < mejor_p:
            mejor, mejor_p = m, p
    return mejor


def _poner_formato(m, n, k):
    f = _FORMATO_M[k]
    bits = [(f >> i) & 1 for i in range(14, -1, -1)]     # el bit 14 primero
    pos = [(8,0),(8,1),(8,2),(8,3),(8,4),(8,5),(8,7),(8,8),
           (7,8),(5,8),(4,8),(3,8),(2,8),(1,8),(0,8)]
    for b, (y, x) in zip(bits, pos):
        m[y][x] = b
    # la otra copia, repartida en las otras dos esquinas
    for i in range(7):
        m[n - 1 - i][8] = bits[i]
    for i in range(8):
        m[8][n - 8 + i] = bits[7 + i]
    m[n - 8][8] = 1


def texto_consola(dato, borde=2):
    """El QR para leer desde la terminal."""
    # dos caracteres por módulo: con uno sale aplastado y el celular no lo lee
    m = matriz(dato)
    n = len(m)
    lleno, vacio = "██", "  "
    filas = []
    for _ in range(borde):
        filas.append(vacio * (n + 2 * borde))
    for y in range(n):
        f = vacio * borde
        for x in range(n):
            f += lleno if m[y][x] else vacio
        f += vacio * borde
        filas.append(f)
    for _ in range(borde):
        filas.append(vacio * (n + 2 * borde))
    return "\n".join(filas)


def svg(dato, lado_px=320, borde=2):
    m = matriz(dato)
    n = len(m)
    total = n + 2 * borde
    p = []
    for y in range(n):
        for x in range(n):
            if m[y][x]:
                p.append("M%d %dh1v1h-1z" % (x + borde, y + borde))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d" shape-rendering="crispEdges">'
            '<rect width="%d" height="%d" fill="#fff"/>'
            '<path d="%s" fill="#000"/></svg>'
            % (lado_px, lado_px, total, total, total, total, "".join(p)))
