# Programa de la Raspberry Pi 5

Tablero H-08, Sikorsky S-55 / H-19A. EEST N° 7, Taller Regional Quilmes.

En esta carpeta está lo que va en la Raspberry Pi 5 y nada más. Se instala una vez y desde ahí, cada vez que se prende la Raspberry:

1. Arranca el servicio del tablero, en reposo. Los servos no reciben pulso, no se mueve nada y la página muestra todo en cero con el cartel "Esperando al profesor". El mismo servicio sirve la página web.
2. La pantalla conectada a la Raspberry muestra el tablero a pantalla completa, con las mismas carátulas que están pegadas en los instrumentos. Abajo a la derecha aparecen los dos QR para entrar desde el celular.
3. La Raspberry levanta su propia red wifi, Tablero-H08, con la clave sikorsky55. Desde un celular o una tablet conectados se entra escribiendo `10.55.0.1` en el navegador. Los detalles están en "La red del tablero".

Cuando el profesor toca "Activar tablero" en el modo profesor, se mueven los 20 servos, las 6 luces de alerta y el motor paso a paso de la brújula, cada uno con la calibración y la mecánica de su instrumento, y arranca el vuelo normal.

"Detener" lleva las agujas al cero y las suelta. Lo mismo pasa cuando el último profesor cierra la sesión.

No hace falta internet ni pip, ni instalar nada fuera de los paquetes del sistema.

## Qué hace falta

- Raspberry Pi 5 con su fuente oficial de 27 W (5,1 V 5 A).
- Raspberry Pi OS con escritorio, 64 bits, Bookworm o posterior.
- Una pantalla HDMI, la de la Raspberry. Es opcional: sin pantalla anda igual.
- La placa madre armada y cableada. Ojo, J1 va con Dupont (está explicado en el cableado).
- La fuente de servos del tablero (LM2596, 5 V). **Los servos nunca se alimentan desde la Pi.**
- Una zapatilla con interruptor para los tres enchufes (Pi, fuente de servos y pantalla). Hace de general del tablero.
- La llave BATERÍA, que es la llave de palanca del panel, cableada a la Pi. Con ella se apaga en orden.

## Instalación

Se hace una sola vez.

1. Copiar la carpeta `H08_Pi5` a la Raspberry, por ejemplo con un pendrive, y dejarla en la carpeta del usuario (`/home/USUARIO/H08_Pi5`).
2. Abrir una terminal y correr:

   ```
   cd ~/H08_Pi5/raspberry_pi5
   bash instalar.sh
   sudo reboot
   ```

   `instalar.sh` se corre sin `sudo` adelante; la clave la pide solo. Lo que hace:

   - instala `gpiozero`, `lgpio`, `i2c-tools`, Chromium, `rsync` y `unzip`;
   - habilita el I2C a 400 kHz;
   - suma el usuario a los grupos `i2c`, `gpio` y `video`;
   - genera la clave del profesor;
   - instala el servicio `tablero-h08`, que arranca solo;
   - configura la pantalla con `pantalla.sh`: el escritorio entra sin contraseña, la pantalla no se apaga y el tablero se abre a pantalla completa;
   - deja preparada la red wifi propia para el próximo encendido.

   **Mientras la red propia está levantada, la Pi no se conecta al wifi de la escuela.** Cómo volver está en "Volver a la red de la escuela".

   Tiene dos opciones: `--sin-pantalla` no abre el tablero en la pantalla, y `--sin-wifi` no arma la red propia (queda el wifi de la escuela).

3. Después del reinicio, comprobar que quedó todo bien:

   ```
   cd ~/H08_Pi5/raspberry_pi5
   python3 diagnostico_pi.py
   ```

## Cableado de la Raspberry a la placa madre

El diagnóstico tiene una opción para el cableado:

```
python3 diagnostico_pi.py --cableado
```

