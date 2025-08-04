# Swarm Playwright W34R3L3G10N

Un serveur MCP agent avancé basé sur mcp-playwright-stealth avec load balancing, réplication sur N machines, et simulation d'utilisateurs réels pour tests avec VLLM.

## 🎯 Objectifs

- **Load Balancing Intelligent**: Distribution automatique des requêtes sur N machines répliquées
- **Simulation d'Utilisateurs Réels**: Comportements humains authentiques avec Playwright
- **Double Proxying**: Tor → Cloudflare WARP pour anonymat maximal
- **Scalabilité Transparente**: Du développement local à la production avec Docker Swarm
- **Intégration VLLM**: Optimisé pour générer des essaims d'utilisateurs réels

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Coordinator   │    │  Load Balancer  │    │   Agent Pool    │
│   (MCP Server)  │◄──►│   (FastAPI)     │◄──►│  (N Replicas)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Task Queue    │    │   Monitoring    │    │  Tor + WARP     │
│   (Redis)       │    │   (Prometheus)  │    │  (Proxy Chain)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Flux de Données

1. **Requête MCP** → Coordinateur reçoit les commandes via le protocole MCP
2. **Load Balancing** → Distribution intelligente vers les agents disponibles
3. **Exécution** → Agents Playwright simulent des comportements humains réalistes
4. **Proxy Chain** → Trafic routé via Tor → Cloudflare WARP pour anonymat
5. **Résultats** → Agrégation et retour via le coordinateur MCP

## 🚀 Démarrage Rapide

### Prérequis

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- Connexion Internet stable

### Installation Développement

```bash
# Cloner le repo
git clone https://github.com/votre-username/swarm-playwright-w34r3l3g10n.git
cd swarm-playwright-w34r3l3g10n

# Démarrer tous les services
./scripts/deploy-dev.sh start

# Avec monitoring (optionnel)
./scripts/deploy-dev.sh start --monitoring

# Vérifier le statut
./scripts/deploy-dev.sh status

# Tester la connectivité
./scripts/deploy-dev.sh test
```

### Installation Production (Docker Swarm)

```bash
# Initialiser Docker Swarm
docker swarm init

# Déployer en production
./scripts/deploy-swarm.sh

# Scaler les agents
docker service scale swarm-playwright_agent=20
```

## 📁 Structure du Projet

```
swarm-playwright-w34r3l3g10n/
├── coordinator/              # Serveur MCP principal
│   ├── mcp_server.py        # Serveur MCP avec outils
│   ├── task_queue.py        # Système de queue distribuée
│   ├── Dockerfile           # Image Docker coordinateur
│   └── requirements.txt     # Dépendances Python
├── agent/                   # Agents Playwright
│   ├── main.py             # Serveur FastAPI agent
│   ├── playwright_agent.py # Agent Playwright avec stealth
│   ├── user_profiles.py    # Profils utilisateurs réalistes
│   ├── Dockerfile          # Image Docker agent
│   ├── entrypoint.sh       # Script de démarrage
│   └── requirements.txt    # Dépendances Python
├── load-balancer/          # Load balancer FastAPI
│   ├── main.py            # Load balancer intelligent
│   ├── Dockerfile         # Image Docker load balancer
│   └── requirements.txt   # Dépendances Python
├── tor/                   # Configuration Tor
│   ├── Dockerfile        # Image Docker Tor
│   ├── torrc            # Configuration Tor optimisée
│   └── entrypoint.sh    # Script de démarrage Tor
├── warp/                 # Configuration Cloudflare WARP
│   ├── Dockerfile       # Image Docker WARP
│   ├── entrypoint.sh   # Script de démarrage WARP
│   ├── warp-manager.sh # Gestionnaire WARP
│   └── wgcf-profile.conf.template # Template config WARP
├── scripts/             # Scripts de déploiement
│   ├── deploy-dev.sh   # Déploiement développement
│   ├── deploy-swarm.sh # Déploiement production
│   └── build-images.sh # Construction des images
├── monitoring/         # Configuration monitoring
│   ├── prometheus.yml # Configuration Prometheus
│   └── grafana/      # Dashboards Grafana
├── tests/            # Tests
│   ├── unit/        # Tests unitaires
│   ├── integration/ # Tests d'intégration
│   └── load/       # Tests de charge
├── docs/           # Documentation
├── docker-compose.yml      # Développement local
├── docker-compose.prod.yml # Production Swarm
└── README.md
```

## 🔧 Configuration

### Variables d'Environnement

#### Coordinateur MCP
```bash
REDIS_URL=redis://redis:6379
LOAD_BALANCER_URL=http://load-balancer:8080
AGENT_POOL_SIZE=5
LOG_LEVEL=INFO
```

#### Load Balancer
```bash
REDIS_URL=redis://redis:6379
AGENT_DISCOVERY_INTERVAL=30
HEALTH_CHECK_INTERVAL=10
AGENT_TIMEOUT=30
```

#### Agents Playwright
```bash
TOR_PROXY_HOST=tor
TOR_PROXY_PORT=9050
HEADLESS=true
MAX_CONCURRENT_TASKS=3
STEALTH_LEVEL=high
```

