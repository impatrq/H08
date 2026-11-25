# -*- coding: utf-8 -*-
"""Bus de señales: valor real (lo que pasa en la máquina) y valor indicado (lo
que marca la aguja), con el retardo y el ruido de cada sensor en el medio.

Una falla de sistema cambia el real; una de indicación, solo el indicado.
Distinguirlas es justamente lo que se practica con el tablero.
"""

from utiles import aproximar, limitar, RNG

# (tau en s, amplitud de ruido en unidades de la señal).
# Ruido puesto a ojo: el R-1340 es un radial de 9 cilindros y las agujas tiemblan
SENSORES = {
    "ias_kt":        (0.30, 0.6),
    "alt_ind_ft":    (0.40, 4.0),
    "alt_centenas":  (0.40, 4.0),
    "vs_ind_fpm":    (1.80, 25.0),    # el VSI real tiene un retardo enorme
    "hdg_ind_deg":   (0.50, 0.4),
    "pitch_ind_deg": (0.15, 0.20),
    "roll_ind_deg":  (0.15, 0.25),
    "turn_rate_dps": (0.35, 0.06),
    "slip":          (0.30, 0.02),
    "n_eng_rpm":     (0.20, 12.0),    # vibración del radial
    "n_rot_rpm":     (0.25, 1.2),
    "map_inhg":      (0.20, 0.35),
    "oil_p_psi":     (0.30, 1.5),
    "oil_t_c":       (2.50, 0.4),
    "cht_c":         (2.00, 2.0),
    "cat_c":         (1.50, 0.5),
    "fuel_p_psi":    (0.30, 0.4),
    "fuel_fwd_l":    (2.00, 2.5),     # flotante: lento y sucio
    "fuel_aft_l":    (2.00, 2.5),
    "xmsn_p_psi":    (0.40, 1.0),
    "xmsn_t_c":      (3.00, 0.5),
    "bus_v":         (0.30, 0.10),
    "amp_a":         (0.50, 2.5),
    "cdi":           (0.80, 0.05),
}

# Con su período. Si no, al cruzar el norte la rosa desanda una vuelta entera
CIRCULARES = {
    "hdg_ind_deg": 360.0,
    "alt_centenas": 1000.0,
}


def envolver(d, periodo):
    return (d + periodo / 2.0) % periodo - periodo / 2.0


# anomalías de indicación
IND_CONGELADO = "congelado"
IND_FIJO = "fijo"             # ej: 0 = transductor cortado
IND_RUIDO = "ruido"           # mal contacto
IND_OSCILA = "oscila"


class BusSenales:
    # real lo escribe el modelo de vuelo, indicado lo leen los actuadores

    def __init__(self):
        self.real = {}
        self.indicado = {}        # filtrado + ruido
        self._filtrado = {}       # sin ruido
        self._anomalias = {}
        self._fase_osc = 0.0
        self._inicializado = False

    def poner(self, nombre, valor):
        self.real[nombre] = valor

    def obtener(self, nombre, por_defecto=0.0):
        return self.real.get(nombre, por_defecto)

    def ver(self, nombre, por_defecto=0.0):
        # el indicado, no el real
        return self.indicado.get(nombre, por_defecto)

    def limpiar_anomalias(self):
        self._anomalias = {}

    def agregar_anomalia(self, senal, tipo, valor=0.0):
        lst = self._anomalias.get(senal)
        if lst is None:
            lst = []
            self._anomalias[senal] = lst
        lst.append({"tipo": tipo, "valor": valor})

    def tiene_anomalia(self, senal):
        return senal in self._anomalias

    def actualizar_indicaciones(self, dt, energia=1.0, vibracion=0.0):
        """Real a indicado: retardo, ruido, anomalías y caída de la barra.

        vibracion (0..1.2) escala el ruido con las RPM: con el motor parado no tiembla nada.
        """
        self._fase_osc += dt

        # 0..1 o booleano. Con la barra en 18 V durante el arranque los
        # aforadores marcan de menos y después se recuperan
        if energia is True:
            factor_e = 1.0
        elif energia is False:
            factor_e = 0.0
        else:
            factor_e = limitar(float(energia), 0.0, 1.0)

        # así las agujas no salen disparadas desde cero
        if not self._inicializado:
            for k in self.real:
                self._filtrado[k] = self.real[k]
                self.indicado[k] = self.real[k]
            self._inicializado = True

        for nombre in self.real:
            valor = self.real[nombre]
            tau, ruido = SENSORES.get(nombre, (0.0, 0.0))
            previo = self._filtrado.get(nombre, valor)

            anomalias = self._anomalias.get(nombre)
            congelado = False
            extra_ruido = 0.0

            if anomalias:
                for a in anomalias:
                    t = a["tipo"]
                    if t == IND_CONGELADO:
                        congelado = True
                    elif t == IND_FIJO:
                        valor = a["valor"]
                        tau = 0.35          # igual tarda en llegar
                        ruido = 0.0
                    elif t == IND_RUIDO:
                        # no depende de la vibración del motor
                        extra_ruido += a["valor"]
                    elif t == IND_OSCILA:
                        # ~0,8 Hz
                        valor = valor + a["valor"] * _sin_aprox(self._fase_osc * 5.0)

            if congelado:
                # pitot obstruido, estática tapada o aguja trabada
                self.indicado[nombre] = previo
                continue

            if factor_e < 1.0 and nombre in _SENALES_ELECTRICAS:
                valor = valor * factor_e
                tau = tau if tau > 1.2 else 1.2

            periodo = CIRCULARES.get(nombre)
            if periodo:
                valor = previo + envolver(valor - previo, periodo)
            filtrado = aproximar(previo, valor, dt, tau)
            if periodo:
                filtrado %= periodo
            self._filtrado[nombre] = filtrado

            # El ruido va después del filtro y no se realimenta: si entrara,
            # haría un paseo aleatorio mucho más grande que el declarado.
            amplitud = ruido * vibracion + extra_ruido
            if amplitud > 0.0:
                mostrado = filtrado + RNG.simetrico() * amplitud
            else:
                mostrado = filtrado
            self.indicado[nombre] = mostrado % periodo if periodo else mostrado


# Los que dejan de indicar sin la barra de 24 V: aforadores, bulbos de
# resistencia (aceite, carburador), transmisores de la transmisión y el CDI.
# Velocímetro, altímetro y VSI son neumáticos; el tacómetro tiene su generador
# (por eso es EL instrumento del arranque); los Bourdon son mecánicos y la CHT
# es termocupla. Es la base del escenario de falla eléctrica.
_SENALES_ELECTRICAS = (
    "oil_t_c", "cat_c",
    "fuel_fwd_l", "fuel_aft_l", "xmsn_p_psi", "xmsn_t_c",
    "cdi",
)


def _sin_aprox(x):
    # Bhaskara, error < 0,2 %
    TWO_PI = 6.283185307179586
    PI = 3.141592653589793
    x = x % TWO_PI
    if x > PI:
        x -= TWO_PI
    neg = False
    if x < 0.0:
        x = -x
        neg = True
    y = (16.0 * x * (PI - x)) / (5.0 * PI * PI - 4.0 * x * (PI - x))
    return -y if neg else y
