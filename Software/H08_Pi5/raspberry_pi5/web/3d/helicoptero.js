// -*- coding: utf-8 -*-
// Toma el casco de sikorsky.js y le suma rotores, luces, faro y el tablero vivo (three.js r128).
// Marco de la página: nariz en x = 0 mirando a -x, piso en y = 0, +z es el lado izquierdo.
// El modelo tiene +x a la nariz y el origen bajo el mástil, por eso se gira 180° y se corre.
(function () {
  "use strict";

  function crear(THREE, op) {
    op = op || {};
    var T = THREE, D2R = Math.PI / 180;
    var V = function (x, y, z) { return new T.Vector3(x, y, z); };
    var col = function (h) { return new T.Color(h).convertSRGBToLinear(); };
    var NAR = H08Modelo.COTAS.nariz;
    var casco = H08Modelo.construir(T, { detalle: op.detalle || 1 });
    var grupo = new T.Group(); grupo.name = "H-08";
    casco.rotation.y = Math.PI; casco.position.x = NAR; grupo.add(casco);
    var sombras = op.calidad === "alta";
    // la sombra la hace la chapa de afuera: el forro, los vidrios y los marcos no suman nada y cuestan
    var SIN_SOMBRA = /^(Interior|Vidrios|Ventanas|Marcos|Burletes|Marco )/;
    casco.traverse(function (o) { if (o.isMesh) { o.castShadow = sombras && !SIN_SOMBRA.test(o.name || ""); o.receiveShadow = false; } });
    // del marco del modelo (x a la nariz, z a la derecha) al marco de la página
    function P(x, y, z) { return V(NAR - x, y, -z); }

    // rotores
    var rotor = casco.userData.rotor, rotorCola = casco.userData.rotorCola;
    function discoBorroso(r, padre, pos, rot) {
      var m = new T.Mesh(new T.CircleGeometry(r, 48), new T.MeshBasicMaterial({ color: 0x1b1d20, transparent: true, opacity: 0, depthWrite: false, side: T.DoubleSide }));
      if (pos) m.position.copy(pos); if (rot) m.rotation.copy(rot); m.visible = false; padre.add(m); return m;
    }
    var disco = discoBorroso(H08Modelo.COTAS.rotorDiam / 2, rotor.parent, rotor.position.clone().add(V(0, 0.05, 0)), new T.Euler(-Math.PI / 2, 0, 0));
    var discoCola = discoBorroso(H08Modelo.COTAS.rotorColaDiam / 2, rotorCola.parent, rotorCola.position.clone().add(V(0, 0, 0.02)), new T.Euler(0, 0, 0));
    var ang = 0, angCola = 0, ang0 = rotor.rotation.y, angCola0 = rotorCola.rotation.z;
    function rotores(dt, rpm, rpmCola) {
      // tope 1,6 vueltas/s: más rápido parece que gira para atrás
      var w = Math.min(rpm / 60, 1.6) * 2 * Math.PI, wc = Math.min(rpmCola / 60, 2.4) * 2 * Math.PI;
      ang += w * dt; angCola += wc * dt;
      rotor.rotation.y = ang0 + ang; rotorCola.rotation.z = angCola0 - angCola;
      var borr = Math.max(0, Math.min(1, (rpm - 90) / 110)), borrC = Math.max(0, Math.min(1, (rpmCola - 300) / 600));
      disco.material.opacity = 0.16 * borr; disco.visible = borr > 0.01;
      discoCola.material.opacity = 0.16 * borrC; discoCola.visible = borrC > 0.01;
    }

    // luces
    var brillo = (function () {
      var c = document.createElement("canvas"); c.width = c.height = 64; var g = c.getContext("2d"), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.25, "rgba(255,255,255,.55)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return new T.CanvasTexture(c);
    })();
    function luz(color, pos, tam) {
      var g = new T.Group(); g.position.copy(pos);
      var foco = new T.Mesh(new T.SphereGeometry(0.045, 10, 8), new T.MeshBasicMaterial({ color: color }));
      var halo = new T.Sprite(new T.SpriteMaterial({ map: brillo, color: color, transparent: true, depthWrite: false, blending: T.AdditiveBlending }));
      halo.scale.set(tam, tam, tam); g.add(foco, halo); grupo.add(g); return { g: g, halo: halo, foco: foco };
    }
    var navIzq = luz(0xff2a20, P(0.6, 1.05, -1.02), 1.1);      // babor: roja
    var navDer = luz(0x2bff6a, P(0.6, 1.05, 1.02), 1.1);       // estribor: verde
    var navCola = luz(0xf4f6ff, P(-9.35, 2.95, 0), 0.9);       // cola: blanca
    var baliza = luz(0xff3020, P(-1.6, 3.32, 0), 1.6);         // baliza roja arriba
    function luces(on) { [navIzq, navDer, navCola].forEach(function (l) { l.g.visible = !!on; }); }
    function luzBaliza(on) { baliza.halo.visible = !!on; baliza.foco.material.color.set(on ? 0xff3020 : 0x3a0d0a); }
    luces(false); luzBaliza(false);
    // faro de aterrizaje debajo de la nariz
    var faro = new T.SpotLight(0xfff0d8, 0, 160, 0.42, 0.55, 1.4);
    faro.position.copy(P(3.2, 0.75, 0)); faro.target.position.copy(P(16, -8, 0)); grupo.add(faro, faro.target);
    var haloFaro = luz(0xfff0d8, P(3.35, 0.72, 0), 1.3); haloFaro.g.visible = false;
    function ponerFaro(k) { faro.intensity = 6 * (k || 0); haloFaro.g.visible = (k || 0) > 0.05; }

    // tablero vivo en la cabina
    casco.traverse(function (o) {
      if (o.name !== "Tablero" || !op.texturaTablero) return;
      var pl = new T.Mesh(new T.PlaneGeometry(0.92, 0.42), new T.MeshBasicMaterial({ map: op.texturaTablero, toneMapped: false }));
      pl.rotation.y = -Math.PI / 2; pl.position.x = -0.04; o.add(pl);
    });

    return {
      grupo: grupo, rotor: rotor, rotorCola: rotorCola, rotores: rotores, luzBaliza: luzBaliza, luces: luces, faro: ponerFaro,
      // puntos del modelo de donde salen el humo y donde va la cámara
      puntos: {
        escape: P(2.72, 0.98, -1.1), rejillaIzq: P(2.85, 1.55, -0.72), rejillaDer: P(2.85, 1.55, 0.72), careno: P(0, 3.25, 0),
        panza: P(-0.5, 0.42, 0), ojo: P(0.72, 3.02, 0.4), tablero: P(1.33, 2.68, 0), cg: P(0, 1.45, 0), mastil: P(0, 3.84, 0),
        cola: P(-9.02, 3.86, 0.26), nariz: P(3.6, 1.3, 0), ruedas: P(-2.57, 0.1, 0)
      }
    };
  }

  window.H08Heli = { crear: crear };
})();
