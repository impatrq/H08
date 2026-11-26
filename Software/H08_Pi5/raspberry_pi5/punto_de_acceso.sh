#!/usr/bin/env bash
# La Pi levanta su propia red wifi (sin internet), por si en la muestra no hay
# wifi o está saturado. Va con nmcli, sin hostapd.
#   sudo bash punto_de_acceso.sh encender|permanente|preparar|apagar|revisar
# Ojo: si estás conectado por SSH por wifi, se corta. El wifi de la Pi aguanta
# unos 8 celulares. RED, CLAVE e IP las lee también el servidor para el QR.
set -e

RED="Tablero-H08"
CLAVE="sikorsky55"          # WPA exige 8 caracteres como mínimo
IP="10.55.0.1"
CONEXION="tablero-ap"
IFAZ="wlan0"
PUERTO="${TABLERO_PUERTO:-8000}"
PUERTO_WEB="${TABLERO_PUERTO_WEB:-80}"     # el corto: la dirección queda sin número
LIMITE_CELULARES=8
# vacío: al encender elige el menos ocupado entre 1, 6 y 11. Fijo: CANAL_FIJO="6"
CANAL_FIJO=""
# el dnsmasq de NetworkManager lee esta carpeta en las redes compartidas
# (las variables H08_* son para las pruebas automáticas)
DIR_DNSMASQ="${H08_DNSMASQ_DIR:-/etc/NetworkManager/dnsmasq-shared.d}"
PORTAL="$DIR_DNSMASQ/h08-portal.conf"
VIGILANTE="tablero-h08-red"
DIR_SYSTEMD="${H08_SYSTEMD_DIR:-/etc/systemd/system}"
CADA="${H08_VIGILAR_CADA:-20}"
# /run se borra en cada encendido, ahí va la marca de "ya se encendió"
DIR_RUN="${H08_RUN_DIR:-/run}"
# celulares que el profesor desconectó desde la página de mando
BLOQUEADOS="${H08_BLOQUEADOS:-$AQUI/bloqueados_red.txt}"
PASO="${H08_VIGILAR_PASO:-2}"
MARCA_ENCENDIDO="$DIR_RUN/$VIGILANTE.encendido"
AQUI="$(cd "$(dirname "$0")" && pwd)"

command -v nmcli >/dev/null || {
    echo "No se encontró NetworkManager (nmcli). Usar Raspberry Pi OS Bookworm o posterior."
    exit 1
}

con_sudo() {
    if [ "$(id -u)" != "0" ]; then
        echo "Esto cambia la red: correrlo con sudo delante:"
        echo "    sudo bash $0 $1"
        exit 1
    fi
}

hay_dnsmasq() {
    [ -x "${H08_DNSMASQ:-/usr/sbin/dnsmasq}" ] || command -v dnsmasq >/dev/null
}

placa_presente() {
    nmcli -t -f DEVICE,TYPE device status 2>/dev/null | grep -qx "$IFAZ:wifi"
}

crear() {
    if [ "${#CLAVE}" -lt 8 ]; then
        echo "La CLAVE de este archivo tiene ${#CLAVE} caracteres: WPA pide 8 como mínimo."
        exit 1
    fi
    # desde Bookworm la placa viene bloqueada hasta que se elige el país
    if command -v raspi-config >/dev/null; then
        if [ -z "$(raspi-config nonint get_wifi_country 2>/dev/null)" ]; then
            raspi-config nonint do_wifi_country AR || true
        fi
    fi
    if command -v rfkill >/dev/null; then
        rfkill unblock wifi || true
    fi
    if ! placa_presente; then
        echo "NetworkManager no ve la placa wifi ($IFAZ)."
        echo "  Revisar con:  nmcli device status   y   rfkill list"
        exit 1
    fi
    if ! hay_dnsmasq; then
        echo "Falta dnsmasq: sin él los celulares se conectan pero no reciben dirección."
        echo "  Instalarlo (hace falta internet):  sudo apt install -y dnsmasq-base"
        exit 1
    fi
    if ! nmcli -t -f NAME connection show | grep -qx "$CONEXION"; then
        nmcli connection add type wifi ifname "$IFAZ" con-name "$CONEXION" \
              autoconnect no ssid "$RED" >/dev/null
    fi
    # Siempre, no solo al crearla: así la red guardada queda igual a este
    # archivo, que es lo que muestran el QR y el cartel.
    nmcli connection modify "$CONEXION" \
          802-11-wireless.ssid "$RED" \
          802-11-wireless.mode ap 802-11-wireless.band bg \
          802-11-wireless.channel "${CANAL_FIJO:-6}" 802-11-wireless.powersave 2 \
          ipv4.method shared ipv4.addresses "$IP/24" ipv6.method disabled \
          wifi-sec.key-mgmt wpa-psk wifi-sec.proto rsn \
          wifi-sec.pairwise ccmp wifi-sec.group ccmp wifi-sec.psk "$CLAVE"
    # cualquier nombre lleva a la Pi; así el celular abre la página solo, como en un aeropuerto
    mkdir -p "$DIR_DNSMASQ"
    printf '# Tablero H-08: cualquier nombre lleva a la Raspberry (punto_de_acceso.sh)\naddress=/#/%s\n' "$IP" > "$PORTAL"
}