#### Tor
```bash
CIRCUIT_ROTATION_INTERVAL=300
ENABLE_CIRCUIT_ROTATION=true
ENABLE_MONITORING=true
```

#### WARP
```bash
ENABLE_SOCKS_PROXY=true
ENABLE_HTTP_PROXY=true
SOCKS_PORT=1080
HTTP_PORT=3128
```

## 🛠️ API Reference

### Coordinateur MCP

Le coordinateur expose les outils MCP suivants:

#### `navigate_url`
Navigue vers une URL avec un comportement d'utilisateur réel.

```json
{
  "url": "https://example.com",
  "user_profile": "desktop",
  "behavior_pattern": "casual",
  "stealth_level": "high"
}
```

#### `search_query`
Effectue une recherche avec un comportement humain réaliste.

```json
{
  "query": "playwright automation",
  "search_engine": "duckduckgo",
  "user_profile": "mobile",
  "max_results": 10
}
```

#### `interact_page`
Interagit avec une page web de manière naturelle.

```json
{
  "url": "https://example.com",
  "actions": [
    {"type": "click", "selector": "#button"},
    {"type": "type", "selector": "#input", "text": "Hello"},
    {"type": "scroll", "direction": "down"}
  ],
  "user_profile": "desktop"
}
```

#### `swarm_execute`
Exécute une tâche sur plusieurs agents en parallèle.

```json
{
  "task": {
    "type": "navigate",
    "payload": {"url": "https://example.com"}
  },
  "replicas": 5,
  "strategy": "parallel"
}
```

### Load Balancer API

#### `GET /health`
Retourne l'état de santé du load balancer.

#### `GET /agents`
Liste tous les agents disponibles.

#### `POST /execute`
Exécute une tâche sur un agent sélectionné.

#### `POST /execute/batch`
Exécute plusieurs tâches en parallèle.

#### `GET /metrics`
Retourne les métriques de performance.

### Agent API

#### `GET /health`
Retourne l'état de santé de l'agent.

#### `POST /navigate`
Navigue vers une URL.

#### `POST /search`
Effectue une recherche.

#### `POST /interact`
Interagit avec une page.

#### `POST /screenshot`
Prend une capture d'écran.

## 🎭 Simulation d'Utilisateurs Réels

### Profils Utilisateurs

Le système inclut des profils d'utilisateurs sophistiqués:

- **Types d'appareils**: Desktop, Mobile, Tablet
- **Patterns de comportement**: Casual, Focused, Researcher, Shopper, Social
- **User-agents réalistes**: Base de données mise à jour régulièrement
- **Tailles d'écran**: Résolutions courantes par type d'appareil

### Comportements Humains

- **Vitesse de frappe variable**: Basée sur le profil utilisateur
- **Mouvements de souris naturels**: Courbes de Bézier et variations
- **Délais de lecture**: Simulation de temps de lecture réaliste
- **Erreurs de frappe**: Erreurs occasionnelles avec correction
- **Pauses et fatigue**: Simulation de fatigue progressive
- **Patterns de scroll**: Vitesses et pauses variables

### Techniques de Stealth

- **Masquage WebDriver**: Suppression des traces d'automatisation
- **Fingerprinting résistant**: Protection contre la détection
- **Rotation des circuits**: Changement d'IP automatique
- **Headers réalistes**: Simulation de navigateurs réels
- **Timing humain**: Délais et variations naturelles

## 🔒 Anonymat et Sécurité

### Double Proxying

```
Agent Playwright → Tor (SOCKS5) → Cloudflare WARP → Internet
```

1. **Tor**: Anonymisation via le réseau Tor
2. **WARP**: Tunnel Cloudflare pour masquer la sortie Tor
3. **Rotation**: Changement automatique des circuits

### Configuration Tor

- **Circuits optimisés**: Sélection de nœuds fiables
- **Rotation automatique**: Nouveaux circuits toutes les 5 minutes
- **Exclusion de pays**: Évitement des nœuds malveillants
- **Monitoring**: Surveillance de la connectivité

### Configuration WARP

- **WireGuard**: Tunnel VPN haute performance
- **Génération automatique**: Configuration WARP dynamique
- **Monitoring**: Surveillance de la santé du tunnel
- **Failover**: Redémarrage automatique en cas d'échec

## 📊 Monitoring et Métriques

### Métriques Collectées

- **Performance des agents**: Temps de réponse, taux de succès
- **Utilisation des ressources**: CPU, mémoire, réseau
- **Santé des proxies**: Connectivité Tor et WARP
- **Métriques de queue**: Tâches en attente, temps d'exécution
- **Erreurs et échecs**: Taux d'erreur par type

### Dashboards Grafana

- **Vue d'ensemble**: Statut global du système
- **Performance des agents**: Métriques détaillées par agent
- **Réseau et proxies**: Santé des connexions
- **Alertes**: Notifications en cas de problème

### Alertes Prometheus

