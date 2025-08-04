#!/bin/bash
set -e

# Configuration
PROJECT_NAME="swarm-playwright-w34r3l3g10n"
COMPOSE_FILE="docker-compose.yml"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Fonction d'aide
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [COMMAND]

Commandes:
    start       Démarrer tous les services
    stop        Arrêter tous les services
    restart     Redémarrer tous les services
    build       Construire les images Docker
    logs        Afficher les logs
    status      Afficher le statut des services
    clean       Nettoyer les conteneurs et volumes
    scale       Modifier le nombre de répliques
    test        Tester la connectivité

Options:
    -h, --help      Afficher cette aide
    -v, --verbose   Mode verbeux
    --monitoring    Inclure les services de monitoring

Exemples:
    $0 start                    # Démarrer tous les services
    $0 start --monitoring       # Démarrer avec monitoring
    $0 scale agent=5            # Scaler les agents à 5 répliques
    $0 logs agent               # Afficher les logs des agents
EOF
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Vérifier que Docker fonctionne
    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas démarré ou accessible"
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Construction des images
build_images() {
    log "Construction des images Docker..."
    
    if [ "$VERBOSE" = "true" ]; then
        docker-compose -f "$COMPOSE_FILE" build
    else
        docker-compose -f "$COMPOSE_FILE" build > /dev/null 2>&1
    fi
    
    log_success "Images construites avec succès"
}

# Démarrage des services
start_services() {
    log "Démarrage des services..."
    
    local compose_args=""
    if [ "$INCLUDE_MONITORING" = "true" ]; then
        compose_args="--profile monitoring"
    fi
    
    docker-compose -f "$COMPOSE_FILE" up -d $compose_args
    
    log_success "Services démarrés"
    
    # Attendre que les services soient prêts
    wait_for_services
}

# Arrêt des services
stop_services() {
    log "Arrêt des services..."
    
    docker-compose -f "$COMPOSE_FILE" down
    
    log_success "Services arrêtés"
}

# Redémarrage des services
restart_services() {
    log "Redémarrage des services..."
    
    stop_services
    start_services
}

# Attendre que les services soient prêts
wait_for_services() {
    log "Attente de la disponibilité des services..."
    
    local services=("redis:6379" "load-balancer:8080" "coordinator:8001")
    local max_attempts=30
    local attempt=1
    
    for service in "${services[@]}"; do
        local host=$(echo "$service" | cut -d':' -f1)
        local port=$(echo "$service" | cut -d':' -f2)
        
        log "Attente de $host:$port..."
        
        while [ $attempt -le $max_attempts ]; do
            if docker-compose -f "$COMPOSE_FILE" exec -T "$host" sh -c "nc -z localhost $port" 2>/dev/null; then
                log_success "$host:$port est prêt"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                log_warning "$host:$port n'est pas prêt après $max_attempts tentatives"
                break
            fi
            
            sleep 2
            attempt=$((attempt + 1))
        done
        
        attempt=1
    done
    
    # Test de connectivité des agents
    log "Test de connectivité des agents..."
    sleep 10
    
    if curl -f http://localhost:8080/health >/dev/null 2>&1; then
        log_success "Load balancer accessible"
    else
        log_warning "Load balancer non accessible"
    fi
    
    if curl -f http://localhost:8001/health >/dev/null 2>&1; then
        log_success "Coordinateur accessible"
    else
        log_warning "Coordinateur non accessible"
    fi
}

# Affichage des logs
show_logs() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log "Affichage des logs pour $service..."
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        log "Affichage des logs de tous les services..."
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Affichage du statut
show_status() {
    log "Statut des services:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo
    log "Utilisation des ressources:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    echo
    log "Santé des services:"
    
    # Vérifier la santé des services principaux
    local services=("load-balancer:8080/health" "coordinator:8001/health")
    
    for service in "${services[@]}"; do
        local url="http://localhost/$service"
        if curl -f "$url" >/dev/null 2>&1; then
            log_success "✓ $service"
        else
            log_error "✗ $service"
        fi
    done
}