# reintentos sin límite y prioridad 100, por encima de cualquier otro wifi guardado
al_encender() {
    nmcli connection modify "$CONEXION" autoconnect yes \
          connection.autoconnect-priority 100 connection.autoconnect-retries 0
}

instalar_vigilante() {
    mkdir -p "$DIR_SYSTEMD"
    cat > "$DIR_SYSTEMD/$VIGILANTE.service" <<FIN
[Unit]
Description=Tablero H-08: mantiene levantada la red wifi propia ($RED)
Wants=NetworkManager.service
After=NetworkManager.service
StartLimitIntervalSec=0

[Service]
ExecStart=/bin/bash $AQUI/punto_de_acceso.sh vigilar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
FIN
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable "$VIGILANTE" >/dev/null 2>&1 \
        || echo "No se pudo habilitar el servicio $VIGILANTE: la red no se va a volver a levantar sola."
}

red_pedida() {
    [ "$(nmcli -g connection.autoconnect connection show "$CONEXION" 2>/dev/null)" = "yes" ]
}

red_levantada() {
    nmcli -t -f NAME connection show --active 2>/dev/null | grep -qx "$CONEXION"
}

# Cada red vecina pesa su señal en los canales que pisa (en 2,4 GHz un canal
# se superpone con los 4 de cada lado). Si empatan gana el 6.
canal_libre() {
    local lista c carga mejor=6 menor=-1
    lista="$(nmcli -t -f CHAN,SIGNAL device wifi list --rescan yes ifname "$IFAZ" 2>/dev/null)" || return 1
    [ -n "$lista" ] || { echo 6; return 0; }
    for c in 6 1 11; do
        carga="$(printf '%s\n' "$lista" | awk -F: -v c="$c" '$1>=1 && $1<=14 { d=$1-c; if (d<0) d=-d; if (d<=4) s+=$2*(5-d)/5 } END { print int(s) }')"
        if [ "$menor" -lt 0 ] || [ "$carga" -lt "$menor" ]; then menor=$carga; mejor=$c; fi
    done
    echo "$mejor"
}

# para escanear la placa tiene que estar libre: se baja la red un momento
# (recién prendida la Pi todavía no hay celulares)
elegir_canal() {
    local canal
    if [ -n "$CANAL_FIJO" ]; then
        nmcli connection modify "$CONEXION" 802-11-wireless.channel "$CANAL_FIJO" >/dev/null 2>&1 || true
        return 0
    fi
    if red_levantada; then nmcli connection down "$CONEXION" >/dev/null 2>&1 || true; fi
    sleep "${H08_ESPERA_ESCANEO:-3}"
    canal="$(canal_libre)" || canal=""
    if [ -n "$canal" ]; then
        nmcli connection modify "$CONEXION" 802-11-wireless.channel "$canal" >/dev/null 2>&1 || true
        echo "Al encender: canal $canal, el que tiene menos wifi alrededor."
    fi
}

# Una vez por encendido: la red vuelve aunque se haya corrido 'apagar'. Si el
# servicio se reinicia en el mismo encendido, la marca en /run evita que se
# repita y se respeta el 'apagar'.
arrancar() {
    [ -e "$MARCA_ENCENDIDO" ] && return 0
    mkdir -p "$DIR_RUN" 2>/dev/null || true
    : > "$MARCA_ENCENDIDO" 2>/dev/null || true
    # los que el profesor desconectó pueden volver después de reiniciar
    if [ -s "$BLOQUEADOS" ]; then : > "$BLOQUEADOS"; echo "Al encender: se borró la lista de desconectados."; fi
    # si la placa todavía no apareció, sigue igual
    ( crear ) >/dev/null 2>&1 || true
    if ! nmcli -t -f NAME connection show 2>/dev/null | grep -qx "$CONEXION"; then
        echo "Al encender: la red $RED no está creada. Para crearla:  sudo bash $AQUI/punto_de_acceso.sh permanente"
        return 0
    fi
    al_encender
    elegir_canal
    if red_levantada; then
        echo "Al encender: la red $RED ya estaba levantada."
    elif nmcli connection up "$CONEXION" >/dev/null 2>&1; then
        echo "Al encender: se levantó la red $RED."
    else
        echo "Al encender: la red $RED todavía no se pudo levantar; se reintenta cada ${CADA}s."
    fi
}