| Función | GPIO | Pata de la Raspberry |
|---|---|---|
| 3,3 V (lógica de los PCA9685) | - | 1 |
| SDA (I2C) | GPIO2 | 3 |
| SCL (I2C) | GPIO3 | 5 |
| GND | - | 6, 9, 14, 20, 25, 30, 34, 39 |
| Motor IN1 | GPIO12 | 32 |
| Motor IN2 | GPIO16 | 36 |
| Motor IN3 | GPIO20 | 38 |
| Motor IN4 | GPIO21 | 40 |
| Llave BATERÍA | GPIO26 | 37 (la otra pata de la llave a GND, pata 39) |

La llave BATERÍA va directo a la Raspberry, no a J1: dos cables Dupont, uno a la pata 37 y otro a la 39. Tiene que cerrar el contacto en APAG (abajo), así si se suelta un cable el tablero no se apaga solo. Por esos cables pasan solo 3,3 V de señal.

> **La placa salió espejada y en J1 el cable plano no sirve.** Las columnas par e impar de J1 quedaron cambiadas. Hay que cablear pata por pata con Dupont hembra-hembra y seguir la tabla por función (SDA con SDA, IN1 con IN1, y así con cada una), mirando la serigrafía de la placa que tienen en la mano. El programa no cambia, porque las funciones son las mismas.

Los dos PCA9685 van así:

- PCA0 en 0x40, sin puentes.
- PCA1 en 0x41, con el puente A0 soldado.

El V+ de los dos sale de la fuente de servos, y el GND de esa fuente va unido al de la Pi.

## Qué mueve cada canal

| Canal | Instrumento | Cómo va la aguja |
|---|---|---|
| PCA0:0 | Combustible, tanque delantero | barre 120°, aguja directa en el servo |
| PCA0:1 | Temperatura de aceite | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:2 | Presión de aceite | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:3 | Presión de combustible | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:4 | Temperatura de aire del carburador | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:5 | Temperatura de culata | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:6 | Velocímetro | barre 300°, engranajes 40/24 (servo al revés) |
| PCA0:7 | Tacómetro (aguja del motor) | barre 300°, engranajes 40/24 (servo al revés) |
| PCA0:9 | Altímetro (miles de pies) | barre 360°, engranajes 48/24 (servo al revés) |
| PCA0:10 | Variómetro | barre 300°, engranajes 40/24 (servo al revés) |
| PCA0:11 | Viraje (aguja) | barre 60°, aguja directa |
| PCA0:13 | Horizonte, cabeceo | yugo escocés v3, ±20° = ±7 mm de disco |
| PCA0:14 | Horizonte, alabeo | plato 70/50 |
| PCA0:15 | AN/ARN-14 (desvío de curso) | barre 40°, aguja directa |
| PCA1:0 | Presión de admisión | barre 270°, engranajes 36/24 (servo al revés) |
| PCA1:1 | Temperatura de transmisión | barre 270°, engranajes 36/24 (servo al revés) |
| PCA1:2 | Presión de transmisión | barre 270°, engranajes 36/24 (servo al revés) |
| PCA1:3 | Amperímetro | barre 120°, aguja directa |
| PCA1:4 | Voltímetro | barre 120°, aguja directa |
| PCA1:5 | Combustible, tanque trasero | barre 120°, aguja directa |
| GPIO 12-16-20-21 | Brújula | paso a paso 28BYJ-48, giro continuo |
| PCA1:8 | Luz FUEL FWD (ámbar) | combustible delantero bajo |
| PCA1:9 | Luz FUEL AFT (ámbar) | combustible trasero bajo |
| PCA1:10 | Luz XMSN PRESS (roja) | baja presión de transmisión con el rotor girando |
| PCA1:11 | Luz GENERATOR (roja) | batería conectada y generador fuera de línea |
| PCA1:12 | Luz LOW ROTOR (roja) | rotor por debajo de su mínimo |
| PCA1:13 | Luz IGNITION (verde) | magnetos activos |

