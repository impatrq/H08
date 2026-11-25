# Piezas impresas

Todas las piezas del tablero en STL, separadas por tipo. La cantidad va en el nombre del archivo: `Tapa_carcasa50_engranajes_36-24_x6.stl` se imprime 6 veces. Todo va a escala 100 %, en PLA y sin soportes (las piezas ya están acostadas como se imprimen).

En `Modelo_3D_helicoptero` está el modelo 3D del Sikorsky entero (.glb). Se abre con el Visor 3D de Windows o en cualquier visor de glTF.

`Caratulas_para_imprimir.pdf` tiene las carátulas de papel del tamaño de cada carcasa.

## Carcasas redondas

En `H_Carcasas_redondas` están las carcasas de 50, 58 y 80 mm que diseñamos nosotros. Son una placa cuadrada con el lugar para la carátula adelante y dos soportes atrás, en el centro. Va una por instrumento, pegada adelante de la chapa.

Según el instrumento las usamos de dos formas:

- Si la aguja va directo al servo (combustible delantero y trasero, amperímetro, voltímetro, viraje y AN/ARN-14), la carcasa va como está y el servo se fija a los dos soportes.
- Si lleva engranajes, a la carcasa le cortamos los dos soportes y en su lugar pegamos la tapa (carpeta B). A la tapa se pega la placa del servo (carpeta C), que deja el servo corrido del centro para que su rueda engrane con la de la aguja.

## Cuánto imprimir

Aparte de una carcasa redonda por instrumento:

| Cant. | Pieza | Carpeta |
|---|---|---|
| 1 | Carcasa de la brújula (135 x 135) | A |
| 1 | Carcasa del horizonte con ventana (135 x 135) | A |
| 1 | Tapa de la brújula | B |
| 6 | Tapa carcasa 50, engranajes 36/24 | B |
| 1 | Tapa carcasa 58, engranajes 36/24 | B |
| 1 | Tapa carcasa 80, engranajes 36/24 | B |
| 3 | Tapa carcasa 80, engranajes 40/24 | B |
| 1 | Tapa carcasa 80, engranajes 48/24 | B |
| 6 | Placa del servo carcasa 50, engranajes (espejada) | C |
| 1 | Placa del servo carcasa 58, 36/24 | C |
| 1 | Placa del servo carcasa 80, 36/24 | C |
| 3 | Placa del servo carcasa 80, 40/24 | C |
| 1 | Placa del servo carcasa 80, 48/24 | C |
| 1 | Placa del motor de la brújula | C |
| 1 | Acople del motor a la aguja de la brújula | D |
| 12 | Rueda de la aguja, 24 dientes | D |
| 8 | Rueda del servo, 36 dientes | D |
| 3 | Rueda del servo, 40 dientes | D |
| 1 | Rueda del servo, 48 dientes | D |
| 3 | Horizonte: disco, plato y chasis, una de cada una | F |

Son 56 piezas. En `G_Agujas_SG90` están las agujas que calzan en el eje del servo (16, 22, 34 y 47 mm).

La placa del servo de las carcasas de 50 con engranajes es la versión espejada. Con la primera el eje del servo quedaba en el centro, y para que la rueda de 36 llegue a la de 24 tiene que quedar a 15 mm. Va en presión y temperatura de aceite, presión de combustible, aire del carburador y presión y temperatura de transmisión.

## Engranajes

Con la aguja directa el recorrido es el del servo, de 40° a 120° según el instrumento. Con 36/24 la aguja gira 1,5 veces lo que gira el servo y llega a 270°: aceite, combustible, carburador, culata, admisión y transmisión. Con 40/24 llega a 300° (velocímetro, tacómetro y variómetro) y con 48/24 a 360°, que es el altímetro. La brújula gira sin fin con el paso a paso.

## Horizonte

El horizonte del tablero mueve solo el alabeo. Lleva tres piezas: el disco de cielo y tierra, el plato, que va pegado al eje del servo, y el chasis fijo, recortado para que no choque con el plato. Están en `F_Horizonte_artificial`, junto con el dibujo del disco en PDF para imprimir en papel.