# Con la clave guardada el celular desconectado vuelve enseguida, por eso se
# mira cada PASO segundos y no cada CADA.
echar_bloqueados() {
    [ -s "$BLOQUEADOS" ] || return 0
    local m
    for m in $(iw dev "$IFAZ" station dump 2>/dev/null | awk '/^Station/ {print tolower($2)}'); do
        if grep -qi "^$m" "$BLOQUEADOS"; then
            iw dev "$IFAZ" station del "$m" >/dev/null 2>&1 \
                && echo "Desconectado (lo desconectó el profesor): $m"
        fi
    done
}

# avisa solo cuando cambia algo, para no llenar el registro
vigilar() {
    local fallando=no pasado=0
    while true; do
        sleep "$PASO"
        echar_bloqueados
        pasado=$((pasado + PASO))
        if [ "$pasado" -lt "$CADA" ]; then
            [ -n "${H08_VIGILAR_UNA_VEZ:-}" ] && return 0
            continue
        fi
        pasado=0
        if red_pedida && ! red_levantada; then
            if nmcli connection up "$CONEXION" >/dev/null 2>&1; then
                echo "La red $RED no estaba levantada: se levantó de nuevo."
                fallando=no
            elif [ "$fallando" = "no" ]; then
                echo "La red $RED no está levantada y no se pudo levantar; se reintenta cada ${CADA}s."
                echo "  Para ver qué falla:  sudo bash $AQUI/punto_de_acceso.sh revisar"
                fallando=si
            fi
        fi
        [ -n "${H08_VIGILAR_UNA_VEZ:-}" ] && return 0
    done
}

levantar() {
    local salida
    if ! salida="$(nmcli connection up "$CONEXION" 2>&1)"; then
        echo "$salida"
        echo
        echo "No se pudo levantar la red $RED. Lo más común:"
        echo "  - el país del wifi sin elegir:  sudo raspi-config nonint do_wifi_country AR  (y reiniciar)"
        echo "  - la placa bloqueada:           sudo rfkill unblock wifi"
        echo "  - el detalle del error:         journalctl -u NetworkManager -n 40"
        echo "Para revisar todo junto:  sudo bash $0 revisar"
        exit 1
    fi
}

contesta() {
    (exec 3<>"/dev/tcp/$1/$2") 2>/dev/null
}

direccion() {
    if contesta 127.0.0.1 "$PUERTO_WEB"; then
        [ "$PUERTO_WEB" = "80" ] && echo "http://$IP/" || echo "http://$IP:$PUERTO_WEB/"
    else
        echo "http://$IP:$PUERTO/"
    fi
}

# revisar: en el orden en que se suele romper
PROBLEMAS=0
bien() { printf '  [ ok ] %s\n' "$1"; }
mal()  { printf '  [MAL ] %s\n         -> %s\n' "$1" "$2"; PROBLEMAS=$((PROBLEMAS + 1)); }
info() { printf '         %s\n' "$1"; }