Libres: PCA0:8, PCA0:12, PCA1:6, PCA1:7, PCA1:14, PCA1:15 y el lugar del motor 0 (GPIO 6-13-19-26).

Hay agujas que existen solo en la página, porque en el tablero no tienen actuador: la del rotor en el tacómetro, la bola de ladeo y las centenas del altímetro.

## Pruebas de puesta en marcha

Van en este orden y se corren todas desde `~/H08_Pi5/raspberry_pi5`. Las guiadas preguntan si se movió o se encendió y guardan un informe con fecha en `informes/`. Casi todas manejan las placas directo, así que necesitan el servicio detenido:

```
sudo systemctl stop tablero-h08        # antes
sudo systemctl start tablero-h08       # después
```

### Prueba 1: diagnóstico de conexiones

`python3 diagnostico_pi.py`

Revisa sistema, alimentación (baja tensión y 5 V medidos), bus I2C (qué hay conectado y si cada PCA9685 quedó configurado a 50 Hz), GPIO del motor, servicio, pantalla, wifi y archivos. No mueve nada y puede correr con el servicio andando. Para cada falla dice el comando que la arregla.

### Prueba 2: calzar las agujas

`python3 probar_canal.py ID --valor V` sirve para calzar la aguja de cada instrumento sobre su marca, por ejemplo `AIRSPEED --valor 60`.

### Prueba 3: el servo con el transportador

`python3 calibrar_instrumento.py AIRSPEED --transportador`

Solo hace falta si un servo no llega a un extremo o zumba en el tope. Mide su 0° y su 180° con el transportador impreso. Para buscar el tope se usa `--explorar arriba` (o `abajo`), y para barrerlo, `--probar`.

### Prueba 4: cada aguja sobre su carátula

`python3 calibrar_instrumento.py AIRSPEED`

Se hace con el instrumento armado. El programa lleva la aguja a cada número grande y con las flechas se la deja justo encima; después, Enter. Izquierda y derecha la mueven un poquito, arriba y abajo más. No hace falta Enter para cada toque y se pueden dejar apretadas. Si las flechas no andan, con `--sin-flechas` se usa `+` / `-` con Enter.

Guarda el pulso de cada marca en `calibracion_servos.json`, y desde ahí el tablero usa esas marcas. Otras opciones:

- `--todos` pasa por todos. Antes de cada uno, y también en el medio, `p` lo saltea sin guardarlo y sigue con el siguiente; al final dice cuáles quedaron. `--saltear VSI,TURN` deja afuera los que se nombran.
- `--listar` muestra cuáles tienen calibración.
- `AIRSPEED --olvidar` borra las de uno.

El horizonte depende del armado, que se elige en `HORIZONTE` de `configuracion.py` con `alabeo_directo` y `cabeceo_fijo`. En el armado simple, que es el que tenemos ahora, el plato va pegado al eje del servo de alabeo (1 a 1, marcas −60, 0 y 60) y el disco va fijo. Ahí se calibra solo `ATT_ROLL`, el canal 13 queda libre y la página avisa "cabeceo fijo en el tablero".

En el armado intermedio (`cabeceo_fijo` en False) el cabeceo funciona con la corredera. Se calibra igual, pero moviendo el disco: cada línea (20, 10, 0, 10, 20) sobre el avioncito. Antes hay que correr `python3 probar_canal.py ATT_PITCH --valor 0` para calzar el brazo del servo derecho hacia la ranura de la corredera.

### Prueba 5: prueba general

`python3 prueba_general.py`

Prueba el tablero entero. Tarda unos 15 minutos y detiene y arranca el servicio sola. Tiene tres partes: diagnóstico, hardware solo y tablero entero.

En la de hardware las 20 agujas barren juntas mientras se mide la alimentación, y esa es la prueba de la fuente de servos. En la del tablero entero se toma el mando con la clave del profesor, se prueban las luces desde el mando, se meten dos fallas (aceite y generador) y se comprueba la pantalla y un celular.

