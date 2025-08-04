#!/bin/bash
set -e

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] AGENT: $1"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt de l'agent..."
    
    if [ -n "$APP_PID" ]; then
        kill "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    
    exit 0
}

# Gestionnaire de signaux
trap cleanup SIGTERM SIGINT

# Configuration de l'environnement
setup_environment() {
    log "Configuration de l'environnement..."
    
    export PLAYWRIGHT_BROWSERS_PATH=/tmp/ms-playwright
    export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
    export HEADLESS=true
    export AGENT_ID="${HOSTNAME:-agent-$(date +%s)}"
    export PYTHONPATH=/app
    export PYTHONUNBUFFERED=1

    mkdir -p /tmp/screenshots /tmp/downloads /tmp/playwright

    log "Variables d'environnement configurées:"
    log "  AGENT_ID=$AGENT_ID"
    log "  HEADLESS=$HEADLESS"
}

# Vérification des dépendances
check_dependencies() {
    log "Vérification des dépendances..."

    if ! python -c "import playwright, fastapi, uvicorn" 2>/dev/null; then
        log "ERREUR: Modules Python manquants"
        return 1
    fi

    if ! python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.firefox.launch(); p.stop()" 2>/dev/null; then
        log "ATTENTION: Firefox Playwright non disponible, tentative de réinstallation..."
        playwright install firefox || log "ERREUR: Impossible d'installer Firefox"
    fi

    log "Dépendances vérifiées"
}

# Test de connectivité
test_connectivity() {
    log "Test de connectivité..."

    if ! curl -s --max-time 10 http://httpbin.org/ip >/dev/null; then
        log "ATTENTION: Connectivité Internet limitée"
    else
        log "Connectivité Internet confirmée"
    fi

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

    setup_environment
    check_dependencies
    test_connectivity

    sleep 5

    log "Démarrage de l'agent Playwright..."
    cd /app
    python main.py &
    APP_PID=$!

    sleep 10

    if ! kill -0 "$APP_PID" 2>/dev/null; then
        log "ERREUR: L'application s'est arrêtée de manière inattendue"
        exit 1
    fi

    log "Agent Playwright démarré avec le PID: $APP_PID"

    while kill -0 "$APP_PID" 2>/dev/null; do
        sleep 30
        if ! curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log "ATTENTION: Health check échoué"
        fi
    done

    log "Application arrêtée"
    cleanup
}

main "$@"
