// -*- coding: utf-8 -*-
// El helicóptero 3D que vuela con el simulador. Lee EST y CAT igual que la
// página y no manda órdenes. Usa EST.vuelo y no las agujas: si una falla de
// indicación hace mentir a un instrumento, el 3D sigue mostrando lo real.
// three.js r128 lo sirve la Pi (/3d/three.min.js) porque en esa wifi no hay internet.
(function () {
  "use strict";
  var D2R = Math.PI / 180;
  // globales de tablero.html; si falta alguno se sigue sin eso
  var GL = {
    EST: function () { return typeof EST !== "undefined" ? EST : null; },
    CAT: function () { return typeof CAT !== "undefined" ? CAT : null; },
    MODO: function () { return typeof MODO !== "undefined" ? MODO : null; },
    V: function () { return typeof V === "function" ? V : null; },
    giroAguja: function () { return typeof giroAguja === "function" ? giroAguja : null; },
    instr: function () { return typeof instr === "function" ? instr : null; },
    luzEncendida: function () { return typeof luzEncendida === "function" ? luzEncendida : null; },
  };
  var G = function (n) { return GL[n] ? GL[n]() : null; }, hay = function (n) { return !!G(n); };
  var guard = function (f) { try { return f(); } catch (e) { return null; } };

  // lo que se ve desde afuera con cada falla (lo de adentro lo cuenta la página)
  var AFUERA = {
    ENG_FAIL_TOTAL: "Sale humo negro y el motor se para. Las aspas siguen girando con el aire.",
    ENG_FAIL_PARTIAL: "Sale humo del escape: el motor no tiene toda su fuerza.",
    MAG_L_FAIL: "El motor tose de a ratos.",
    CARB_ICE: "El motor tose: pierde fuerza de a poco.",
    ENG_ROUGH: "Sale humo negro a bocanadas: el motor anda mal.",
    CHT_OVERHEAT: "Sale humo gris de los costados del motor.",
    OIL_PRESS_LOSS: "Sale humo de aceite quemado de los costados del motor.",
    OIL_OVERHEAT: "Sale humo gris de aceite caliente.",
    FUEL_PUMP_FAIL: "El motor tose porque no le llega bien la nafta.",
    FUEL_LEAK: "Se ve una estela blanca de nafta por debajo.",
    FUEL_STARVATION: "El motor tose y se apaga si no se cambia de tanque.",
    XMSN_PRESS_LOSS: "Sale humo gris de arriba, donde está la caja que mueve las aspas.",
    XMSN_OVERHEAT: "Sale humo gris de arriba, donde está la caja que mueve las aspas.",
    CLUTCH_SLIP: "Sale algo de humo arriba y las aspas no giran como deberían.",
    LOW_ROTOR_RPM: "Las aspas giran lento y se ven más caídas.",
    TAIL_ROTOR_LOSS: "Se para la hélice de la cola y el helicóptero gira sobre sí mismo.",
    GEN_FAIL: "Desde afuera no se ve nada: todo sigue andando con la batería.",
    BATTERY_WEAK: "Desde afuera no se ve nada.",
    ELEC_TOTAL: "Se apaga la luz roja de arriba.",
  };
  var MIENTE = { PITOT_BLOCK: 1, STATIC_BLOCK: 1, GYRO_FAIL: 1, OILP_GAGE_FAIL: 1, TACH_GAGE_FAIL: 1 };

  function iniciar(cont) {
    var LS = function (k, v) { return guard(function () { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); }); };
    var pantalla = hay("MODO") && G("MODO") && G("MODO").pantalla;
    var CAL = LS("h08-3d-calidad") || (pantalla || window.innerWidth < 900 ? "liviana" : "alta");

    // escena
    var renderer = new THREE.WebGLRenderer({ antialias: CAL === "alta", powerPreference: "low-power" });
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.95;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.className = "lienzo3d";
    cont.appendChild(renderer.domElement);
    var scene = new THREE.Scene();
    // near 0,12 (no 0,05): con 0,05 el piso y el helipuerto, separados 2 cm, titilaban de lejos
    var camera = new THREE.PerspectiveCamera(45, 1, 0.12, 5000);
    var controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.1; controls.maxPolarAngle = 1.55; controls.minDistance = 4; controls.maxDistance = 220;
    if (THREE.RoomEnvironment) scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new THREE.RoomEnvironment(), 0.04).texture;
    var col = function (h) { return new THREE.Color(h).convertSRGBToLinear(); };
    (function cielo() {
      var c = document.createElement("canvas"); c.width = 4; c.height = 256;
      var g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 0, 256);
      gr.addColorStop(0, "#2c4877"); gr.addColorStop(0.35, "#5d6f9c"); gr.addColorStop(0.62, "#c9938a"); gr.addColorStop(0.8, "#efb27d"); gr.addColorStop(1, "#f3c690");
      g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
      var t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; scene.background = t;
      scene.fog = new THREE.Fog(0xe2ab84, 260, 2300);
    })();
    // sol bajo de atardecer y cielo de relleno
    var hemi = new THREE.HemisphereLight(col(0x9fb0d6), col(0x6a5844), 0.62); scene.add(hemi);
    var sol = new THREE.DirectionalLight(col(0xffb27a), 2.6);
    sol.shadow.camera.left = sol.shadow.camera.bottom = -22; sol.shadow.camera.right = sol.shadow.camera.top = 22;
    sol.shadow.camera.near = 1; sol.shadow.camera.far = 220; sol.shadow.mapSize.set(1024, 1024); sol.shadow.bias = -0.0005; sol.shadow.normalBias = 0.03;
    scene.add(sol, sol.target);

    // el suelo acompaña al helicóptero, la textura queda quieta en el mundo
    var TILE = 1600;
    var pasto = (function () {
      var c = document.createElement("canvas"); c.width = c.height = 512; var g = c.getContext("2d"), s = 7;
      var rnd = function () { s = (s * 16807) % 2147483647; return s / 2147483647; };
      g.fillStyle = "#6f8a4c"; g.fillRect(0, 0, 512, 512);
      var tonos = ["#7a9353", "#667f45", "#8a9a5a", "#5f7a40", "#9a9a62", "#738c4b"];
      for (var i = 0; i < 9; i++) { g.fillStyle = tonos[i % tonos.length]; g.fillRect(rnd() * 512, rnd() * 512, 60 + rnd() * 200, 40 + rnd() * 160); }
      for (i = 0; i < 2600; i++) { g.fillStyle = "rgba(" + (40 + rnd() * 50 | 0) + "," + (60 + rnd() * 50 | 0) + ",30," + (0.12 + rnd() * 0.12).toFixed(2) + ")"; g.fillRect(rnd() * 512, rnd() * 512, 2 + rnd() * 5, 2 + rnd() * 5); }
      g.strokeStyle = "rgba(110,95,60,.5)"; g.lineWidth = 3; g.beginPath(); g.moveTo(0, 300); g.lineTo(512, 270); g.moveTo(180, 0); g.lineTo(220, 512); g.stroke();
      var t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4;
      return t;
    })();
    var REP = 160, suelo = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000), new THREE.MeshStandardMaterial({ map: pasto, roughness: 1 }));
    suelo.rotation.x = -Math.PI / 2; suelo.receiveShadow = true; pasto.repeat.set(8000 / REP, 8000 / REP); scene.add(suelo);

    // helipuerto y hangar del Taller Regional Quilmes, formas simples
    var baseMats = [];
    (function base() {
      var c = document.createElement("canvas"); c.width = c.height = 512; var g = c.getContext("2d");
      g.fillStyle = "#9c9e9b"; g.fillRect(0, 0, 512, 512);
      g.strokeStyle = "#f2f2ee"; g.lineWidth = 14; g.beginPath(); g.arc(256, 256, 190, 0, 7); g.stroke();
      g.fillStyle = "#f2f2ee"; g.fillRect(176, 136, 40, 240); g.fillRect(296, 136, 40, 240); g.fillRect(216, 236, 80, 40);
      g.strokeStyle = "#e0b43a"; g.lineWidth = 10; g.strokeRect(10, 10, 492, 492);
      var t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; t.anisotropy = 4;
      // polygonOffset para que la H no titile contra el pasto
      var pad = new THREE.Mesh(new THREE.PlaneGeometry(36, 36), new THREE.MeshStandardMaterial({ map: t, roughness: 0.95, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 }));
      pad.rotation.x = -Math.PI / 2; pad.position.y = 0.005; pad.receiveShadow = true; scene.add(pad);
      var chapa = new THREE.MeshStandardMaterial({ color: col(0xa9b0b5), roughness: 0.5, metalness: 0.5 });
      var cuerpo = new THREE.Mesh(new THREE.BoxGeometry(34, 9, 26), chapa); cuerpo.position.set(-48, 4.5, -38);
      // techo: medio cilindro un poco más largo que el galpón, si no las tapas
      // quedaban en el plano de las paredes y titilaban
      var tg = new THREE.CylinderGeometry(13, 13, 34.6, 28, 1, false, 0, Math.PI); tg.rotateZ(Math.PI / 2);
      var techo = new THREE.Mesh(tg, chapa); techo.scale.set(1, 0.35, 1); techo.position.set(-48, 9, -38);
      var porton = new THREE.Mesh(new THREE.PlaneGeometry(24, 8), new THREE.MeshStandardMaterial({ color: col(0x3a4046), roughness: 0.7, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 })); porton.position.set(-48, 4, -24.9);
      [cuerpo, techo].forEach(function (m) { m.castShadow = m.receiveShadow = true; });
      scene.add(cuerpo, techo, porton); baseMats.push(pad.material, chapa, porton.material);
    })();
    // árboles: baldosa de 1600 m repetida 3 x 3
    var arboles = new THREE.Group(); scene.add(arboles);
    (function () {
      var s = 11, rnd = function () { s = (s * 16807) % 2147483647; return s / 2147483647; }, N = 170, pos = [];
      while (pos.length < N) { var x = (rnd() - 0.5) * TILE, z = (rnd() - 0.5) * TILE; if (Math.hypot(x, z) > 90) pos.push([x, z, 6 + rnd() * 8]); }
      var copa = new THREE.InstancedMesh(new THREE.ConeGeometry(1, 1, 7), new THREE.MeshStandardMaterial({ color: col(0x3f5a2c), roughness: 0.95 }), N * 9);
      var tronco = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.25, 0.3, 1, 5), new THREE.MeshStandardMaterial({ color: col(0x5a4632), roughness: 1 }), N * 9);
      var m = new THREE.Matrix4(), q = new THREE.Quaternion(), k = 0;
      for (var i = -1; i <= 1; i++) for (var j = -1; j <= 1; j++) pos.forEach(function (p) {
        var h = p[2];
        m.compose(new THREE.Vector3(p[0] + i * TILE, h * 0.55, p[1] + j * TILE), q, new THREE.Vector3(h * 0.32, h * 0.8, h * 0.32)); copa.setMatrixAt(k, m);
        m.compose(new THREE.Vector3(p[0] + i * TILE, h * 0.12, p[1] + j * TILE), q, new THREE.Vector3(1, h * 0.25, 1)); tronco.setMatrixAt(k, m); k++;
      });
      arboles.add(copa, tronco);
    })();

    // el tablero vivo
    var TV = (function () {
      var lien = (hay("CAT") && G("CAT") && G("CAT").lienzo) || [1340, 680];
      var esc = CAL === "alta" ? 1 : 0.5, c = document.createElement("canvas");
      c.width = Math.round(lien[0] * esc); c.height = Math.round(lien[1] * esc);
      var g = c.getContext("2d"), tex = new THREE.CanvasTexture(c); tex.encoding = THREE.sRGBEncoding; tex.anisotropy = 4;
      var imgs = {};
      function imagen(id, archivo) {
        if (!imgs[id]) { imgs[id] = new Image(); imgs[id].src = "/caratulas/" + archivo; }
        return imgs[id].complete && imgs[id].naturalWidth ? imgs[id] : null;
      }
      function aguja(cx, cy, giro, largo, color, ancho) {
        g.save(); g.translate(cx, cy); g.rotate(giro * D2R);
        g.fillStyle = color; g.beginPath(); g.moveTo(-ancho / 2, ancho * 2); g.lineTo(-ancho * 0.3, -largo); g.lineTo(ancho * 0.3, -largo); g.lineTo(ancho / 2, ancho * 2); g.closePath(); g.fill();
        g.restore();
      }
      function dibujar() {
        var CAT = G("CAT"), EST = G("EST");
        if (!CAT || !EST) return;
        var Vv = hay("V") ? G("V") : function () { return 0; }, giro = hay("giroAguja") ? G("giroAguja") : null, instr = hay("instr") ? G("instr") : function () { return null; };
        var luzOn = hay("luzEncendida") ? G("luzEncendida") : function () { return false; };
        g.setTransform(esc, 0, 0, esc, 0, 0);
        g.fillStyle = "#141415"; g.fillRect(0, 0, lien[0], lien[1]);
        (CAT.zonas || []).forEach(function (z) {
          g.fillStyle = z.estilo === "tapa" ? "#1c1c1e" : "#0c0c0d"; g.fillRect(z.pos[0], z.pos[1], z.tam[0], z.tam[1]);
          g.fillStyle = "#cdd5b6"; g.font = "600 11px Arial, sans-serif"; g.textAlign = "center"; g.fillText(z.titulo || "", z.pos[0] + z.tam[0] / 2, z.pos[1] + 14);
        });
        (CAT.instrumentos || []).forEach(function (it) {
          if (!it.pos || !it.dial || it.dial === "luz") return;
          var t = it.tam, s = t / 200, x0 = it.pos[0], y0 = it.pos[1], cx = x0 + t / 2, cy = y0 + t / 2;
          g.fillStyle = "#08090a"; g.beginPath(); g.arc(cx, cy, t / 2, 0, 7); g.fill();
          g.fillStyle = "#1b1d1f"; g.beginPath(); g.arc(cx, cy, t * 0.465, 0, 7); g.fill();
          if (it.dial === "horizonte") {
            var cab = Vv("ATT_PITCH"), ala = Vv("ATT_ROLL"), r = t * 0.4;
            g.save(); g.beginPath(); g.arc(cx, cy, r, 0, 7); g.clip(); g.translate(cx, cy); g.rotate(-ala * D2R); g.translate(0, cab * r / 30);
            g.fillStyle = "#3f7fc0"; g.fillRect(-2 * r, -3 * r, 4 * r, 3 * r); g.fillStyle = "#7a5a33"; g.fillRect(-2 * r, 0, 4 * r, 3 * r);
            g.fillStyle = "#f2f2ee"; g.fillRect(-2 * r, -1.5, 4 * r, 3);
            for (var k = -2; k <= 2; k++) if (k) g.fillRect(-r * 0.22, -k * r / 3 - 1, r * 0.44, 2);
            g.restore();
            g.strokeStyle = "#f2c230"; g.lineWidth = 4; g.beginPath(); g.moveTo(cx - r * 0.55, cy); g.lineTo(cx - r * 0.15, cy); g.lineTo(cx, cy + r * 0.1); g.lineTo(cx + r * 0.15, cy); g.lineTo(cx + r * 0.55, cy); g.stroke();
            return;
          }
          var car = (CAT.caratulas || {})[it.id];
          if (car) { var im = imagen(it.id, car.archivo); if (im) { var kk = 87 / car.R, Lc = car.L * kk, o = 100 - Lc / 2; g.drawImage(im, x0 + o * s, y0 + o * s, Lc * s, Lc * s); } }
          if (!giro) return;
          if (it.dial === "tacometro") {
            var rr = instr("TACH_ROT"); if (rr) aguja(cx, cy, giro(rr, Vv("TACH_ROT")), 50 * s, "#ff9f38", 5 * s);
            aguja(cx, cy, giro(it, Vv("TACH_ENG")), 72 * s, "#f4f8fd", 5 * s);
          } else if (it.dial === "brujula") aguja(cx, cy, giro(it, Vv("COMPASS")), 70 * s, "#ffce4a", 9 * s);
          else if (it.dial === "viraje") aguja(cx, cy, giro(it, Vv("TURN")), 66 * s, "#f4f8fd", 5 * s);
          else if (it.dial === "reloj") { var T = EST.t || 0; aguja(cx, cy, (T / 3600 % 12) * 30, 40 * s, "#e8eef6", 6 * s); aguja(cx, cy, (T / 60 % 60) * 6, 62 * s, "#e8eef6", 4 * s); }
          else aguja(cx, cy, giro(it, Vv(it.id)), 72 * s, "#f4f8fd", 5 * s);
          g.fillStyle = "#2a2d30"; g.beginPath(); g.arc(cx, cy, 6 * s, 0, 7); g.fill();
        });
        var COL = { ambar: ["#ffb02e", "#4a3610"], rojo: ["#ff4433", "#46140f"], verde: ["#5fdc6f", "#173a1c"] };
        (CAT.anunciador || []).forEach(function (a) {
          var on = luzOn(EST.instrumentos && EST.instrumentos[a.id]), cc = COL[a.color] || COL.ambar;
          g.fillStyle = on ? cc[0] : cc[1]; g.fillRect(a.pos[0], a.pos[1], a.tam[0], a.tam[1]);
          g.fillStyle = on ? "#1a1208" : "rgba(220,220,200,.45)"; g.font = "700 10px Arial, sans-serif"; g.textAlign = "center"; g.fillText(a.leyenda || "", a.pos[0] + a.tam[0] / 2, a.pos[1] + a.tam[1] / 2 + 4);
        });
        tex.needsUpdate = true;
      }
      return { tex: tex, dibujar: dibujar };
    })();

    // el helicóptero
    // el detalle de la chapa solo se nota de muy cerca y ahorra muchos triángulos
    var DETALLE = +(LS("h08-3d-detalle") || 0) || (CAL === "alta" ? 1.8 : 2.4);
    var H = H08Heli.crear(THREE, { calidad: CAL, detalle: DETALLE, texturaTablero: TV.tex, anisotropia: 4 });
    var mov = new THREE.Group(), act = new THREE.Group(); act.rotation.order = "ZXY";
    var CG = H.puntos.cg; H.grupo.position.set(-CG.x, -CG.y, 0); act.position.y = CG.y;
    act.add(H.grupo); mov.add(act); scene.add(mov);

    // humo
    var Humo = (function () {
      // bocanada de varios grumos, no un círculo
      var c = document.createElement("canvas"); c.width = c.height = 128; var g = c.getContext("2d"), sem = 5;
      var rnd = function () { sem = (sem * 16807) % 2147483647; return sem / 2147483647; };
      for (var b = 0; b < 14; b++) {
        var x = 64 + (rnd() - 0.5) * 50, y = 64 + (rnd() - 0.5) * 50, r = 18 + rnd() * 26, gr = g.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, "rgba(255,255,255,.55)"); gr.addColorStop(0.6, "rgba(255,255,255,.22)"); gr.addColorStop(1, "rgba(255,255,255,0)");
        g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
      }
      var bor = g.createRadialGradient(64, 64, 30, 64, 64, 64); bor.addColorStop(0, "rgba(0,0,0,0)"); bor.addColorStop(1, "rgba(0,0,0,1)");
      g.globalCompositeOperation = "destination-out"; g.fillStyle = bor; g.fillRect(0, 0, 128, 128);
      var tex = new THREE.CanvasTexture(c), pool = [], N = CAL === "alta" ? 220 : 110;
      // color, opacidad, tamaño inicial y final (m), vida (s), velocidad
      var TIPOS = { negro: [0x1a1b1c, 0.85, 0.7, 6.5, 4.2, 1.2], gris: [0x767b80, 0.62, 0.6, 5.2, 4.0, 0.9], blanco: [0xf4f7f8, 0.5, 0.35, 2.8, 2.8, 0.6],
        escape: [0xa3a8ad, 0.14, 0.25, 1.3, 1.2, 0.6], vapor: [0xf0e6dc, 0.35, 0.4, 3.2, 2.4, 0.8] };
      for (var i = 0; i < N; i++) {
        var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, opacity: 0, fog: true }));
        sp.visible = false; scene.add(sp); pool.push({ sp: sp, vida: 0, max: 1, v: new THREE.Vector3(), a0: 0, s0: 0, s1: 0, giro: 0 });
      }
      var sig = 0, tmp = new THREE.Vector3(), base = new THREE.Color();
      function emitir(local, tipo, n, fuerza) {
        var T = TIPOS[tipo] || TIPOS.gris, f = fuerza || 1;
        for (var k = 0; k < (n || 1); k++) {
          var p = pool[sig]; sig = (sig + 1) % pool.length;
          H.grupo.localToWorld(tmp.copy(local));
          p.sp.position.copy(tmp).add(new THREE.Vector3((Math.random() - 0.5) * 0.25, (Math.random() - 0.5) * 0.25, (Math.random() - 0.5) * 0.25));
          p.v.set((Math.random() - 0.5) * T[5] * f, (0.35 + Math.random() * 0.6) * T[5] * f, (Math.random() - 0.5) * T[5] * f).addScaledVector(velHeli, 0.85);   // sale con la velocidad del helicóptero
          base.set(T[0]); base.offsetHSL(0, 0, (Math.random() - 0.5) * 0.08); p.sp.material.color.copy(base);
          p.sp.material.rotation = Math.random() * Math.PI * 2; p.giro = (Math.random() - 0.5) * 0.6;
          p.a0 = T[1] * (0.8 + Math.random() * 0.3); p.s0 = T[2]; p.s1 = T[3] * (0.85 + Math.random() * 0.3); p.max = T[4] * (0.8 + Math.random() * 0.4); p.vida = p.max; p.sp.visible = true;
        }
      }
      function paso(dt) {
        var rotorOn = st.rpm > 90, cx = mov.position.x, cz = mov.position.z, cy = mov.position.y + 3.8;
        pool.forEach(function (p) {
          if (p.vida <= 0) return;
          p.vida -= dt; if (p.vida <= 0) { p.sp.visible = false; return; }
          var f = 1 - p.vida / p.max;
          // el viento de las palas lo empuja para abajo y afuera
          if (rotorOn) {
            var dx = p.sp.position.x - cx, dz = p.sp.position.z - cz, d = Math.hypot(dx, dz);
            if (d < 9 && p.sp.position.y < cy + 1) { var k = (st.rpm / 215) * (1 - d / 9); p.v.y -= 6 * k * dt; p.v.x += dx / (d + 0.5) * 2.5 * k * dt; p.v.z += dz / (d + 0.5) * 2.5 * k * dt; }
          }
          var piso = Math.max(0.3, p.sp.scale.x * 0.42);           // si no, la nube se veía cortada por el piso
          if (p.sp.position.y < piso) { p.sp.position.y = piso; p.v.y = Math.abs(p.v.y) * 0.2; }
          p.sp.position.addScaledVector(p.v, dt); p.v.multiplyScalar(Math.exp(-dt * 0.8)); p.v.x += 0.35 * dt; p.v.y += 0.25 * dt;      // el aire lo frena; viento y humo que sube
          p.sp.material.rotation += p.giro * dt;
          var s = p.s0 + (p.s1 - p.s0) * (1 - Math.pow(1 - f, 2)); p.sp.scale.set(s, s, s); p.sp.material.opacity = p.a0 * Math.pow(1 - f, 1.3) * Math.min(1, f * 10);
        });
      }
      return { emitir: emitir, paso: paso };
    })();

    // cartel (HUD)
    var hud = document.createElement("div"); hud.className = "hud3d";
    hud.innerHTML = '<div class="h3-sup"><b class="h3-fase">—</b><span class="h3-real"></span></div>' +
      '<div class="h3-botones"><button type="button" data-cam="seguir" aria-pressed="true">Seguir</button><button type="button" data-cam="cabina" aria-pressed="false">Cabina</button>' +
      '<button type="button" class="h3-cal" title="Calidad de imagen"></button><button type="button" class="h3-cine" title="Cinemáticas al elegir un accidente, una falla o una etapa del vuelo"></button>' +
      '<button type="button" class="h3-pc" title="Ver el helicóptero en pantalla completa">⛶ Pantalla completa</button></div><div class="h3-fallas"></div>';
    cont.appendChild(hud);
    if (!document.getElementById("hud3d-css")) {
      var css = document.createElement("style"); css.id = "hud3d-css";
      css.textContent = ".hud3d{position:absolute;inset:0;pointer-events:none;font-family:'Inter',system-ui,sans-serif;color:#eef2f5;z-index:4}" +
        ".hud3d .h3-sup{position:absolute;left:12px;top:10px;max-width:72%;background:rgba(10,13,17,.6);border-radius:10px;padding:6px 11px;backdrop-filter:blur(3px)}" +
        ".hud3d .h3-fase{display:block;font:700 14px/1.25 'Inter',sans-serif}.hud3d .h3-real{display:block;font:12px/1.3 'Inter',sans-serif;color:#c3ccd4}" +
        ".hud3d .h3-botones{position:absolute;right:10px;bottom:10px;display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;max-width:70%;pointer-events:auto}" +
        ".hud3d button{font:600 12px 'Inter',sans-serif;color:#e8edf1;background:rgba(10,13,17,.62);border:1px solid rgba(255,255,255,.22);border-radius:8px;padding:6px 10px;cursor:pointer}" +
        ".hud3d button:hover{background:rgba(255,255,255,.14)}.hud3d button[aria-pressed=true]{background:#ff7a1a;border-color:#ff7a1a;color:#1a0c00}" +
        ".hud3d .h3-fallas{position:absolute;left:12px;bottom:10px;display:grid;gap:6px;max-width:52%}" +
        ".hud3d .h3-falla{background:rgba(110,22,12,.78);border-radius:8px;padding:6px 10px}.hud3d .h3-falla b{display:block;font:700 13px 'Inter',sans-serif}.hud3d .h3-falla span{font:12px/1.3 'Inter',sans-serif;color:#f1dcd6}" +
        ".heli3d:fullscreen{border-radius:0;background:#000}.heli3d:-webkit-full-screen{border-radius:0;background:#000}";
      document.head.appendChild(css);
    }
    // pantalla completa del 3D (con las cinemáticas adentro)
    var elPC = hud.querySelector(".h3-pc");
    function enPantallaCompleta() { return (document.fullscreenElement || document.webkitFullscreenElement) === cont; }
    function pantallaCompleta() {
      guard(function () {
        if (enPantallaCompleta()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        else (cont.requestFullscreen || cont.webkitRequestFullscreen).call(cont);
      });
    }
    function rotularPC() { var on = enPantallaCompleta(); elPC.textContent = on ? "Salir de pantalla completa" : "⛶ Pantalla completa"; elPC.setAttribute("aria-pressed", on); if (cine && cine.rotularPC) cine.rotularPC(on); }
    elPC.onclick = pantallaCompleta;
    document.addEventListener("fullscreenchange", rotularPC); document.addEventListener("webkitfullscreenchange", rotularPC);
    if (!(cont.requestFullscreen || cont.webkitRequestFullscreen)) elPC.hidden = true;
    var elFase = hud.querySelector(".h3-fase"), elReal = hud.querySelector(".h3-real"), elFallas = hud.querySelector(".h3-fallas"), elCal = hud.querySelector(".h3-cal");
    var CAM = "seguir";
    hud.querySelectorAll("[data-cam]").forEach(function (b) { b.onclick = function () { ponerCamara(b.dataset.cam); }; });
    function ponerCamara(m) {
      CAM = m; controls.enabled = m !== "cabina";
      hud.querySelectorAll("[data-cam]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.cam === m); });
      if (m === "seguir") { var p = mov.position, h = st.yaw; camera.position.set(p.x + Math.sin(h) * 18 + Math.cos(h) * 10, p.y + 6, p.z - Math.cos(h) * 18 + Math.sin(h) * 10); controls.target.set(p.x, p.y + 1.3, p.z); }
      camara0 = true;
    }
    // Si la placa no llega a los cuadros de la calidad elegida, baja hasta el 70 %
    // de los píxeles y estira la imagen. Si sobra, vuelve.
    var BASE_PR = 1, ESCALA = 1, medioMs = 0, ultAjuste = 0;
    function aplicarEscala() { renderer.setPixelRatio(BASE_PR * ESCALA); tamaño(); }
    function ajustarResolucion(t, ms) {
      medioMs = medioMs ? medioMs * 0.93 + ms * 0.07 : ms;
      if (t - ultAjuste < 2500) return;
      var meta = CAL === "alta" ? 1000 / 45 : 1000 / 28;          // alta unos 45 cuadros, liviana 28
      if (medioMs > meta * 1.2 && ESCALA > 0.7) ESCALA = Math.max(0.7, +(ESCALA - 0.1).toFixed(2));
      else if (medioMs < meta * 0.85 && ESCALA < 1) ESCALA = Math.min(1, +(ESCALA + 0.1).toFixed(2));
      else return;
      ultAjuste = t; aplicarEscala();
    }
    function ponerCalidad(q) {
      CAL = q; LS("h08-3d-calidad", q); elCal.textContent = q === "alta" ? "Imagen alta" : "Imagen liviana";
      BASE_PR = q === "alta" ? Math.min(2, window.devicePixelRatio || 1) : 1; ESCALA = 1; medioMs = 0; ultAjuste = performance.now();
      renderer.setPixelRatio(BASE_PR);
      renderer.shadowMap.enabled = sol.castShadow = q === "alta";
      renderer.shadowMap.autoUpdate = false; renderer.shadowMap.needsUpdate = true;
      sombraFalsa.visible = q !== "alta";
      scene.traverse(function (o) { if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) { m.needsUpdate = true; }); });
      tamaño();
    }
    elCal.onclick = function () { ponerCalidad(CAL === "alta" ? "liviana" : "alta"); };

    // seguir al simulador
    var velHeli = new THREE.Vector3();
    var st = { x: 0, z: 0, alt: 0, yaw: 0, cab: 0, ala: 0, rpm: 0, rpmCola: 0, tPrev: null, faseAnt: null, iniciado: false, acum: {} };
    var camara0 = false;
    function suave(a, b, dt, tau) { return a + (b - a) * (1 - Math.exp(-dt / tau)); }
    function difAng(a, b) { var d = (b - a) % (2 * Math.PI); if (d > Math.PI) d -= 2 * Math.PI; if (d < -Math.PI) d += 2 * Math.PI; return d; }
    function vueloDe(E) {
      if (E.vuelo) return E.vuelo;
      var I = E.instrumentos || {}, r = function (id) { return I[id] ? I[id].real : 0; };   // servidor viejo: usa las señales
      return { alt_ft: E.en_tierra ? 0 : r("ALTIMETER"), terreno_ft: 0, ias_kt: r("AIRSPEED"), vs_fpm: r("VSI"), rumbo: r("COMPASS"), cabeceo: r("ATT_PITCH"), alabeo: r("ATT_ROLL"), rotor_rpm: r("TACH_ROT"), motor_rpm: r("TACH_ENG") };
    }
    function emisor(clave, porSeg, dt, fn) { st.acum[clave] = (st.acum[clave] || 0) + porSeg * dt; while (st.acum[clave] >= 1) { st.acum[clave] -= 1; fn(); } }
    function seguir(dt) {
      var E = G("EST"); if (!E) return;
      vigilar(E);
      var vu = vueloDe(E), vel = E.pausado ? 0 : (E.velocidad || 1), f = {};
      (E.fallas || []).forEach(function (id) { f[id] = true; });
      // si el simulador arranca de cero, vuelve al helipuerto
      var reinicio = st.tPrev !== null && E.t < st.tPrev - 1;
      if (!st.iniciado || reinicio || (E.fase_id === "FRIO" && st.faseAnt !== "FRIO")) {
        st.x = st.z = 0; st.alt = 0; st.yaw = vu.rumbo * D2R; st.iniciado = true; camara0 = false;
      }
      st.tPrev = E.t; st.faseAnt = E.fase_id;
      var yawObj = vu.rumbo * D2R; st.yaw += difAng(st.yaw, yawObj) * (1 - Math.exp(-dt / 0.35));
      var v = E.en_tierra ? 0 : vu.ias_kt * 0.5144;
      st.x += Math.sin(st.yaw) * v * dt * vel; st.z -= Math.cos(st.yaw) * v * dt * vel;
      var altObj = E.en_tierra ? 0 : Math.max(0, (vu.alt_ft - (vu.terreno_ft || 0)) * 0.3048);
      var altAntes = st.alt; st.alt = suave(st.alt, altObj, dt, 0.35);
      velHeli.set(Math.sin(st.yaw) * v * vel, dt > 0 ? (st.alt - altAntes) / dt : 0, -Math.cos(st.yaw) * v * vel);
      var enTierra = E.en_tierra && altObj < 0.5;          // en las ruedas va derecho aunque el modelo guarde un ángulo
      st.cab = suave(st.cab, enTierra ? 0 : (vu.cabeceo || 0) * D2R, dt, 0.25); st.ala = suave(st.ala, enTierra ? 0 : (vu.alabeo || 0) * D2R, dt, 0.25);
      st.rpm = suave(st.rpm, vu.rotor_rpm || 0, dt, 0.3);
      st.rpmCola = suave(st.rpmCola, f.TAIL_ROTOR_LOSS ? 0 : st.rpm * 5.4, dt, f.TAIL_ROTOR_LOSS ? 1.6 : 0.3);
      mov.position.set(st.x, st.alt, st.z); mov.rotation.y = -(st.yaw + Math.PI / 2);
      act.rotation.z = -st.cab; act.rotation.x = -st.ala;
      H.rotores(dt * (vel || 0), st.rpm, st.rpmCola);
      H.luzBaliza(!!E.energia_ok && (performance.now() % 1300) < 160); if (H.luces) H.luces(!!E.energia_ok);
      var mot = vu.motor_rpm || 0, P = H.puntos;
      if (mot > 300) emisor("esc", 5, dt, function () { Humo.emitir(P.escape, "escape"); });
      if (f.ENG_FAIL_TOTAL && mot > 40) emisor("neg", 14, dt, function () { Humo.emitir(P.escape, "negro"); });
      if ((f.ENG_ROUGH || f.ENG_FAIL_PARTIAL || f.FUEL_STARVATION || f.FUEL_PUMP_FAIL) && mot > 300 && Math.random() < dt * 2.2) Humo.emitir(P.escape, "negro", 4);
      if ((f.MAG_L_FAIL || f.CARB_ICE) && mot > 300 && Math.random() < dt * 1.5) Humo.emitir(P.escape, "gris", 3);
      if ((f.OIL_PRESS_LOSS || f.OIL_OVERHEAT || f.CHT_OVERHEAT) && mot > 200) emisor("rej", 7, dt, function () { Humo.emitir(Math.random() < 0.5 ? P.rejillaIzq : P.rejillaDer, "gris"); });
      if ((f.XMSN_PRESS_LOSS || f.XMSN_OVERHEAT) && st.rpm > 50) emisor("xm", 6, dt, function () { Humo.emitir(P.careno, "gris"); });
      if (f.CLUTCH_SLIP && st.rpm > 50) emisor("emb", 2, dt, function () { Humo.emitir(P.careno, "gris"); });
      if (f.FUEL_LEAK) emisor("comb", 10, dt, function () { Humo.emitir(P.panza, "blanco"); });
      Humo.paso(dt);
      elFase.textContent = E.escenario || E.fase || E.modo_nombre || "—";
      elReal.textContent = "Valores reales: " + Math.round(vu.alt_ft - (vu.terreno_ft || 0)) + " ft · " + Math.round(vu.ias_kt) + " kt · rumbo " + ("00" + Math.round((vu.rumbo + 360) % 360)).slice(-3) + "° · rotor " + Math.round(vu.rotor_rpm) + " RPM";
      var clave = (E.fallas || []).join(",");
      if (clave !== st.clave) {
        st.clave = clave;
        var CAT = G("CAT") || {}, nom = {}; (CAT.fallas || []).forEach(function (x) { nom[x.id] = x.nombre; });
        elFallas.innerHTML = (E.fallas || []).map(function (id) {
          return '<div class="h3-falla"><b></b><span></span></div>';
        }).join("");
        elFallas.querySelectorAll(".h3-falla").forEach(function (d, i) {
          var id = E.fallas[i]; d.querySelector("b").textContent = nom[id] || id;
          d.querySelector("span").textContent = MIENTE[id] ? "Afuera todo normal: el que miente es el instrumento. Compará con los valores reales de arriba." : (AFUERA[id] || "");
        });
        ubicarFallas();
      }
    }

    // cámara
    // La cámara guarda su posición relativa al helicóptero y lo sigue. Si el
    // helicóptero salta (escenario en el aire, vuelta al helipuerto) se reubica.
    var antes = new THREE.Vector3(), ahora = new THREE.Vector3(), rel = new THREE.Vector3(), q = new THREE.Quaternion(),
      qBase = new THREE.Quaternion().setFromEuler(new THREE.Euler(-10 * D2R, Math.PI / 2, 0, "YXZ"));
    function camara() {
      mov.updateMatrixWorld(true);
      if (CAM === "cabina") {
        H.grupo.localToWorld(camera.position.copy(H.puntos.ojo));
        act.getWorldQuaternion(q); camera.quaternion.copy(q).multiply(qBase);
        return;
      }
      ahora.set(mov.position.x, mov.position.y + 1.3, mov.position.z);
      if (!camara0 || ahora.distanceTo(antes) > 60) { ponerCamara("seguir"); antes.copy(ahora); controls.update(); return; }
      rel.copy(camera.position).sub(controls.target);
      controls.target.copy(ahora); camera.position.copy(ahora).add(rel);
      if (camera.position.y < 1.5) camera.position.y = 1.5;
      controls.update(); antes.copy(ahora);
    }

    // cinemáticas (cine3d.js)
    // misma luz que en vivo para que no salte, más un contraluz frío y niebla si el guion la pide
    var contraluz = new THREE.DirectionalLight(col(0x8fb0ff), 0); scene.add(contraluz, contraluz.target);
    var AMB = null;
    function ambiente(on, niebla) {
      if (on) {
        if (!AMB) AMB = { fog: scene.fog, exp: renderer.toneMappingExposure };
        scene.fog = niebla ? new THREE.Fog(0xd9b298, 30, 420) : AMB.fog;
        contraluz.intensity = 0.8; renderer.toneMappingExposure = 0.86;
      } else if (AMB) {
        scene.fog = AMB.fog; contraluz.intensity = 0; renderer.toneMappingExposure = AMB.exp; AMB = null;
      }
    }
    // pone el helicóptero donde dice st (el guion o el simulador)
    var antesPos = new THREE.Vector3();
    function aplicarPose(dt) {
      antesPos.copy(mov.position);
      mov.position.set(st.x, st.alt, st.z); mov.rotation.y = -(st.yaw + Math.PI / 2);
      act.rotation.z = -st.cab; act.rotation.x = -st.ala;
      if (dt > 0) { velHeli.copy(mov.position).sub(antesPos).divideScalar(dt); if (velHeli.length() > 80) velHeli.set(0, 0, 0); }
      H.rotores(dt, st.rpm, st.rpmCola); Humo.paso(dt);
      contraluz.position.set(st.x + 40, st.alt + 25, st.z - 60); contraluz.target.position.set(st.x, st.alt, st.z);
    }
    var cineOn = LS("h08-cine") !== "no", elCine = hud.querySelector(".h3-cine");
    function ponerCine(v) { cineOn = v; LS("h08-cine", v ? "si" : "no"); elCine.textContent = v ? "Cinemáticas: sí" : "Cinemáticas: no"; elCine.setAttribute("aria-pressed", v); if (!v && cine && cine.activo()) cine.terminar(); }
    elCine.onclick = function () { ponerCine(!cineOn); };
    var cine = window.H08Cine ? H08Cine.crear({ THREE: THREE, scene: scene, camera: camera, renderer: renderer, cont: cont, H: H, act: act, st: st, Humo: Humo, aplicar: aplicarPose, ambiente: ambiente,
      pantallaCompleta: pantallaCompleta,
      // en la cinemática sigue al simulador, igual que el tablero
      seguir: function (dt) { seguir(Math.min(0.1, dt)); contraluz.position.set(st.x + 40, st.alt + 25, st.z - 60); contraluz.target.position.set(st.x, st.alt, st.z); },
      calidad: function () { return CAL; },
      termino: function () { hud.style.visibility = ""; controls.enabled = CAM !== "cabina"; camera.fov = 45; camera.updateProjectionMatrix(); camara0 = false; } }) : null;
    ponerCine(cineOn);
    if (!cine) elCine.hidden = true;
    // qué cambió: accidente nuevo, otra parte del vuelo o una falla suelta
    var EN_TIERRA = { ENG_FAIL_TOTAL: "Sale humo negro y el motor se para. En el piso, las aspas frenan hasta quedar quietas.", LOW_ROTOR_RPM: "Las aspas giran más lento de lo normal: no hay que despegar." };
    var vig = { esc: null, grupo: null, fallas: null };
    function vigilar(E) {
      if (!cine) return;
      var reposo = E.modo_nombre === "En reposo", esc = E.escenario_id || null, grupo = H08Cine.ACTIVIDAD[E.fase_id] || null, fl = (E.fallas || []).slice();
      var id = null, extra = null;
      if (vig.fallas !== null && !reposo) {
        if (esc && esc !== vig.esc) id = esc;
        else if (!esc && grupo && grupo !== vig.grupo) id = grupo;
        else {
          var nueva = fl.filter(function (f) { return vig.fallas.indexOf(f) < 0; })[0];
          if (nueva) {
            var CAT = G("CAT") || {}, ff = (CAT.fallas || []).filter(function (x) { return x.id === nueva; })[0] || {};
            id = H08Cine.SISTEMA[ff.sistema] || null;
            extra = { id: nueva, nombre: ff.nombre || nueva, afuera: MIENTE[nueva] ? "Afuera todo está normal: el que falla es el reloj." : ((E.en_tierra && EN_TIERRA[nueva]) || AFUERA[nueva] || "") };
          }
        }
      }
      vig.esc = esc; vig.grupo = grupo; vig.fallas = fl;
      if (id && cineOn && visible && !document.hidden && cont.clientWidth) { if (cine.enEspera()) cine.esperaFin(true); if (cine.iniciar(id, extra)) { hud.style.visibility = "hidden"; controls.enabled = false; } }
    }

    // cuadro
    function tamaño() {
      var w = cont.clientWidth, h = cont.clientHeight; if (!w || !h) return;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
      ubicarFallas();
    }
    // con el 3D angosto los botones ocupan dos renglones y el cartel va arriba
    function ubicarFallas() {
      var w = cont.clientWidth, bot = hud.querySelector(".h3-botones"), angosto = w < 760;
      elFallas.style.bottom = (angosto && bot ? bot.offsetHeight + 18 : 10) + "px";
      elFallas.style.maxWidth = angosto ? "calc(100% - 24px)" : "52%";
    }
    if (window.ResizeObserver) new ResizeObserver(tamaño).observe(cont); else window.addEventListener("resize", tamaño);
    // sombra falsa para la liviana: sin ella parece que flota, y no cuesta nada
    var sombraFalsa = (function () {
      var c = document.createElement("canvas"); c.width = 256; c.height = 128; var g = c.getContext("2d");
      var gr = g.createRadialGradient(128, 64, 4, 128, 64, 62); gr.addColorStop(0, "rgba(0,0,0,0.55)"); gr.addColorStop(0.6, "rgba(0,0,0,0.3)"); gr.addColorStop(1, "rgba(0,0,0,0)");
      g.setTransform(2, 0, 0, 1, -128, 0); g.fillStyle = gr; g.fillRect(0, 0, 256, 128);
      var m = new THREE.Mesh(new THREE.PlaneGeometry(15, 5.2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -8 }));
      m.rotation.x = -Math.PI / 2; m.renderOrder = 1; scene.add(m); return m;
    })();
    var sTmpA = new THREE.Vector3(), sTmpB = new THREE.Vector3();
    var ult = performance.now(), tTab = 0, visible = true, cuadroN = 0;
    function cuadro(t) {
      requestAnimationFrame(cuadro);
      if (!visible || document.hidden || !cont.clientWidth) { ult = t; return; }
      var dt = Math.min(0.1, (t - ult) / 1000), dtReal = Math.min(0.6, (t - ult) / 1000);    // el cine va con el reloj para que con pocos cuadros no se atrasen los textos
      if (CAL !== "alta" && dt < 1 / 32) return;          // liviana: con 30 cuadros alcanza
      var msCuadro = t - ult; ult = t;
      if (cine && cine.activo()) cine.paso(dtReal);
      else {
        seguir(dt);
        // mientras se espera al profe, recorrido por las partes
        var E = G("EST"), espera = !!(cine && cineOn && E && E.modo_nombre === "En reposo" && CAM !== "cabina");
        if (cine && cine.activo()) { /* recién arrancó una cinemática: la cámara es de ella */ }
        else if (espera) { if (!cine.enEspera()) { cine.esperaInicio(); hud.style.visibility = "hidden"; controls.enabled = false; } cine.esperaPaso(dtReal); }
        else { if (cine && cine.enEspera()) cine.esperaFin(); camara(); }
      }
      var sx = Math.round(st.x / REP) * REP, sz = Math.round(st.z / REP) * REP;
      suelo.position.set(sx, 0, sz); pasto.offset.set(sx / REP, -sz / REP);
      arboles.position.set(Math.round(st.x / TILE) * TILE, 0, Math.round(st.z / TILE) * TILE);
      sol.position.set(st.x - 75, st.alt + 24, st.z + 45); sol.target.position.set(st.x, st.alt, st.z);
      var cerca = CAM === "cabina" || camera.position.distanceTo(mov.position) < 14;
      if (cerca && t - tTab > 200) { tTab = t; TV.dibujar(); }
      if (sombraFalsa.visible) {
        var hS = Math.max(0, st.alt), fS = Math.max(0, 1 - hS / 45);
        H.grupo.updateWorldMatrix(true, false);            // del medio del fuselaje, de la nariz a la cola
        var sA = H.grupo.localToWorld(sTmpA.set(0.5, 0, 0)), sB = H.grupo.localToWorld(sTmpB.set(12.5, 0, 0));
        sombraFalsa.position.set((sA.x + sB.x) / 2, 0.03, (sA.z + sB.z) / 2); sombraFalsa.rotation.z = Math.atan2(-(sB.z - sA.z), sB.x - sA.x);
        sombraFalsa.scale.setScalar(1 + hS / 60); sombraFalsa.material.opacity = fS; sombraFalsa.visible = fS > 0.02 || CAL !== "alta";
      }
      // la sombra real se recalcula un cuadro sí y otro no, ahorra un dibujo entero
      if (CAL === "alta") renderer.shadowMap.needsUpdate = (++cuadroN % 2) === 0;
      renderer.render(scene, camera);
      if (msCuadro > 0) ajustarResolucion(t, Math.min(msCuadro, 200));
    }
    ponerCalidad(CAL); tamaño(); requestAnimationFrame(cuadro);
    return {
      mostrar: function (v) { visible = !!v; if (v) tamaño(); },
      camara: ponerCamara,
      cine: cine,
      _prueba: { scene: scene, camera: camera, st: st, H: H, cine: cine, render: function () { renderer.render(scene, camera); } },
    };
  }

  window.H08Vuelo3D = { iniciar: iniciar };
})();