Todas las pruebas aceptan `--simulado --auto` para ver cómo son en una computadora, sin hardware. Las pruebas automáticas del programa tampoco necesitan hardware y se corren con `python3 pruebas/correr_pruebas.py`.

## Uso de todos los días

### Encender y apagar

Para encender, la llave BATERÍA en ENC y prender la zapatilla. La Raspberry arranca sola y el tablero queda en reposo hasta que el profesor toca "Activar tablero" en el modo profesor.

Para apagar, la llave BATERÍA a APAG y dejarla ahí. A los 2 segundos la pantalla muestra "Apagando el tablero" con una cuenta de 5 segundos; si en ese tiempo la llave vuelve a ENC, se cancela y el cartel se va. Al terminar la cuenta se apagan las luces, los servos quedan sueltos, la brújula vuelve a su cero y la Raspberry se apaga, y eso ya no se cancela. Cuando la pantalla queda negra, esperar un minuto y recién ahí apagar la zapatilla. Para volver a prenderla hay que cortar la zapatilla y volver a darla.

Si la Pi arranca con la llave ya en APAG, no se apaga: avisa arriba de la pantalla hasta que la pasen a ENC.

Para poder apagar, el servicio tiene un permiso de sudo solo para `systemctl poweroff`. Lo deja `instalar.sh`; si falta, `bash instalar.sh --permiso-apagado`. El punto 4 de `python3 diagnostico_pi.py` dice en qué posición lee la llave y si está el permiso.

### Clave del profesor

Es para operar el tablero desde el celular: modos, fallas, prueba de luces. En la página se toca "Profesor" (arriba a la derecha) y se escribe la clave. La primera vez es `profesor-h08`, y con esa solo se puede entrar a elegir una propia de 6 caracteres o más. Después se cambia desde el final de la botonera. Si el profesor se la olvida, vuelve a la inicial con:

```
python3 tablero_pi5.py --restablecer-clave
```

Después de 5 errores seguidos, ese celular tiene que esperar un minuto. La clave viaja sin cifrar por la red del tablero: alcanza para un aula, no para alguien que se lo proponga.

Ya no hay QR del profesor, se entra solo con la clave. La clave interna que guarda `secreto_admin.json` la usan los programas de prueba de la propia Raspberry, y el servidor la acepta únicamente desde la Raspberry.

### La página

Es el diseño F. En el proyector y en una computadora se ve la chapa negra con los instrumentos en el mismo orden que el tablero real, las luces con nombres simples, la fase del vuelo y el QR para entrar, con la clave del wifi y la dirección escrita.

En el celular del alumno aparece la fase, un instrumento grande con su ficha (qué mide, normal y máximo), las pestañas "Vuelo", "Motor", "Luces" y "3D", y abajo "Ver el tablero completo".

Si el tablero se reinicia, la página muestra "Reconectando" y vuelve sola. Las agujas se mueven continuas entre dato y dato, y las carátulas quedan guardadas en el celular: solo se vuelven a bajar si cambiaron. Las letras, el logo y los colores viajan con el programa (`web/fuentes`, `web/logo.png`, `web/estilo.css`).

Para el público hay un cartel para imprimir en `http://10.55.0.1/cartel`, con el QR de la red wifi y el de la página. Debajo de cada QR van escritas la clave del wifi y la dirección, y en el proyector también.

### El helicóptero en 3D

En la pantalla ancha, arriba hay tres botones: "Tablero", "Los dos" y "Helicóptero" (teclas 1, 2 y 3). En el celular es la pestaña "3D".

El helicóptero vuela con el simulador: despega, vira, entra en autorrotación, y con cada falla muestra lo que se vería desde afuera (humo, rotor de cola parado, baliza apagada). Con "Cabina" se ve el tablero desde el asiento del piloto, con las mismas agujas. Lo que elige cada uno queda en su navegador y no les cambia nada a los demás.

