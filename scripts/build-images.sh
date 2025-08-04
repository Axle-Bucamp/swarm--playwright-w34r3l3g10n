#!/bin/bash
set -e

# Configuration
PROJECT_NAME="swarm-playwright"
VERSION="${VERSION:-latest}"

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

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Fonction d'aide
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -h, --help      Afficher cette aide
    -v, --version   Version des images (défaut: latest)
    --push          Pousser les images vers le registry
    --parallel      Construire en parallèle
    --no-cache      Construire sans cache

Exemples:
    $0                          # Construire toutes les images
    $0 --version v1.0.0         # Construire avec version spécifique
    $0 --push                   # Construire et pousser
    $0 --parallel --no-cache    # Construction parallèle sans cache
EOF
}

# Construction d'une image
build_image() {
    local service="$1"
    local context="$2"
    local dockerfile="${3:-Dockerfile}"
    local tag="${PROJECT_NAME}/${service}:${VERSION}"
    
    log "Construction de l'image $tag..."
    
    local build_args=""
    if [ "$NO_CACHE" = "true" ]; then
        build_args="--no-cache"
    fi
    
    if docker build $build_args -t "$tag" -f "$context/$dockerfile" "$context"; then
        log_success "Image $tag construite avec succès"
        
        if [ "$PUSH_IMAGES" = "true" ]; then
            log "Push de l'image $tag..."
            docker push "$tag"
            log_success "Image $tag poussée avec succès"
        fi
        
        return 0
    else
        log_error "Échec de la construction de l'image $tag"
        return 1
    fi
}

# Construction en parallèle
build_parallel() {
    local pids=()
    
    # Lancer les constructions en arrière-plan
    build_image "coordinator" "./coordinator" &
    pids+=($!)
    
    build_image "load-balancer" "./load-balancer" &
    pids+=($!)
    
    build_image "agent" "./agent" &
    pids+=($!)
    
    build_image "tor" "./tor" &
    pids+=($!)
    
    build_image "warp" "./warp" &
    pids+=($!)
    
    # Attendre que toutes les constructions se terminent
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            failed=1
        fi
    done
    
    return $failed
}

# Construction séquentielle
build_sequential() {
    local services=("coordinator" "load-balancer" "agent" "tor" "warp")
    local contexts=("./coordinator" "./load-balancer" "./agent" "./tor" "./warp")
    
    for i in "${!services[@]}"; do
        if ! build_image "${services[$i]}" "${contexts[$i]}"; then
            return 1
        fi
    done
    
    return 0
}

# Nettoyage des images anciennes
cleanup_old_images() {
    log "Nettoyage des images anciennes..."
    
    # Supprimer les images <none>
    docker images | grep "<none>" | awk '{print $3}' | xargs -r docker rmi
    
    # Supprimer les anciennes versions du projet
    docker images | grep "$PROJECT_NAME" | grep -v "$VERSION" | awk '{print $3}' | xargs -r docker rmi
    
    log_success "Nettoyage terminé"
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    # Vérifier que Docker fonctionne
    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas démarré ou accessible"
        exit 1
    fi
    
    # Vérifier l'espace disque
    local available_space
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5000000 ]; then  # 5GB en KB
        log_error "Espace disque insuffisant (minimum 5GB requis)"
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Affichage des informations de construction
show_build_info() {
    log "=== Construction des Images Swarm Playwright ==="
    log "Projet: $PROJECT_NAME"
    log "Version: $VERSION"
    log "Mode parallèle: $PARALLEL_BUILD"
    log "Push images: $PUSH_IMAGES"
    log "No cache: $NO_CACHE"
    log "================================================="
}

# Variables par défaut
PARALLEL_BUILD=false
PUSH_IMAGES=false
NO_CACHE=false

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGES=true
            shift
            ;;
        --parallel)
            PARALLEL_BUILD=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        *)
            log_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Vérification des prérequis
check_prerequisites

# Affichage des informations
show_build_info

# Construction des images
log "Début de la construction des images..."
start_time=$(date +%s)

if [ "$PARALLEL_BUILD" = "true" ]; then
    if build_parallel; then
        log_success "Toutes les images construites avec succès (parallèle)"
    else
        log_error "Échec de la construction de certaines images"
        exit 1
    fi
else
    if build_sequential; then
        log_success "Toutes les images construites avec succès (séquentiel)"
    else
        log_error "Échec de la construction de certaines images"
        exit 1
    fi
fi

end_time=$(date +%s)
duration=$((end_time - start_time))

log_success "Construction terminée en ${duration}s"

# Nettoyage optionnel
if [ "$NO_CACHE" = "true" ]; then
    cleanup_old_images
fi

# Affichage des images construites
log "Images construites:"
docker images | grep "$PROJECT_NAME" | grep "$VERSION"

log_success "Script de construction terminé avec succès!"

