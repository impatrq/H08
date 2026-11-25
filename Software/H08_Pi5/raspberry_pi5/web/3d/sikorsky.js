// Modelo exterior del Sikorsky S-55 / H-19A "H-08" (c/n 55-135), en metros.
// Ejes: +x a la nariz, +y arriba, +z a estribor; origen en el piso bajo el rotor.
// Cotas de Sikorsky Archives, Airvectors y Flugzeuginfo. Lo que no encontramos
// (ancho del fuselaje, batalla, ventanas) salió de las proporciones: COTAS.estimado.
(function (root) {
  "use strict";
  var COTAS = {
    // Guía técnica del H-08: X desde la punta del morro (0) hasta el pilón (12,85); mástil en X = 3,66.
    // Acá el origen está en el mástil: x = 3,66 - X.
    largoFuselaje: 12.85, nariz: 3.66, cola: -9.19,
    rotorDiam: 16.15, rotorY: 3.84, cuerdaPala: 0.42,
    rotorColaDiam: 2.64, rotorCola: [-9.02, 3.86, 0.26],          // a estribor de la cima del pilón
    trochaPrincipal: 3.35, ejePrincipal: -2.57, ejeNariz: 1.80,   // X = 6,23 m y X = 1,86 m
    estimado: { anchoFuselaje: 2.0, trochaNariz: 1.44, boomTop: 2.88 }
  };

  function construir(THREE, opciones) {
    opciones = opciones || {};
    var T = THREE, G = new T.Group(); G.name = "S-55 H-08";
    // detalle: cuánto más gruesa la grilla fina de las ventanas. Con 1,6 queda la
    // mitad de triángulos y la misma forma, porque los bordes se calculan cortando
    var DET = Math.max(1, opciones.detalle || 1), DET_FORRO = DET * 2.2;
    var D2R = Math.PI / 180;

    // materiales
    function mat(color, o) {
      o = o || {};
      return new T.MeshStandardMaterial({ color: new T.Color(color).convertSRGBToLinear(), metalness: o.m === undefined ? 0 : o.m,
        roughness: o.r === undefined ? 0.6 : o.r, side: o.side || T.FrontSide,
        transparent: !!o.t, opacity: o.op === undefined ? 1 : o.op });
    }
    var M = {
      aluminio: mat(0xb8c0c8, { m: 0.85, r: 0.36, side: T.DoubleSide }),
      naranja: mat(0xea581a, { m: 0.05, r: 0.28, side: T.DoubleSide }),
      amarillo: mat(0xf2c21a, { r: 0.5 }),
      negro: mat(0x16181a, { r: 0.7 }),
      goma: mat(0x1e2022, { r: 0.78 }),
      acero: mat(0x8d949b, { m: 0.9, r: 0.3 }),
      pala: mat(0x4b5563, { m: 0.6, r: 0.45, side: T.DoubleSide }),
      vidrio: mat(0xa9d2e6, { m: 0.1, r: 0.05, t: true, op: 0.28, side: T.DoubleSide }),
      interior: mat(0x2b2f2c, { r: 0.9, side: T.DoubleSide }),
      asiento: mat(0x4d5a3c, { r: 0.85 })
    };
    M.vidrio = new T.MeshPhysicalMaterial({ color: new T.Color(0xd6e8f0).convertSRGBToLinear(), metalness: 0, roughness: 0.03,
      transmission: 0.9, transparent: true, opacity: 1, side: T.FrontSide, depthWrite: false });
    M.burlete = mat(0x1c1f22, { r: 0.75, side: T.DoubleSide });          // goma del marco de las ventanas
    M.forro = mat(0x33383c, { r: 0.85, side: T.BackSide });               // interior, visto a través de los vidrios
    // chapas remachadas: uniones y filas de remaches
    function texChapas() {
      var c = document.createElement("canvas"); c.width = c.height = 512; var g = c.getContext("2d");
      g.fillStyle = "#ffffff"; g.fillRect(0, 0, 512, 512);
      for (var i = 0; i < 40; i++) {                                   // chapas de tono apenas distinto
        g.fillStyle = "rgba(60,70,80," + (0.006 + 0.012 * ((i * 37) % 10) / 10) + ")";
        g.fillRect(((i * 97) % 4) * 128, ((i * 53) % 4) * 128, 128, 128);
      }
      g.strokeStyle = "rgba(40,46,52,.38)"; g.lineWidth = 1.5;
      for (i = 0; i <= 4; i++) { g.beginPath(); g.moveTo(i * 128, 0); g.lineTo(i * 128, 512); g.stroke(); g.beginPath(); g.moveTo(0, i * 128); g.lineTo(512, i * 128); g.stroke(); }
      g.fillStyle = "rgba(40,46,52,.3)";
      for (i = 0; i < 4; i++) for (var k = 0; k < 512; k += 10) { g.fillRect(i * 128 + 6, k, 2, 2); g.fillRect(k, i * 128 + 6, 2, 2); g.fillRect(i * 128 + 120, k, 2, 2); g.fillRect(k, i * 128 + 120, 2, 2); }
      var t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 8; return t;
    }
    var CHAPAS = null;
    M.aluminioCola = M.aluminio; void CHAPAS;

    // perfil del fuselaje
    // x, yAbajo, yArriba, medio ancho, exponente de la sección (2 = elipse, >2 = más cuadrada)
    var DOMO = [
      [2.900, 1.250, 1.250, 0.004, 2.00], [2.897, 1.193, 1.337, 0.070, 2.00], [2.885, 1.124, 1.445, 0.155, 2.00], [2.860, 1.046, 1.566, 0.252, 2.00], [2.820, 0.964, 1.693, 0.353, 2.00],
      [2.760, 0.877, 1.827, 0.459, 2.00], [2.680, 0.793, 1.957, 0.563, 2.00], [2.580, 0.715, 2.079, 0.660, 2.00], [2.460, 0.645, 2.186, 0.746, 2.07],
      [2.320, 0.588, 2.276, 0.817, 2.30], [2.180, 0.549, 2.335, 0.864, 2.53], [2.040, 0.527, 2.369, 0.891, 2.77], [1.900, 0.520, 2.380, 0.900, 3.00]
    ];
    // trompa (puertas del motor) de x = 1,55 a la punta: roma, casi media esfera de frente,
    // con el lomo plano hasta bien adelante como en las fotos
    var NARIZ = COTAS.nariz;
    var EST = DOMO.map(function (e) {
      var t = Math.min(1, e[0] - 1.90), f = function (p) { return Math.pow(1 - Math.pow(t, p), 1 / p); };
      return [1.80 + t * (NARIZ - 1.80), 1.52 - 1.02 * f(3.2), 1.52 + 0.98 * f(3.4), Math.max(0.004, 0.9 * f(2.8)), 3.2 - 1.0 * t * t];
    }).concat([
      [1.20, 0.50, 2.50, 0.90, 3.2], [0.40, 0.50, 2.50, 0.90, 3.5], [-0.40, 0.50, 2.50, 0.90, 3.5], [-1.10, 0.50, 2.52, 0.89, 3.4],
      // atrás de la cabina el lomo sigue derecho hasta el tubo de cola; la panza sube a buscarlo
      [-1.60, 0.50, 2.60, 1.00, 3.3], [-2.40, 0.50, 2.70, 0.98, 3.1], [-3.28, 0.55, 2.78, 0.92, 2.8],
      [-4.20, 1.06, 2.84, 0.70, 2.4], [-5.20, 1.61, 2.87, 0.52, 2.1], [-6.11, 2.12, 2.88, 0.38, 2.0]
    ]);
    // ancho: 2,0 m de lado a lado en la cabina de carga y la trompa; hacia el tubo de cola vuelve a lo de antes
    EST.forEach(function (e) { if (e[0] > -1.5) e[3] *= 1.111; });
    function interp(x, col) {                    // Catmull-Rom sobre las estaciones (x decreciente)
      var n = EST.length, i = 0;
      if (x >= EST[0][0]) return EST[0][col];
      if (x <= EST[n - 1][0]) return EST[n - 1][col];
      while (i < n - 2 && EST[i + 1][0] > x) i++;
      var p0 = EST[Math.max(0, i - 1)], p1 = EST[i], p2 = EST[i + 1], p3 = EST[Math.min(n - 1, i + 2)];
      var t = (x - p1[0]) / (p2[0] - p1[0]);
      var m1 = (p2[col] - p0[col]) / (p2[0] - p0[0]) * (p2[0] - p1[0]);
      var m2 = (p3[col] - p1[col]) / (p3[0] - p1[0]) * (p2[0] - p1[0]);
      var t2 = t * t, t3 = t2 * t;
      return (2 * t3 - 3 * t2 + 1) * p1[col] + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2[col] + (t3 - t2) * m2;
    }
    function afinado() { return 1; }
    function seccion(x) { var yb = interp(x, 1), yt = interp(x, 2); return { yc: (yb + yt) / 2, H: (yt - yb) / 2, W: interp(x, 3), n: interp(x, 4) }; }
    // medio ancho del fuselaje a la altura y; y altura del techo en z
    function medioAncho(x, y) {
      var s = seccion(x), u = Math.abs((y - s.yc) / s.H); if (u >= 1) return 0;
      return s.W * Math.pow(1 - Math.pow(u, s.n), 1 / s.n) * afinado(x, y);
    }
    function techo(x, z) {
      var s = seccion(x), y = s.yc + s.H;
      for (var k = 0; k < 6; k++) {              // el afinado depende de y: unas vueltas alcanzan
        var w = s.W * afinado(x, y), u = Math.min(0.999, Math.abs(z) / w);
        y = s.yc + s.H * Math.pow(1 - Math.pow(u, s.n), 1 / s.n);
      }
      return y;
    }
    function puntoSeccion(x, a) {
      var s = seccion(x), c = Math.cos(a), sn = Math.sin(a), e = 2 / s.n;
      var y = s.yc + s.H * Math.sign(sn) * Math.pow(Math.abs(sn), e);
      var z = s.W * Math.sign(c) * Math.pow(Math.abs(c), e) * afinado(x, y);
      return [x, y, z];
    }
    // modo "todo", "abajo" (sin la cabina de pilotos) o "arriba" (solo esa parte)
    var Y_CABINA = 2.42, XC0 = 0.55, XC1 = 1.87;
    function anguloCorte(x) { var s = seccion(x), u = Math.max(0, Math.min(1, (Y_CABINA - s.yc) / s.H)); return Math.asin(Math.pow(u, s.n / 2)); }
    function fuselaje(x0, x1, material, nombre, modo, punta) {
      var NX = punta ? 44 : Math.max(4, Math.round((x0 - x1) * 22)), NA = modo === "arriba" ? 48 : 72, pos = [], uv = [], idx = [];
      for (var i = 0; i <= NX; i++) {
        var x = x0 + (x1 - x0) * (punta ? Math.pow(i / NX, 2) : i / NX), ac = modo && modo !== "todo" ? anguloCorte(x) : 0;
        for (var j = 0; j <= NA; j++) {
          var t = j / NA, a = modo === "arriba" ? ac + t * (Math.PI - 2 * ac) : modo === "abajo" ? Math.PI - ac + t * (Math.PI + 2 * ac) : t * 2 * Math.PI;
          var p = puntoSeccion(x, a); pos.push(p[0], p[1], p[2]);
          if (modo === "arriba") uv.push((x - x1) / (x0 - x1), t); else uv.push(x / 1.9, t * 3);
        }
      }
      for (i = 0; i < NX; i++) for (j = 0; j < NA; j++) {
        var q = i * (NA + 1) + j, b = q + NA + 1;
        idx.push(q, q + 1, b, q + 1, b + 1, b);
      }
      var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
      var m = new T.Mesh(g, material); m.name = nombre; m.castShadow = m.receiveShadow = true; return m;
    }
    var X_NARANJA = 1.93;                    // fin de las compuertas bivalvas (X = 1,73 m)
    function xArco(y) { var k = Math.max(0, Math.min(1, (y - 2.05) / 0.45)); return X_NARANJA + 0.30 * k * k * (3 - 2 * k); }                    // borde de las puertas del motor: justo delante del parabrisas, como en la foto

    // piezas simples
    function tubo(a, b, r, material, r2) {
      var va = new T.Vector3(a[0], a[1], a[2]), vb = new T.Vector3(b[0], b[1], b[2]), d = vb.clone().sub(va), L = d.length();
      var g = new T.CylinderGeometry(r2 === undefined ? r : r2, r, L, 20);
      var m = new T.Mesh(g, material); m.position.copy(va).addScaledVector(d, 0.5);
      m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); m.castShadow = true; return m;
    }
    function rueda(x, y, z, r, ancho) {
      var g = new T.Group();
      var c = new T.Mesh(new T.TorusGeometry(r - ancho / 2, ancho / 2, 14, 28), M.goma); g.add(c);
      var l = new T.Mesh(new T.CylinderGeometry(r - ancho * 0.8, r - ancho * 0.8, ancho * 0.7, 24), M.acero); l.rotation.x = Math.PI / 2; g.add(l);
      g.position.set(x, y, z); g.traverse(function (o) { o.castShadow = true; }); return g;
    }
    // placa plana con espesor a partir de un contorno en el plano x-y
    function placa(pts, esp, material) {
      var s = new T.Shape(); pts.forEach(function (p, i) { if (i) s.lineTo(p[0], p[1]); else s.moveTo(p[0], p[1]); });
      var g = new T.ExtrudeGeometry(s, { depth: esp, bevelEnabled: false }); g.translate(0, 0, -esp / 2);
      var m = new T.Mesh(g, material); m.castShadow = true; return m;
    }

    // cola (guía: botalón recto, H-19A de 1952)
    var BTOP = COTAS.estimado.boomTop, cola = new T.Group(); cola.name = "Cola";
    var XB0 = -6.09, XB1 = -8.30;                                                      // el tubo: del fuselaje a la raíz del pilón
    function rBoom(x) { return Math.max(0.15, 0.38 + (0.38 - 0.17) / (XB0 + 7.97) * (x - XB0)); }   // 0,38 m al salir, 0,17 m en el pilón
    function yBoom(x) { return BTOP - rBoom(x); }                                       // el borde de arriba queda horizontal
    function tramoBoom(xa, xb, material) {
      var m = tubo([xa, yBoom(xa), 0], [xb, yBoom(xb), 0], rBoom(xa), material, rBoom(xb));
      m.geometry = new T.CylinderGeometry(rBoom(xb), rBoom(xa), m.geometry.parameters.height, 40, 1, true); return m;
    }
    var XN0 = -7.07, XN1 = -8.03;                                                       // banda naranja (X = 10,73 a 11,69 m)
    cola.add(tramoBoom(XB0, XN0, M.aluminio), tramoBoom(XN0, XN1, M.naranja), tramoBoom(XN1, XB1, M.aluminio));
    var punta = new T.Mesh(new T.SphereGeometry(rBoom(XB1), 24, 12), M.aluminio); punta.position.set(XB1, yBoom(XB1), 0); punta.scale.set(0.6, 1, 1); cola.add(punta);
    // pilón inclinado ~44° hacia atrás, de perfil simétrico, con la caja del rotor de cola arriba
    (function () {
      var P = [[-7.93, BTOP - 0.30], [-8.35, BTOP - 0.36], [-9.19, BTOP + 0.86], [-9.17, BTOP + 1.06], [-8.86, BTOP + 1.10], [-8.06, BTOP + 0.02]];
      var sh = new T.Shape(); P.forEach(function (p, i) { if (i) sh.lineTo(p[0], p[1]); else sh.moveTo(p[0], p[1]); });
      var g = new T.ExtrudeGeometry(sh, { depth: 0.12, bevelEnabled: true, bevelThickness: 0.035, bevelSize: 0.035, bevelSegments: 3 }); g.translate(0, 0, -0.06);
      var m = new T.Mesh(g, M.aluminio); m.name = "Pilón de cola"; m.castShadow = true; cola.add(m);
      var caja = new T.Mesh(new T.SphereGeometry(0.16, 20, 12), M.aluminio); caja.position.set(-9.02, COTAS.rotorCola[1], 0.05); caja.scale.set(1.3, 0.9, 1); cola.add(caja);
    })();
    // estabilizadores trapezoidales en V invertida (-16°), con el borde de ataque aflechado, en la base del pilón
    [-1, 1].forEach(function (s) {
      var sh = new T.Shape(); sh.moveTo(-7.98, 0); sh.lineTo(-8.62, 0); sh.lineTo(-8.66, s * 0.95); sh.lineTo(-8.30, s * 0.95); sh.lineTo(-7.98, 0);
      var g = new T.ExtrudeGeometry(sh, { depth: 0.04, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 2 });
      g.rotateX(Math.PI / 2);
      var m = new T.Mesh(g, M.aluminio); m.name = "Estabilizador (V invertida)"; m.castShadow = true;
      m.position.y = BTOP - 0.30; m.rotation.x = s * 16 * D2R; cola.add(m);                     // diedro negativo de 16°
    });
    // patín de cola: aleta ventral corta y un tubo curvado hacia atrás con la punta redondeada
    cola.add(placa([[-8.05, BTOP - 0.32], [-8.45, BTOP - 0.34], [-8.40, BTOP - 0.62], [-8.20, BTOP - 0.62]], 0.05, M.aluminio));
    (function () {
      var c = new T.CatmullRomCurve3([new T.Vector3(-8.30, BTOP - 0.60, 0), new T.Vector3(-8.55, BTOP - 0.85, 0), new T.Vector3(-8.90, BTOP - 0.98, 0), new T.Vector3(-9.12, BTOP - 0.96, 0)]);
      cola.add(new T.Mesh(new T.TubeGeometry(c, 30, 0.022, 8, false), M.acero));
      var bola = new T.Mesh(new T.SphereGeometry(0.04, 12, 8), M.acero); bola.position.copy(c.getPoint(1)); cola.add(bola);
    })();
    // rotor de cola: eje horizontal a estribor de la cima del pilón, buje a la vista y dos palas angostas
    var RC = COTAS.rotorCola;
    cola.add(tubo([RC[0], RC[1], 0.05], [RC[0], RC[1], RC[2] + 0.04], 0.06, M.acero));
    var rotorCola = new T.Group(); rotorCola.name = "Rotor de cola"; rotorCola.position.set(RC[0], RC[1], RC[2]);
    var cubo = new T.Mesh(new T.CylinderGeometry(0.07, 0.07, 0.12, 20), M.negro); cubo.rotation.x = Math.PI / 2; rotorCola.add(cubo);
    [0, 1].forEach(function (k) {
      var L = COTAS.rotorColaDiam / 2, p = new T.Mesh(new T.BoxGeometry(0.15, L - 0.08, 0.025), M.pala);
      p.position.y = (L + 0.08) / 2; var b = new T.Group(); b.add(p);
      var pt = new T.Mesh(new T.BoxGeometry(0.152, 0.14, 0.027), M.amarillo); pt.position.y = L - 0.07; b.add(pt);
      b.rotation.z = k * Math.PI; rotorCola.add(b);
    });
    rotorCola.rotation.z = 35 * D2R; cola.add(rotorCola);
    G.add(cola);

    // rotor principal
    var RY = COTAS.rotorY, CALAJE = 3 * D2R, rotor = new T.Group(); rotor.name = "Rotor principal";
    var eje = new T.Group(); eje.name = "Mástil (3° hacia adelante)"; eje.position.set((RY - 3.40) * Math.sin(CALAJE), RY, 0); eje.rotation.z = -CALAJE; eje.add(rotor);
    G.add(tubo([0, 3.36, 0], [(RY - 0.05 - 3.40) * Math.sin(CALAJE), RY - 0.05, 0], 0.075, M.acero));
    // carenado de la transmisión: un domo largo de bordes redondeados sobre el techo de la cabina
    var carenado = new T.Mesh(new T.SphereGeometry(1, 40, 16, 0, Math.PI * 2, 0, Math.PI / 2), M.aluminio);
    carenado.scale.set(0.80, 0.44, 0.46); carenado.position.set(0.0, 3.23, 0); carenado.name = "Carenado del rotor"; carenado.castShadow = true; G.add(carenado);
    G.add(tubo([0, 3.58, 0], [0.006, 3.71, 0], 0.17, M.aluminio, 0.12));
    var luz = new T.Mesh(new T.SphereGeometry(0.045, 16, 10), new T.MeshStandardMaterial({ color: 0xd8160c, emissive: 0x7a0500, roughness: 0.25 }));
    luz.position.set(0.72, 3.53, 0); luz.name = "Luz anticolisión"; G.add(luz);
    G.add(tubo([-0.80, 3.46, 0], [-1.50, 4.24, 0], 0.008, M.negro, 0.004));                      // antena látigo, inclinada hacia atrás
    var cabeza = new T.Mesh(new T.CylinderGeometry(0.20, 0.24, 0.17, 28), M.negro); rotor.add(cabeza);
    var plato = new T.Mesh(new T.CylinderGeometry(0.27, 0.27, 0.05, 32), M.acero); plato.position.y = -0.16; rotor.add(plato);      // plato cíclico
    [0, 1, 2].forEach(function (k) {                                                                       // bieletas de paso
      var a = k * 120 * D2R + 80 * D2R; rotor.add(tubo([Math.cos(a) * 0.24, -0.14, Math.sin(a) * 0.24], [Math.cos(a) * 0.30, 0.02, Math.sin(a) * 0.30], 0.012, M.acero));
      var b = k * 120 * D2R + 60 * D2R; rotor.add(tubo([Math.cos(b) * 0.22, 0.02, Math.sin(b) * 0.22], [Math.cos(b + 0.45) * 0.55, 0.0, Math.sin(b + 0.45) * 0.55], 0.03, M.negro));   // amortiguadores
    });
    var tapa = new T.Mesh(new T.SphereGeometry(0.15, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), M.acero); tapa.position.y = 0.08; rotor.add(tapa);
    var R = COTAS.rotorDiam / 2;
    [0, 1, 2].forEach(function (k) {
      var b = new T.Group(), r0 = 0.75, L = R - r0, seg = 28;
      var g = new T.BoxGeometry(L, 0.045, COTAS.cuerdaPala, seg, 1, 2), p = g.attributes.position;
      for (var i = 0; i < p.count; i++) {
        var x = p.getX(i) + L / 2 + r0, z = p.getZ(i), y = p.getY(i);
        if (Math.abs(z) > 0.2) y *= 0.25;                                          // bordes finos: perfil de pala
        p.setXYZ(i, x, y - 0.42 * Math.pow(x / R, 2), z + 0.06);                   // en reposo las palas cuelgan
      }
      g.computeVertexNormals(); var pala = new T.Mesh(g, M.pala); pala.castShadow = true; b.add(pala);
      b.add(tubo([0.18, 0, 0], [r0 + 0.1, -0.42 * Math.pow((r0 + 0.1) / R, 2), 0.03], 0.05, M.acero));
      var punta = new T.Mesh(new T.BoxGeometry(0.16, 0.05, COTAS.cuerdaPala + 0.004), M.amarillo); punta.position.set(R - 0.08, -0.42, 0.06); b.add(punta);
      b.rotation.y = k * 120 * D2R + 20 * D2R; rotor.add(b);
    });
    G.add(eje);

    // tren de aterrizaje cuadriciclo (guía)
    var tren = new T.Group(); tren.name = "Tren de aterrizaje";
    var XP = COTAS.ejePrincipal, ZP = COTAS.trochaPrincipal / 2, RP = 0.31, XN = COTAS.ejeNariz, ZN = COTAS.estimado.trochaNariz / 2, RN = 0.23;
    [-1, 1].forEach(function (s) {
      // principales: puntal oleoneumático largo anclado a media altura del costado y trapecio tubular a la quilla
      tren.add(rueda(XP, RP, s * ZP, RP, 0.20));
      var eje = [XP, RP, s * (ZP - 0.14)];
      tren.add(tubo(eje, [XP, RP, s * (ZP + 0.02)], 0.03, M.acero));
      var arriba = [XP + 0.12, 1.45, s * (medioAncho(XP + 0.12, 1.45) - 0.02)];
      tren.add(tubo(eje, arriba, 0.045, M.acero, 0.06));
      var ex = arriba[0] - eje[0], ey = arriba[1] - eje[1], ez = arriba[2] - eje[2];
      tren.add(tubo([eje[0] + ex * 0.55, eje[1] + ey * 0.55, eje[2] + ez * 0.55], arriba, 0.065, M.aluminio));          // cilindro del amortiguador
      tren.add(tubo(eje, [XP + 0.55, 0.56, s * 0.32], 0.032, M.aluminio));                                                // trapecio a la quilla
      tren.add(tubo(eje, [XP - 0.55, 0.62, s * 0.32], 0.032, M.aluminio));
      // delanteras: horquilla vertical con amortiguador telescópico y brazos de arrastre triangulados
      tren.add(rueda(XN, RN, s * ZN, RN, 0.15));
      var cubo = [XN, RN, s * (ZN - 0.10)];
      tren.add(tubo(cubo, [XN, RN, s * ZN], 0.025, M.acero));
      tren.add(tubo(cubo, [XN, 0.50, s * (ZN - 0.10)], 0.035, M.acero));
      tren.add(tubo([XN, 0.46, s * (ZN - 0.10)], [XN, interp(XN, 1) + 0.05, s * (ZN - 0.10)], 0.05, M.aluminio));
      tren.add(tubo(cubo, [XN - 0.55, interp(XN - 0.55, 1) + 0.04, s * 0.40], 0.022, M.aluminio));
      tren.add(tubo(cubo, [XN + 0.45, interp(XN + 0.45, 1) + 0.04, s * 0.40], 0.022, M.aluminio));
    });
    G.add(tren);

    // parches sobre el fuselaje (vidrios, puerta, marcas)
    function lienzo(w, h, dibujar) {
      var c = document.createElement("canvas"); c.width = w; c.height = h; dibujar(c.getContext("2d"), w, h);
      var t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.anisotropy = 8; return t;
    }
    function matParche(tex, o) {
      o = o || {};
      return new T.MeshStandardMaterial({ map: tex, transparent: true, alphaTest: 0.35, side: T.DoubleSide,
        metalness: o.m || 0, roughness: o.r === undefined ? 0.5 : o.r, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    }
    // sobre el costado: rectángulo (x0..x1, y0..y1) pegado a la superficie. lado = +1 derecha, -1 izquierda
    function parcheLado(x0, x1, y0, y1, lado, material, ancho, nombre) {
      ancho = ancho || medioAncho;
      var NX = 16, NY = 10, pos = [], uv = [], idx = [];
      for (var j = 0; j <= NY; j++) for (var i = 0; i <= NX; i++) {
        var x = x0 + (x1 - x0) * i / NX, y = y0 + (y1 - y0) * j / NY;
        pos.push(x, y, lado * (ancho(x, y) + 0.006));
        // el texto se lee de izquierda a derecha mirando cada costado desde afuera
        uv.push(lado > 0 ? i / NX : 1 - i / NX, j / NY);
      }
      for (j = 0; j < NY; j++) for (i = 0; i < NX; i++) { var a = j * (NX + 1) + i; idx.push(a, a + 1, a + NX + 1, a + 1, a + NX + 2, a + NX + 1); }
      var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
      var m = new T.Mesh(g, material); m.name = nombre || "Marca"; return m;
    }
    // sobre el techo o el frente: rectángulo (x0..x1, z0..z1)
    function parcheTecho(x0, x1, z0, z1, material, nombre) {
      var NX = 12, NZ = 16, pos = [], uv = [], idx = [];
      for (var j = 0; j <= NX; j++) for (var i = 0; i <= NZ; i++) {
        var x = x0 + (x1 - x0) * j / NX, z = z0 + (z1 - z0) * i / NZ;
        pos.push(x + 0.004, techo(x, z) + 0.006, z); uv.push(i / NZ, j / NX);
      }
      for (j = 0; j < NX; j++) for (i = 0; i < NZ; i++) { var a = j * (NZ + 1) + i; idx.push(a, a + NZ + 1, a + 1, a + 1, a + NZ + 1, a + NZ + 2); }
      var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
      var m = new T.Mesh(g, material); m.name = nombre || "Vidrio"; return m;
    }
    function rr(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
    var vidrios = new T.Group(); vidrios.name = "Vidrios";
    var mMallaChica = matParche(lienzo(128, 96, function (g, w, h) {
      rr(g, 4, 4, w - 8, h - 8, 14); g.fillStyle = "#1a1c1e"; g.fill(); g.fillStyle = "#565b60";
      for (var i = 0; i < 4; i++) for (var j = 0; j < 3; j++) { g.beginPath(); g.arc(22 + i * 28, 22 + j * 26, 7, 0, 7); g.fill(); }
      rr(g, 4, 4, w - 8, h - 8, 14); g.lineWidth = 6; g.strokeStyle = "#9aa0a5"; g.stroke();
    }));
    // cabina de pilotos: una caja aparte, más angosta, apoyada sobre la cubierta (queda un escalón a cada lado)
    // Perfil del techo medido sobre la foto de costado: sube apenas hacia adelante hasta 3,47 m, el
    // parabrisas baja hasta la trompa y atrás cae redondeado hasta el lomo.
    var PT = [[2.30, 2.30], [2.10, 2.46], [1.95, 2.60], [1.25, 3.40], [1.08, 3.45], [0.40, 3.46], [-0.40, 3.41], [-0.84, 3.32], [-1.10, 3.19], [-1.36, 3.00], [-1.58, 2.92], [-2.60, 2.91], [-4.00, 2.90], [-5.40, 2.895], [-6.00, 2.89], [-6.30, 2.86]];
    function curva(P, x) {                       // Catmull-Rom sobre puntos con x decreciente
      var n = P.length, i = 0; if (x >= P[0][0]) return P[0][1]; if (x <= P[n - 1][0]) return P[n - 1][1];
      while (i < n - 2 && P[i + 1][0] > x) i++;
      var p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(n - 1, i + 2)], t = (x - p1[0]) / (p2[0] - p1[0]);
      var m1 = (p2[1] - p0[1]) / (p2[0] - p0[0]) * (p2[0] - p1[0]), m2 = (p3[1] - p1[1]) / (p3[0] - p1[0]) * (p2[0] - p1[0]), t2 = t * t, t3 = t2 * t;
      return (2 * t3 - 3 * t2 + 1) * p1[1] + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2[1] + (t3 - t2) * m2;
    }
    // XF: donde el techo de la cabina llega a la trompa. Hasta ahí llega la cabina.
    var XF = (function () { var lo = 1.7, hi = 2.44; for (var k = 0; k < 40; k++) { var m = (lo + hi) / 2; if (curva(PT, m) > techo(m, 0)) lo = m; else hi = m; } return lo; })();
    // XR: lo mismo atrás, donde la caída de la cabina llega al lomo
    var XR = (function () { var lo = -4.0, hi = -6.28; for (var k = 0; k < 40; k++) { var m = (lo + hi) / 2; if (curva(PT, m) > techo(m, 0)) lo = m; else hi = m; } return lo; })();
    var CX0 = XR - 0.05, CX1 = XF + 0.05;
    function cabTecho(x) { return curva(PT, x); }
    // Sobre la trompa la cabina se angosta hasta caber en ella: el parabrisas
    // termina en punta contra las puertas del motor, sin aletas que asomen.
    function cabAncho(x) {
      // atrás de la última ventana la cabina se mete para adentro y sigue como un lomo angosto hasta la cola
      var k = Math.max(0, Math.min(1, (x - 1.2) / 0.9)), a = Math.max(0, Math.min(1, (-0.80 - x) / 0.50));
      var w = 0.80 - 0.07 * k * k * (3 - 2 * k) - 0.26 * a * a * (3 - 2 * a);
      if (x < -1.30) w = Math.min(w, 0.54 + (x + 1.30) * (0.54 - 0.19) / (6.10 - 1.30));
      return w;
    }
    function cabPiso(x) { var q = seccion(x); return Math.max(q.yc + q.H * 0.35, Math.min(2.30, techo(x, cabAncho(x)) - 0.05, cabTecho(x) - 0.02)); }
    // Sección de la cabina en x: paredes rectas, esquinas redondeadas y techo plano.
    var cacheCab = {};
    function seccionCab(x) {
      var c = cacheCab[x]; if (c) return c;
      // adelante (sobre la trompa) y atrás (sobre el lomo) el techo copia la curva de lo que tiene abajo
      var k = Math.max(0, Math.min(1, (x - 1.80) / 0.32), Math.min(1, (XR + 0.42 - x) / 0.36)), bl = k * k * (3 - 2 * k), lomo = bl > 0 ? techo(x, 0) : 0;
      // hacia la trompa la esquina se va afilando: así el borde llega entero hasta el encuentro
      var W = cabAncho(x), yt = cabTecho(x), yb = cabPiso(x), rc = Math.max(0.012, Math.min(0.25 * (1 - 0.9 * bl), (yt - yb) * 0.9, W * 0.45));
      c = { x: x, W: W, yt: yt, yb: yb, rc: rc, bl: bl, lomo: lomo, La: Math.PI / 2 * rc, Lt: 2 * (W - rc) };
      c.d1 = caida(c, W - rc); c.L1 = Math.max(0, yt - c.d1 - rc - yb);
      return (cacheCab[x] = c);
    }
    // cuánto baja el techo de la cabina a la distancia z del medio (0 donde el techo es plano)
    function caida(c, z) {
      var abombado = 0.035 * Math.pow(Math.min(1, Math.abs(z) / Math.max(0.05, c.W - c.rc)), 2) * (1 - c.bl);   // techo apenas abombado
      return (c.bl > 0 ? c.bl * (c.lomo - techo(c.x, Math.abs(z))) : 0) + abombado;
    }
    // v: 0-1 pared derecha, 1-2 esquina, 2-3 techo (de derecha a izquierda), 3-4 esquina, 4-5 pared izquierda
    function puntoCabV(c, v) {
      var a, z, yc = c.yt - c.d1 - c.rc;
      if (v <= 1) return [c.x, c.yb + v * c.L1, c.W];
      if (v <= 2) { a = (v - 1) * Math.PI / 2; return [c.x, yc + Math.sin(a) * c.rc, c.W - c.rc + Math.cos(a) * c.rc]; }
      if (v <= 3) { z = (c.W - c.rc) * (1 - 2 * (v - 2)); return [c.x, c.yt - caida(c, z), z]; }
      if (v <= 4) { a = (v - 3) * Math.PI / 2; return [c.x, yc + Math.cos(a) * c.rc, -(c.W - c.rc) - Math.sin(a) * c.rc]; }
      return [c.x, yc - (v - 4) * c.L1, -c.W];
    }
    // ventanas en medidas reales
    function dRect(px, py, x0, x1, y0, y1, r) {   // distancia con signo a un rectángulo de puntas redondeadas
      var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, hx = (x1 - x0) / 2 - r, hy = (y1 - y0) / 2 - r;
      var qx = Math.abs(px - cx) - hx, qy = Math.abs(py - cy) - hy;
      return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
    }
    // Malla recortada: parte la superficie P(u,v) por niveles de f(u,v,p) y da una geometría por región.
    // Cortamos cada celda donde f cruza el nivel, así los bordes quedan nítidos de cerca y de lejos
    // y cada región lleva su material (vidrio, burlete, chapa) sin texturas con huecos.
    function recortar(us, vs, P, f, niveles, centro, ciclico) {
      var nu = us.length, nv = vs.length, i, j, k, Pg = [], Fg = [], Ng = [];
      for (i = 0; i < nu; i++) { Pg.push([]); Fg.push([]); for (j = 0; j < nv; j++) { var p = P(us[i], vs[j]); Pg[i].push(p); Fg[i].push(f(us[i], vs[j], p)); } }
      for (i = 0; i < nu; i++) {
        Ng.push([]);
        for (j = 0; j < nv; j++) {
          var a = Pg[Math.min(nu - 1, i + 1)][j], b = Pg[Math.max(0, i - 1)][j];
          var c = Pg[i][j + 1 < nv ? j + 1 : (ciclico ? 1 : j)], d = Pg[i][j > 0 ? j - 1 : (ciclico ? nv - 2 : 0)];
          var ux = a[0] - b[0], uy = a[1] - b[1], uz = a[2] - b[2], vx = c[0] - d[0], vy = c[1] - d[1], vz = c[2] - d[2];
          var nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, l = Math.hypot(nx, ny, nz), q = Pg[i][j], o = centro(q);
          if (l < 1e-10) { nx = q[0] - o[0]; ny = q[1] - o[1]; nz = q[2] - o[2]; l = Math.hypot(nx, ny, nz) || 1; }
          nx /= l; ny /= l; nz /= l;
          if (nx * (q[0] - o[0]) + ny * (q[1] - o[1]) + nz * (q[2] - o[2]) < 0) { nx = -nx; ny = -ny; nz = -nz; }
          Ng[i].push([nx, ny, nz]);
        }
      }
      var R = [];
      for (k = 0; k <= niveles.length; k++) R.push({ pos: [], nor: [], idx: [], mapa: new Int32Array(nu * nv).fill(-1) });
      function emitir(reg, poly, i, j) {
        if (poly.length < 3) return;
        var ids = [], pts = [], nrs = [];
        poly.forEach(function (w) {
          var esq = (w.a === 0 || w.a === 1) && (w.b === 0 || w.b === 1), p, n, id;
          if (esq) {
            var gi = i + w.a, gj = j + w.b, llave = gi * nv + gj; p = Pg[gi][gj]; n = Ng[gi][gj]; id = reg.mapa[llave];
            if (id < 0) { id = reg.mapa[llave] = reg.pos.length / 3; reg.pos.push(p[0], p[1], p[2]); reg.nor.push(n[0], n[1], n[2]); }
          } else {
            p = P(us[i] + w.a * (us[i + 1] - us[i]), vs[j] + w.b * (vs[j + 1] - vs[j]));
            var A = w.a, B = w.b, n00 = Ng[i][j], n10 = Ng[i + 1][j], n11 = Ng[i + 1][j + 1], n01 = Ng[i][j + 1];
            n = [0, 1, 2].map(function (e) { return n00[e] * (1 - A) * (1 - B) + n10[e] * A * (1 - B) + n11[e] * A * B + n01[e] * (1 - A) * B; });
            var ln = Math.hypot(n[0], n[1], n[2]) || 1; n = [n[0] / ln, n[1] / ln, n[2] / ln];
            id = reg.pos.length / 3; reg.pos.push(p[0], p[1], p[2]); reg.nor.push(n[0], n[1], n[2]);
          }
          ids.push(id); pts.push(p); nrs.push(n);
        });
        for (var t = 1; t < ids.length - 1; t++) {
          var p0 = pts[0], p1 = pts[t], p2 = pts[t + 1];
          var ex = p1[0] - p0[0], ey = p1[1] - p0[1], ez = p1[2] - p0[2], gx = p2[0] - p0[0], gy = p2[1] - p0[1], gz = p2[2] - p0[2];
          var tx = ey * gz - ez * gy, ty = ez * gx - ex * gz, tz = ex * gy - ey * gx;
          if (tx * tx + ty * ty + tz * tz < 1e-20) continue;
          if (tx * nrs[0][0] + ty * nrs[0][1] + tz * nrs[0][2] >= 0) reg.idx.push(ids[0], ids[t], ids[t + 1]); else reg.idx.push(ids[0], ids[t + 1], ids[t]);
        }
      }
      function cortar(poly, L) {
        var ab = [], ar = [];
        for (var m = 0; m < poly.length; m++) {
          var A = poly[m], B = poly[(m + 1) % poly.length], ia = A.f < L, ib = B.f < L;
          (ia ? ab : ar).push(A);
          if (ia !== ib) { var t = (L - A.f) / (B.f - A.f), X = { a: A.a + (B.a - A.a) * t, b: A.b + (B.b - A.b) * t, f: L }; ab.push(X); ar.push(X); }
        }
        return [ab, ar];
      }
      var ult = niveles.length;
      for (i = 0; i < nu - 1; i++) for (j = 0; j < nv - 1; j++) {
        var poly = [{ a: 0, b: 0, f: Fg[i][j] }, { a: 1, b: 0, f: Fg[i + 1][j] }, { a: 1, b: 1, f: Fg[i + 1][j + 1] }, { a: 0, b: 1, f: Fg[i][j + 1] }];
        if (Math.min(poly[0].f, poly[1].f, poly[2].f, poly[3].f) >= niveles[ult - 1]) { emitir(R[ult], poly, i, j); continue; }
        for (k = 0; k < ult && poly.length; k++) { var cc = cortar(poly, niveles[k]); emitir(R[k], cc[0], i, j); poly = cc[1]; }
        emitir(R[ult], poly, i, j);
      }
      return R.map(function (r) {
        var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(r.pos, 3));
        g.setAttribute("normal", new T.Float32BufferAttribute(r.nor, 3)); g.setIndex(r.idx); return g;
      });
    }
    function tramo(a, b, paso, f) {
      if (paso < 0.03) paso *= f || DET;          // sólo el enrejado fino; las curvas grandes quedan igual
      var n = Math.max(1, Math.round(Math.abs(b - a) / paso)), l = []; for (var i = 1; i <= n; i++) l.push(a + (b - a) * i / n); return l;
    }
    function malla(g, material, nombre, sombra) { var m = new T.Mesh(g, material); m.name = nombre; m.castShadow = !!sombra; m.receiveShadow = !!sombra; return m; }
    var BURLETE = 0.018;

    // Fuselaje: trompa naranja y cuerpo gris, con las ventanas de carga caladas.
    // v: 0-1 costado derecho, 1-2 lomo, 2-3 costado izquierdo, 3-4 panza
    function puntoCasco(x, v) {
      var s = seccion(x), a1 = Math.asin(Math.pow(0.6, s.n / 2)), u;
      if (v <= 1) { u = -0.6 + 1.2 * v; return [x, s.yc + s.H * u, s.W * Math.pow(1 - Math.pow(Math.abs(u), s.n), 1 / s.n)]; }
      if (v <= 2) return puntoSeccion(x, a1 + (v - 1) * (Math.PI - 2 * a1));
      if (v <= 3) { u = 0.6 - 1.2 * (v - 2); return [x, s.yc + s.H * u, -s.W * Math.pow(1 - Math.pow(Math.abs(u), s.n), 1 / s.n)]; }
      return puntoSeccion(x, Math.PI + a1 + (v - 3) * (Math.PI - 2 * a1));
    }
    // dos ventanas por lado, iguales, más anchas que altas
    var VCARGA = [[-0.33, 0.17, 1.55, 2.05], [-1.37, -0.87, 1.55, 2.05]];      // las dos de la puerta corrediza (y las dos de babor)
    var VCARGA_IZQ = [[0.64, 1.06, 1.55, 1.98], [-0.08, 0.42, 1.55, 2.05], [-1.12, -0.62, 1.55, 2.05]];   // babor: la de la puerta de acceso y dos más
    function distCasco(x, v, p) {
      if (!(v <= 1 || (v >= 2 && v <= 3))) return 9;
      var d = 9; (v <= 1 ? VCARGA : VCARGA_IZQ).forEach(function (w) { d = Math.min(d, dRect(x, p[1], w[0], w[1], w[2], w[3], 0.075)); }); return d;
    }
    function vsDe(f) {
      // fino sólo en la franja de las ventanas (u de -0,14 a 0,50 del alto)
      var lado = [0].concat(tramo(0, 0.383, 0.065), tramo(0.383, 0.917, 0.0105, f), tramo(0.917, 1, 0.05));
      var l = lado.slice();
      tramo(1, 2, 1 / 24).forEach(function (v) { l.push(v); });
      lado.slice(1).map(function (v) { return 3 - v; }).reverse().concat([3]).forEach(function (v) { if (v > 2) l.push(v); });
      tramo(3, 4, 1 / 24).forEach(function (v) { l.push(v); });
      return l;
    }
    var vsCasco = vsDe(DET);
    function centroCasco(p) { var s = seccion(p[0]); return [p[0], s.yc, 0]; }
    (function () {
      var xs = [], i; for (i = 0; i <= 80; i++) xs.push(NARIZ - 0.0005 + (X_NARANJA - NARIZ + 0.0005) * Math.pow(i / 80, 1.6));
      var gt = recortar(xs, vsCasco, puntoCasco, function (x, v, p) { return xArco(p[1]) - x; }, [0], centroCasco, true);
      G.add(malla(gt[0], M.naranja, "Trompa (puertas del motor)", true), malla(gt[1], M.aluminio, "Fuselaje", true));
      xs = [X_NARANJA].concat(tramo(X_NARANJA, -0.06, 0.045), tramo(-0.06, -1.74, 0.012), tramo(-1.74, -6.11, 0.045));
      var g = recortar(xs, vsCasco, puntoCasco, distCasco, [0, BURLETE], centroCasco, true);
      G.add(malla(g[2], M.aluminio, "Fuselaje", true));
      vidrios.add(malla(g[0], M.vidrio, "Ventanas de la cabina de carga"), malla(g[1], M.burlete, "Marcos de las ventanas de carga"));
      // forro interior de la cabina de carga: lo que se ve a través de los vidrios
      var xf = [0.75].concat(tramo(0.75, -0.06, 0.045), tramo(-0.06, -1.74, 0.012, DET_FORRO), tramo(-1.74, -2.05, 0.045));
      var forro = malla(recortar(xf, vsDe(DET_FORRO), puntoCasco, distCasco, [0.035], centroCasco, true)[1], M.forro, "Interior de la cabina de carga");
      forro.scale.set(1, 0.965, 0.965); forro.position.y = 1.5 * (1 - 0.965); G.add(forro);
      [0.75, -2.05].forEach(function (x) {
        var pos = [], idx = [], s = seccion(x); pos.push(x + (x > -1 ? 0.3 : -0.3), s.yc, 0);
        for (var j = 0; j <= 48; j++) { var p = puntoSeccion(x, j / 48 * 2 * Math.PI); pos.push(p[0], p[1], p[2]); if (j) idx.push(0, j, j + 1); }
        var gt = new T.BufferGeometry(); gt.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); gt.setIndex(idx); gt.computeVertexNormals();
        var tapa = malla(gt, mat(0x3a3f44, { r: 0.9, side: T.DoubleSide }), "Interior de la cabina de carga");
        tapa.scale.copy(forro.scale); tapa.position.copy(forro.position); G.add(tapa);
      });
    })();

    // Cabina de pilotos: casi toda vidrio, con parantes finos. Medidas sacadas de la foto.
    function dPoli(px, py, P) {                  // distancia con signo a un polígono
      var d = Infinity, sg = 1, n = P.length;
      for (var i = 0, j = n - 1; i < n; j = i, i++) {
        var ex = P[j][0] - P[i][0], ey = P[j][1] - P[i][1], wx = px - P[i][0], wy = py - P[i][1];
        var t = Math.max(0, Math.min(1, (wx * ex + wy * ey) / (ex * ex + ey * ey))), bx = wx - ex * t, by = wy - ey * t;
        d = Math.min(d, bx * bx + by * by);
        var c1 = py >= P[i][1], c2 = py < P[j][1], c3 = ex * wy > ey * wx;
        if ((c1 && c2 && c3) || (!c1 && !c2 && !c3)) sg = -sg;
      }
      return sg * Math.sqrt(d);
    }
    // ventana = polígono convexo (en sentido antihorario) con las puntas redondeadas con radio r
    function ventana(P, r) {
      var n = P.length, L = P.map(function (a, i) {
        var b = P[(i + 1) % n], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy);
        return { x: a[0] - dy / l * r, y: a[1] + dx / l * r, dx: dx, dy: dy };       // el lado, corrido r hacia adentro
      });
      var Q = L.map(function (b, i) {
        var a = L[(i + n - 1) % n], den = a.dx * b.dy - a.dy * b.dx, t = ((b.x - a.x) * b.dy - (b.y - a.y) * b.dx) / den;
        return [a.x + a.dx * t, a.y + a.dy * t];
      });
      return function (x, y) { return dPoli(x, y, Q) - r; };
    }
    function arribaV(x) { return cabTecho(x) - 0.25; }        // borde de arriba: paralelo al techo, debajo de la vuelta
    var VLADO = [
      // atrás, con la esquina de arriba bien redondeada
      ventana([[-0.62, 2.66], [0.06, 2.66], [0.06, 3.16], [-0.30, 3.16]], 0.06),                                // fija, trapezoidal
      // adelante, la grande: baja más y el borde de adelante se inclina hacia atrás arriba
      ventana([[0.22, 2.52], [1.30, 2.52], [1.06, 3.16], [0.22, 3.16]], 0.07)                                  // corrediza
    ];
    var PUERTA_PILOTO = [[0.22, 2.52], [1.30, 2.52], [1.06, 3.16], [0.22, 3.16]];
    // Parabrisas envolvente: de cada lado un paño de frente y uno de costado que siguen la vuelta de la
    // esquina, separados sólo por el parante de la esquina (el techo es todo chapa: el H-08 no tiene vidrios arriba).
    var PE = { x0: 1.30, x1: 2.02, xc: 1.06, xe: 1.26, incl: 0.48, poste: 0.024, parante: 0.022, abajo: 2.62, t0: 0.80, t1: 1.155 };
    function distCab(x, v) {
      var c = seccionCab(x), s;                       // s: distancia sobre la chapa desde el medio del techo
      if (v <= 1) s = c.Lt / 2 + c.La + (1 - v) * c.L1;
      else if (v <= 2) s = c.Lt / 2 + c.La * (2 - v);
      else if (v <= 3) s = Math.abs((c.W - c.rc) * (1 - 2 * (v - 2)));
      else if (v <= 4) s = c.Lt / 2 + c.La * (v - 3);
      else s = c.Lt / 2 + c.La + (v - 4) * c.L1;
      var yv = c.yt - c.d1 - c.rc + (c.Lt / 2 + c.La - s), d = 9;      // altura "desenrollada": en la pared es la altura real
      VLADO.forEach(function (w) { d = Math.min(d, w(x, yv)); });
      if (x > PE.t0 - 0.1 && x < PE.x1 + 0.1) {
        var sC = c.Lt / 2 + c.La * 0.5;                                     // mitad de la esquina
        var sB = c.Lt / 2 + c.La + (c.yt - c.d1 - c.rc - PE.abajo);         // el borde de abajo del paño de costado
        d = Math.min(d, dRect(x, s, PE.x0, PE.x1, PE.poste, sC - PE.parante, 0.10));                       // frente
        d = Math.min(d, dRect(x, s, 0.98, 1.22, 0.10, sC - 0.06, 0.06));                                     // cejas: en el borde del techo
      }
      return d;
    }
    (function () {
      function grilla(f) {
        var xs = [CX1].concat(tramo(CX1, 1.92, 0.04), tramo(1.92, -0.94, 0.012, f), tramo(-0.94, CX0, 0.04));
        var pared = [0].concat(tramo(0, 0.14, 0.07), tramo(0.14, 1, 0.0125, f)), vs = pared.slice();
        tramo(1, 2, 0.1).concat(tramo(2, 3, 0.0125, f), tramo(3, 4, 0.1)).forEach(function (v) { vs.push(v); });
        pared.slice(0, -1).map(function (v) { return 5 - v; }).reverse().forEach(function (v) { vs.push(v); });
        return [xs, vs];
      }
      var gr = grilla(DET), xs = gr[0], vs = gr[1];
      var HUNDE = 0.04;
      function puntoHundido(x, v) {                 // los vidrios quedan hundidos; el burlete es la pared del hueco
        var p = puntoCabV(seccionCab(x), v), f = distCab(x, v), h = HUNDE * Math.max(0, Math.min(1, 1 - f / BURLETE));
        if (h <= 0) return p;
        var c = [p[0], Math.min(2.7, cabTecho(p[0]) - 0.3), 0], q = [0, p[1] - c[1], p[2] - c[2]];
        if (v > 1.0 && v < 4.0) q = [0, p[1] - c[1], p[2] - c[2]];
        if (v <= 1) q = [0, 0, 1]; else if (v >= 4) q = [0, 0, -1];
        var l = Math.hypot(q[1], q[2]) || 1;
        return [p[0], p[1] - q[1] / l * h, p[2] - q[2] / l * h];
      }
      var cen = function (p) { return [p[0], Math.min(2.7, cabTecho(p[0]) - 0.3), 0]; };
      var g = recortar(xs, vs, puntoHundido, distCab, [0, BURLETE], cen);
      var chapa = M.aluminio.clone(); chapa.side = T.FrontSide;
      vidrios.add(malla(g[0], M.vidrio, "Vidrios de la cabina de pilotos"), malla(g[1], M.burlete, "Marcos de las ventanas"));
      // el forro de adentro sólo se ve por los vidrios: con una grilla más gruesa alcanza
      var gf = DET > 1 ? recortar(grilla(DET_FORRO)[0], grilla(DET_FORRO)[1], puntoHundido, distCab, [0, BURLETE], cen) : g;
      G.add(malla(g[2], chapa, "Cabina de pilotos", true), malla(gf[2], M.forro, "Interior de la cabina de pilotos"));
    })();
    // Empalme: una curva cóncava que une el costado de la cabina con la cubierta,
    // como el carenado de la chapa real (la cabina no queda "apoyada").
    function empalme(lado) {
      var NX = 140, NS = 10, pos = [], idx = [], R = 0.16;
      for (var i = 0; i <= NX; i++) {
        var x = CX1 + (CX0 - CX1) * i / NX, W = cabAncho(x), yt = cabTecho(x);
        var y0 = techo(x, W), libre = yt - 0.18 - y0;               // alto de pared vertical disponible
        var fin = Math.max(0, Math.min(1, (X_NARANJA - 0.02 - x) / 0.30, (x - XR - 0.04) / 0.30));     // se apaga antes de la trompa naranja y atrás
        var r = Math.max(0, Math.min(R * fin * fin * (3 - 2 * fin), libre * 0.8, interp(x, 3) * 0.93 - W));
        for (var j = 0; j <= NS; j++) {
          var t = j / NS, a = 1 - t;
          // Bézier cuadrática: de la pared (W, y0 + r) a la cubierta (W + r, techo), con control en la esquina
          var z = a * a * W + 2 * a * t * W + t * t * (W + r);
          var y = a * a * (y0 + r) + 2 * a * t * y0 + t * t * techo(x, W + r);
          pos.push(x, y + 0.002, lado * (z + 0.002));
        }
      }
      for (i = 0; i < NX; i++) for (var j2 = 0; j2 < NS; j2++) {
        var q = i * (NS + 1) + j2, b = q + NS + 1;
        if (lado > 0) idx.push(q, b, q + 1, q + 1, b, b + 1); else idx.push(q, q + 1, b, q + 1, b + 1, b);
      }
      var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
      var m = new T.Mesh(g, M.aluminio); m.name = "Carenado de la cabina"; m.castShadow = m.receiveShadow = true; return m;
    }
    G.add(empalme(1), empalme(-1));
    // Piso de la cabina, pegado al lomo del fuselaje: a través de los vidrios se ve
    // la cabina vacía y no la trompa naranja que queda adentro.
    (function () {
      var NX = 110, NZ = 12, pos = [], idx = [];
      for (var i = 0; i <= NX; i++) {
        var x = XF - 0.04 + (-1.2 - XF + 0.04) * i / NX, W = cabAncho(x) - 0.012, c = seccionCab(x);
        for (var j = 0; j <= NZ; j++) { var z = -W + 2 * W * j / NZ; pos.push(x, Math.min(techo(x, z) + 0.012, c.yt - caida(c, z) - 0.03), z); }
      }
      for (i = 0; i < NX; i++) for (var j = 0; j < NZ; j++) { var q = i * (NZ + 1) + j, b = q + NZ + 1; idx.push(q, q + 1, b, q + 1, b + 1, b); }
      var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
      var m = new T.Mesh(g, mat(0x33383c, { r: 0.85, side: T.DoubleSide })); m.name = "Piso de la cabina"; m.receiveShadow = true; G.add(m);
      var mInt = mat(0x2b2f2c, { r: 0.9 }), mButaca = mat(0x4d5a3c, { r: 0.85 });
      var tunel = tubo([1.18, 2.50, 0], [0.18, 3.24, 0], 0.13, mInt); tunel.name = "Túnel del eje de transmisión"; G.add(tunel);
      var consola = new T.Mesh(new T.BoxGeometry(0.36, 0.34, 0.40), M.negro); consola.position.set(1.10, 2.62, 0); consola.name = "Consola"; G.add(consola);
      var tablero = new T.Mesh(new T.BoxGeometry(0.07, 0.24, 0.96), M.negro); tablero.position.set(1.36, 2.68, 0); tablero.rotation.z = -0.35; tablero.name = "Tablero"; G.add(tablero);
      [-0.36, 0.36].forEach(function (zs) {
        var asiento = new T.Mesh(new T.BoxGeometry(0.44, 0.10, 0.40), mButaca); asiento.position.set(0.62, 2.68, zs); G.add(asiento);
        var respaldo = new T.Mesh(new T.BoxGeometry(0.10, 0.56, 0.40), mButaca); respaldo.position.set(0.38, 2.98, zs); respaldo.rotation.z = 0.15; G.add(respaldo);
        asiento.name = respaldo.name = "Butaca";
      });
    })();
    // Marco metálico de la ventana corrediza: un aro plano pegado a la pared, con la forma de la ventana
    (function () {
      function corrida(P, d) {                     // el polígono (antihorario) agrandado d hacia afuera
        var n = P.length, L = P.map(function (a, i) {
          var b = P[(i + 1) % n], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy);
          return { x: a[0] + dy / l * d, y: a[1] - dx / l * d, dx: dx, dy: dy };
        });
        return L.map(function (b, i) {
          var a = L[(i + n - 1) % n], den = a.dx * b.dy - a.dy * b.dx, t = ((b.x - a.x) * b.dy - (b.y - a.y) * b.dx) / den;
          return [a.x + a.dx * t, a.y + a.dy * t];
        });
      }
      function camino(p, Q) { Q.forEach(function (q, i) { if (i) p.lineTo(q[0], q[1]); else p.moveTo(q[0], q[1]); }); p.closePath(); return p; }
      var P = PUERTA_PILOTO, forma = camino(new T.Shape(), corrida(P, 0.06));
      forma.holes.push(camino(new T.Path(), corrida(P, BURLETE * 0.5).reverse()));
      var g = new T.ShapeGeometry(forma), mMarco = mat(0xd5dade, { m: 0.6, r: 0.35, side: T.DoubleSide });
      [-1, 1].forEach(function (s) {
        var m = malla(g, mMarco, "Marco de la ventana corrediza"); m.position.z = s * (cabAncho(0.7) + 0.003); G.add(m);
      });
    })();
    G.add(vidrios);

    // detalles
    var det = new T.Group(); det.name = "Detalles";
    // puerta corrediza de carga, a la derecha (se abre hacia atrás)
    var texPuerta = lienzo(512, 640, function (g, w, h) { g.lineWidth = 9; g.strokeStyle = "#3b4045"; rr(g, 8, 8, w - 16, h - 16, 30); g.stroke(); g.fillStyle = "#3b4045"; g.fillRect(40, h * 0.56, 60, 12); });
    var SALE = 0.036;
    function fuera(x, y) { return medioAncho(x, y) + SALE; }
    (function () {
      var X0 = -1.61, X1 = 0.45, Y0 = 0.62, Y1 = 2.20;
      var xs = [X1].concat(tramo(X1, X0, 0.012)), ys = [Y0].concat(tramo(Y0, Y1, 0.012));
      var g = recortar(xs, ys, function (x, y) { return [x, y, fuera(x, y)]; },
        function (x, y) { var d = 9; VCARGA.forEach(function (w) { d = Math.min(d, dRect(x, y, w[0], w[1], w[2], w[3], 0.075)); }); return d; },
        [0, BURLETE], function (p) { return [p[0], 1.5, 0]; });
      det.add(malla(g[2], M.aluminio, "Puerta corrediza", true), malla(g[1], M.burlete, "Burletes de la puerta"));
      // canto de la puerta: del casco al panel, todo alrededor
      var borde = [], k;
      for (k = 0; k <= 40; k++) borde.push([X1 + (X0 - X1) * k / 40, Y0]);
      for (k = 1; k <= 30; k++) borde.push([X0, Y0 + (Y1 - Y0) * k / 30]);
      for (k = 1; k <= 40; k++) borde.push([X0 + (X1 - X0) * k / 40, Y1]);
      for (k = 1; k <= 30; k++) borde.push([X1, Y1 + (Y0 - Y1) * k / 30]);
      var pw = [], iw = [];
      borde.forEach(function (b, i) {
        pw.push(b[0], b[1], medioAncho(b[0], b[1]) - 0.004, b[0], b[1], fuera(b[0], b[1]));
        if (i) { var q = (i - 1) * 2; iw.push(q, q + 2, q + 1, q + 1, q + 2, q + 3); }
      });
      var gw = new T.BufferGeometry(); gw.setAttribute("position", new T.Float32BufferAttribute(pw, 3)); gw.setIndex(iw); gw.computeVertexNormals();
      det.add(malla(gw, M.aluminio, "Canto de la puerta", true));
      // los dos rieles extruidos (la puerta se corre hacia atrás)
      [2.27, 0.66].forEach(function (y) {
        var pr = []; for (var x = 0.52; x >= -3.12; x -= 0.12) pr.push(new T.Vector3(x, y, medioAncho(x, y) + 0.022));
        det.add(malla(new T.TubeGeometry(new T.CatmullRomCurve3(pr), 60, 0.02, 8, false), M.acero, "Riel de la puerta", true));
      });
    })();
    // marco de la ventana de la puerta corrediza
    var texMarcoV = lienzo(256, 256, function (g, w, h) { g.lineWidth = 22; g.strokeStyle = "#c9cdd0"; rr(g, 14, 14, w - 28, h - 28, 46); g.stroke(); g.lineWidth = 4; g.strokeStyle = "#7d8287"; rr(g, 3, 3, w - 6, h - 6, 54); g.stroke(); });
    [[-0.33, 0.17], [-1.37, -0.87]].forEach(function (v) { det.add(parcheLado(v[0] - 0.05, v[1] + 0.05, 1.50, 2.10, 1, matParche(texMarcoV), fuera, "Marco de ventana")); });
    // manija embutida en el borde delantero de la puerta
    det.add(parcheLado(0.28, 0.40, 1.28, 1.36, 1, matParche(lienzo(64, 32, function (g, w, h) { g.fillStyle = "#2b2f33"; rr(g, 2, 2, w - 4, h - 4, 10); g.fill(); })), fuera, "Manija"));
    var texRiel = lienzo(512, 32, function (g, w, h) { g.fillStyle = "#3b4045"; g.fillRect(0, 8, w, 16); });
    // babor: puerta chica de acceso adelante y los peldaños
    det.add(parcheLado(0.55, 1.15, 0.70, 2.05, -1, matParche(texPuerta), null, "Puerta de acceso"));
    [[0.95, 0.75], [0.70, 1.20]].forEach(function (p) {
      det.add(parcheLado(p[0] - 0.13, p[0] + 0.13, p[1], p[1] + 0.06, -1, matParche(lienzo(64, 16, function (g, w, h) { g.fillStyle = "#24282b"; rr(g, 1, 1, w - 2, h - 2, 6); g.fill(); })), null, "Peldaño"));
    });
    // juntas de las dos puertas del motor (almeja) y borde trasero
    var texJunta = lienzo(32, 256, function (g, w, h) { g.fillStyle = "#7a2f05"; g.fillRect(12, 0, 8, h); });
    var junta = new T.Mesh(new T.PlaneGeometry(0.02, 1), mat(0x7a2f05)); void junta;
    [-1, 1].forEach(function (s) { det.add(parcheLado(X_NARANJA - 0.015, X_NARANJA + 0.015, 0.56, 2.04, s, matParche(texJunta), null, "Bisagra de la puerta del motor")); });
    var NJ = 60, pj = [];
    for (var q = 0; q <= NJ; q++) { var xx = NARIZ - 0.002 - (NARIZ - 0.002 - XF - 0.10) * q / NJ; pj.push(new T.Vector3(xx + 0.004, techo(xx, 0) + 0.004, 0)); }
    for (q = NJ; q >= 0; q--) { xx = NARIZ - 0.002 - (NARIZ - 0.002 - X_NARANJA) * q / NJ; pj.push(new T.Vector3(xx + 0.004, interp(xx, 1) - 0.004, 0)); }
    det.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pj), 200, 0.007, 6, false), mat(0x7a2f05)));
    // Unión de la cabina con la trompa: la banda de tomas de aire del ventilador sigue justo la
    // línea donde la cabina se mete en las puertas del motor, con una moldura de cada lado.
    (function () {
      function dentro(p) { return Math.abs(p[2]) < medioAncho(p[0], p[1]); }
      function proy(p, sube) {                     // lleva el punto a la chapa de la trompa (y lo levanta un poco)
        var x = Math.min(p[0], NARIZ - 0.01), q = seccion(x), ny = (p[1] - q.yc) / q.H, nz = p[2] / q.W;
        var k = Math.pow(Math.pow(Math.abs(nz), q.n) + Math.pow(Math.abs(ny), q.n), -1 / q.n);
        var y = q.yc + q.H * ny * k, z = q.W * nz * k, l = Math.hypot(y - q.yc, z) || 1;
        return [x, y + (y - q.yc) / l * sube, z + z / l * sube];
      }
      // El arco es un aro plano en x = X_NARANJA que rodea la nariz por arriba y los costados, hasta
      // la mitad de su alto; adelante se extiende sobre la trompa y atrás tapa el encuentro con la cabina.
      var xr = X_NARANJA, q0 = seccion(xr), der = [], N = 90;
      var aLo = Math.asin(Math.max(-1, Math.min(1, Math.sign((2.00 - q0.yc) / q0.H) * Math.pow(Math.abs((2.00 - q0.yc) / q0.H), q0.n / 2))));
      for (var i = 0; i <= N; i++) {
        var a = aLo + (Math.PI / 2 - aLo) * i / N, xa = xArco(puntoSeccion(xr, a)[1]), p = puntoSeccion(xa, a);
        xa = xArco(p[1]); p = puntoSeccion(xa, a);
        der.push({ p: [xa, p[1], i === N ? 0 : p[2] + 0.002], n: [1, 0, 0] });
      }
      var linea = der.concat(der.slice(0, -1).reverse().map(function (e) { return { p: [e.p[0], e.p[1], -e.p[2]], n: [e.n[0], e.n[1], -e.n[2]] }; }));
      // Arco de chapa que abraza la nariz: sale de la base del parabrisas (y del borde gris en los costados),
      // sube redondeado hasta 11 cm y cae en una cara inclinada hacia la nariz, donde van las rejillas.
      var ANCHO = 0.22, ALTO = 0.11, T_CIMA = 0.62, T_CAE = 0.92;
      function perfil(t) {                       // altura del arco en t (0 = lado cabina, 1 = lado nariz)
        if (t <= T_CIMA) return ALTO * Math.sin(Math.PI / 2 * Math.pow(t / T_CIMA, 0.8));
        if (t <= T_CAE) return ALTO * (1 - (t - T_CIMA) / (T_CAE - T_CIMA));
        return 0;
      }
      var largos = [0]; for (var li = 1; li < linea.length; li++) { var A = linea[li - 1].p, B = linea[li].p; largos.push(largos[li - 1] + Math.hypot(B[0] - A[0], B[1] - A[1], B[2] - A[2])); }
      function franja(t0, t1, NJ, material, nombre, conUV, sombra) {
        var pw = [], uw = [], iw = [];
        linea.forEach(function (e, i) {
          for (var k = 0; k <= NJ; k++) {
            var t = t0 + (t1 - t0) * k / NJ, b = [e.p[0] + e.n[0] * ANCHO * t, e.p[1] + e.n[1] * ANCHO * t, e.p[2] + e.n[2] * ANCHO * t], w = proy(b, perfil(t) - 0.004);
            pw.push(w[0], w[1], w[2]); uw.push(largos[i] / largos[largos.length - 1], k / NJ);
          }
          if (i) for (k = 0; k < NJ; k++) { var q = (i - 1) * (NJ + 1) + k, r = q + NJ + 1; iw.push(q, q + 1, r, q + 1, r + 1, r); }
        });
        var gw = new T.BufferGeometry(); gw.setAttribute("position", new T.Float32BufferAttribute(pw, 3));
        if (conUV) gw.setAttribute("uv", new T.Float32BufferAttribute(uw, 2));
        gw.setIndex(iw); gw.computeVertexNormals(); det.add(malla(gw, material, nombre, sombra));
      }
      // seis paneles de malla metálica, tres de cada lado (aletas cada 16,5 cm)
      var tex = lienzo(2048, 128, function (c, w, h) {
        c.fillStyle = "#aab2ba"; c.fillRect(0, 0, w, h);
        var paso = w / 6;
        for (var k = 0; k < 6; k++) {
          var x0 = k * paso + 18, x1 = (k + 1) * paso - 18;
          c.fillStyle = "#121416"; rr(c, x0, 14, x1 - x0, h - 28, 10); c.fill();
          c.save(); rr(c, x0, 14, x1 - x0, h - 28, 10); c.clip(); c.strokeStyle = "#5d646a"; c.lineWidth = 2;
          for (var a = x0 - h; a < x1 + h; a += 9) { c.beginPath(); c.moveTo(a, 0); c.lineTo(a + h, h); c.stroke(); c.beginPath(); c.moveTo(a + h, 0); c.lineTo(a, h); c.stroke(); }
          c.restore(); c.lineWidth = 5; c.strokeStyle = "#6c747b"; rr(c, x0, 14, x1 - x0, h - 28, 10); c.stroke();
        }
      });
      var chapaArco = M.aluminio.clone(); chapaArco.side = T.DoubleSide;
      franja(0, T_CIMA + 0.04, 10, chapaArco, "Arco de chapa sobre la nariz", false, true);
      franja(T_CIMA + 0.04, T_CAE, 4, new T.MeshStandardMaterial({ map: tex, metalness: 0.3, roughness: 0.55, side: T.DoubleSide }), "Tomas de aire del ventilador", true, false);
      var adentro = [], afuera = [];
      linea.forEach(function (e) {
        [[0, adentro], [T_CAE, afuera]].forEach(function (par) {
          var t = par[0], b = [e.p[0] + e.n[0] * ANCHO * t, e.p[1] + e.n[1] * ANCHO * t, e.p[2] + e.n[2] * ANCHO * t], w = proy(b, 0.004);
          par[1].push(new T.Vector3(w[0], w[1], w[2]));
        });
      });
      var mMoldura = mat(0x2b2f33, { m: 0.5, r: 0.45 });
      det.add(malla(new T.TubeGeometry(new T.CatmullRomCurve3(adentro), 320, 0.011, 8, false), mMoldura, "Moldura del parabrisas"));
      det.add(malla(new T.TubeGeometry(new T.CatmullRomCurve3(afuera), 320, 0.009, 8, false), mMoldura, "Borde del arco"));
    })();
    // rejilla de salida de aire del motor, a cada lado, entre la trompa y la puerta
    var texMalla = lienzo(256, 384, function (g, w, h) {
      rr(g, 6, 6, w - 12, h - 12, 14); g.fillStyle = "#121416"; g.fill();
      for (var i = 22; i < h - 14; i += 22) {                                          // lamas horizontales
        var gr = g.createLinearGradient(0, i, 0, i + 12); gr.addColorStop(0, "#c3cad0"); gr.addColorStop(1, "#5b6268");
        g.fillStyle = gr; g.fillRect(14, i, w - 28, 11);
      }
      rr(g, 6, 6, w - 12, h - 12, 14); g.lineWidth = 8; g.strokeStyle = "#8f9498"; g.stroke();
    });
    var mMalla = matParche(texMalla);
    [-1, 1].forEach(function (s) { det.add(parcheLado(1.36, 1.84, 1.20, 2.02, s, mMalla, null, "Toma lateral con lamas")); });
    // boca del escape, abajo en la trompa
    (function () {
      var x = 2.72, y = 0.98, z = -medioAncho(x, y);
      det.add(tubo([x, y, z + 0.06], [x, y, z - 0.10], 0.085, mat(0x8a3a1c, { m: 0.5, r: 0.5 })));        // caño corto
      var aro = new T.Mesh(new T.TorusGeometry(0.085, 0.014, 10, 28), M.acero); aro.position.set(x, y, z - 0.10); det.add(aro);
      var hueco = new T.Mesh(new T.CircleGeometry(0.074, 28), M.negro); hueco.position.set(x, y, z - 0.095); hueco.rotation.y = Math.PI; det.add(hueco);
    })();
    G.add(det);

    // pintura y marcas
    // sacado de fotos de los S-55 de la Fuerza Aérea (1962-1968) y del helicóptero preservado
    var marcas = new T.Group(); marcas.name = "Marcas";
    var FUENTE = "900 %dpx 'Arial Narrow', Arial, Helvetica, sans-serif";
    function texTexto(txt, w, h, color, px) {
      return lienzo(w, h, function (g) { g.fillStyle = color; g.font = FUENTE.replace("%d", px); g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(txt, w / 2, h / 2 + px * 0.04); });
    }
    function escarapela(g, cx, cy, r) {
      g.beginPath(); g.arc(cx, cy, r, 0, 7); g.fillStyle = "#74acdf"; g.fill();
      g.beginPath(); g.arc(cx, cy, r * 0.66, 0, 7); g.fillStyle = "#ffffff"; g.fill();
      g.beginPath(); g.arc(cx, cy, r * 0.33, 0, 7); g.fillStyle = "#74acdf"; g.fill();
    }
    // matrícula: una sola, grande, en el frente de la trompa (se lee mirando el helicóptero de adelante)
    function frente(y, z) {                        // el x de la superficie de la trompa en (y, z)
      var a = 1.6, b = NARIZ;
      for (var k = 0; k < 26; k++) { var m = (a + b) / 2; if (medioAncho(m, y) >= Math.abs(z)) a = m; else b = m; }
      return a;
    }
    (function () {
      var z0 = -0.76, z1 = 0.76, y0 = 0.94, y1 = 1.54, NZ = 44, NY = 18, pos = [], uv = [], idx = [];
      for (var j = 0; j <= NY; j++) {
        var y = y0 + (y1 - y0) * j / NY, fila = [], arcos = [0];
        for (var i = 0; i <= NZ; i++) { var z = z0 + (z1 - z0) * i / NZ; fila.push([frente(y, z) + 0.008, y, z]); }
        for (i = 1; i <= NZ; i++) arcos.push(arcos[i - 1] + Math.hypot(fila[i][0] - fila[i - 1][0], fila[i][2] - fila[i - 1][2]));
        for (i = 0; i <= NZ; i++) { pos.push(fila[i][0], fila[i][1], fila[i][2]); uv.push(1 - arcos[i] / arcos[NZ], j / NY); }   // mirando de frente, +z queda a la izquierda
      }
      for (j = 0; j < NY; j++) for (i = 0; i < NZ; i++) { var q = j * (NZ + 1) + i; idx.push(q, q + NZ + 1, q + 1, q + 1, q + NZ + 1, q + NZ + 2); }
      var g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
      var m = new T.Mesh(g, matParche(texTexto("H-08", 1024, 400, "#111111", 380))); m.name = "Matrícula"; marcas.add(m);
    })();
    // escarapela en la puerta de carga y en el mismo lugar del otro lado
    var mEsc = matParche(lienzo(256, 256, function (g) { escarapela(g, 128, 128, 122); }));
    marcas.add(parcheLado(-1.40, -0.84, 0.86, 1.42, 1, mEsc, function (x, y) { return medioAncho(x, y) + 0.036; }, "Escarapela"));
    marcas.add(parcheLado(-1.40, -0.84, 0.86, 1.42, -1, mEsc, null, "Escarapela"));
    // matrícula grande atrás, donde el fuselaje se afina, y la bandera sobre el tubo de cola
    var mMatCola = matParche(texTexto("H-08", 1024, 330, "#14181f", 300));
    var mLeyenda = matParche(texTexto("FUERZA AEREA ARGENTINA", 3200, 240, "#14181f", 190));
    var texBandera = lienzo(384, 240, function (g, w, h) {
      g.fillStyle = "#74acdf"; g.fillRect(0, 0, w, h); g.fillStyle = "#ffffff"; g.fillRect(0, h / 3, w, h / 3);
      g.beginPath(); g.arc(w / 2, h / 2, h * 0.11, 0, 7); g.fillStyle = "#f6b40e"; g.fill();
    });
    var mBandera = matParche(texBandera);
    function anchoBoom(x, y) { var r = rBoom(x), d = y - yBoom(x); return Math.sqrt(Math.max(0, r * r - d * d)); }
    [-1, 1].forEach(function (s) {
      var yc = yBoom(-7.55);
      marcas.add(parcheLado(-7.95, -7.15, yc - 0.13, yc + 0.13, s, mMatCola, anchoBoom, "Matrícula"));
      marcas.add(parcheLado(-6.95, -4.25, 2.44, 2.64, s, mLeyenda, function (x, y) { return x < -6.09 ? anchoBoom(x, y) : medioAncho(x, y); }, "Leyenda FUERZA AEREA ARGENTINA"));
      var bandera = new T.Mesh(new T.PlaneGeometry(0.34, 0.21), mBandera); bandera.name = "Bandera";
      bandera.position.set(-8.62, BTOP + 0.42, s * 0.105); bandera.rotation.set(0, s > 0 ? 0 : Math.PI, s * -0.0); marcas.add(bandera);
    });
    G.add(marcas);

    G.userData = { rotor: rotor, rotorCola: rotorCola, cotas: COTAS, medioAncho: medioAncho, techo: techo };
    return G;
  }
  root.H08Modelo = { construir: construir, COTAS: COTAS };
})(typeof window !== "undefined" ? window : this);