Para que la pantalla de la Pi arranque mostrando los dos, en `pantalla.sh` se cambia la línea `URL="http://localhost:${PUERTO}/?pantalla=1"` por `URL="http://localhost:${PUERTO}/?pantalla=1&vista=dos"` (o `vista=heli` para el helicóptero solo).

Si la Pi se pone lenta, el botón "Imagen" del 3D pasa a la imagen liviana. Además, si no le alcanzan los cuadros por segundo, el 3D baja un poco la resolución solo y la recupera cuando sobra.

### La pantalla de la Raspberry

`pantalla.sh` agranda todo para que se vea como en una pantalla de 1920 × 1080; en un televisor 4K, sin esto, queda chiquito. Si igual se ve chico porque la pantalla está lejos, en `pantalla.sh` se pone `ESCALA="1.25"` (o `"1.5"`) y se reinicia. `actualizar.sh` lo vuelve a automático.

Para salir al escritorio de la Raspberry, Alt + F4 cierra la pantalla del tablero, que no se vuelve a abrir sola hasta el próximo encendido. Con Ctrl + Alt + T se abre una terminal encima. Para volver a la pantalla: menú > "Pantalla del tablero", o `bash pantalla.sh`.

Para que deje de abrirse sola al encender, `bash pantalla.sh quitar`, y `bash pantalla.sh instalar` para que vuelva.

### La red del tablero

La red se llama Tablero-H08 y la clave es sikorsky55. Cualquier celular o tablet conectado entra escribiendo `10.55.0.1` en el navegador y ve el tablero en vivo.

En la mayoría de los celulares la página se abre sola al conectarse, como en el wifi de un aeropuerto. Si no, hay que tocar "Mantener conexión" cuando avisa que no hay internet. Esa ventana muestra directamente el tablero, con un renglón de ayuda arriba (no hay botón "Entrar"). Para esto el servicio atiende también en el puerto 80, cosa que deja lista `instalar.sh`.

A Android nunca se le dice que hay internet, porque si no cierra solo esa ventana. En Android, si el navegador no carga `10.55.0.1`, hay que apagar los datos móviles: como la red del tablero no tiene internet, el celular manda todo por los datos. Al iPhone sí se le dice, después de abrir el tablero, para que muestre "OK" y no se desconecte. Eso vale mientras lo usa; con 5 minutos sin usarlo, la próxima vez vuelve a ver la ventana.

Para revisar la red hay dos comandos. `sudo bash punto_de_acceso.sh revisar` dice, paso a paso, qué está bien y qué falla, con el comando que lo arregla. `python3 diagnostico_pi.py` prueba, como si fuera un celular, que los nombres de internet lleven a la Raspberry y que la prueba de Android abra la bienvenida.

Si se cambia el nombre o la clave en `punto_de_acceso.sh`, alcanza con `sudo bash punto_de_acceso.sh encender` para que la red los tome. El QR y el cartel los leen del mismo archivo.

El wifi de la Raspberry acepta unos 8 celulares a la vez. La pantalla muestra "Celulares conectados: N de 8" y avisa "Red llena" cuando no entran más. Al encender, la Pi mira los wifi de alrededor y se pone en el canal más libre (1, 6 u 11); para dejarlo fijo, `CANAL_FIJO="6"` en `punto_de_acceso.sh`. El wifi de la Pi no usa ahorro de energía, así no hay demoras ni cortes.

Al encender, la Raspberry levanta Tablero-H08 antes que cualquier otro wifi guardado y, si falla, la reintenta sin límite. Además, el servicio `tablero-h08-red` revisa cada 20 segundos que esté levantada; si se cayó o la placa quedó en el wifi de la escuela, la vuelve a levantar. O sea que cada vez que se prende la Pi arrancan solos el tablero y la red Tablero-H08, aunque antes se haya apagado la red. Lo dejan listo `instalar.sh` y `actualizar.sh`.

