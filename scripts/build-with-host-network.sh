#!/bin/bash
# ==============================================================================
# Solution alternative: Build Docker avec réseau host
# ==============================================================================

set -e

echo "🔧 Build Docker avec réseau host (contourne les problèmes DNS)..."
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

success() { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}❌ ERREUR: $1${NC}"; exit 1; }

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "Dockerfile" ]; then
    error "Dockerfile non trouvé. Exécutez ce script depuis ~/Documents/Music/AR_AS"
fi

# Nettoyer le cache Docker
info "Nettoyage du cache Docker..."
docker builder prune -af --filter "until=1h" 2>/dev/null || true
success "Cache nettoyé"

# Configuration BUILDKIT pour utiliser le réseau host
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

info "Configuration de buildkit avec réseau host..."

# Build chaque image avec --network=host
IMAGES=("api" "worker" "beat" "flower")

for target in "${IMAGES[@]}"; do
    info "Build de ar-as-${target}:latest (avec réseau host)..."

    docker build \
        --network=host \
        --target=${target} \
        --tag=ar-as-${target}:latest \
        --file=Dockerfile \
        --progress=plain \
        . || error "Build de ${target} échoué"

    success "ar-as-${target}:latest créé"
done

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Toutes les images Docker sont construites!            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
info "Vous pouvez maintenant lancer:"
echo -e "  ${BLUE}docker-compose up -d${NC}"
echo -e "  ${BLUE}# OU${NC}"
echo -e "  ${BLUE}make up${NC}"
echo ""
