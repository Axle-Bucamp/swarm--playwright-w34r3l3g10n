#!/bin/bash
set -e

# Configuration
DISPLAY_NUM=99
SCREEN_WIDTH=1920
SCREEN_HEIGHT=1080
SCREEN_DEPTH=24

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] AGENT: $1"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt de l'agent..."
    
    # Arrêter Xvfb
    if [ -n "$XVFB_PID" ]; then
        kill "$XVFB_PID" 2>/dev/null || true
        wait "$XVFB_PID" 2>/dev/null || true
    fi
    
    # Arrêter l'application
    if [ -n "$APP_PID" ]; then
        kill "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    
    exit 0
}

# Gestionnaire de signaux
trap cleanup SIGTERM SIGINT

# Démarrer Xvfb pour l'affichage virtuel
start_xvfb() {
    log "Démarrage de Xvfb sur DISPLAY=:$DISPLAY_NUM"
    
    Xvfb ":$DISPLAY_NUM" \
        -screen 0 "${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH}" \
        -ac \
        -nolisten tcp \
        -dpi 96 \
        +extension GLX \
        +render \
        -noreset &
    
    XVFB_PID=$!
    
    # Attendre que Xvfb soit prêt
    local timeout=10
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if xdpyinfo -display ":$DISPLAY_NUM" >/dev/null 2>&1; then
            log "Xvfb prêt sur DISPLAY=:$DISPLAY_NUM"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    
    log "ERREUR: Timeout lors du démarrage de Xvfb"
    return 1
}

# Configuration de l'environnement
setup_environment() {
    log "Configuration de l'environnement..."
    
    # Variables d'affichage
    export DISPLAY=":$DISPLAY_NUM"
    export XAUTHORITY=/tmp/.Xauth
    
    # Variables Playwright
    export PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
    export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
    
    # Variables de l'agent
    export AGENT_ID="${HOSTNAME:-agent-$(date +%s)}"
    export PYTHONPATH=/app
    export PYTHONUNBUFFERED=1
    
    # Créer les répertoires nécessaires
    mkdir -p /tmp/screenshots /tmp/downloads /tmp/playwright
    
    log "Variables d'environnement configurées:"
    log "  DISPLAY=$DISPLAY"
    log "  AGENT_ID=$AGENT_ID"
    log "  HEADLESS=${HEADLESS:-true}"
}

# Vérification des dépendances
check_dependencies() {
    log "Vérification des dépendances..."
    
    # Vérifier Python et les modules
    if ! python -c "import playwright, fastapi, uvicorn" 2>/dev/null; then
        log "ERREUR: Modules Python manquants"
        return 1
    fi
    
    # Vérifier les navigateurs Playwright
    if ! python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.firefox.launch(); p.stop()" 2>/dev/null; then
        log "ATTENTION: Firefox Playwright non disponible, tentative de réinstallation..."
        playwright install firefox || log "ERREUR: Impossible d'installer Firefox"
    fi
    
    log "Dépendances vérifiées"
}

# Test de connectivité
test_connectivity() {
    log "Test de connectivité..."
    
    # Test de connectivité de base
    if ! curl -s --max-time 10 http://httpbin.org/ip >/dev/null; then
        log "ATTENTION: Connectivité Internet limitée"
    else
        log "Connectivité Internet confirmée"
    fi
    
    # Test du proxy Tor si configuré
    if [ -n "$TOR_PROXY_HOST" ]; then
        local tor_url="socks5://$TOR_PROXY_HOST:${TOR_PROXY_PORT:-9050}"
        if curl --socks5-hostname "$TOR_PROXY_HOST:${TOR_PROXY_PORT:-9050}" -s --max-time 15 http://httpbin.org/ip >/dev/null 2>&1; then
            log "Proxy Tor accessible à $tor_url"
        else
            log "ATTENTION: Proxy Tor non accessible à $tor_url"
        fi
    fi
}

# Fonction principale
main() {
    log "=== Swarm Playwright W34R3L3G10N - Agent ==="
    log "Instance: ${HOSTNAME:-$(hostname)}"
    log "Version: 1.0.0"
    log "Timestamp: $(date)"
    log "=============================================="
    
    # Configuration
    setup_environment
    check_dependencies
    
    # Démarrer Xvfb si en mode headless
    if [ "${HEADLESS:-true}" = "true" ]; then
        if ! start_xvfb; then
            log "ERREUR: Impossible de démarrer Xvfb"
            exit 1
        fi
    fi
    
    # Test de connectivité
    test_connectivity
    
    # Attendre un peu pour que tous les services soient prêts
    sleep 5
    
    # Démarrer l'application
    log "Démarrage de l'agent Playwright..."
    
    cd /app
    python main.py &
    APP_PID=$!
    
    # Attendre un peu pour vérifier que l'application démarre
    sleep 10
    
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        log "ERREUR: L'application s'est arrêtée de manière inattendue"
        exit 1
    fi
    
    log "Agent Playwright démarré avec le PID: $APP_PID"
    
    # Monitoring simple
    while kill -0 "$APP_PID" 2>/dev/null; do
        sleep 30
        
        # Vérifier la santé de l'application
        if ! curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log "ATTENTION: Health check échoué"
        fi
    done
    
    log "Application arrêtée"
    cleanup
}

# Point d'entrée
main "$@"

