#!/usr/bin/env bash
# Pasa a la Pi una versión nueva: bash actualizar.sh /media/$USER/PENDRIVE/H08_Pi5.zip
# Deja la carpeta igual al paquete (borra lo que sobra) pero no toca la clave,
# la calibración, la posición del motor ni los informes. Antes guarda una copia
# en ../H08_respaldo_FECHA.
set -e

ORIGEN="${1:-}"
AQUI="$(cd "$(dirname "$0")" && pwd)"          # .../H08_Pi5/raspberry_pi5
RAIZ="$(dirname "$AQUI")"                      # .../H08_Pi5
SERVICIO=tablero-h08
INFORMES_QUEDAN=20
RESPALDOS_QUEDAN=2

if [ -z "$ORIGEN" ] || [ ! -e "$ORIGEN" ]; then
    echo "Uso:  bash actualizar.sh ARCHIVO.zip | CARPETA"
    exit 1
fi

command -v rsync >/dev/null || { echo "Falta rsync:  sudo apt install -y rsync"; exit 1; }

TMP=""
if [ -f "$ORIGEN" ]; then
    command -v unzip >/dev/null || { echo "Falta unzip:  sudo apt install -y unzip"; exit 1; }
    TMP="$(mktemp -d)"
    unzip -q "$ORIGEN" -d "$TMP"
    ORIGEN="$TMP"
fi
# el zip puede traer una carpeta arriba de todo, por eso se busca tablero_pi5.py
NUEVO="$(dirname "$(dirname "$(find "$ORIGEN" -path '*raspberry_pi5/tablero_pi5.py' | head -n1)")" 2>/dev/null || true)"
if [ -z "$NUEVO" ] || [ ! -f "$NUEVO/raspberry_pi5/tablero_pi5.py" ]; then
    echo "No encuentro raspberry_pi5/tablero_pi5.py dentro de $1"
    [ -n "$TMP" ] && rm -rf "$TMP"
    exit 1
fi

NUEVO="$(cd "$NUEVO" && pwd)"
if [ "$NUEVO" = "$RAIZ" ]; then
    echo "Esa es la carpeta instalada: pasame el zip nuevo o la carpeta descomprimida."
    exit 1
fi
# Si el paquete quedó adentro de la carpeta instalada, se copia aparte: si no,
# el --delete lo borra a mitad de camino.
case "$NUEVO/" in
    "$RAIZ"/*)
        [ -n "$TMP" ] || TMP="$(mktemp -d)"
        cp -a "$NUEVO" "$TMP/paquete"
        NUEVO="$TMP/paquete" ;;
esac

RESPALDO="$(dirname "$RAIZ")/H08_respaldo_$(date +%Y%m%d_%H%M%S)"
echo "== Respaldo de lo instalado en $RESPALDO =="
cp -a "$RAIZ" "$RESPALDO"

echo "== Deteniendo el tablero (agujas a cero) =="
sudo systemctl stop "$SERVICIO" 2>/dev/null || true

echo "== Copiando la versión nueva (y borrando lo que ya no va) =="
# lo excluido no se toca nunca
rsync -a --delete \
    --exclude 'secreto_admin.json' \
    --exclude 'calibracion_servos.json' \
    --exclude 'posicion_motores.json' \
    --exclude 'bloqueados_red.txt' \
    --exclude '__pycache__/' \
    --exclude 'informes/' \
    --exclude '.git/' \
    "$NUEVO"/ "$RAIZ"/
# por si algo vino con CRLF de Windows
sed -i 's/\r$//' "$AQUI"/*.sh 2>/dev/null || true
chmod +x "$AQUI"/*.sh 2>/dev/null || true
[ -n "$TMP" ] && rm -rf "$TMP"

# Si la pantalla se abría sola (con el nombre viejo o el nuevo), queda con
# pantalla.sh y se reabre con la versión nueva.
VIEJO="kios""co"
if [ -f "$HOME/.config/autostart/tablero-$VIEJO.desktop" ] || [ -f "$HOME/.config/autostart/tablero-pantalla.desktop" ] \
   || grep -qs "$VIEJO\.sh\|pantalla\.sh" "$HOME/.config/labwc/autostart"; then
    echo "== Pantalla del tablero =="
    bash "$AQUI/pantalla.sh" instalar
    REABRIR=si
fi

echo "== Informes: quedan los $INFORMES_QUEDAN más nuevos =="
if [ -d "$AQUI/informes" ]; then
    find "$AQUI/informes" -maxdepth 1 -type f -printf '%T@ %p\n' | sort -rn \
        | tail -n +$((INFORMES_QUEDAN + 1)) | cut -d' ' -f2- \
        | while IFS= read -r f; do rm -f -- "$f"; done
fi

echo "== Permiso de la llave BATERÍA =="
bash "$AQUI/instalar.sh" --permiso-apagado \
    || echo "   Sin permiso de apagado: después corré  bash instalar.sh --permiso-apagado"

echo "== Red wifi propia =="
# Si el tablero tiene red propia (aunque ahora esté apagada) se le aplican los
# arreglos nuevos. 'preparar' no la levanta ahora, así no corta un SSH por wifi.
if command -v nmcli >/dev/null \
   && { nmcli -t -f NAME connection show 2>/dev/null | grep -qx tablero-ap \
        || [ -f /etc/systemd/system/tablero-h08-red.service ]; }; then
    if sudo bash "$AQUI/punto_de_acceso.sh" preparar >/dev/null; then
        echo "   Tablero-H08 en cada encendido, y si se cae se vuelve a levantar sola."
    else
        echo "   No se pudo revisar la red propia: después corré  sudo bash punto_de_acceso.sh revisar"
    fi
else
    echo "   Este tablero no usa la red propia ahora: se deja como está."
fi

echo "== Arrancando el tablero =="
# por si quedó deshabilitado
sudo systemctl enable "$SERVICIO" >/dev/null 2>&1 \
    || echo "   No se pudo dejar el tablero para que arranque solo: sudo systemctl enable $SERVICIO"
sudo systemctl start "$SERVICIO"
sleep 3
if systemctl is-active --quiet "$SERVICIO"; then
    if [ "${REABRIR:-}" = "si" ] && { [ -n "${WAYLAND_DISPLAY:-}" ] || [ -n "${DISPLAY:-}" ]; }; then
        bash "$AQUI/pantalla.sh" parar >/dev/null 2>&1 || true
        sleep 2
        setsid nohup bash "$AQUI/pantalla.sh" >/dev/null 2>&1 < /dev/null &
        echo "Listo. La pantalla del tablero se abre en unos segundos con la versión nueva."
    else
        echo "Listo. La pantalla se recarga sola en unos segundos."
    fi
    echo "Si algo salió mal, lo anterior está entero en: $RESPALDO"
    # el nombre lleva la fecha, así que sort -r deja primero los más nuevos
    find "$(dirname "$RAIZ")" -maxdepth 1 -type d -name 'H08_respaldo_*' | sort -r \
        | tail -n +$((RESPALDOS_QUEDAN + 1)) | while IFS= read -r d; do rm -rf -- "$d"; done
else
    echo "El servicio no arrancó:  journalctl -u $SERVICIO -n 50"
    echo "Para volver atrás:  sudo systemctl stop $SERVICIO; rm -rf '$RAIZ'; mv '$RESPALDO' '$RAIZ'; sudo systemctl start $SERVICIO"
    exit 1
fi