### Desconectar celulares

En el modo profesor, "Celulares conectados" muestra quién está en la red: nombre, hace cuánto, y cuál es el del profesor. "Desconectar" (dos toques) lo anota en `bloqueados_red.txt`. El servicio `tablero-h08-red`, que corre como root, lo saca de la wifi cada 2 segundos si intenta volver, y la página le contesta "El profesor te desconectó".

"Permitir" lo deja volver. Al reiniciar la Pi la lista se borra. `actualizar.sh` no toca ese archivo y no viaja en el zip.

### Volver a la red de la escuela

Con `sudo bash punto_de_acceso.sh apagar`, y después conectarse al wifi de la escuela con el ícono de red del escritorio. Dura hasta que se reinicia la Pi: al encender vuelve sola la red del tablero. Mientras la red propia esté apagada así, el servicio `tablero-h08-red` no la vuelve a levantar.

Para volver a la red propia sin reiniciar: `sudo bash punto_de_acceso.sh permanente`.

### Cortes y reinicios

Cada página hace un pedido por vez y no queda colgada. Las conexiones de un celular que se fue se cierran solas a los 20 s y los cortes no llenan el registro. Si un PCA9685 se reinicia, sus servos vuelven de a tandas, sin el pico que lo reinició. Si el motor de la brújula da un error, se reintenta y `diagnostico_pi.py` lo muestra.

## Actualizar a una versión nueva

Si trabajás el código en la computadora, el zip se arma ahí con `py empaquetar.py`. Primero corre las pruebas y, si pasan, deja `dist/H08_Pi5.zip`. Eso se lleva a la Pi en un pendrive y se instala con:

```
bash actualizar.sh /media/USUARIO/PENDRIVE/H08_Pi5.zip
```

Deja la carpeta instalada igual al paquete nuevo: copia lo nuevo y **borra lo que ya no viene** (programas viejos, archivos sueltos). Antes guarda al lado un respaldo completo (`H08_respaldo_FECHA`; quedan los 2 más nuevos). Nunca toca lo que es de este tablero:

- `secreto_admin.json`, la clave del profesor;
- `calibracion_servos.json`, lo medido en cada servo;
- `posicion_motores.json`, dónde quedó la aguja de la brújula;
- `informes/`, donde quedan los 20 más nuevos.

Después da el permiso de la llave BATERÍA y reinicia el servicio. La pantalla de la Raspberry se recarga sola con la versión nueva, y los celulares la ven al recargar la página. Si venía de una versión que llamaba a la pantalla con el nombre anterior, `actualizar.sh` la pasa sola a `pantalla.sh`.

## Cómo funcionan las luces

En la placa, el ánodo de cada LED va a +5 V y el cátodo va, por su resistencia de 220 Ω, a una salida del PCA9685. Por eso la luz enciende con la salida en BAJO. El programa ya lo tiene en cuenta (`LUCES_ACTIVAS_EN_BAJO` en `nucleo/configuracion.py`).

Al dar energía, las seis luces se encienden hasta que arranca el servicio, unos 20 a 30 segundos. Es normal y sirve de prueba de lámparas del encendido: la que no prende ahí tiene el LED o el cable cortado.

Cada luz se enciende por su condición del modelo, la que figura en la tabla de canales. Si la barra eléctrica cae por debajo de 20 V se apagan todas, como en el avión. La prueba de lámparas del mando enciende las seis en el tablero y también en la página, que muestra lo que tienen las luces de verdad.

Con la salida "apagada" (en alto, 3,3 V), al LED le quedan 1,7 V, así que un LED rojo o ámbar puede verse apenas encendido en la oscuridad. Es una luz fantasma que el programa no puede evitar. Se arregla en la placa con un diodo 1N4148 en serie con cada LED. Se ve con `python3 probar_canal.py --luces` en la oscuridad.

