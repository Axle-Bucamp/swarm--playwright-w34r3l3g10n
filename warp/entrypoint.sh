#!/bin/bash
set -e

# Configuration
LOG_FILE="/var/log/warp/entrypoint.log"
WARP_MANAGER="/opt/warp/warp-manager.sh"

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARP-ENTRYPOINT: $1" | tee -a "$LOG_FILE"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt du conteneur WARP..."
    
    # Arrêter le gestionnaire WARP
    if [ -n "$WARP_MANAGER_PID" ]; then
        kill -TERM "$WARP_MANAGER_PID" 2>/dev/null || true
        wait "$WARP_MANAGER_PID" 2>/dev/null || true
    fi
    
    exit 0
}

# Gestionnaire de signaux
trap cleanup SIGTERM SIGINT

# Vérification des privilèges
check_privileges() {
    if [ "$(id -u)" != "0" ]; then
        log "ERREUR: Ce conteneur doit être exécuté avec des privilèges root pour configurer WireGuard"
        exit 1
    fi
    
    # Vérifier les capacités nécessaires
    if ! ip link add test type dummy 2>/dev/null; then
        log "ERREUR: Capacité NET_ADMIN requise pour créer des interfaces réseau"
        exit 1
    else
        ip link delete test 2>/dev/null || true
    fi
    
    log "Privilèges réseau vérifiés"
}

# Configuration du système
setup_system() {
    log "Configuration du système..."

    mkdir -p /var/log/warp /etc/wireguard /opt/warp

    # Persist only, let Docker set it
    echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf 2>/dev/null || true
    echo 'net.ipv6.conf.all.forwarding = 1' >> /etc/sysctl.conf 2>/dev/null || true

    modprobe wireguard 2>/dev/null || log "Module WireGuard déjà chargé ou intégré au noyau"

    log "Système configuré"
}

# Vérification de la connectivité Internet
check_internet_connectivity() {
    log "Vérification de la connectivité Internet..."
    
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if timeout 10 curl -s http://httpbin.org/ip >/dev/null 2>&1; then
            log "Connectivité Internet confirmée"
            return 0
        fi
        
        log "Tentative de connectivité $attempt/$max_attempts échouée"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log "ATTENTION: Connectivité Internet non confirmée, mais continuation..."
    return 0  # Ne pas échouer, WARP pourrait résoudre le problème
}

# Configuration des variables d'environnement
setup_environment() {
    log "Configuration de l'environnement..."
    
    # Variables par défaut
    export WARP_INTERFACE="${WARP_INTERFACE:-wgcf}"
    export WARP_CONFIG="${WARP_CONFIG:-/etc/wireguard/wgcf.conf}"
    export ENABLE_SOCKS_PROXY="${ENABLE_SOCKS_PROXY:-true}"
    export ENABLE_HTTP_PROXY="${ENABLE_HTTP_PROXY:-true}"
    export SOCKS_PORT="${SOCKS_PORT:-1080}"
    export HTTP_PORT="${HTTP_PORT:-3128}"
    
    log "Variables d'environnement configurées:"
    log "  WARP_INTERFACE=$WARP_INTERFACE"
    log "  WARP_CONFIG=$WARP_CONFIG"
    log "  ENABLE_SOCKS_PROXY=$ENABLE_SOCKS_PROXY"
    log "  ENABLE_HTTP_PROXY=$ENABLE_HTTP_PROXY"
    log "  SOCKS_PORT=$SOCKS_PORT"
    log "  HTTP_PORT=$HTTP_PORT"
}

# Affichage des informations de démarrage
show_startup_info() {
    log "=== Swarm Playwright W34R3L3G10N - Cloudflare WARP ==="
    log "Instance: ${HOSTNAME:-$(hostname)}"
    log "Version: 1.0.0"
    log "Timestamp: $(date)"
    log "PID: $$"
    log "========================================================="
}

# Fonction de monitoring de santé
health_monitor() {
    local check_interval=60
    
    while true; do
        sleep "$check_interval"
        
        # Vérifier que le gestionnaire WARP fonctionne
        if [ -n "$WARP_MANAGER_PID" ] && kill -0 "$WARP_MANAGER_PID" 2>/dev/null; then
            log "Gestionnaire WARP opérationnel"
        else
            log "ERREUR: Gestionnaire WARP arrêté de manière inattendue"
            break
        fi
        
        # Vérifier les proxies si activés
        if [ "$ENABLE_SOCKS_PROXY" = "true" ]; then
            if ! netstat -ln | grep ":$SOCKS_PORT " >/dev/null 2>&1; then
                log "ATTENTION: Proxy SOCKS5 non accessible sur le port $SOCKS_PORT"
            fi
        fi
        
        if [ "$ENABLE_HTTP_PROXY" = "true" ]; then
            if ! netstat -ln | grep ":$HTTP_PORT " >/dev/null 2>&1; then
                log "ATTENTION: Proxy HTTP non accessible sur le port $HTTP_PORT"
            fi
        fi
    done
}

# Fonction principale
main() {
    # Créer le répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Afficher les informations de démarrage
    show_startup_info
    
    # Vérifications préliminaires
    check_privileges
    setup_system
    setup_environment
    check_internet_connectivity
    
    # Vérifier que le gestionnaire WARP existe
    if [ ! -f "$WARP_MANAGER" ]; then
        log "ERREUR: Gestionnaire WARP non trouvé: $WARP_MANAGER"
        exit 1
    fi
    
    # Rendre le gestionnaire exécutable
    chmod +x "$WARP_MANAGER"
    
    # Démarrer le gestionnaire WARP
    log "Démarrage du gestionnaire WARP..."
    "$WARP_MANAGER" -y &
    WARP_MANAGER_PID=$!
    
    # Attendre un peu pour vérifier que le démarrage s'est bien passé
    sleep 10
    
    if ! kill -0 "$WARP_MANAGER_PID" 2>/dev/null; then
        log "ERREUR: Le gestionnaire WARP s'est arrêté de manière inattendue"
        exit 1
    fi
    
    log "Gestionnaire WARP démarré avec le PID: $WARP_MANAGER_PID"
    
    # Démarrer le monitoring de santé
    health_monitor &
    HEALTH_MONITOR_PID=$!
    
    log "WARP est opérationnel et prêt à recevoir du trafic"
    
    # Attendre que le gestionnaire WARP se termine
    wait "$WARP_MANAGER_PID"
    
    # Nettoyer le monitoring
    [ -n "$HEALTH_MONITOR_PID" ] && kill "$HEALTH_MONITOR_PID" 2>/dev/null || true
    
    log "Gestionnaire WARP arrêté"
}

# Point d'entrée
main "$@"

