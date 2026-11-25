// -*- coding: utf-8 -*-
// Cinemáticas del 3D: cuando el profe elige un accidente, otra parte del vuelo
// o una falla, sale un clip corto con planos de cámara, títulos y un mini tablero.
// El helicóptero y el mini tablero siguen siempre al simulador; lo único armado
// como cine es la cámara. Los campos textos y pista de cada clip ya no se usan,
// quedaron de referencia.
(function () {
  "use strict";
  var D2R = Math.PI / 180;
  var KT = 1.944, FT = 3.281;

  // planos: [t0, t1, tipo, parámetros]
  //   seguir   pegada al helicóptero, de/a = [adelante, arriba, derecha] en m
  //   orbita   r, h, a0 a a1 en grados (0 = adelante, 90 = derecha)
  //   plantada quieta donde arrancó (de), lo sigue con la vista
  //   detalle  primer plano de un punto, de "de" a "a"
  //   cabina   desde el asiento del piloto
  // además: fov (o fov0/fov1), mira, temblor (m)
  function pl(t0, t1, tipo, o) { o = o || {}; o.t0 = t0; o.t1 = t1; o.tipo = tipo; return o; }
  var VUELO = { alt: [[0, 120]], v: [[0, 38]], cab: [[0, -3]], rpm: [[0, 215]], mot: [[0, 2500]], cola: [[0, 1160]], luces: [[0, 1]] };
  function pista(base, extra) { var p = {}; Object.keys(base).forEach(function (k) { p[k] = base[k]; }); Object.keys(extra || {}).forEach(function (k) { p[k] = extra[k]; }); return p; }

  var CLIPS = {
    // las 6 actividades
    ACT_MARCHA: {
      titulo: "Puesta en marcha", sub: "Así se enciende el helicóptero", dur: 30,
      pista: { alt: [[0, 0]], v: [[0, 0]], cab: [[0, 0]], mot: [[0, 0], [4, 0], [5.5, 700], [7, 400], [8.5, 1100], [11, 1400], [30, 1500]],
        rpm: [[0, 0], [12, 0], [20, 90], [26, 180], [30, 215]], cola: [[0, 0], [12, 0], [30, 1160]], luces: [[0, 0], [2, 1]], baliza: [[0, 0], [2, 1]],
        OIL_PRESS: [[0, 0], [6, 0], [10, 55], [30, 62]], OIL_TEMP: [[0, 15], [30, 40]], AMMETER: [[0, -25], [9, -25], [12, 18], [30, 10]] },
      planos: [pl(0, 7, "orbita", { r: 26, h: 4, a0: 215, a1: 245, fov: 38 }), pl(7, 13, "detalle", { punto: "escape", de: [3.38, 0.54, -4.32], a: [2.16, 0.27, -3.51], fov: 34 }),
        pl(13, 21, "detalle", { punto: "mastil", de: [5.5, 2.6, 6], a: [4.2, 2.1, 5], fov: 50 }), pl(21, 30, "orbita", { r: 19, h: 5, a0: 300, a1: 350, fov: 40 })],
      textos: [[0.8, 6.5, "Se prende la electricidad del helicóptero."], [7, 12.5, "Arranca el motor: tose un poco y empieza a andar."], [13, 20.5, "Ahora el motor empieza a mover las aspas."], [21.5, 29.5, "El motor se calienta y las aspas giran cada vez más rápido."]],
      efectos: [{ t: [5, 8], tipo: "humo", color: "gris", punto: "escape", tasa: 12 }, { t: [5.1, 7.5], tipo: "tos", punto: "escape", tasa: 1.4, color: "gris" }, { t: [5.2, 8.5], tipo: "fogonazo", punto: "escape", tasa: 1.6 }],
      mini: ["TACH_ENG", "OIL_PRESS", "OIL_TEMP", "AMMETER"], lucesTablero: { LT_STARTER: [[2, 30]] }
    },
    ACT_DESPEGUE: {
      titulo: "Despegue", sub: "Del piso al aire", dur: 26,
      pista: pista(VUELO, { alt: [[0, 0], [3, 0], [6, 1.5], [11, 1.5], [17, 8], [26, 45]], v: [[0, 0], [11, 0], [16, 12], [26, 30]], cab: [[0, 0], [10, 0], [12.5, -8], [18, -6], [26, -4]],
        faro: [[0, 1]], baliza: [[0, 1]] }),
      planos: [pl(0, 8, "plantada", { de: [7, 0.8, 20], fov: 42 }), pl(8, 14, "seguir", { de: [17, 1.6, 2], a: [15, 1.4, -2], mira: [0, 1.4, 0], fov: 46 }),
        pl(14, 20, "seguir", { de: [4, 2.5, 22], a: [-4, 3.5, 22], fov: 38, temblor: 0.08 }), pl(20, 26, "plantada", { de: [-28, 4, -10], fov: 34 })],
      textos: [[0.8, 7.5, "El piloto sube la palanca y el helicóptero se despega del piso."], [8, 13.5, "Queda flotando quieto, cerca del suelo. El viento de las aspas levanta polvo."], [14, 19.5, "Inclina la nariz hacia adelante y empieza a avanzar."], [20, 25.5, "Gana velocidad y sube."]],
      mini: ["AIRSPEED", "ALTIMETER", "VSI", "TACH_ENG"]
    },
    ACT_CRUCERO: {
      titulo: "Subida y vuelo", sub: "Sube despacio y sigue derecho", dur: 24,
      pista: pista(VUELO, { alt: [[0, 90], [14, 135], [24, 140]], v: [[0, 31], [12, 37], [24, 38]], cab: [[0, -2], [12, -3]], ala: [[0, 0], [8, 1.5], [16, -1], [24, 0]], baliza: [[0, 1]] }),
      planos: [pl(0, 8, "seguir", { de: [10, 2, 24], a: [-6, 2.5, 24], fov: 36 }), pl(8, 14, "seguir", { de: [3, -9, 6], a: [-3, -9, 3], mira: [0, 1, 0], fov: 55 }),
        pl(14, 24, "seguir", { de: [-34, 9, 8], a: [-30, 6, -10], fov: 34 })],
      textos: [[0.8, 7.5, "Sube de a poco, sin apuro."], [8.5, 13.5, "Las luces de los costados: roja a la izquierda y verde a la derecha."], [14.5, 23.5, "Ya arriba, vuela derecho y tranquilo."]],
      mini: ["AIRSPEED", "ALTIMETER", "VSI", "TACH_ENG"]
    },
    ACT_VIRAJE: {
      titulo: "Giro", sub: "Cambia de dirección hacia la derecha", dur: 22,
      pista: pista(VUELO, { alt: [[0, 140]], v: [[0, 37]], ala: [[0, 0], [3, 0], [6, 20], [16, 20], [19.5, 0]], giro: [[0, 0], [4, 0], [18.5, 90], [22, 92]], baliza: [[0, 1]] }),
      planos: [pl(0, 7, "seguir", { de: [-26, 5, 0], a: [-22, 4, 6], fov: 36 }), pl(7, 15, "cabina", { fov: 70 }), pl(15, 22, "orbita", { r: 30, h: 3, a0: 40, a1: 75, fov: 36 })],
      textos: [[0.8, 6.5, "Para girar, el helicóptero se inclina hacia un costado."], [7.5, 14.5, "Desde adentro se ve el horizonte inclinado."], [15.5, 21.5, "Se endereza y sigue en la nueva dirección."]],
      mini: ["TURN", "ATT_ROLL", "COMPASS", "AIRSPEED"]
    },
    ACT_ATERRIZAJE: {
      titulo: "Aterrizaje", sub: "Bajar, frenar y apoyarse", dur: 30,
      pista: pista(VUELO, { alt: [[0, 70], [12, 18], [17, 3], [20, 1.4], [25, 1.4], [27.5, 0]], v: [[0, 32], [10, 20], [15, 8], [18, 0]], cab: [[0, -2], [11, 2], [14.5, 10], [18, 3], [20, 0]],
        rpm: [[0, 215], [28, 215], [30, 200]], faro: [[0, 1]], baliza: [[0, 1]] }),
      planos: [pl(0, 8, "seguir", { de: [6, 3, 26], a: [-4, 2, 26], fov: 36 }), pl(8, 16, "plantada", { de: [125, -90, 16], fov: 30 }),
        pl(16, 24, "seguir", { de: [15, 0.8, 4], a: [13, 0.9, 1], mira: [0, 1.5, 0], fov: 46 }), pl(24, 30, "orbita", { r: 24, h: 3, a0: 120, a1: 150, fov: 38 })],
      textos: [[0.8, 7.5, "Baja despacio hacia el lugar de aterrizaje."], [8.5, 15.5, "Levanta la nariz para frenar."], [16.5, 23.5, "Se queda flotando quieto sobre el círculo."], [24.5, 29.5, "Apoya primero las ruedas de atrás y queda en el piso."]],
      mini: ["AIRSPEED", "ALTIMETER", "VSI", "TACH_ENG"]
    },
    ACT_APAGADO: {
      titulo: "Apagado", sub: "Enfriar, apagar y dejarlo seguro", dur: 25,
      pista: { alt: [[0, 0]], v: [[0, 0]], cab: [[0, 0]], mot: [[0, 1500], [7, 1500], [9, 300], [10.5, 0]], rpm: [[0, 200], [8, 190], [12, 140], [20, 40], [24, 0]],
        cola: [[0, 1100], [8, 1050], [24, 0]], luces: [[0, 1], [22, 1], [22.5, 0]], baliza: [[0, 1], [20, 1], [20.5, 0]],
        OIL_PRESS: [[0, 60], [8, 60], [11, 0]], AMMETER: [[0, 8], [8, 8], [10, -20], [22, -20], [23, 0]] },
      planos: [pl(0, 8, "orbita", { r: 24, h: 6, a0: 20, a1: 60, fov: 38 }), pl(8, 16, "detalle", { punto: "mastil", de: [6, 2.5, 6.5], a: [5, 2.1, 5.5], fov: 52 }),
        pl(16, 25, "plantada", { de: [32, 7, 22], fov: 32 })],
      textos: [[0.8, 7.5, "Antes de apagarlo, el motor anda despacio para enfriarse."], [8.5, 15.5, "Se corta el motor y las aspas frenan de a poco."], [16.5, 24.5, "Se apagan las luces y la electricidad. Listo para guardar."]],
      mini: ["TACH_ENG", "OIL_PRESS", "AMMETER", "VOLTMETER"], fin: true
    },

    // los 8 accidentes
    ESC_AUTORROTACION: {
      titulo: "Se para el motor", sub: "Aterriza planeando, sin motor", dur: 36, grave: true,
      pista: pista(VUELO, { alt: [[0, 150], [6, 148], [10, 135], [26, 12], [30, 1.6], [31.5, 0]], v: [[0, 38], [6, 37], [10, 33], [25, 33], [29, 6], [31, 0]],
        cab: [[0, -3], [5, -3], [6.5, 4], [9, -2], [24, -3], [27, 14], [29.5, 10], [31.2, 0]], mot: [[0, 2500], [4, 2500], [6, 300], [7.5, 0]],
        rpm: [[0, 215], [5, 215], [7, 178], [10, 214], [25, 214], [28.5, 240], [31, 190], [36, 140]], cola: [[0, 1160], [5, 1160], [7, 960], [10, 1150], [28, 1250], [36, 760]] }),
      planos: [pl(0, 4, "seguir", { de: [8, 3, 28], a: [2, 3, 28], fov: 34 }), pl(4, 8, "detalle", { punto: "escape", de: [4.05, 0.81, -5.4], a: [2.7, 0.54, -4.32], fov: 38, temblor: 0.04 }),
        pl(8, 15, "detalle", { punto: "mastil", de: [7, 1.6, 8], a: [5, 1.0, 6.5], fov: 46 }), pl(15, 24, "seguir", { de: [-20, 5, 10], a: [-14, 3, 14], fov: 40, temblor: 0.12 }),
        pl(24, 31, "plantada", { de: [115, -60, 22], fov: 30 }), pl(31, 36, "orbita", { r: 22, h: 3, a0: 60, a1: 85, fov: 38 })],
      textos: [[0.6, 4, "Vuela tranquilo y alto."], [4.2, 8, "De repente el motor se para: sale humo negro."], [8.2, 15, "El aire que pasa sigue haciendo girar las aspas, como un molino."], [15.2, 24, "Así planea, y el piloto busca dónde aterrizar."], [24.2, 31, "Cerca del piso levanta la nariz para frenar."], [31.2, 35.5, "Aterriza bien. Las aspas nunca dejaron de girar."]],
      efectos: [{ t: [4, 9.5], tipo: "humo", color: "negro", punto: "escape", tasa: 20 }, { t: [4.2, 6], tipo: "fogonazo", punto: "escape", tasa: 3 },
        { t: [4.3, 5.8], tipo: "fuego", punto: "escape", tasa: 16 }, { t: [6, 8.5], tipo: "tos", punto: "escape", tasa: 1.5, color: "negro" }],
      mini: ["TACH_ENG", "AIRSPEED", "ALTIMETER", "VSI"], lucesTablero: { LT_LOW_ROTOR: [[5.6, 9.5]] }
    },
    ESC_HIELO_CARB: {
      titulo: "Hielo en el motor", sub: "El hielo le quita fuerza", dur: 32, niebla: true,
      pista: pista(VUELO, { alt: [[0, 120], [16, 108], [26, 112], [32, 118]], v: [[0, 38], [14, 33], [20, 31], [28, 37]], mot: [[0, 2500], [4, 2480], [15, 2180], [17, 2050], [19, 2120], [25, 2480], [32, 2500]],
        CARB_AIR_TEMP: [[0, 3], [10, -4], [16, -5], [19, 15], [26, 28], [32, 30]], MAP: [[0, 32], [15, 27], [17, 26], [25, 32]] }),
      planos: [pl(0, 6, "seguir", { de: [-30, 6, 10], a: [-26, 5, 4], fov: 34 }), pl(6, 12, "detalle", { punto: "nariz", de: [5, 1, 3], a: [4, 0.6, 2.4], fov: 40 }),
        pl(12, 20, "cabina", { fov: 66 }), pl(20, 26, "detalle", { punto: "escape", de: [3.51, 0.54, -4.59], a: [2.43, 0.27, -3.78], fov: 38, temblor: 0.03 }), pl(26, 32, "seguir", { de: [6, 2.5, 24], a: [-4, 2.5, 24], fov: 36 })],
      textos: [[0.6, 6, "El aire está húmedo y fresco."], [6.2, 12, "Adentro del motor, por donde entra el aire, se forma hielo."], [12.2, 20, "El motor pierde fuerza de a poco, sin avisar."], [20.2, 26, "El piloto calienta esa parte: el hielo se derrite y el motor tose."], [26.2, 31.5, "El motor vuelve a tener toda su fuerza."]],
      efectos: [{ t: [6, 18], tipo: "tos", punto: "escape", tasa: 1.2, color: "gris" }, { t: [18, 22], tipo: "tos", punto: "escape", tasa: 3, color: "gris" }, { t: [18.5, 21], tipo: "fogonazo", punto: "escape", tasa: 1.5 }],
      mini: ["CARB_AIR_TEMP", "MAP", "TACH_ENG", "AIRSPEED"]
    },
    ESC_TRANSMISION: {
      titulo: "Sin aceite en la transmisión", sub: "La falla más peligrosa", dur: 30, grave: true,
      pista: pista(VUELO, { alt: [[0, 120], [5, 120], [18, 25], [22, 3], [24, 1.4], [26, 0]], v: [[0, 38], [6, 36], [16, 20], [21, 4], [23, 0]], cab: [[0, -3], [6, -1], [17, 4], [20.5, 12], [23, 2], [25, 0]],
        rpm: [[0, 215], [27, 215], [30, 190]], XMSN_OIL_PRESS: [[0, 50], [4, 50], [9, 8], [30, 5]], XMSN_OIL_TEMP: [[0, 75], [5, 78], [16, 120], [30, 135]] }),
      planos: [pl(0, 5, "seguir", { de: [8, 3, 26], a: [2, 3, 26], fov: 34 }), pl(5, 11, "detalle", { punto: "careno", de: [3, 2, 5], a: [1.5, 2.6, 4], fov: 42, temblor: 0.03 }),
        pl(11, 18, "cabina", { fov: 66, temblor: 0.02 }), pl(18, 25, "plantada", { de: [60, -60, 16], fov: 32 }), pl(25, 30, "orbita", { r: 22, h: 3, a0: 200, a1: 230, fov: 38 })],
      textos: [[0.6, 5, "Vuela tranquilo."], [5.2, 11, "Se prende la luz PRES. TRANSM.: la caja que mueve las aspas se quedó sin aceite."], [11.2, 18, "Sin aceite, esa caja se puede trabar en cualquier momento."], [18.2, 25, "Hay que aterrizar ya, en el primer lugar posible."], [25.2, 29.5, "En el piso se apaga el motor y no se vuelve a volar."]],
      efectos: [{ t: [6, 24], tipo: "humo", color: "gris", punto: "careno", tasa: 7 }],
      mini: ["XMSN_OIL_PRESS", "XMSN_OIL_TEMP", "TACH_ENG", "ALTIMETER"], lucesTablero: { LT_XMSN_PRESS: [[6, 30]] }
    },
    ESC_ELECTRICO: {
      titulo: "Se queda sin electricidad", sub: "De a poco se apaga todo", dur: 30,
      pista: pista(VUELO, { alt: [[0, 130]], luces: [[0, 1], [17, 1], [17.4, 0], [17.8, 1], [18.3, 0], [18.6, 1], [20, 0]], baliza: [[0, 1], [20, 0]],
        AMMETER: [[0, 12], [4, 12], [5.5, -30], [20, -38], [21, 0]], VOLTMETER: [[0, 28], [5, 28], [12, 24], [18, 19], [20, 0]] }),
      planos: [pl(0, 6, "seguir", { de: [-24, 4, 10], a: [-20, 3, 6], fov: 36 }), pl(6, 12, "detalle", { punto: "careno", de: [-4, 3, 3], a: [-5, 3.4, 1], mira: "baliza", fov: 40 }),
        pl(12, 20, "cabina", { fov: 66 }), pl(20, 30, "seguir", { de: [6, 2, 22], a: [-6, 2, 22], fov: 36 })],
      textos: [[0.6, 6, "Vuela con todas las luces prendidas."], [6.2, 12, "Se prende la luz GENERADOR: dejó de cargar la batería."], [12.2, 20, "Ahora todo anda con la batería, que se va gastando."], [20.2, 29.5, "La batería se agota y se apagan las luces. Algunos relojes siguen andando: no usan electricidad."]],
      efectos: [{ t: [5.5, 7], tipo: "chispas", punto: "nariz", tasa: 30 }],
      mini: ["AMMETER", "VOLTMETER", "AIRSPEED", "ALTIMETER"], lucesTablero: { LT_GEN: [[5.5, 20]] }
    },
    ESC_COMBUSTIBLE: {
      titulo: "Se acaba la nafta de un tanque", sub: "Cuando no se hace caso al aviso", dur: 32,
      pista: pista(VUELO, { mot: [[0, 2500], [11, 2500], [13, 1700], [14, 2100], [15.5, 900], [17, 1100], [19.5, 2400], [21, 2500]], rpm: [[0, 215], [15, 200], [17, 196], [20, 214]],
        alt: [[0, 120], [13, 120], [19, 100], [32, 110]], FUEL_QTY_FWD: [[0, 45], [10, 0]], FUEL_QTY_AFT: [[0, 210]], FUEL_PRESS: [[0, 18], [11, 18], [13, 4], [16.5, 2], [18.5, 17]] }),
      planos: [pl(0, 6, "seguir", { de: [8, 3, 25], a: [2, 3, 25], fov: 34 }), pl(6, 12, "cabina", { fov: 66 }), pl(12, 18, "detalle", { punto: "escape", de: [3.78, 0.54, -4.59], a: [2.7, 0.27, -3.78], fov: 38, temblor: 0.05 }),
        pl(18, 26, "seguir", { de: [18, 1, 6], a: [16, 1.5, -6], mira: [0, 1.5, 0], fov: 44 }), pl(26, 32, "orbita", { r: 30, h: 4, a0: 250, a1: 280, fov: 36 })],
      textos: [[0.6, 6, "El tanque de adelante se está vaciando."], [6.2, 12, "Se prende la luz COMB. DEL.… y nadie cambia de tanque."], [12.2, 18, "Se acaba la nafta: el motor tose y se apaga de a ratos."], [18.2, 26, "El piloto pasa al tanque de atrás y el motor vuelve a andar."], [26.2, 31.5, "Siempre hay que mirar las luces de la nafta."]],
      efectos: [{ t: [12.5, 18], tipo: "tos", punto: "escape", tasa: 2.6, color: "negro" }, { t: [13, 17], tipo: "fogonazo", punto: "escape", tasa: 1.2 }],
      mini: ["FUEL_QTY_FWD", "FUEL_QTY_AFT", "FUEL_PRESS", "TACH_ENG"], lucesTablero: { LT_FUEL_FWD: [[5, 19]] }
    },
    ESC_ROTOR_COLA: {
      titulo: "Se para el rotor de cola", sub: "El helicóptero gira sobre sí mismo", dur: 30, grave: true,
      pista: pista(VUELO, { alt: [[0, 45], [5, 45], [14, 38], [24, 6], [27, 1.5], [28.5, 0]], v: [[0, 14], [5, 12], [12, 4], [20, 3], [27, 0]], cab: [[0, -2], [24, -1], [26, 8], [28, 0]],
        cola: [[0, 1160], [5, 1160], [7, 0]], giro: [[0, 0], [6, 0], [8, 40], [13, 330], [20, 560], [26, 620], [28.5, 630]], ala: [[0, 0], [7, 6], [13, 9], [20, 4], [26, 0]],
        mot: [[0, 2500], [13, 2500], [15, 900], [16, 700]], rpm: [[0, 215], [14, 215], [16, 205], [26, 232], [28, 200], [30, 170]] }),
      planos: [pl(0, 5.5, "detalle", { punto: "cola", de: [-3, 0.5, 5], a: [-2, 0.3, 4], fov: 42 }), pl(5.5, 13, "plantada", { de: [30, 6, 26], fov: 34, temblor: 0.05 }),
        pl(13, 20, "orbita", { r: 6, h: 30, a0: 0, a1: 40, fov: 50 }), pl(20, 30, "plantada", { de: [26, -2, 18], fov: 36 })],
      textos: [[0.6, 5.5, "La hélice chica de la cola evita que el helicóptero gire."], [5.7, 13, "Se para esa hélice: el helicóptero empieza a dar vueltas."], [13.2, 20, "El piloto apaga el motor y las vueltas se frenan."], [20.2, 29.5, "Aterriza girando un poco. La brújula no paraba de dar vueltas."]],
      mini: ["COMPASS", "TURN", "TACH_ENG", "ALTIMETER"], lucesTablero: {}
    },
    ESC_ACEITE: {
      titulo: "El motor se queda sin aceite", sub: "Hay que bajar antes de que se rompa", dur: 32,
      pista: pista(VUELO, { alt: [[0, 120], [10, 120], [26, 3], [28, 1.4], [30, 0]], v: [[0, 38], [10, 36], [24, 8], [27, 0]], cab: [[0, -3], [22, 3], [24.5, 11], [27, 2], [29, 0]],
        mot: [[0, 2500], [18, 2420], [20, 2250], [22, 2350], [30, 2300]], OIL_PRESS: [[0, 75], [4, 75], [14, 12], [32, 8]], OIL_TEMP: [[0, 70], [6, 72], [22, 112], [32, 118]], CHT: [[0, 200], [10, 205], [26, 250]] }),
      planos: [pl(0, 6, "seguir", { de: [8, 3, 26], a: [2, 3, 26], fov: 34 }), pl(6, 12, "detalle", { punto: "rejillaDer", de: [3.5, 0.3, 4.2], a: [2.6, 0.1, 3.4], fov: 42 }),
        pl(12, 18, "cabina", { fov: 66 }), pl(18, 26, "plantada", { de: [130, -200, 18], fov: 30 }), pl(26, 32, "orbita", { r: 22, h: 3, a0: 300, a1: 330, fov: 38 })],
      textos: [[0.6, 6, "Vuela tranquilo."], [6.2, 12, "Baja el aceite del motor: sale humo gris de los costados."], [12.2, 18, "El motor se calienta cada vez más."], [18.2, 26, "El piloto aterriza antes de que el motor se rompa."], [26.2, 31.5, "En el piso, se apaga el motor enseguida."]],
      efectos: [{ t: [7, 26], tipo: "humo", color: "gris", punto: "rejillas", tasa: 8 }, { t: [19, 23], tipo: "tos", punto: "escape", tasa: 1.5, color: "gris" }],
      mini: ["OIL_PRESS", "OIL_TEMP", "CHT", "TACH_ENG"]
    },
    ESC_INSTRUMENTO_MIENTE: {
      titulo: "El reloj miente", sub: "Falla el reloj, no el motor", dur: 28,
      pista: pista(VUELO, { OIL_PRESS: [[0, 75], [6, 75], [9, 0], [28, 0]], OIL_TEMP: [[0, 72]], baliza: [[0, 1]] }),
      planos: [pl(0, 7, "seguir", { de: [-28, 6, 10], a: [-24, 5, 4], fov: 34 }), pl(7, 14, "cabina", { fov: 66 }), pl(14, 21, "detalle", { punto: "escape", de: [3.78, 0.81, -4.86], a: [2.7, 0.41, -4.05], fov: 38 }),
        pl(21, 28, "seguir", { de: [6, 2.5, 24], a: [-4, 2.5, 24], fov: 36 })],
      textos: [[0.6, 7, "Vuela tranquilo."], [7.2, 14, "El reloj del aceite cae a cero de golpe…"], [14.2, 21, "…pero afuera no hay humo y el motor anda igual que antes."], [21.2, 27.5, "El que falla es el reloj. Antes de hacer algo, hay que mirar los otros relojes."]],
      mini: ["OIL_PRESS", "OIL_TEMP", "TACH_ENG", "CHT"]
    },

    // fallas sueltas: filman el vuelo en vivo
    FALLA_MOTOR: { vivo: true, dur: 11, sub: "Motor",
      efectos: [{ t: [0.2, 1.6], tipo: "fogonazo", punto: "escape", tasa: 3 }, { t: [0.3, 1.8], tipo: "fuego", punto: "escape", tasa: 14 }, { t: [1.5, 4], tipo: "tos", punto: "escape", tasa: 1.4, color: "negro" }],
      planos: [pl(0, 5, "detalle", { punto: "escape", de: [4.05, 0.81, -5.4], a: [2.7, 0.54, -4.32], fov: 38, temblor: 0.03 }), pl(5, 11, "seguir", { de: [10, 3, 24], a: [0, 3, 24], fov: 36 })],
      mini: ["TACH_ENG", "MAP", "CHT", "OIL_PRESS"] },
    FALLA_LUBRICACION: { vivo: true, dur: 11, sub: "Aceite", planos: [pl(0, 5.5, "detalle", { punto: "rejillaDer", de: [3.5, 0.3, 4.2], a: [2.6, 0.1, 3.4], fov: 42 }), pl(5.5, 11, "seguir", { de: [-22, 4, 10], a: [-18, 3, 6], fov: 36 })],
      mini: ["OIL_PRESS", "OIL_TEMP", "CHT", "TACH_ENG"] },
    FALLA_COMBUSTIBLE: { vivo: true, dur: 11, sub: "Nafta", planos: [pl(0, 5.5, "detalle", { punto: "panza", de: [4, -2, -6], a: [2, -2.5, -5], fov: 44 }), pl(5.5, 11, "cabina", { fov: 66 })],
      mini: ["FUEL_PRESS", "FUEL_QTY_FWD", "FUEL_QTY_AFT", "TACH_ENG"] },
    FALLA_TRANSMISION: { vivo: true, dur: 11, sub: "Transmisión", planos: [pl(0, 5.5, "detalle", { punto: "careno", de: [3, 2, 5], a: [1.5, 2.6, 4], fov: 42 }), pl(5.5, 11, "seguir", { de: [8, 3, 26], a: [0, 3, 26], fov: 34 })],
      mini: ["XMSN_OIL_PRESS", "XMSN_OIL_TEMP", "TACH_ENG", "ALTIMETER"] },
    FALLA_ROTORES: { vivo: true, dur: 11, sub: "Aspas", planos: [pl(0, 5.5, "detalle", { punto: "mastil", de: [5, 2.4, 5.5], a: [3.5, 2.1, 6], fov: 55 }), pl(5.5, 11, "detalle", { punto: "cola", de: [-3, 0.5, 5], a: [-2, 0.3, 4], fov: 42 })],
      mini: ["TACH_ENG", "COMPASS", "TURN", "ALTIMETER"] },
    FALLA_ELECTRICO: { vivo: true, dur: 11, sub: "Electricidad", planos: [pl(0, 5.5, "detalle", { punto: "careno", de: [-4, 3, 3], a: [-5, 3.4, 1], mira: "baliza", fov: 40 }), pl(5.5, 11, "cabina", { fov: 66 })],
      mini: ["AMMETER", "VOLTMETER", "AIRSPEED", "ALTIMETER"] },
    FALLA_INSTRUMENTOS: { vivo: true, dur: 11, sub: "Relojes", planos: [pl(0, 5.5, "cabina", { fov: 66 }), pl(5.5, 11, "seguir", { de: [-24, 5, 8], a: [-20, 4, 2], fov: 36 })],
      mini: ["AIRSPEED", "ALTIMETER", "COMPASS", "OIL_PRESS"], texto2: "Afuera todo está normal: el que falla es el reloj." }
  };
  // qué clip va con cada etapa del vuelo
  var ACTIVIDAD = { FRIO: "ACT_MARCHA", BATERIA: "ACT_MARCHA", PREARRANQUE: "ACT_MARCHA", ARRANQUE: "ACT_MARCHA", RALENTI: "ACT_MARCHA", EMBRAGUE: "ACT_MARCHA", RUNUP: "ACT_MARCHA",
    MAG_L: "ACT_MARCHA", MAG_BOTH: "ACT_MARCHA", MAG_R: "ACT_MARCHA", DESPEGUE: "ACT_DESPEGUE", ASCENSO: "ACT_CRUCERO", CRUCERO: "ACT_CRUCERO", VIRAJE: "ACT_VIRAJE",
    DESCENSO: "ACT_ATERRIZAJE", APROXIMACION: "ACT_ATERRIZAJE", ESTACIONARIO: "ACT_ATERRIZAJE", ATERRIZAJE: "ACT_ATERRIZAJE", ENFRIAMIENTO: "ACT_APAGADO", CORTE: "ACT_APAGADO", APAGADO: "ACT_APAGADO" };
  var SISTEMA = { MOTOR: "FALLA_MOTOR", LUBRICACION: "FALLA_LUBRICACION", COMBUSTIBLE: "FALLA_COMBUSTIBLE", TRANSMISION: "FALLA_TRANSMISION", ROTORES: "FALLA_ROTORES", ELECTRICO: "FALLA_ELECTRICO", INSTRUMENTOS: "FALLA_INSTRUMENTOS" };
  var LUZ_DE = { XMSN_PRESS_LOSS: "LT_XMSN_PRESS", XMSN_OVERHEAT: "LT_XMSN_PRESS", GEN_FAIL: "LT_GEN", ELEC_TOTAL: "LT_GEN", LOW_ROTOR_RPM: "LT_LOW_ROTOR", FUEL_STARVATION: "LT_FUEL_FWD" };

  // valores en el tiempo
  function val(arr, t) {
    if (!arr || !arr.length) return undefined;
    if (t <= arr[0][0]) return arr[0][1];
    for (var i = 1; i < arr.length; i++) {
      if (t <= arr[i][0]) { var a = arr[i - 1], b = arr[i], u = (t - a[0]) / Math.max(1e-6, b[0] - a[0]); u = u * u * (3 - 2 * u); return a[1] + (b[1] - a[1]) * u; }
    }
    return arr[arr.length - 1][1];
  }
  function ease(u) { u = Math.max(0, Math.min(1, u)); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }
  function ruido(t, s) { return Math.sin(t * 13.1 + s) * 0.5 + Math.sin(t * 7.3 + s * 2.1) * 0.3 + Math.sin(t * 23.7 + s * 3.3) * 0.2; }

  // ojo: CAT y EST son "let" en tablero.html, no están en window
  function gCAT() { return typeof CAT !== "undefined" ? CAT : null; }
  function gEST() { return typeof EST !== "undefined" ? EST : null; }
  function gF(n) { return typeof window[n] === "function" ? window[n] : null; }

  // estilos de la capa de cine
  var CSS = ".cine3d{position:absolute;inset:0;pointer-events:none;z-index:5;font-family:'Inter',system-ui,sans-serif;color:#eef2f5}" +
    ".cine3d .franja{position:absolute;left:0;right:0;height:0;background:#000;transition:height .7s ease}" +
    ".cine3d .franja.arr{top:0}.cine3d .franja.aba{bottom:0}.cine3d.on .franja{height:10.5%}" +
    ".cine3d .velo{position:absolute;inset:0;background:#000;opacity:0;transition:opacity .35s ease}" +
    ".cine3d .vigneta{position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(0,0,0,0) 55%,rgba(0,0,0,.55) 100%);opacity:0;transition:opacity .7s}.cine3d.on .vigneta{opacity:1}" +
    ".cine3d .titulo{position:absolute;left:6%;top:16%;max-width:70%;opacity:0;transform:translateY(8px);transition:opacity .8s ease,transform .8s ease}" +
    ".cine3d .titulo.vis{opacity:1;transform:none}" +
    ".cine3d .titulo small{display:block;font:600 11px/1.2 'Inter',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:#f08a3c;margin-bottom:6px}" +
    ".cine3d .titulo b{display:block;font:700 clamp(20px,4.2vw,42px)/1.05 'Space Grotesk','Inter',sans-serif;letter-spacing:.01em;text-shadow:0 2px 18px rgba(0,0,0,.6)}" +
    ".cine3d .titulo span{display:block;margin-top:6px;font:400 clamp(12px,1.8vw,17px)/1.3 'Inter',sans-serif;color:#b9c4cc}" +
    ".cine3d .texto{position:absolute;left:8%;right:8%;bottom:13.5%;text-align:center;font:500 clamp(12px,2vw,19px)/1.35 'Inter',sans-serif;text-shadow:0 1px 3px #000,0 0 22px rgba(0,0,0,.8);opacity:0;transition:opacity .45s ease}" +
    ".cine3d .texto.vis{opacity:1}" +
    ".cine3d canvas.c3mini{position:absolute;right:2.2%;top:calc(10.5% + 10px);opacity:0;transition:opacity .6s}.cine3d.on canvas.c3mini{opacity:1}" +
    ".cine3d .saltar{position:absolute;right:14px;top:calc(10.5% - 34px);pointer-events:auto;font:600 12px 'Inter',sans-serif;color:#d6dde3;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.25);border-radius:6px;padding:4px 10px;cursor:pointer;opacity:0;transition:opacity .4s}" +
    ".cine3d.on .saltar{opacity:1}.cine3d .saltar:hover{background:rgba(255,255,255,.16)}" +
    ".cine3d .c3barra{position:absolute;left:0;bottom:0;height:2px;background:#f08a3c;width:0}" +
    ".cine3d canvas.fundido{position:absolute;inset:0;width:100%;height:100%;opacity:0}" +
    ".cine3d .pc{position:absolute;right:92px;top:calc(10.5% - 34px);pointer-events:auto;font:600 12px 'Inter',sans-serif;color:#d6dde3;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.25);border-radius:6px;padding:4px 10px;cursor:pointer;opacity:0;transition:opacity .4s}" +
    ".cine3d.on .pc{opacity:1}.cine3d .pc:hover{background:rgba(255,255,255,.16)}" +
    ".cine3d.espera .saltar,.cine3d.espera canvas.c3mini,.cine3d.espera .c3barra{display:none}.cine3d.espera .pc{right:14px}" +
    ".cine3d .tono{position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,170,110,.10),rgba(255,140,70,.16) 60%,rgba(120,60,40,.22));mix-blend-mode:soft-light;opacity:0;transition:opacity 1s}.cine3d.on .tono{opacity:1}" +
    ".cine3d.espera .titulo{left:0;top:13%;max-width:58%;padding:14px 48px 16px 5%;background:linear-gradient(90deg,rgba(6,10,16,.72) 0,rgba(6,10,16,.5) 70%,rgba(6,10,16,0))}" +
    ".cine3d.espera .titulo b{font-size:clamp(18px,3.3vw,34px)}.cine3d.espera .titulo span{color:#e3e9ee;font-size:clamp(12px,1.6vw,16px)}" +
    ".cine3d.chico canvas.c3mini{top:auto;bottom:calc(10.5% + 4px);right:2%}.cine3d.chico .titulo{left:5%;top:13%;max-width:90%}.cine3d.chico .titulo b{font-size:clamp(15px,5.5vw,22px)}.cine3d.chico .titulo span{display:none}.cine3d.chico .texto{left:4%;right:4%;font-size:12px}";

  function crear(ctx) {
    var T = ctx.THREE, scene = ctx.scene, camera = ctx.camera, H = ctx.H, st = ctx.st;
    var V = function (x, y, z) { return new T.Vector3(x, y, z); };
    if (!document.getElementById("cine3d-css")) { var s = document.createElement("style"); s.id = "cine3d-css"; s.textContent = CSS; document.head.appendChild(s); }

    // capa HTML
    var capa = document.createElement("div"); capa.className = "cine3d"; capa.hidden = true;
    capa.innerHTML = '<canvas class="fundido"></canvas><div class="tono"></div><div class="vigneta"></div><div class="franja arr"></div><div class="franja aba"></div><div class="titulo"><small></small><b></b><span></span></div>' +
      '<div class="texto"></div><canvas class="c3mini"></canvas><button type="button" class="pc" title="Pantalla completa">⛶ Pantalla completa</button><button type="button" class="saltar">Saltar ▸</button><div class="c3barra"></div><div class="velo"></div>';
    ctx.cont.appendChild(capa);
    var elTit = capa.querySelector(".titulo"), elTxt = capa.querySelector(".texto"), elVelo = capa.querySelector(".velo"), elBarra = capa.querySelector(".c3barra"), cvMini = capa.querySelector("canvas.c3mini");
    capa.querySelector(".saltar").onclick = function () { terminar(); };
    var elPC = capa.querySelector(".pc"), cvFun = capa.querySelector("canvas.fundido"), funT = 0, FUN = 0.7;
    elPC.onclick = function () { if (ctx.pantallaCompleta) ctx.pantallaCompleta(); };
    if (!ctx.pantallaCompleta) elPC.hidden = true;
    function rotularPC(on) { elPC.textContent = on ? "Salir de pantalla completa" : "⛶ Pantalla completa"; }
    // fundido: la última imagen del plano viejo se desvanece encima del nuevo
    // (lo maneja el reloj del cine, no el CSS)
    function fundir() {
      if (!ctx.renderer) return;
      var cv = ctx.renderer.domElement; ctx.renderer.render(scene, camera);
      if (cvFun.width !== cv.width || cvFun.height !== cv.height) { cvFun.width = cv.width; cvFun.height = cv.height; }
      var g = cvFun.getContext("2d"); g.clearRect(0, 0, cvFun.width, cvFun.height); g.drawImage(cv, 0, 0);
      funT = FUN; cvFun.style.opacity = 1;
    }
    function pasoFundido(dt) { if (funT <= 0) return; funT -= dt; var u = Math.max(0, funT / FUN); cvFun.style.opacity = (u * u * (3 - 2 * u)).toFixed(3); }

    // partículas propias (chispas, fogonazos, polvo)
    var PART = (function () {
      var c = document.createElement("canvas"); c.width = c.height = 64; var g = c.getContext("2d"), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.35, "rgba(255,255,255,.5)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64); var tex = new T.CanvasTexture(c);
      var pool = [], N = 220, sig = 0;
      var destello = new T.PointLight(0xff8a3a, 0, 16, 2), destelloT = 0; scene.add(destello);
      for (var i = 0; i < N; i++) {
        var sp = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, opacity: 0 }));
        sp.visible = false; scene.add(sp); pool.push({ sp: sp, vida: 0, max: 1, v: V(0, 0, 0), g: 0, s0: 1, s1: 1, a0: 1 });
      }
      var TIPOS = {
        chispa: { color: 0xffc35a, add: true, s0: 0.12, s1: 0.04, a0: 1, vida: 0.7, vel: 5, g: -9 },
        fogonazo: { color: 0xff7a26, add: true, s0: 0.45, s1: 1.1, a0: 0.85, vida: 0.24, vel: 0.6, g: 0 },
        fuego: { color: 0xff8a2a, add: true, s0: 0.45, s1: 0.1, a0: 0.95, vida: 0.5, vel: 1.6, g: 2.8, tonos: [0xff5a14, 0xff8a2a, 0xffb347, 0xffd27a] },
        brasa: { color: 0xffb347, add: true, s0: 0.09, s1: 0.03, a0: 1, vida: 1.3, vel: 3.2, g: -3 },
        polvo: { color: 0x8a7b62, add: false, s0: 2.0, s1: 6.5, a0: 0.32, vida: 2.2, vel: 9, g: 0.4 }
      };
      function emitir(pos, tipo, n, dir) {
        var D = TIPOS[tipo];
        for (var k = 0; k < (n || 1); k++) {
          var p = pool[sig]; sig = (sig + 1) % N;
          p.sp.position.copy(pos); p.sp.material.color.set(D.tonos ? D.tonos[(Math.random() * D.tonos.length) | 0] : D.color); p.sp.material.blending = D.add ? T.AdditiveBlending : T.NormalBlending;
          if (tipo === "fogonazo") { destello.position.copy(pos); destelloT = 0.2; }
          if (dir) p.v.copy(dir).multiplyScalar(D.vel * (0.6 + Math.random() * 0.6)).add(V((Math.random() - 0.5) * 0.8, Math.random() * 0.6, (Math.random() - 0.5) * 0.8));
          else p.v.set((Math.random() - 0.5) * D.vel, Math.random() * D.vel * 0.6, (Math.random() - 0.5) * D.vel);
          p.g = D.g; p.s0 = D.s0; p.s1 = D.s1; p.a0 = D.a0; p.max = D.vida * (0.7 + Math.random() * 0.6); p.vida = p.max; p.sp.visible = true;
        }
      }
      function paso(dt) {
        destelloT = Math.max(0, destelloT - dt); destello.intensity = destelloT > 0 ? 7 * (destelloT / 0.2) * (0.7 + Math.random() * 0.3) : 0;
        pool.forEach(function (p) {
          if (p.vida <= 0) return; p.vida -= dt; if (p.vida <= 0) { p.sp.visible = false; return; }
          var f = 1 - p.vida / p.max; p.v.y += p.g * dt; p.v.multiplyScalar(Math.exp(-dt * 1.2)); p.sp.position.addScaledVector(p.v, dt);
          var s = p.s0 + (p.s1 - p.s0) * f; p.sp.scale.set(s, s, s); p.sp.material.opacity = p.a0 * (1 - f);
          if (p.sp.position.y < s * 0.5) { p.sp.position.y = s * 0.5; p.v.y = Math.abs(p.v.y) * 0.3; p.v.x *= 0.6; p.v.z *= 0.6; }   // que no atraviesen el piso
        });
      }
      function apagar() { pool.forEach(function (p) { p.vida = 0; p.sp.visible = false; }); destelloT = 0; destello.intensity = 0; }
      return { emitir: emitir, paso: paso, apagar: apagar };
    })();

    // mini tablero (carátulas de la página)
    var imgs = {};
    function carImg(id) {
      var C = gCAT(), car = C && C.caratulas && C.caratulas[id]; if (!car) return null;
      if (!imgs[id]) { imgs[id] = new Image(); imgs[id].src = "/caratulas/" + car.archivo; }
      return imgs[id].complete && imgs[id].naturalWidth ? { im: imgs[id], car: car } : null;
    }
    function instr(id) { var C = gCAT(); return C && (C.instrumentos || []).filter(function (x) { return x.id === id; })[0]; }
    function giro(it, v) { try { var f = gF("giroAguja"); return f ? f(it, v) : null; } catch (e) { return null; } }
    var CORTO = { TACH_ENG: "MOTOR Y ASPAS", AIRSPEED: "VELOCIDAD", ALTIMETER: "ALTURA", VSI: "SUBE / BAJA", OIL_PRESS: "PRES. ACEITE", OIL_TEMP: "TEMP. ACEITE", AMMETER: "CARGA",
      VOLTMETER: "VOLTAJE", CARB_AIR_TEMP: "CARBURADOR", MAP: "POTENCIA", XMSN_OIL_PRESS: "ACEITE TRANSM.", XMSN_OIL_TEMP: "TEMP. TRANSM.", FUEL_QTY_FWD: "NAFTA DEL.",
      FUEL_QTY_AFT: "NAFTA TRAS.", FUEL_PRESS: "PRES. NAFTA", TURN: "GIRO", ATT_ROLL: "HORIZONTE", COMPASS: "BRÚJULA", CHT: "TEMP. MOTOR" };
    var LUCES = { LT_STARTER: ["ENCENDIDO", "#5fdc6f"], LT_GEN: ["GENERADOR", "#ff4433"], LT_XMSN_PRESS: ["PRES. TRANSM.", "#ff4433"], LT_FUEL_FWD: ["COMB. DEL.", "#ffb02e"], LT_FUEL_AFT: ["COMB. TRAS.", "#ffb02e"], LT_LOW_ROTOR: ["ROTOR BAJO", "#ff4433"] };
    function aguja(g, cx, cy, ang, largo, color, ancho) {
      g.save(); g.translate(cx, cy); g.rotate(ang * D2R); g.fillStyle = color; g.beginPath();
      g.moveTo(-ancho / 2, ancho * 2); g.lineTo(-ancho * 0.3, -largo); g.lineTo(ancho * 0.3, -largo); g.lineTo(ancho / 2, ancho * 2); g.closePath(); g.fill(); g.restore();
    }
    function dibujarMini(valores, luces) {
      var ids = clip.mini || [], n = ids.length; if (!n) { cvMini.style.display = "none"; return; }
      cvMini.style.display = "";
      var w0 = ctx.cont.clientWidth, h0 = ctx.cont.clientHeight, chico = w0 < 700 || h0 < 420, pad = chico ? 6 : 10, hLuz = Object.keys(luces).length ? 22 : 0;
      var d = chico ? Math.max(30, Math.min(52, (w0 * 0.5 - (n + 1) * pad) / n, h0 * 0.14)) : Math.max(64, Math.min(104, w0 * 0.085));
      capa.classList.toggle("chico", chico);
      var W = n * d + (n + 1) * pad, Hh = d + (chico ? 16 : 24) + pad * 2 + hLuz, k = Math.min(2, window.devicePixelRatio || 1);
      elTit.style.maxWidth = chico ? "" : Math.max(220, w0 * 0.92 - W - 24 - w0 * 0.06) + "px";
      elTxt.style.bottom = ""; elTxt.style.right = chico ? (W + w0 * 0.04) + "px" : "";   // pantalla chica: mini abajo a la derecha, texto a su izquierda
      if (cvMini.width !== Math.round(W * k) || cvMini.height !== Math.round(Hh * k)) { cvMini.width = Math.round(W * k); cvMini.height = Math.round(Hh * k); cvMini.style.width = W + "px"; cvMini.style.height = Hh + "px"; }
      var g = cvMini.getContext("2d"); g.setTransform(k, 0, 0, k, 0, 0); g.clearRect(0, 0, W, Hh);
      g.fillStyle = "rgba(8,11,15,.78)"; g.strokeStyle = "rgba(255,255,255,.12)"; g.lineWidth = 1;
      g.beginPath(); if (g.roundRect) g.roundRect(0.5, 0.5, W - 1, Hh - 1, 8); else g.rect(0.5, 0.5, W - 1, Hh - 1); g.fill(); g.stroke();
      ids.forEach(function (id, i) {
        var cx = pad + i * (d + pad) + d / 2, cy = pad + d / 2, r = d / 2, it = instr(id), v = valores[id];
        g.fillStyle = "#08090a"; g.beginPath(); g.arc(cx, cy, r, 0, 7); g.fill();
        var ci = carImg(id);
        if (ci) { var kk = r * 0.93 / ci.car.R, L = ci.car.L * kk; g.drawImage(ci.im, cx - L / 2, cy - L / 2, L, L); }
        else if (id === "ATT_ROLL") {
          g.save(); g.beginPath(); g.arc(cx, cy, r * 0.86, 0, 7); g.clip(); g.translate(cx, cy); g.rotate(-(v || 0) * D2R);
          g.fillStyle = "#2c6c9e"; g.fillRect(-r, -r, 2 * r, r); g.fillStyle = "#6b4a22"; g.fillRect(-r, 0, 2 * r, r); g.fillStyle = "#f4f3ee"; g.fillRect(-r, -1, 2 * r, 2); g.restore();
          g.strokeStyle = "#f2c230"; g.lineWidth = 3; g.beginPath(); g.moveTo(cx - r * 0.5, cy); g.lineTo(cx - r * 0.12, cy); g.moveTo(cx + r * 0.12, cy); g.lineTo(cx + r * 0.5, cy); g.stroke();
        }
        if (it && v !== undefined && id !== "ATT_ROLL") {
          var a = giro(it, v);
          if (a !== null) {
            if (id === "TACH_ENG") { var ir = instr("TACH_ROT"), ar = ir ? giro(ir, valores.TACH_ROT || 0) : null; if (ar !== null) aguja(g, cx, cy, ar, r * 0.5, "#ff9f38", r * 0.05); }
            aguja(g, cx, cy, a, r * (id === "COMPASS" ? 0.7 : 0.74), id === "COMPASS" ? "#ffce4a" : "#f4f8fd", r * 0.055);
            g.fillStyle = "#2a2d30"; g.beginPath(); g.arc(cx, cy, r * 0.06, 0, 7); g.fill();
          }
        }
        var fz = Math.max(chico ? 7 : 9, d * 0.105), et = CORTO[id] || id; g.font = "600 " + fz + "px Inter, sans-serif";
        var ancho = g.measureText(et).width; if (ancho > d + pad - 3) { fz = Math.max(6, fz * (d + pad - 3) / ancho); g.font = "600 " + fz.toFixed(1) + "px Inter, sans-serif"; }
        g.fillStyle = "#9fb0bd"; g.textAlign = "center";
        g.fillText(CORTO[id] || id, cx, pad + d + (chico ? 12 : 15));
      });
      var lk = Object.keys(luces);
      if (lk.length) {
        var wl = (W - pad * 2 - (lk.length - 1) * 6) / lk.length;
        lk.forEach(function (id, i) {
          var L = LUCES[id] || [id, "#ffb02e"], on = luces[id], x = pad + i * (wl + 6), y = Hh - pad - 16;
          g.fillStyle = on ? L[1] : "rgba(255,255,255,.07)"; g.fillRect(x, y, wl, 16);
          g.fillStyle = on ? "#140c06" : "rgba(220,220,210,.45)"; g.font = "700 9px Inter, sans-serif"; g.textAlign = "center"; g.fillText(L[0], x + wl / 2, y + 11.5);
        });
      }
    }

    // estado del clip
    var gen = 0, clip = null, idClip = null, t = 0, fin = 0, dur = 1, plano = -1, txtAct = -2, titOn = false, cerrando = 0;
    var P0 = { x: 0, z: 0, yaw: 0 }, plantada = V(0, 0, 0), acum = {}, prev = { alt: 0 }, info = {};
    var tmp = V(0, 0, 0), tmp2 = V(0, 0, 0), foco = V(0, 0, 0), ultimoMini = 0;

    function activo() { return !!clip; }
    function iniciar(id, extra) {
      var c = CLIPS[id]; if (!c) return false;
      gen++; clip = c; idClip = id; info = extra || {}; t = 0; fin = 0; plano = -1; txtAct = -2; titOn = false; cerrando = 0; acum = {}; funT = 0; cvFun.style.opacity = 0;
      esp.on = false; capa.classList.remove("espera"); elTxt.style.bottom = "";
      P0.x = st.x; P0.z = st.z; P0.yaw = st.yaw;
      // Actividades y accidentes son una presentación corta: cortan en el primer
      // cambio de plano después de los 12 s. Lo que venga después lo muestran
      // las fallas sueltas cuando el simulador las mete.
      dur = c.dur;
      if (!c.vivo) { var corte = c.planos.map(function (p) { return p.t1; }).filter(function (x) { return x >= 12; })[0]; dur = Math.min(c.dur, corte || 14); }
      capa.hidden = false; void capa.offsetWidth; capa.classList.add("on");
      elVelo.style.opacity = 1; setTimeout(function () { elVelo.style.opacity = 0; }, 60);
      var tt = elTit.querySelectorAll("small,b,span");
      tt[0].textContent = c.vivo ? "Falla · " + (c.sub || "") : (c.grave ? "Emergencia" : (id.indexOf("ACT_") === 0 ? "Vuelo" : "Accidente"));
      tt[1].textContent = c.vivo ? (info.nombre || "Falla") : c.titulo;
      tt[2].textContent = c.vivo ? (c.texto2 || info.afuera || "") : (c.sub || "");
      ctx.ambiente(true, c.niebla);
      return true;
    }
    function terminar() {
      if (!clip) return;
      elVelo.style.opacity = 1;
      var mio = gen;
      setTimeout(function () {
        if (mio !== gen) return;          // mientras cerraba, arrancó otro clip
        clip = null; idClip = null; PART.apagar(); capa.classList.remove("on"); elTit.classList.remove("vis"); elTxt.classList.remove("vis");
        capa.hidden = true; elVelo.style.opacity = 0; ctx.ambiente(false); H.faro(0); ctx.termino();
      }, 380);
      cerrando = 1;
    }

    // el helicóptero según el guion
    function valoresMini() {
      var o = {}, fV = gF("V");
      (clip.mini || []).concat(["TACH_ROT"]).forEach(function (id) { o[id] = fV ? fV(id) : 0; });
      return o;
    }
    function lucesMini() {
      var o = {}, L = clip.lucesTablero;
      var fl = gF("luzEncendida"), E = gEST(), real = function (id) { return fl && E ? !!fl(E.instrumentos && E.instrumentos[id]) : false; };
      if (clip.vivo) { var luz = LUZ_DE[info.id]; if (luz) o[luz] = real(luz); return o; }
      Object.keys(L || {}).forEach(function (id) { o[id] = real(id); });   // luces reales, no las del guion
      return o;
      Object.keys(L || {}).forEach(function (id) { o[id] = L[id].some(function (r) { return t >= r[0] && t <= r[1]; }); });
      return o;
    }

    // efectos
    function punto(n) {
      var P = H.puntos;
      if (n === "rejillas") n = Math.random() < 0.5 ? "rejillaIzq" : "rejillaDer";
      if (n === "baliza") return H.grupo.localToWorld(tmp2.set(P.careno.x + 1.6, P.careno.y + 0.1, 0));
      return H.grupo.localToWorld(tmp2.copy(P[n] || P.cg));
    }
    function efectos(dt) {
      (clip.vivo ? clip.efectos || [] : []).forEach(function (e, i) {
        if (t < e.t[0] || t > e.t[1]) return;
        var clave = "e" + i; acum[clave] = (acum[clave] || 0) + (e.tasa || 1) * dt;
        while (acum[clave] >= 1) {
          acum[clave] -= 1;
          var pnt = e.punto === "rejillas" ? (Math.random() < 0.5 ? H.puntos.rejillaIzq : H.puntos.rejillaDer) : (H.puntos[e.punto] || H.puntos.cg);
          if (e.tipo === "humo") ctx.Humo.emitir(pnt, e.color || "gris");
          else if (e.tipo === "tos") { ctx.Humo.emitir(pnt, e.color || "gris", 5, 2.4); }
          else if (e.tipo === "fogonazo") PART.emitir(punto(e.punto), "fogonazo", 2);
          else if (e.tipo === "fuego") { PART.emitir(punto(e.punto), "fuego", 2, V(0, 1, 0)); if (Math.random() < 0.35) PART.emitir(punto(e.punto), "brasa", 1); }
          else if (e.tipo === "chispas") PART.emitir(punto(e.punto), "chispa", 3);
        }
      });
      // escape normal y polvo del rotor; el humo de las fallas lo pone vuelo3d.js
      if (true) {
        if (st.alt < 9 && st.rpm > 140) {
          var tasa = (1 - st.alt / 9) * (st.rpm / 215) * (ctx.calidad() === "alta" ? 26 : 12);
          acum.polvo = (acum.polvo || 0) + tasa * dt;
          while (acum.polvo >= 1) {
            acum.polvo -= 1; var a = Math.random() * Math.PI * 2, r = 3 + Math.random() * 4;
            PART.emitir(tmp.set(st.x + Math.cos(a) * r, 0.4, st.z + Math.sin(a) * r), "polvo", 1, tmp2.set(Math.cos(a), 0.15, Math.sin(a)));
          }
        }
      }
    }

    // cámara
    function ejes() {
      var y = st.yaw; return { f: V(Math.sin(y), 0, -Math.cos(y)), r: V(Math.cos(y), 0, Math.sin(y)) };
    }
    function centro() { return V(st.x, st.alt + 1.5, st.z); }
    function local(o, E, c) { return (c || centro()).clone().addScaledVector(E.f, o[0]).add(V(0, o[1], 0)).addScaledVector(E.r, o[2]); }
    // fuselaje, cabina, cola y pilón como cápsulas para que la cámara no se meta
    // (salvo el plano "cabina", que va adentro a propósito)
    var CAPS = [[V(0.9, 1.7, 0), V(8.6, 1.75, 0), 1.25], [V(1.8, 3.0, 0), V(9.4, 3.0, 0), 0.8], [V(9.4, 2.7, 0), V(13.6, 3.5, 0), 0.55], [V(12.2, 2.7, 0), V(13.4, 4.9, 0), 0.45]];
    var cl = V(0, 0, 0), ab = V(0, 0, 0), lc = V(0, 0, 0);
    function afuera(pos) {
      H.grupo.updateWorldMatrix(true, false); lc.copy(pos); H.grupo.worldToLocal(lc);
      var movio = false;
      CAPS.forEach(function (c) {
        ab.subVectors(c[1], c[0]); var u = Math.max(0, Math.min(1, lc.clone().sub(c[0]).dot(ab) / ab.lengthSq()));
        cl.copy(c[0]).addScaledVector(ab, u); var d = lc.distanceTo(cl), lim = c[2] + 0.45;
        if (d < lim) { if (d < 1e-4) lc.y += lim; else lc.sub(cl).multiplyScalar(lim / d).add(cl); movio = true; }
      });
      // tampoco en el disco que barren las palas
      var m = H.puntos.mastil, dx = lc.x - m.x, dz = lc.z - m.z;
      if (dx * dx + dz * dz < 8.8 * 8.8 && lc.y > m.y - 1 && lc.y < m.y + 0.6) { lc.y = lc.y < m.y - 0.2 ? m.y - 1 : m.y + 0.6; movio = true; }
      if (movio) H.grupo.localToWorld(pos.copy(lc));
    }
    function ponerPlano(p, e, tt) {
      var E = ejes(), C = centro();
      var fov = p.fov0 !== undefined ? p.fov0 + (p.fov1 - p.fov0) * e : (p.fov || 40) * (p.tipo === "orbita" || p.tipo === "cabina" ? 1 : 1 - 0.06 * e);   // acercamiento lento
      var mira = C.clone();
      if (p.tipo === "seguir") { camera.position.copy(local(p.de.map(function (a, k) { return a + (p.a[k] - a) * e; }), E, C)); }
      else if (p.tipo === "orbita") {
        var ang = (p.a0 + (p.a1 - p.a0) * e) * D2R; camera.position.copy(C).addScaledVector(E.f, Math.cos(ang) * p.r).addScaledVector(E.r, Math.sin(ang) * p.r).add(V(0, p.h, 0));
      } else if (p.tipo === "pieza") {
        H.grupo.updateWorldMatrix(true, false);
        H.grupo.localToWorld(camera.position.set.apply(camera.position, p.de.map(function (a, k) { return a + (p.a[k] - a) * e; })));
        H.grupo.localToWorld(mira.set(p.mira[0], p.mira[1], p.mira[2]));
      } else if (p.tipo === "plantada") { camera.position.copy(plantada); if (camera.position.y < 0.6) camera.position.y = 0.6; }
      else if (p.tipo === "detalle") {
        mira.copy(p.mira === "baliza" ? punto("baliza") : punto(p.punto));
        camera.position.copy(local(p.de.map(function (a, k) { return a + (p.a[k] - a) * e; }), E, mira));
      } else if (p.tipo === "cabina") {
        H.grupo.localToWorld(camera.position.copy(H.puntos.ojo));
        var q = new T.Quaternion(); ctx.act.getWorldQuaternion(q);
        camera.quaternion.copy(q).multiply(new T.Quaternion().setFromEuler(new T.Euler(-7 * D2R, Math.PI / 2, 0, "YXZ")));
      }
      if (p.mira && p.tipo !== "detalle" && p.tipo !== "pieza" && Array.isArray(p.mira)) mira.copy(local(p.mira, E, V(st.x, st.alt, st.z)));
      if (p.temblor) { var a2 = p.temblor * (0.6 + 0.4 * Math.abs(ruido(tt * 0.7, 9))); camera.position.add(V(ruido(tt, 1) * a2, ruido(tt, 2) * a2, ruido(tt, 3) * a2)); }
      if (p.tipo !== "cabina") { afuera(camera.position); if (camera.position.y < 0.5) camera.position.y = 0.5; camera.lookAt(mira); }
      if (Math.abs(camera.fov - fov) > 0.01) { camera.fov = fov; camera.updateProjectionMatrix(); }
    }
    function camara(dt) {
      var ps = clip.planos, i = 0; while (i < ps.length - 1 && t > ps[i].t1) i++;
      var p = ps[i], u = (t - p.t0) / Math.max(0.01, p.t1 - p.t0), e = ease(u);
      if (i !== plano) {             // corte con fundido
        if (plano >= 0) fundir();
        plano = i; if (p.tipo === "plantada") plantada.copy(local(p.de, ejes(), centro()));
      }
      ponerPlano(p, e, t);
    }

    // mientras se espera al profe la cámara recorre las partes, con nombre y una frase
    var PARTES = [   // de/a: cámara al empezar y al terminar; mira: a dónde apunta (x hacia la cola, +z a la izquierda)
      { n: "El H-08", d: "Un Sikorsky H-19A, el helicóptero que voló en la Fuerza Aérea Argentina.", dur: 10, tipo: "orbita", r: 18, h: 2.2, a0: 210, a1: 250, fov: 40 },
      { n: "El rotor principal", d: "Las aspas grandes de arriba: al girar, lo sostienen en el aire.", dur: 8, tipo: "pieza", de: [-7, 7.8, 7.5], a: [-5, 7, 8.5], mira: [4.5, 3.4, 0], fov: 50 },
      { n: "El motor", d: "Va adentro de la nariz, detrás de esas dos puertas redondas.", dur: 8, tipo: "pieza", de: [-6.5, 2.4, 4.2], a: [-5.4, 2.0, 3.0], mira: [0.8, 1.5, 0], fov: 40 },
      { n: "El escape", d: "Este caño redondo: por acá sale el humo cuando el motor anda.", dur: 7, tipo: "pieza", de: [3.4, 0.8, 3.4], a: [2.6, 0.85, 2.7], mira: [0.5, 0.98, 1.05], fov: 38 },
      { n: "La cabina", d: "Los dos pilotos van arriba, por encima del motor.", dur: 8, tipo: "pieza", de: [-4, 5, -4.5], a: [-3, 4.4, -3.6], mira: [2.6, 2.8, 0], fov: 42 },
      { n: "El rotor de cola", d: "La hélice chica de atrás: no deja que el helicóptero gire sobre sí mismo.", dur: 8, tipo: "pieza", de: [8, 3, -7.5], a: [9.6, 3.4, -6.6], mira: [12.4, 3.7, -0.3], fov: 42 },
      { n: "Las ruedas", d: "Cuatro ruedas para apoyarse en el piso.", dur: 7, tipo: "pieza", de: [-1.5, 0.9, 7], a: [0.5, 0.75, 6.4], mira: [4, 0.6, 0], fov: 44 }
    ];
    var esp = { on: false, i: 0, t: 0 };
    function enEspera() { return esp.on; }
    function rotularEspera() {
      var P = PARTES[esp.i], tt = elTit.querySelectorAll("small,b,span");
      tt[0].textContent = "Mientras esperamos al profesor"; tt[1].textContent = P.n; tt[2].textContent = P.d;
      elTit.classList.remove("vis"); setTimeout(function () { if (esp.on) elTit.classList.add("vis"); }, 250);
    }
    function esperaInicio() {
      if (clip) return;
      esp.on = true; esp.i = 0; esp.t = 0; PART.apagar();
      capa.hidden = false; capa.classList.add("espera"); void capa.offsetWidth; capa.classList.add("on");
      elTxt.textContent = "El vuelo empieza cuando el profesor activa el tablero."; elTxt.classList.add("vis"); elTxt.style.bottom = ""; elTxt.style.right = "";
      ctx.ambiente(true); rotularEspera();
    }
    function esperaPaso(dt) {
      if (!esp.on) return;
      esp.t += dt; var P = PARTES[esp.i];
      if (esp.t > P.dur) { fundir(); esp.i = (esp.i + 1) % PARTES.length; esp.t = 0; P = PARTES[esp.i]; rotularEspera(); }
      ctx.act.updateWorldMatrix(true, true);
      ponerPlano(P, ease(esp.t / P.dur), esp.t); PART.paso(dt); pasoFundido(dt);
    }
    function esperaFin(sigueCine) {
      if (!esp.on) return;
      esp.on = false; capa.classList.remove("espera"); elTit.classList.remove("vis"); elTxt.classList.remove("vis"); funT = 0; cvFun.style.opacity = 0;
      if (sigueCine) return;                 // si arranca una cinemática, la capa es de ella
      capa.classList.remove("on"); capa.hidden = true; ctx.ambiente(false); ctx.termino();
    }

    // textos
    function textos() {
      if (!titOn && t > 0.3 && t < 4.2) { elTit.classList.add("vis"); titOn = true; }
      if (titOn && t >= 4.2) { elTit.classList.remove("vis"); titOn = false; }
      var lista = clip.vivo ? [[4.5, dur - 0.6, info.afuera || clip.texto2 || ""]] : [];
      var k = -1; lista.forEach(function (x, i) { if (t >= x[0] && t <= x[1]) k = i; });
      if (k !== txtAct) {
        txtAct = k;
        if (k < 0) elTxt.classList.remove("vis");
        else { elTxt.classList.remove("vis"); var s = lista[k][2]; setTimeout(function () { elTxt.textContent = s; elTxt.classList.add("vis"); }, 120); }
      }
    }

    // un cuadro
    function paso(dt) {
      if (!clip) return false;
      if (cerrando) { PART.paso(dt); return true; }
      t += dt;
      ctx.seguir(dt);                              // el vuelo real, no un guion
      if (!clip) return true;                      // seguir pudo arrancar otra cinemática y cerrar ésta
      ctx.act.updateWorldMatrix(true, true);      // los puntos del helicóptero, ya en su lugar de este cuadro
      efectos(dt); PART.paso(dt);
      camara(dt); textos(); pasoFundido(dt);
      var ahora = performance.now();
      if (ahora - ultimoMini > 90) { ultimoMini = ahora; dibujarMini(valoresMini(), lucesMini()); }
      elBarra.style.width = (100 * Math.min(1, t / dur)).toFixed(1) + "%";
      if (t >= dur) terminar();
      return true;
    }
    return { iniciar: iniciar, terminar: terminar, activo: activo, paso: paso, clips: CLIPS, actividad: ACTIVIDAD, sistema: SISTEMA, id: function () { return idClip; },
      enEspera: enEspera, esperaInicio: esperaInicio, esperaPaso: esperaPaso, esperaFin: esperaFin, rotularPC: rotularPC, partes: PARTES,
      planoActual: function () { return clip && plano >= 0 ? clip.planos[plano] : null; } };
  }

  window.H08Cine = { crear: crear, CLIPS: CLIPS, ACTIVIDAD: ACTIVIDAD, SISTEMA: SISTEMA };
})();