## Si algo no anda

| Síntoma | Qué hacer |
|---|---|
| La llave BATERÍA no apaga | `python3 diagnostico_pi.py`, punto 4: si no lee APAG, revisar los cables a las patas 37 y 39; si falta el permiso, `bash instalar.sh --permiso-apagado` |
| La pantalla dice "La llave BATERÍA está en APAG" | Arrancó con la llave abajo: pasarla a ENC (no apaga nada) |
| La pantalla queda en el escritorio | `bash pantalla.sh`. Si al reiniciar sigue igual: `python3 diagnostico_pi.py`, punto 6 |
| La Pi no se conecta al wifi de la escuela | Está levantada la red propia: `sudo bash punto_de_acceso.sh apagar` |
| La página dice "sin conexión" | `sudo systemctl status tablero-h08`, `journalctl -u tablero-h08 -n 50` |
| Ninguna aguja se mueve | `python3 diagnostico_pi.py`: el punto 3 dice si responden los PCA9685 |
| Una sola aguja no se mueve | `python3 probar_canal.py ESA --recorrer`, después el cable de su canal |
| La aguja marca corrido | `python3 probar_canal.py ESA --valor V` y calzar la aguja |
| Cae bien en unas marcas y en otras no | `python3 calibrar_instrumento.py ESA` |
| Zumba contra un tope | `python3 calibrar_instrumento.py ESA --explorar arriba` (o `abajo`) y después `ESA --transportador` |
| Las placas se reinician cuando se mueven muchas agujas | Es la fuente de servos: el LM2596 da 3 A como máximo. `prueba_general.py` (A3) lo muestra |
| La aguja de un instrumento gira al revés | `python3 calibrar_instrumento.py ESE` y, al empezar, elegir el giro al revés (`r`) |
| La brújula gira al revés | `python3 calibrar_instrumento.py COMPASS` (lo detecta y lo da vuelta) |
| La brújula tiembla y no gira | `python3 probar_motor.py 1 --bobinas`: las bobinas tienen que ir en orden A-B-C-D |
| El celular no ve la red | `sudo bash punto_de_acceso.sh revisar`: revisa placa, país, dnsmasq, clave, dirección y página, y dice qué falla |
| El celular se conecta pero no abre la página | `sudo bash punto_de_acceso.sh revisar` (lo más común: falta `dnsmasq-base`, o la clave guardada no es la del QR) |
| No entran más de 8 celulares | Es el límite del wifi de la Raspberry; para más hace falta un router aparte |

## Qué hay en la carpeta

- `LEEME.md`: esto.
- `VERSION.txt`: qué versión es.
- `empaquetar.py`: arma `dist/H08_Pi5.zip` para llevar a la Pi.
- `.gitignore` y `.gitattributes`: para git, dejan lo privado afuera y el fin de línea en LF.
- `nucleo/`: el modelo, las fallas, el mapa del tablero, las placas, el motor y el servidor web.
- `raspberry_pi5/`:
  - `tablero_pi5.py`: el programa (lo arranca el servicio).
  - `instalar.sh`: la instalación, una vez.
  - `actualizar.sh`: para pasar a una versión nueva.
  - `pantalla.sh`: el tablero en la pantalla de la Raspberry.
  - `punto_de_acceso.sh`: la red wifi propia.
  - `diagnostico_pi.py`: diagnóstico de conexiones e instalación.
  - `prueba_general.py`: el tablero entero.
  - `probar_canal.py`: un canal suelto, para calzar agujas.
  - `probar_motor.py`: el motor suelto, sentido y cero.
  - `calibrar_instrumento.py`: la calibración de cada aguja sobre su carátula, del servo suelto (`--transportador`) y de la brújula.
  - `web/`: la página del tablero, la del mando, las carátulas y `3d/` (el helicóptero en 3D, con three.js).
- `pruebas/`: pruebas automáticas, sin hardware.
