#!/usr/bin/env bash
# Deja la Pi 5 lista para el tablero. Se corre una vez, sin sudo delante, en
# Raspberry Pi OS con escritorio (Bookworm o posterior, 64 bits), y después
# hay que reiniciar. Opciones: --sin-pantalla, --sin-wifi, --quitar-pantalla,
# --permiso-apagado (este último lo usa actualizar.sh).
# Nada de pip ni entorno virtual: todo sale de apt.
set -e

AQUI="$(cd "$(dirname "$0")" && pwd)"
USUARIO="$(id -un)"
SERVICIO=tablero-h08
PANTALLA=si
WIFI=si
REGLA_APAGADO=/etc/sudoers.d/tablero-h08-apagar

# para la llave BATERÍA: el servicio no es root y solo puede correr
# systemctl poweroff sin contraseña
permiso_apagado() {
    local tmp
    tmp="$(mktemp)"
    echo "$USUARIO ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff" > "$tmp"
    if sudo visudo -cf "$tmp" >/dev/null; then
        sudo install -m 0440 -o root -g root "$tmp" "$REGLA_APAGADO"
        echo "   La llave BATERÍA puede apagar la Raspberry ($REGLA_APAGADO)."
    else
        echo "   No se pudo crear el permiso de apagado: la llave BATERÍA no va a apagar."
    fi
    rm -f "$tmp"
}

for a in "$@"; do
    case "$a" in
        --sin-pantalla) PANTALLA=no ;;
        --sin-wifi) WIFI=no ;;
        --quitar-pantalla)
            bash "$AQUI/pantalla.sh" quitar
            exit 0 ;;
        --permiso-apagado)
            [ "$(id -u)" = "0" ] && { echo "Correrlo sin sudo delante"; exit 1; }
            permiso_apagado
            exit 0 ;;
        *) echo "Opción desconocida: $a"; exit 1 ;;
    esac
done

if [ "$(id -u)" = "0" ]; then
    echo "Correrlo sin sudo delante:  bash instalar.sh"
    exit 1
fi

echo "== 1. Paquetes del sistema =="
# solo lo que falta, así se puede reinstalar sin internet (con la red propia levantada no hay)
FALTAN=""
# dnsmasq-base e iw suelen venir, pero no siempre
for p in python3 python3-gpiozero python3-lgpio i2c-tools rsync unzip dnsmasq-base iw; do
    dpkg -s "$p" >/dev/null 2>&1 || FALTAN="$FALTAN $p"
done
if [ "$PANTALLA" = "si" ] && ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null; then
    FALTAN="$FALTAN chromium"
fi
if [ -n "$FALTAN" ]; then
    echo "   Faltan:$FALTAN"
    if ! { sudo apt-get update && sudo apt-get install -y $FALTAN; }; then
        echo
        echo "   No se pudieron bajar los paquetes: ¿la Pi tiene internet?"
        echo "   Si está levantada la red propia, no hay internet. Volvé a la red de"
        echo "   la escuela con  sudo bash punto_de_acceso.sh apagar  y corré esto de nuevo."
        exit 1
    fi
else
    echo "   Ya están todos."
fi

echo
echo "== 2. I2C =="
if command -v raspi-config >/dev/null; then
    sudo raspi-config nonint do_i2c 0
fi
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
if [ -f "$CONFIG" ]; then
    if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG"; then
        echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG" >/dev/null
    fi
    if ! grep -q "^dtparam=i2c_arm_baudrate=" "$CONFIG"; then
        echo "dtparam=i2c_arm_baudrate=400000" | sudo tee -a "$CONFIG" >/dev/null
    fi
    echo "   I2C habilitado en $CONFIG"
fi

echo
echo "== 3. Grupos del usuario $USUARIO =="
sudo usermod -aG i2c,gpio,video "$USUARIO"

echo
echo "== 4. Clave interna =="
python3 "$AQUI/tablero_pi5.py" --preparar-clave >/dev/null
chmod 600 "$AQUI/secreto_admin.json"
echo "   Lista. El profesor entra con su clave desde la página (“Profesor”)."

