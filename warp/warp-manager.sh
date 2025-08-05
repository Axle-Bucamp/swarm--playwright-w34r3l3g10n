#!/usr/bin/env bash
set -e

# Configuration
WARP_INTERFACE="wgcf"
WARP_CONFIG="${WARP_CONFIG:-/etc/wireguard/wgcf.conf}"
WARP_ACCOUNT_FILE="/etc/wireguard/wgcf-account.toml"
LOG_FILE="/var/log/warp/warp.log"
HEALTH_CHECK_INTERVAL=30
MAX_RECONNECT_ATTEMPTS=5

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARP: $1" | tee -a "$LOG_FILE"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt de WARP..."
    
    # Arrêter l'interface WireGuard
    if ip link show "$WARP_INTERFACE" >/dev/null 2>&1; then
        ip link set down "$WARP_INTERFACE" 2>/dev/null || true
        ip link delete "$WARP_INTERFACE" 2>/dev/null || true
    fi
    
    # Nettoyer les règles iptables
    cleanup_iptables
    
    exit 0
}

# Gestionnaire de signaux
trap cleanup SIGTERM SIGINT

# Configuration des règles iptables pour le proxy
setup_iptables() {
    log "Configuration des règles iptables..."
    
    # Permettre le trafic sur l'interface WARP
    iptables -A INPUT -i "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -A OUTPUT -o "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    
    # Permettre le forwarding pour les proxies
    iptables -A FORWARD -i "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -A FORWARD -o "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    
    # NAT pour le trafic sortant
    iptables -t nat -A POSTROUTING -o "$WARP_INTERFACE" -j MASQUERADE 2>/dev/null || true
    
    # Permettre les connexions établies
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
}

# Nettoyage des règles iptables
cleanup_iptables() {
    log "Nettoyage des règles iptables..."
    
    # Supprimer les règles spécifiques à WARP (ignorer les erreurs)
    iptables -D INPUT -i "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -D OUTPUT -o "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -D FORWARD -i "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -D FORWARD -o "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -t nat -D POSTROUTING -o "$WARP_INTERFACE" -j MASQUERADE 2>/dev/null || true
}

# Génération ou récupération de la configuration WARP
setup_warp_config() {
    log "Configuration de WARP..."
    
    # Vérifier si la configuration existe déjà
    if [ -f "$WARP_CONFIG" ] && [ -f "$WARP_ACCOUNT_FILE" ]; then
        log "Configuration WARP existante trouvée"
        return 0
    fi
    
    # Créer le répertoire de configuration
    mkdir -p "$(dirname "$WARP_CONFIG")" "$(dirname "$WARP_ACCOUNT_FILE")"
    
    # Générer une nouvelle configuration
    log "Génération d'une nouvelle configuration WARP..."
    
    cd "$(dirname "$WARP_CONFIG")"
    
    # Enregistrer un nouveau compte WARP
    if ! wgcf register; then
        log "ERREUR: Impossible d'enregistrer un compte WARP"
        return 1
    fi
    
    # Générer la configuration WireGuard
    if ! wgcf generate; then
        log "ERREUR: Impossible de générer la configuration WARP"
        return 1
    fi
    
    # Renommer le fichier de configuration
    if [ -f "wgcf-profile.conf" ]; then
        mv "wgcf-profile.conf" "$WARP_CONFIG"
    else
        log "ERREUR: Fichier de configuration WARP non trouvé"
        return 1
    fi
    
    log "Configuration WARP générée avec succès"
    return 0
}

# Démarrage de l'interface WARP
start_warp_interface() {
    log "Démarrage de l'interface WARP..."
    
    # Supprimer l'interface existante si elle existe
    if ip link show "$WARP_INTERFACE" >/dev/null 2>&1; then
        ip link set down "$WARP_INTERFACE" 2>/dev/null || true
        ip link delete "$WARP_INTERFACE" 2>/dev/null || true
    fi
    
    # Créer l'interface WireGuard
    ip link add dev "$WARP_INTERFACE" type wireguard
    
    # Configurer l'interface avec wg
    wg setconf "$WARP_INTERFACE" "$WARP_CONFIG"
    
    # Extraire l'adresse IP de la configuration
    local warp_ip
    warp_ip=$(grep "^Address" "$WARP_CONFIG" | cut -d'=' -f2 | tr -d ' ' | cut -d',' -f1)
    log "base config ip: $warp_ip"

    if [ -z "$warp_ip" ]; then
        log "ERREUR: Impossible d'extraire l'adresse IP WARP"
        return 1
    fi
    
    # Configurer l'adresse IP
    ip address add "$warp_ip" dev "$WARP_INTERFACE"
    
    # Activer l'interface
    ip link set up dev "$WARP_INTERFACE"
    
    # Configurer les routes
    setup_warp_routes
    
    log "Interface WARP démarrée avec l'IP: $warp_ip"
    return 0
}