# Scaling des services
scale_services() {
    local scale_args="$1"
    
    if [ -z "$scale_args" ]; then
        log_error "Arguments de scaling manquants (ex: agent=5)"
        exit 1
    fi
    
    log "Scaling des services: $scale_args"
    docker-compose -f "$COMPOSE_FILE" up -d --scale "$scale_args"
    
    log_success "Scaling effectué"
}

# Nettoyage
clean_environment() {
    log "Nettoyage de l'environnement..."
    
    # Arrêter et supprimer les conteneurs
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
    
    # Supprimer les images du projet
    docker images | grep "$PROJECT_NAME" | awk '{print $3}' | xargs -r docker rmi
    
    # Nettoyer les volumes orphelins
    docker volume prune -f
    
    # Nettoyer les réseaux orphelins
    docker network prune -f
    
    log_success "Nettoyage terminé"
}

# Test de connectivité
test_connectivity() {
    log "Test de connectivité du système..."
    
    # Test du load balancer
    log "Test du load balancer..."
    if response=$(curl -s http://localhost:8080/health); then
        log_success "Load balancer: OK"
        echo "$response" | jq . 2>/dev/null || echo "$response"
    else
        log_error "Load balancer: ÉCHEC"
    fi
    
    echo
    
    # Test du coordinateur
    log "Test du coordinateur..."
    if response=$(curl -s http://localhost:8001/health); then
        log_success "Coordinateur: OK"
        echo "$response" | jq . 2>/dev/null || echo "$response"
    else
        log_error "Coordinateur: ÉCHEC"
    fi
    
    echo
    
    # Test des agents
    log "Test des agents..."
    if response=$(curl -s http://localhost:8080/agents); then
        log_success "Agents disponibles:"
        echo "$response" | jq . 2>/dev/null || echo "$response"
    else
        log_error "Impossible de récupérer la liste des agents"
    fi
    
    echo
    
    # Test d'une tâche simple
    log "Test d'exécution d'une tâche..."
    if response=$(curl -s -X POST http://localhost:8080/execute \
        -H "Content-Type: application/json" \
        -d '{"type":"navigate","payload":{"url":"https://httpbin.org/ip"}}'); then
        log_success "Exécution de tâche: OK"
        echo "$response" | jq . 2>/dev/null || echo "$response"
    else
        log_error "Exécution de tâche: ÉCHEC"
    fi
}

# Variables par défaut
VERBOSE=false
INCLUDE_MONITORING=false

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --monitoring)
            INCLUDE_MONITORING=true
            shift
            ;;
        start)
            COMMAND="start"
            shift
            ;;
        stop)
            COMMAND="stop"
            shift
            ;;
        restart)
            COMMAND="restart"
            shift
            ;;
        build)
            COMMAND="build"
            shift
            ;;
        logs)
            COMMAND="logs"
            SERVICE="$2"
            shift 2
            ;;
        status)
            COMMAND="status"
            shift
            ;;
        scale)
            COMMAND="scale"
            SCALE_ARGS="$2"
            shift 2
            ;;
        clean)
            COMMAND="clean"
            shift
            ;;
        test)
            COMMAND="test"
            shift
            ;;
        *)
            log_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Commande par défaut
if [ -z "$COMMAND" ]; then
    COMMAND="start"
fi

# Vérification des prérequis
check_prerequisites

# Exécution de la commande
case $COMMAND in
    start)
        build_images
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    build)
        build_images
        ;;
    logs)
        show_logs "$SERVICE"
        ;;
    status)
        show_status
        ;;
    scale)
        scale_services "$SCALE_ARGS"
        ;;
    clean)
        clean_environment
        ;;
    test)
        test_connectivity
        ;;
    *)
        log_error "Commande inconnue: $COMMAND"
        show_help
        exit 1
        ;;
esac