- **Agents indisponibles**: Plus de 50% d'agents hors service
- **Latence élevée**: Temps de réponse > 30 secondes
- **Échecs de proxy**: Tor ou WARP non accessible
- **Utilisation mémoire**: > 90% d'utilisation

## 🧪 Tests

### Tests Unitaires

```bash
# Exécuter tous les tests unitaires
pytest tests/unit/ -v

# Tests spécifiques
pytest tests/unit/test_user_profiles.py
pytest tests/unit/test_task_queue.py
pytest tests/unit/test_load_balancer.py
```

### Tests d'Intégration

```bash
# Tests d'intégration complets
pytest tests/integration/ -v

# Test de bout en bout
pytest tests/integration/test_e2e.py
```

### Tests de Charge

```bash
# Tests de charge avec Locust
cd tests/load
locust -f load_test.py --host=http://localhost:8080

# Tests de stress
pytest tests/load/test_stress.py
```

## 🚀 Déploiement

### Développement Local

```bash
# Démarrage simple
./scripts/deploy-dev.sh start

# Avec monitoring
./scripts/deploy-dev.sh start --monitoring

# Scaling des agents
./scripts/deploy-dev.sh scale agent=10

# Logs en temps réel
./scripts/deploy-dev.sh logs agent
```

### Production Docker Swarm

```bash
# Initialiser le swarm
docker swarm init

# Déployer la stack
docker stack deploy -c docker-compose.prod.yml swarm-playwright

# Scaler les services
docker service scale swarm-playwright_agent=20
docker service scale swarm-playwright_tor=20
docker service scale swarm-playwright_warp=20

# Monitoring
docker service ls
docker service logs swarm-playwright_agent
```

### Variables de Scaling

- **Agents**: 1 agent par 2 vCPU recommandé
- **Tor**: 1 instance Tor par agent
- **WARP**: 1 instance WARP par agent
- **Load Balancer**: 3 instances minimum pour HA
- **Redis**: 1 instance avec réplication optionnelle

## 🔧 Maintenance

### Rotation des Proxies

```bash
# Forcer la rotation des circuits Tor
docker exec -it tor_container kill -HUP 1

# Redémarrer WARP
docker restart warp_container
```

### Nettoyage

```bash
# Nettoyer les anciennes tâches
curl -X POST http://localhost:8080/cleanup

# Nettoyer Docker
./scripts/deploy-dev.sh clean
```

### Mise à jour

```bash
# Reconstruire les images
./scripts/deploy-dev.sh build

# Mise à jour rolling en production
docker service update --image swarm-playwright/agent:latest swarm-playwright_agent
```

## 🐛 Troubleshooting

### Problèmes Courants

#### Agents non disponibles
```bash
# Vérifier les logs
docker logs agent_container

# Vérifier la connectivité Tor
curl --socks5-hostname tor:9050 http://httpbin.org/ip
```

#### Problèmes de proxy
```bash
# Tester Tor
docker exec tor_container curl --socks5-hostname 127.0.0.1:9050 http://httpbin.org/ip

# Tester WARP
docker exec warp_container curl --interface wgcf http://httpbin.org/ip
```

#### Performance dégradée
```bash
# Vérifier les métriques
curl http://localhost:8080/metrics

# Scaler les agents
docker service scale swarm-playwright_agent=30
```

### Logs Utiles

```bash
# Logs du coordinateur
docker logs coordinator_container

# Logs du load balancer
docker logs load-balancer_container

# Logs des agents
docker service logs swarm-playwright_agent

# Logs système
journalctl -u docker.service
```

## 🤝 Contribution

### Guidelines

1. **Fork** le repository
2. **Créer** une branche feature (`git checkout -b feature/amazing-feature`)
3. **Commit** les changements (`git commit -m 'Add amazing feature'`)
4. **Push** vers la branche (`git push origin feature/amazing-feature`)
5. **Ouvrir** une Pull Request

### Standards de Code

- **Python**: PEP 8, type hints, docstrings
- **Docker**: Multi-stage builds, non-root users
- **Tests**: Couverture > 80%
- **Documentation**: Mise à jour obligatoire

### Tests Requis

```bash
# Avant de soumettre une PR
pytest tests/ --cov=. --cov-report=html
flake8 .
mypy .
```

## 📄 License

MIT License - voir [LICENSE](LICENSE) pour les détails.

## 🙏 Remerciements

- [Playwright](https://playwright.dev/) pour l'automatisation web
- [Tor Project](https://www.torproject.org/) pour l'anonymat
- [Cloudflare WARP](https://developers.cloudflare.com/warp-client/) pour les tunnels
- [FastAPI](https://fastapi.tiangolo.com/) pour les APIs
- [Docker](https://www.docker.com/) pour la containerisation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/votre-username/swarm-playwright-w34r3l3g10n/issues)
- **Discussions**: [GitHub Discussions](https://github.com/votre-username/swarm-playwright-w34r3l3g10n/discussions)
- **Email**: support@swarm-playwright.com

---

**Swarm Playwright W34R3L3G10N** - Simulation d'utilisateurs réels à l'échelle industrielle 🎭🤖

