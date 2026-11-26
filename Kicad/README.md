# Placa madre

El proyecto de KiCad de la placa madre del tablero: esquemático y placa ruteada, con las librerías que hicimos adentro de la misma carpeta.

En `H08_Placa` está el proyecto. Se abre `H08_Placa.kicad_pro` y con eso aparecen el esquemático y la placa. Las librerías propias son `H08.kicad_sym` (símbolos) y la carpeta `H08.pretty` (huellas con las medidas de los componentes reales). `CONEXIONES.txt` tiene la red completa pata por pata y en `LEEME.txt` está el detalle del diseño y los pasos para hacerla.

En `Planos` están los PDF para fabricarla: el arte del cobre espejado para planchar, el cobre visto desde abajo, el plano de agujeros y el de montaje (dónde va cada componente).

La placa mide 170 x 110 mm y es de una sola cara. Tiene 242 pistas y 25 puentes de alambre, que son 15 del ruteo y 10 para coser el plano de masa. A la entrada de 5 V lleva un fusible lento de 4 A (F1) y después un supresor P6KE6.8A (D2).

Para abrirla usamos KiCad 10. El proyecto está guardado en formato de KiCad 6, así que la primera vez pregunta si lo actualiza y se le dice que sí. No hay que instalar ninguna librería. Al abrir la placa hay que apretar B para que rellene el plano de masa.

Para hacerla no hace falta exportar nada: `Planos/arte_bcu_espejado.pdf` ya está a escala 1:1. Antes de transferirlo conviene medir el contorno con una regla, tiene que dar 170 x 110 mm. Se imprime al 100 %, no con "ajustar a la página".

En la placa que armamos no van U1 y U2 (los ULN2003) ni las borneras J11 y J12 de los motores. El motor de la brújula usa la plaquita ULN2003 que viene con él y se conecta con cables a los pines que pusimos en el lugar de U2.

**Ojo con el conector de la Raspberry (J1).** Cuando hicimos la placa, el dibujo quedó dado vuelta, como en un espejo. Por eso los pines de J1 no quedaron en el mismo orden que los de la Raspberry, y el cable plano de 40 hilos no sirve: conectaría cada señal en el lugar equivocado.

Lo resolvimos con cables sueltos (Dupont hembra-hembra), uno por pin. Cada cable une el pin de la Raspberry con el pin de la placa que tiene el mismo nombre, por ejemplo SDA con SDA. El nombre de cada pin está escrito en la placa. La lista de qué va con qué está en [Software/H08_Pi5/LEEME.md](../Software/H08_Pi5/LEEME.md#cableado-de-la-raspberry-a-la-placa-madre).