# Configuration des routes WARP
setup_warp_routes() {
    log "Configuration des routes WARP..."
    
    # Créer une table de routage personnalisée pour WARP
    local warp_table=51820
    
    # Ajouter la route par défaut via WARP dans la table personnalisée
    ip route add default dev "$WARP_INTERFACE" table "$warp_table" 2>/dev/null || true
    
    # Extraire l'adresse IP WARP
    local warp_ip
    warp_ip=$(ip addr show "$WARP_INTERFACE" | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
    
    if [ -n "$warp_ip" ]; then
        # Règle pour utiliser la table WARP pour le trafic provenant de l'IP WARP
        ip rule add from "$warp_ip" lookup "$warp_table" 2>/dev/null || true
    fi
    
    log "Routes WARP configurées"
}

# Test de connectivité WARP
test_warp_connectivity() {
    local max_attempts=10
    local attempt=1

    log "Test de connectivité WARP via l'interface $WARP_INTERFACE..."

    while [ $attempt -le $max_attempts ]; do
        # Tester la connectivité via WARP
        local warp_exit_ip
        warp_exit_ip=$(timeout 10 curl --interface "$WARP_INTERFACE" -4 -s http://httpbin.org/ip)

        if [ -n "$warp_exit_ip" ]; then
            log "WARP connecté avec succès. IP de sortie: $warp_exit_ip"
            return 0
        fi

        log "Tentative de connexion WARP $attempt/$max_attempts échouée"
        sleep 5
        attempt=$((attempt + 1))
    done

    log "ERREUR: Impossible d'établir la connectivité WARP"
    return 1
}

# Démarrage des proxies
start_proxies() {
    if [ "${ENABLE_SOCKS_PROXY:-true}" = "true" ]; then
        start_socks_proxy &
    fi
    
    if [ "${ENABLE_HTTP_PROXY:-true}" = "true" ]; then
        start_http_proxy &
    fi
}

# Proxy SOCKS5
start_socks_proxy() {
    log "Démarrage du proxy SOCKS5 sur le port ${SOCKS_PORT:-1080}..."
    
    # Utiliser socat pour créer un proxy SOCKS5 simple
    while true; do
        socat TCP-LISTEN:"${SOCKS_PORT:-1080}",reuseaddr,fork \
              SOCKS4A:127.0.0.1:0.0.0.0:0,socksport=1080 2>/dev/null || true
        log "Proxy SOCKS5 redémarré"
        sleep 5
    done
}

# Proxy HTTP
start_http_proxy() {
    log "Démarrage du proxy HTTP sur le port ${HTTP_PORT:-3128}..."
    
    # Proxy HTTP simple avec socat
    while true; do
        socat TCP-LISTEN:"${HTTP_PORT:-3128}",reuseaddr,fork \
              TCP:127.0.0.1:3128 2>/dev/null || true
        log "Proxy HTTP redémarré"
        sleep 5
    done
}

# Monitoring de la santé WARP
monitor_warp_health() {
    local failure_count=0
    local max_failures=3
    
    while true; do
        sleep "$HEALTH_CHECK_INTERVAL"
        
        # Vérifier l'état de l'interface
        if ! ip link show "$WARP_INTERFACE" >/dev/null 2>&1; then
            log "ERREUR: Interface WARP disparue"
            failure_count=$((failure_count + 1))
        elif ! timeout 10 curl --interface "$WARP_INTERFACE" -s http://httpbin.org/ip >/dev/null 2>&1; then
            log "ATTENTION: Test de connectivité WARP échoué"
            failure_count=$((failure_count + 1))
        else
            failure_count=0
            log "WARP fonctionne correctement"
        fi
        
        # Redémarrer si trop d'échecs
        if [ $failure_count -ge $max_failures ]; then
            log "ERREUR: Trop d'échecs WARP, tentative de redémarrage..."
            restart_warp
            failure_count=0
        fi
    done
}

# Redémarrage de WARP
restart_warp() {
    log "Redémarrage de WARP..."
    
    # Arrêter l'interface
    if ip link show "$WARP_INTERFACE" >/dev/null 2>&1; then
        ip link set down "$WARP_INTERFACE" 2>/dev/null || true
        ip link delete "$WARP_INTERFACE" 2>/dev/null || true
    fi
    
    # Attendre un peu
    sleep 5
    
    # Redémarrer
    if start_warp_interface && test_warp_connectivity; then
        log "WARP redémarré avec succès"
    else
        log "ERREUR: Échec du redémarrage WARP"
    fi
}

# Fonction principale
main() {
    log "Démarrage du gestionnaire WARP pour Swarm Playwright W34R3L3G10N"
    log "Instance: ${HOSTNAME:-$(hostname)}"
    
    # Créer les répertoires de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Configuration initiale
    if ! setup_warp_config; then
        log "ERREUR: Échec de la configuration WARP"
        exit 1
    fi
    
    # Démarrer l'interface WARP
    if ! start_warp_interface; then
        log "ERREUR: Échec du démarrage de l'interface WARP"
        exit 1
    fi
    
    # Configurer les règles iptables
    setup_iptables
    
    # Tester la connectivité
    if ! test_warp_connectivity; then
        log "ERREUR: Échec du test de connectivité WARP"
        exit 1
    fi
    
    # Démarrer les proxies
    start_proxies
    
    # Démarrer le monitoring
    monitor_warp_health &
    MONITOR_PID=$!
    
    log "WARP configuré et opérationnel"
    
    # Attendre les signaux
    wait
}

# Point d'entrée
main "$@"

