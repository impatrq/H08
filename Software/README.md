# Programa

`H08_Pi5` es todo lo que va en la Raspberry Pi 5. Está en Python 3 y usa solo la biblioteca estándar y `gpiozero`/`lgpio`, que vienen con el sistema. No usa pip ni necesita internet.

Lo que hace:

- simula el vuelo (motor, rotor, transmisión, aceite, combustible, eléctrico, actitud y rumbo)
- mueve los 20 servos de las dos PCA9685, las 6 luces y el motor de la brújula, cada instrumento con su calibración y sus engranajes
- muestra el tablero en la pantalla HDMI y en los celulares, con el helicóptero en 3D (three.js)
- tiene un modo profesor con clave, para elegir la fase del vuelo, meter fallas, probar las luces y sacar celulares de la red
- arma la red wifi Tablero-H08 (clave sikorsky55) y en casi todos los celulares la página se abre sola
- se apaga en orden con la llave BATERÍA

## Dónde está cada cosa

- `nucleo/`: la simulación y el control. `configuracion.py` tiene todos los números (canales, calibración, red, tiempos), `modelo_vuelo.py` es el modelo del helicóptero, `fallas.py` y `escenarios.py` las fallas y fases del vuelo, `mapa_tablero.py` pasa de valor del instrumento a ángulo del servo, y `servidor_web.py` es la página y el portal de la red.
- `raspberry_pi5/`: el programa principal (`tablero_pi5.py`), los scripts de instalación, pantalla y red, y los programas para probar y calibrar. En `web/` están la página del tablero, la del profesor, las carátulas y el 3D.
- `pruebas/`: pruebas que corren en cualquier compu, sin hardware.

## Conexiones de la Raspberry

| Función | GPIO | Pata |
|---|---|---|
| 3,3 V (lógica de las PCA9685) | - | 1 |
| SDA | GPIO2 | 3 |
| SCL | GPIO3 | 5 |
| GND | - | 6, 9, 14, 20, 25, 30, 34, 39 |
| Motor IN1, IN2, IN3, IN4 | GPIO12, 16, 20, 21 | 32, 36, 38, 40 |
| Llave BATERÍA | GPIO26 | 37 (la otra pata de la llave a GND, en la 39) |

La PCA0 está en 0x40, sin puentes. La PCA1 en 0x41, con el puente A0 soldado. Qué instrumento va en cada canal está en el [LEEME](H08_Pi5/LEEME.md#qué-mueve-cada-canal).

## Instalarlo

Hace falta Raspberry Pi OS con escritorio, 64 bits (Bookworm o más nuevo).

```bash
cd ~/H08_Pi5/raspberry_pi5
bash instalar.sh
sudo reboot
python3 diagnostico_pi.py
```

`instalar.sh` va sin sudo, la clave la pide solo. El diagnóstico se corre después de reiniciar.

Para correr las pruebas en la compu:

```bash
cd H08_Pi5
python3 pruebas/correr_pruebas.py
```

Hay tres archivos que no están en el repo porque son de cada tablero: `secreto_admin.json` (la clave del profesor), `calibracion_servos.json` (la calibración de cada servo) y `posicion_motores.json` (dónde quedó la aguja de la brújula). Los crea la Raspberry y el `.gitignore` ya los deja afuera.