echo
echo "== 5. Servicio $SERVICIO =="
chmod +x "$AQUI"/*.sh "$AQUI"/*.py 2>/dev/null || true
sudo tee /etc/systemd/system/$SERVICIO.service >/dev/null <<FIN
[Unit]
Description=Tablero didáctico Sikorsky S-55 H-08
After=network.target
# Con el tablero arranca también el que levanta la red Tablero-H08
Wants=tablero-h08-red.service
# Que lo reintente siempre, sin límite de intentos
StartLimitIntervalSec=0

[Service]
# notify: el programa avisa que arrancó y, cada 5 s, que sigue vivo. Si se
# cuelga y deja de avisar 30 s, systemd lo reinicia (tablero_pi5.vigilar).
Type=notify
NotifyAccess=main
WatchdogSec=30
User=$USUARIO
SupplementaryGroups=i2c gpio video
# Permiso para atender en el puerto 80 (sólo eso, sin ser root): la dirección
# queda 10.55.0.1, sin número, y la página se abre sola al conectarse.
AmbientCapabilities=CAP_NET_BIND_SERVICE
WorkingDirectory=$AQUI
ExecStart=/usr/bin/python3 $AQUI/tablero_pi5.py
Restart=always
RestartSec=3
# Al detenerse lleva la aguja de la brújula a cero: le damos tiempo.
TimeoutStopSec=20
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
FIN
sudo systemctl daemon-reload
sudo systemctl enable $SERVICIO
permiso_apagado

echo
if [ "$PANTALLA" = "si" ]; then
    echo "== 6. Pantalla: escritorio sin contraseña, sin apagarse y el tablero abierto =="
    if command -v raspi-config >/dev/null; then
        sudo raspi-config nonint do_boot_behaviour B4    # escritorio con autologin
        sudo raspi-config nonint do_blanking 1           # que la pantalla no se apague
    else
        echo "   (sin raspi-config: el inicio automático y el protector de pantalla hay que dejarlos a mano)"
    fi
    bash "$AQUI/pantalla.sh" instalar
    echo "   Para salir al escritorio: Alt + F4 (o  bash pantalla.sh parar)"
else
    echo "== 6. Pantalla: se deja como está (--sin-pantalla) =="
fi

echo
if [ "$WIFI" = "si" ]; then
    echo "== 7. Red wifi propia =="
    # 'preparar' no la levanta ahora: si se instala por wifi, cortaría la conexión
    sudo bash "$AQUI/punto_de_acceso.sh" preparar
    echo "   Si falla al encender o se cae, el servicio tablero-h08-red la vuelve a levantar."
    echo "   Mientras esté levantada, la Pi no entra al wifi de la escuela."
    echo "   Acepta unos 8 celulares a la vez (límite del wifi de la Raspberry)."
    echo "   Para revisarla después de reiniciar:  sudo bash punto_de_acceso.sh revisar"
    echo "   Para volver a la red de la escuela:  sudo bash punto_de_acceso.sh apagar"
    echo "   (dura hasta reiniciar: al encender, la Pi vuelve sola a Tablero-H08)"
else
    echo "== 7. Red wifi propia: no (--sin-wifi). La Pi usa el wifi de la escuela =="
fi

echo
echo "=========================================================================="
echo " Listo. FALTA REINICIAR UNA VEZ:   sudo reboot"
echo
echo " Después del reinicio, solo:"
echo "   - arranca el servicio del tablero (servos, luces, brújula y página);"
[ "$PANTALLA" = "si" ] && echo "   - la pantalla muestra el tablero, con los QR para entrar desde el celular;"
[ "$WIFI" = "si" ] && echo "   - la red Tablero-H08 queda levantada: http://10.55.0.1  (se abre sola al conectarse)"
echo
echo " Para comprobar todo:        python3 diagnostico_pi.py"
echo " Prueba general guiada:      python3 prueba_general.py"
echo " Clave del profesor:         la primera vez es profesor-h08 (la página pide cambiarla)"
echo " Ver lo que hace:            journalctl -u $SERVICIO -f"
echo "=========================================================================="
