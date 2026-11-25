#!/usr/bin/env bash
# El tablero en Chromium a pantalla completa en la pantalla de la Pi.
#   bash pantalla.sh [parar | instalar | quitar]
# Alt + F4 lo cierra y deja el escritorio; si Chromium se cuelga, lo reabre.
# Usa un perfil propio para no tocar el Chromium de todos los días.

AQUI="$(cd "$(dirname "$0")" && pwd)"
PUERTO="${TABLERO_PUERTO:-8000}"
URL="http://localhost:${PUERTO}/?pantalla=1"
# Vacío es automático: se agranda para que se vea como en 1920x1080, porque en
# un televisor 4K queda todo chiquito. Para más grande, un número: ESCALA="1.25"
ESCALA="${TABLERO_ESCALA:-}"
PERFIL="$HOME/.config/tablero-pantalla"
RUN="${XDG_RUNTIME_DIR:-/tmp}"
PARAR="$RUN/tablero-pantalla.parar"
AUTOSTART="$HOME/.config/autostart/tablero-pantalla.desktop"
MENU="$HOME/.local/share/applications/tablero-pantalla.desktop"
# Bookworm y Trixie usan labwc (Wayland): se arranca por su autostart y por
# XDG a la vez; el flock de abajo evita que se abra dos veces
LABWC="$HOME/.config/labwc/autostart"
# nombre de versiones viejas, para limpiarlo
VIEJO_NOMBRE="kios""co"
VIEJO_AUTOSTART="$HOME/.config/autostart/tablero-$VIEJO_NOMBRE.desktop"

cerrar_todo() {
    touch "$PARAR" "$RUN/tablero-$VIEJO_NOMBRE.parar"
    pkill -f -- "--user-data-dir=$PERFIL" 2>/dev/null || true
    pkill -f -- "--user-data-dir=$HOME/.config/tablero-$VIEJO_NOMBRE" 2>/dev/null || true
}

limpiar_viejo() {
    rm -f "$VIEJO_AUTOSTART"
    [ -f "$LABWC" ] && sed -i "/$VIEJO_NOMBRE\.sh/d" "$LABWC"
    rm -f "$AQUI/$VIEJO_NOMBRE.sh"
}

case "${1:-}" in
    parar)
        cerrar_todo
        echo "Pantalla del tablero cerrada. Se vuelve a abrir con:  bash $AQUI/pantalla.sh"
        exit 0 ;;
    instalar)
        limpiar_viejo
        mkdir -p "$(dirname "$AUTOSTART")" "$(dirname "$MENU")" "$(dirname "$LABWC")"
        for f in "$AUTOSTART" "$MENU"; do
            cat > "$f" <<FIN
[Desktop Entry]
Type=Application
Name=Pantalla del tablero
Comment=El tablero H-08 a pantalla completa (Alt + F4 para salir)
Exec=/bin/bash $AQUI/pantalla.sh
Icon=video-display
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
FIN
        done
        touch "$LABWC"
        sed -i '/pantalla\.sh/d' "$LABWC"
        echo "/bin/bash $AQUI/pantalla.sh &" >> "$LABWC"
        echo "   El tablero se abre solo al encender. En el menú queda “Pantalla del tablero”."
        exit 0 ;;
    quitar)
        limpiar_viejo
        rm -f "$AUTOSTART"
        [ -f "$LABWC" ] && sed -i '/pantalla\.sh/d' "$LABWC"
        cerrar_todo
        echo "Listo: el tablero ya no se abre solo en la pantalla."
        echo "Sigue en el menú como “Pantalla del tablero”, y en el navegador: http://localhost:${PUERTO}/"
        exit 0 ;;
    "") ;;
    *)
        echo "Uso:  bash pantalla.sh [parar | instalar | quitar]"
        exit 1 ;;
esac
rm -f "$PARAR"

# una sola a la vez, que el arranque y una abierta a mano no se pisen
exec 9>"$RUN/tablero-pantalla.lock"
if ! flock -n 9; then
    echo "La pantalla del tablero ya está abierta."
    exit 0
fi

NAV=""
for n in chromium chromium-browser; do
    if command -v "$n" >/dev/null; then NAV="$n"; break; fi
done
if [ -z "$NAV" ]; then
    echo "No está Chromium:  sudo apt install -y chromium"
    exit 1
fi

# wlr-randr en Wayland, si no xrandr
ancho_pantalla() {
    local w=""
    if command -v wlr-randr >/dev/null; then
        w="$(wlr-randr 2>/dev/null | awk '/current/ {split($1, a, "x"); print a[1]; exit}')"
    fi
    if [ -z "$w" ] && command -v xrandr >/dev/null; then
        w="$(xrandr 2>/dev/null | awk '/\*/ {split($1, a, "x"); print a[1]; exit}')"
    fi
    echo "${w:-1920}"
}

# ancho/1920 redondeado a 0,25, mínimo 1
escala() {
    if [ -n "$ESCALA" ]; then echo "$ESCALA"; return; fi
    awk -v w="$(ancho_pantalla)" 'BEGIN { f = int(w / 1920 * 4 + 0.5) / 4; if (f < 1) f = 1; print f }'
}

responde() {
    python3 - "$1" <<'FIN' >/dev/null 2>&1
import sys, urllib.request
urllib.request.urlopen(sys.argv[1], timeout=2).read(1)
FIN
}

# Si se corta la luz, Chromium muestra el cartel de "restaurar páginas" y en
# la pantalla no hay nadie que lo cierre.
limpiar_perfil() {
    local pref="$PERFIL/Default/Preferences"
    if [ -f "$pref" ]; then
        sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"[A-Za-z]*"/"exit_type":"Normal"/' "$pref" || true
    fi
}

while [ ! -e "$PARAR" ]; do
    # al encender el escritorio suele estar antes que el programa: hasta 3 min,
    # después abre igual y la página reintenta sola
    for _ in $(seq 1 180); do
        responde "http://localhost:${PUERTO}/api/estado" && break
        [ -e "$PARAR" ] && exit 0
        sleep 1
    done

    limpiar_perfil
    "$NAV" --kiosk "$URL" --force-device-scale-factor="$(escala)" \
        --user-data-dir="$PERFIL" \
        --noerrdialogs --disable-infobars --no-first-run \
        --disable-session-crashed-bubble --disable-features=Translate,TranslateUI \
        --password-store=basic --check-for-update-interval=31536000 \
        --overscroll-history-navigation=0 --disable-pinch \
        --ozone-platform-hint=auto >/dev/null 2>&1
    salida=$?

    # cerrado a propósito (Alt + F4 o parar): queda el escritorio; con error, se reabre
    [ -e "$PARAR" ] && break
    [ "$salida" -eq 0 ] && break
    sleep 3
done
rm -f "$PARAR"