revisar() {
    echo
    echo "  RED WIFI PROPIA ($RED)"
    echo

    if systemctl is-active --quiet NetworkManager 2>/dev/null; then
        bien "NetworkManager andando"
    else
        mal "NetworkManager no está andando" "sudo systemctl restart NetworkManager"
        echo
        echo "  Sin NetworkManager no hay red: arreglar eso primero y volver a revisar."
        echo
        return 1
    fi

    if placa_presente; then
        bien "Placa wifi $IFAZ presente"
    else
        mal "NetworkManager no ve la placa wifi $IFAZ" "nmcli device status   y   rfkill list"
    fi

    if command -v rfkill >/dev/null; then
        if rfkill list wifi 2>/dev/null | grep -q "blocked: yes"; then
            mal "La placa wifi está bloqueada" "sudo rfkill unblock wifi"
        else
            bien "La placa wifi no está bloqueada"
        fi
    fi

    local pais=""
    if command -v raspi-config >/dev/null; then
        pais="$(raspi-config nonint get_wifi_country 2>/dev/null || true)"
    fi
    if [ -n "$pais" ]; then
        bien "País del wifi: $pais"
    elif command -v raspi-config >/dev/null; then
        mal "País del wifi sin elegir (la placa queda apagada)" \
            "sudo raspi-config nonint do_wifi_country AR   y reiniciar"
    fi

    if hay_dnsmasq; then
        bien "dnsmasq instalado (reparte las direcciones)"
    else
        mal "Falta dnsmasq: los celulares no reciben dirección" "sudo apt install -y dnsmasq-base"
    fi

    if ! nmcli -t -f NAME connection show 2>/dev/null | grep -qx "$CONEXION"; then
        mal "La red $RED no está creada" "sudo bash $0 preparar   (o encender)"
    else
        bien "La red $RED está creada"
        local ssid auto clave
        ssid="$(nmcli -g 802-11-wireless.ssid connection show "$CONEXION" 2>/dev/null || true)"
        if [ "$ssid" = "$RED" ]; then
            bien "Nombre de la red igual a este archivo"
        else
            mal "La red guardada se llama “$ssid” y este archivo dice “$RED”" "sudo bash $0 encender"
        fi
        if [ "$(id -u)" = "0" ]; then
            clave="$(nmcli -s -g 802-11-wireless-security.psk connection show "$CONEXION" 2>/dev/null || true)"
            if [ "$clave" = "$CLAVE" ]; then
                bien "Clave igual a este archivo (la del QR)"
            else
                mal "La clave guardada no es la de este archivo: el QR no va a andar" "sudo bash $0 encender"
            fi
        else
            info "(para comparar la clave con la del QR, correr con sudo)"
        fi
        auto="$(nmcli -g connection.autoconnect connection show "$CONEXION" 2>/dev/null || true)"
        if [ "$auto" = "yes" ]; then
            bien "Se levanta sola al encender"
            info "Canal: $(nmcli -g 802-11-wireless.channel connection show "$CONEXION" 2>/dev/null) (al encender elige el menos ocupado)"
            if [ "$(nmcli -g 802-11-wireless.powersave connection show "$CONEXION" 2>/dev/null)" = "2" ]; then
                bien "Sin ahorro de energía en el wifi (menos demoras y cortes)"
            else
                mal "El wifi tiene el ahorro de energía prendido (demoras y cortes)" "sudo bash $0 preparar"
            fi
        else
            info "Apagada a propósito: vuelve sola al reiniciar la Pi (o ya: sudo bash $0 permanente)"
        fi
        if [ "$auto" = "yes" ]; then
            if [ "$(nmcli -g connection.autoconnect-retries connection show "$CONEXION" 2>/dev/null)" = "0" ]; then
                bien "Si falla al encender, la reintenta sin límite"
            else
                mal "Si falla al encender, se rinde y puede quedarse en otro wifi" "sudo bash $0 preparar"
            fi
            if systemctl is-active --quiet "$VIGILANTE" 2>/dev/null; then
                bien "Vigilada: si se cae, se vuelve a levantar sola ($VIGILANTE)"
            elif [ -f "$DIR_SYSTEMD/$VIGILANTE.service" ]; then
                mal "El servicio que la vuelve a levantar ($VIGILANTE) no está andando" \
                    "sudo systemctl enable --now $VIGILANTE"
            else
                mal "Falta el servicio que la vuelve a levantar si se cae ($VIGILANTE)" \
                    "sudo bash $0 preparar   y reiniciar"
            fi
        fi
    fi

    if nmcli -t -f NAME connection show --active 2>/dev/null | grep -qx "$CONEXION"; then
        bien "Red levantada ahora"
        if ip -4 -o addr show dev "$IFAZ" 2>/dev/null | grep -q " $IP/"; then
            bien "La Raspberry tiene la dirección $IP"
        else
            mal "La red está levantada pero $IFAZ no tiene $IP" "sudo bash $0 apagar   y después   encender"
        fi
        local n=0
        if command -v iw >/dev/null; then
            n="$(iw dev "$IFAZ" station dump 2>/dev/null | grep -c '^Station' || true)"
            if [ "$n" -ge "$LIMITE_CELULARES" ]; then
                mal "Celulares conectados: $n (el wifi de la Raspberry acepta unos $LIMITE_CELULARES)" \
                    "los que no entran tienen que esperar; para más hace falta un router aparte"
            else
                bien "Celulares conectados: $n (acepta unos $LIMITE_CELULARES)"
            fi
        else
            info "(sin el comando iw no se pueden contar los celulares: sudo apt install -y iw)"
        fi
    else
        mal "La red no está levantada ahora: los celulares no la van a ver en la lista" "sudo bash $0 encender"
        # hay una sola placa: si está en otro wifi no transmite la propia
        local otra
        otra="$(nmcli -t -f DEVICE,CONNECTION device status 2>/dev/null | awk -F: -v i="$IFAZ" '$1==i {print $2}')"
        if [ -n "$otra" ] && [ "$otra" != "--" ] && [ "$otra" != "$CONEXION" ]; then
            info "La placa $IFAZ está conectada a “$otra”: mientras tanto no transmite $RED."
            info "(encender la saca de esa red; para volver a ella: sudo bash $0 apagar)"
        fi
    fi

    if contesta 127.0.0.1 "$PUERTO"; then
        bien "La página del tablero contesta en el puerto $PUERTO"
        if contesta 127.0.0.1 "$PUERTO_WEB"; then
            bien "También en el puerto $PUERTO_WEB: se entra escribiendo $IP"
        else
            mal "No contesta en el puerto $PUERTO_WEB: hay que escribir $IP:$PUERTO y la página no se abre sola" \
                "bash instalar.sh   (sin sudo; le da el permiso al servicio) y reiniciar"
        fi
        if contesta "$IP" "$PUERTO"; then
            bien "Y contesta desde la red: $(direccion)"
        else
            info "(desde $IP no contesta: normal si la red no está levantada)"
        fi
    else
        mal "La página del tablero no contesta en el puerto $PUERTO" \
            "sudo systemctl restart tablero-h08   y   journalctl -u tablero-h08 -n 50"
    fi

    if grep -qs "address=/#/$IP" "$PORTAL"; then
        bien "La página se abre sola al conectarse (cualquier nombre lleva a $IP)"
    else
        mal "Falta lo que hace que la página se abra sola al conectarse" \
            "sudo bash $0 encender"
    fi

    echo
    if [ "$PROBLEMAS" -eq 0 ]; then
        echo "  Todo bien. Los celulares entran con el QR de la red o en $(direccion)"
    else
        echo "  Hay $PROBLEMAS cosa(s) para arreglar: seguir las flechas de arriba, en orden."
    fi
    echo
    [ "$PROBLEMAS" -eq 0 ]
}

