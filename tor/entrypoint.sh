#!/bin/bash
set -e

# Configuration
TOR_CONFIG="/etc/tor/torrc"
TOR_DATA_DIR="/var/lib/tor"
TOR_LOG_FILE="/var/log/tor/tor.log"
CIRCUIT_ROTATION_INTERVAL=${CIRCUIT_ROTATION_INTERVAL:-300}  # 5 minutes par défaut

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$TOR_LOG_FILE"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt de Tor..."
    if [ -n "$TOR_PID" ]; then
        kill -TERM "$TOR_PID" 2>/dev/null || true
        wait "$TOR_PID" 2>/dev/null || true
    fi
    exit 0
}

# Gestionnaire de signaux
trap cleanup SIGTERM SIGINT

# Vérifier les permissions
if [ "$(id -u)" = "0" ]; then
    log "ERREUR: Ne pas exécuter Tor en tant que root"
    exit 1
fi

# Créer les répertoires nécessaires
mkdir -p "$TOR_DATA_DIR" "$(dirname "$TOR_LOG_FILE")"

# Vérifier la configuration
log "Vérification de la configuration Tor..."
if ! tor --verify-config -f "$TOR_CONFIG"; then
    log "ERREUR: Configuration Tor invalide"
    exit 1
fi

# Fonction de rotation des circuits
rotate_circuits() {
    while true; do
        sleep "$CIRCUIT_ROTATION_INTERVAL"
        if [ -n "$TOR_PID" ] && kill -0 "$TOR_PID" 2>/dev/null; then
            log "Rotation des circuits Tor..."
            # Envoyer SIGHUP pour forcer une nouvelle identité
            kill -HUP "$TOR_PID" 2>/dev/null || true
        fi
    done
}

# Fonction de monitoring
monitor_tor() {
    local check_interval=30
    local max_failures=3
    local failure_count=0
    
    while true; do
        sleep "$check_interval"
        
        # Vérifier si Tor est toujours en vie
        if [ -n "$TOR_PID" ] && kill -0 "$TOR_PID" 2>/dev/null; then
            # Tester la connectivité SOCKS
            if timeout 10 curl --socks5-hostname 127.0.0.1:9050 -s http://httpbin.org/ip >/dev/null 2>&1; then
                failure_count=0
                log "Tor fonctionne correctement"
            else
                failure_count=$((failure_count + 1))
                log "ATTENTION: Test de connectivité Tor échoué ($failure_count/$max_failures)"
                
                if [ "$failure_count" -ge "$max_failures" ]; then
                    log "ERREUR: Tor ne répond plus, redémarrage nécessaire"
                    kill -TERM "$TOR_PID" 2>/dev/null || true
                    break
                fi
            fi
        else
            log "ERREUR: Processus Tor arrêté de manière inattendue"
            break
        fi
    done
}

# Fonction de génération de configuration dynamique
generate_dynamic_config() {
    local config_file="$1"
    local instance_id="${HOSTNAME:-$(hostname)}"
    
    # Ajouter des configurations spécifiques à l'instance
    cat >> "$config_file" << EOF

# Configuration dynamique pour l'instance: $instance_id
Nickname SwarmPlaywright${instance_id}
ContactInfo swarm-playwright@example.com

# Configuration spécifique à l'environnement
EOF

    # Ajouter des nœuds d'entrée aléatoires pour diversifier
    local entry_nodes=(
        "7BE683E65D48141321C5ED92F075C55364AC7123"
        "CF6D0AAFB385BE71B8E111FC687F2B942A75A0E0"
        "9695DFC35FFEB861329B9F1AB04C46397020CE31"
    )
    
    local selected_node=${entry_nodes[$((RANDOM % ${#entry_nodes[@]}))]}
    echo "EntryNodes $selected_node" >> "$config_file"
}

# Fonction principale
main() {
    log "Démarrage de Tor pour Swarm Playwright W34R3L3G10N"
    log "Instance: ${HOSTNAME:-$(hostname)}"
    log "Configuration: $TOR_CONFIG"
    
    # Générer la configuration dynamique
    local temp_config="/tmp/torrc.dynamic"
    cp "$TOR_CONFIG" "$temp_config"
    generate_dynamic_config "$temp_config"
    
    # Démarrer Tor en arrière-plan
    log "Lancement de Tor..."
    tor -f "$temp_config" &
    TOR_PID=$!
    
    # Attendre que Tor soit prêt
    log "Attente de l'initialisation de Tor..."
    local timeout=60
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if timeout 5 curl --socks5-hostname 127.0.0.1:9050 -s http://httpbin.org/ip >/dev/null 2>&1; then
            log "Tor est prêt et fonctionnel"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if [ $elapsed -ge $timeout ]; then
        log "ERREUR: Timeout lors de l'initialisation de Tor"
        exit 1
    fi
    
    # Afficher l'IP de sortie
    local exit_ip
    exit_ip=$(timeout 10 curl --socks5-hostname 127.0.0.1:9050 -s http://httpbin.org/ip | grep -o '"origin":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "Inconnue")
    log "IP de sortie Tor: $exit_ip"
    
    # Démarrer la rotation des circuits en arrière-plan
    if [ "${ENABLE_CIRCUIT_ROTATION:-true}" = "true" ]; then
        log "Démarrage de la rotation automatique des circuits (intervalle: ${CIRCUIT_ROTATION_INTERVAL}s)"
        rotate_circuits &
        ROTATION_PID=$!
    fi
    
    # Démarrer le monitoring en arrière-plan
    if [ "${ENABLE_MONITORING:-true}" = "true" ]; then
        log "Démarrage du monitoring Tor"
        monitor_tor &
        MONITOR_PID=$!
    fi
    
    # Attendre que Tor se termine
    wait "$TOR_PID"
    
    # Nettoyer les processus de fond
    [ -n "$ROTATION_PID" ] && kill "$ROTATION_PID" 2>/dev/null || true
    [ -n "$MONITOR_PID" ] && kill "$MONITOR_PID" 2>/dev/null || true
    
    log "Tor arrêté"
}

# Point d'entrée
main "$@"