case "${1:-estado}" in
encender)
    con_sudo encender
    crear
    levantar
    echo
    echo "  Red ...... $RED"
    echo "  Clave .... $CLAVE"
    echo "  Página ... $(direccion)"
    echo "  Cartel ... http://$IP:$PUERTO/cartel   (para imprimir y pegar)"
    ;;
permanente)
    con_sudo permanente
    crear
    al_encender
    instalar_vigilante
    levantar
    systemctl start "$VIGILANTE" >/dev/null 2>&1 || true
    echo "Listo: al encender, la Raspberry levanta $RED sola, y si se cae la vuelve a levantar."
    ;;
preparar)
    con_sudo preparar
    crear
    al_encender
    # se habilita sin arrancarlo: arrancarlo ahora cortaría un SSH por wifi
    instalar_vigilante
    echo "Listo: desde el próximo encendido la Raspberry levanta $RED sola, y si se cae la vuelve a levantar."
    ;;
apagar)
    con_sudo apagar
    nmcli connection modify "$CONEXION" autoconnect no 2>/dev/null || true
    nmcli connection down "$CONEXION" 2>/dev/null || true
    echo "Punto de acceso apagado. La Raspberry vuelve a su red de siempre."
    echo "(Dura hasta que se reinicie la Pi: al encender, vuelve sola la red $RED."
    echo " Para volver a la red propia ahora:  sudo bash $0 permanente)"
    ;;
vigilar)
    con_sudo vigilar
    arrancar
    vigilar
    ;;
revisar)
    revisar
    ;;
estado)
    if nmcli -t -f NAME connection show --active | grep -qx "$CONEXION"; then
        echo "Punto de acceso LEVANTADO: red $RED, $(direccion)"
    else
        echo "Punto de acceso apagado."
    fi
    ;;
*)
    echo "Uso: sudo bash $0 encender|permanente|preparar|apagar|revisar|vigilar   ·   bash $0 estado"
    exit 1
    ;;
esac
