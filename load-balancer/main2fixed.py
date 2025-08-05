#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - Load Balancer Fixed
Load balancer corrigé avec gestion robuste de la découverte d'agents
"""

import asyncio
import json
import logging
import os
import random
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

# Configuration
AGENT_DISCOVERY_INTERVAL = int(os.getenv("AGENT_DISCOVERY_INTERVAL", "30"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "10"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "30"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Modèles Pydantic
class Agent(BaseModel):
    id: str
    url: str
    status: str = "unknown"
    load: int = 0
    last_seen: datetime = Field(default_factory=datetime.now)
    capabilities: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    failed_attempts: int = 0
    max_failed_attempts: int = 3

class ExecuteRequest(BaseModel):
    agent_id: Optional[str] = None
    task: Dict[str, Any]
    strategy: str = "auto"

class LoadBalancer:
    """Load balancer avec découverte robuste d'agents"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.http_client = httpx.AsyncClient(timeout=AGENT_TIMEOUT)
        self.running = False
        self.discovery_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.last_discovery = 0
        self.discovery_count = 0
        
    async def initialize(self):
        """Initialise le load balancer"""
        logger.info("Initialisation du load balancer")
        
        # Connexion Redis
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            await self.redis_client.ping()
            logger.info("Connexion Redis établie")
        except Exception as e:
            logger.error(f"Erreur connexion Redis: {e}")
            self.redis_client = None
            
        # Découverte initiale des agents
        await self.discover_agents()
        
        # Démarrer les tâches de fond
        self.running = True
        self.discovery_task = asyncio.create_task(self._background_discovery())
        self.health_check_task = asyncio.create_task(self._background_health_check())
        
    async def shutdown(self):
        """Arrête le load balancer"""
        logger.info("Arrêt du load balancer")
        self.running = False
        
        # Annuler les tâches de fond
        if self.discovery_task:
            self.discovery_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
            
        # Fermer les connexions
        await self.http_client.aclose()
        if self.redis_client:
            await self.redis_client.aclose()

    async def resolve_service_ips(self, hostname: str) -> List[str]:
        """Résout les adresses IP de toutes les répliques d'un service Docker DNSRR"""
        try:
            # Utiliser getaddrinfo pour une résolution plus robuste
            result = await asyncio.get_event_loop().run_in_executor(
                None, socket.getaddrinfo, hostname, None
            )
            ips = list(set(info[4][0] for info in result if info[0] == socket.AF_INET))
            return ips
        except Exception as e:
            logger.warning(f"Échec de la résolution DNS pour {hostname}: {e}")
            return []

    async def check_agent(self, ip: str, port: int, service_name: str) -> Optional[Agent]:
        """Interroge une réplique d'agent à l'IP donnée"""
        url = f"http://{ip}:{port}"
        health_url = f"{url}/health"
        
        try:
            response = await self.http_client.get(health_url, timeout=5.0)
            if response.status_code == 200:
                agent_info = response.json()
                agent_id = agent_info.get("agent_id", f"{service_name}-{ip}")
                
                return Agent(
                    id=agent_id,
                    url=url,
                    status="healthy",
                    last_seen=datetime.now(),
                    capabilities=agent_info.get("capabilities", []),
                    performance_metrics=agent_info.get("metrics", {}),
                    failed_attempts=0
                )
        except Exception as e:
            logger.debug(f"Échec de connexion à {health_url}: {e}")
        return None

    async def discover_agents(self):
        """Découvre les agents disponibles via Docker Swarm DNSRR"""
        discovery_start = time.time()
        self.discovery_count += 1
        
        logger.info(f"Découverte des agents #{self.discovery_count}...")

        # Réinitialiser le pool d'agents avant chaque découverte
        previous_agents = self.agents.copy()
        self.agents = {}
        
        service_names = [
            "agent",
            "swarm-playwright-agent",  # Nom alternatif
        ]
        
        discovered_agents = []
        
        for service_name in service_names:
            try:
                ips = await self.resolve_service_ips(service_name)
                logger.debug(f"{len(ips)} IPs résolues pour {service_name}: {ips}")
                
                # Vérifier chaque IP en parallèle
                tasks = [
                    self.check_agent(ip, port=8000, service_name=service_name)
                    for ip in ips
                ]
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Agent):
                            self.agents[result.id] = result
                            discovered_agents.append(result.id)
                            logger.debug(f"Agent découvert: {result.id} @ {result.url}")
                        elif isinstance(result, Exception):
                            logger.debug(f"Erreur lors de la vérification d'agent: {result}")
                            
            except Exception as e:
                logger.warning(f"Erreur lors de la découverte du service {service_name}: {e}")
        
        # Préserver les agents qui étaient déjà connus et toujours accessibles
        for agent_id, agent in previous_agents.items():
            if agent_id not in self.agents:
                # Tenter de reconnecter à l'agent
                try:
                    url_parts = agent.url.replace("http://", "").split(":")
                    if len(url_parts) == 2:
                        ip, port = url_parts[0], int(url_parts[1])
                        reconnected_agent = await self.check_agent(ip, port, "reconnect")
                        if reconnected_agent:
                            reconnected_agent.id = agent_id  # Conserver l'ID original
                            self.agents[agent_id] = reconnected_agent
                            logger.debug(f"Agent reconnecté: {agent_id}")
                        else:
                            # Incrémenter les échecs
                            agent.failed_attempts += 1
                            if agent.failed_attempts < agent.max_failed_attempts:
                                agent.status = "unreachable"
                                self.agents[agent_id] = agent
                                logger.debug(f"Agent temporairement inaccessible: {agent_id} "
                                           f"({agent.failed_attempts}/{agent.max_failed_attempts})")
                            else:
                                logger.info(f"Agent supprimé après {agent.failed_attempts} échecs: {agent_id}")
                except Exception as e:
                    logger.debug(f"Erreur lors de la reconnexion à {agent_id}: {e}")

        # Sauvegarde dans Redis
        if self.redis_client:
            try:
                agents_data = {
                    agent_id: agent.dict(mode="json")
                    for agent_id, agent in self.agents.items()
                }
                await self.redis_client.set(
                    "agents",
                    json.dumps(agents_data, default=str),
                    ex=300  # expire in 5 minutes
                )
                logger.debug("Agents sauvegardés dans Redis")
            except Exception as e:
                logger.error(f"Erreur sauvegarde agents Redis: {e}")

        discovery_time = time.time() - discovery_start
        self.last_discovery = time.time()
        
        logger.info(f"Découverte #{self.discovery_count} terminée: "
                   f"{len(self.agents)} agent(s) trouvé(s) en {discovery_time:.2f}s")
        
        # Log détaillé des agents
        if self.agents:
            for agent in self.agents.values():
                logger.debug(f"  - {agent.id}: {agent.status} @ {agent.url}")
        else:
            logger.warning("Aucun agent découvert!")
        
    async def _background_discovery(self):
        """Tâche de fond pour la découverte périodique d'agents"""
        logger.info(f"Démarrage de la découverte périodique (intervalle: {AGENT_DISCOVERY_INTERVAL}s)")
        
        while self.running:
            try:
                await asyncio.sleep(AGENT_DISCOVERY_INTERVAL)
                if self.running:  # Vérifier à nouveau après le sleep
                    await self.discover_agents()
            except asyncio.CancelledError:
                logger.info("Découverte périodique arrêtée")
                break
            except Exception as e:
                logger.error(f"Erreur découverte agents: {e}")
                await asyncio.sleep(5)  # Attente courte en cas d'erreur
        
    async def _background_health_check(self):
        """Tâche de fond pour les vérifications de santé"""
        logger.info(f"Démarrage des health checks (intervalle: {HEALTH_CHECK_INTERVAL}s)")
        
        while self.running:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                if self.running:  # Vérifier à nouveau après le sleep
                    await self.health_check_agents()
            except asyncio.CancelledError:
                logger.info("Health checks arrêtés")
                break
            except Exception as e:
                logger.error(f"Erreur health check: {e}")
                await asyncio.sleep(5)
                
    async def health_check_agents(self):
        """Vérifie la santé des agents"""
        if not self.agents:
            return
            
        logger.debug(f"Vérification santé de {len(self.agents)} agents...")
        
        for agent_id, agent in list(self.agents.items()):
            try:
                response = await self.http_client.get(
                    f"{agent.url}/health", 
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    health_data = response.json()
                    agent.status = "healthy"
                    agent.load = health_data.get("load", 0)
                    agent.last_seen = datetime.now()
                    agent.performance_metrics = health_data.get("metrics", {})
                    agent.failed_attempts = 0  # Reset sur succès
                else:
                    agent.status = "unhealthy"
                    agent.failed_attempts += 1
                    
            except Exception as e:
                logger.debug(f"Agent {agent_id} non accessible: {e}")
                agent.status = "unreachable"
                agent.failed_attempts += 1
                
                # Supprimer les agents non accessibles depuis trop longtemps
                if (datetime.now() - agent.last_seen > timedelta(minutes=5) or
                    agent.failed_attempts >= agent.max_failed_attempts):
                    logger.info(f"Suppression de l'agent non accessible: {agent_id}")
                    del self.agents[agent_id]

    async def select_agent(self, task_type: str = "default", agent_id: Optional[str] = None) -> Optional[Agent]:
        """Sélectionne un agent optimal pour une tâche donnée"""
        if agent_id:
            # Agent spécifique demandé
            agent = self.agents.get(agent_id)
            if agent and agent.status == "healthy":
                return agent
            else:
                logger.warning(f"Agent spécifique {agent_id} non disponible")
                return None
        
        # Filtrer les agents capables et disponibles
        capable_agents = [
            agent for agent in self.agents.values()
            if (agent.status == "healthy" and 
                (not agent.capabilities or task_type in agent.capabilities))
        ]
        
        if not capable_agents:
            logger.warning(f"Aucun agent capable pour le type de tâche: {task_type}")
            return None
            
        # Sélection basée sur la charge et les performances
        def score_agent(agent: Agent) -> float:
            base_score = 100 - agent.load
            
            # Bonus basé sur les métriques de performance
            if agent.performance_metrics:
                metrics = agent.performance_metrics
                success_rate = metrics.get("success_rate", 0.5)
                avg_response_time = metrics.get("avg_response_time", 10.0)
                
                # Bonus pour taux de succès élevé
                base_score += success_rate * 20
                
                # Malus pour temps de réponse élevé
                base_score -= min(avg_response_time / 1000, 10)
                
            return max(base_score, 0)
            
        # Sélection pondérée
        scored_agents = [(agent, score_agent(agent)) for agent in capable_agents]
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Sélection avec un peu d'aléatoire parmi les meilleurs
        top_agents = scored_agents[:max(1, len(scored_agents) // 3)]
        selected_agent = random.choice(top_agents)[0]
        
        logger.debug(f"Agent sélectionné: {selected_agent.id} (score: {score_agent(selected_agent):.1f})")
        return selected_agent
            
    async def execute_task(self, agent: Agent, task: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une tâche sur un agent spécifique"""
        task_id = task.get("id", f"task_{int(time.time())}")
        
        try:
            # Marquer la tâche comme active
            self.active_tasks[task_id] = {
                "agent_id": agent.id,
                "task": task,
                "start_time": time.time(),
                "status": "running"
            }
            
            # Envoyer la tâche à l'agent
            response = await self.http_client.post(
                f"{agent.url}/execute",
                json=task,
                timeout=task.get("timeout", AGENT_TIMEOUT)
            )
            
            execution_time = time.time() - self.active_tasks[task_id]["start_time"]
            
            if response.status_code == 200:
                result = response.json()
                result["agent_id"] = agent.id
                result["execution_time"] = execution_time
                
                # Mettre à jour les métriques de l'agent
                agent.load = max(0, agent.load - 1)
                
                # Marquer comme terminé
                self.active_tasks[task_id]["status"] = "completed"
                self.active_tasks[task_id]["result"] = result
                
                logger.info(f"Tâche {task_id} exécutée avec succès sur {agent.id} "
                           f"en {execution_time:.2f}s")
                
                return {
                    "success": True,
                    "result": result,
                    "agent_id": agent.id,
                    "execution_time": execution_time
                }
            else:
                error_msg = f"Erreur HTTP {response.status_code}"
                logger.error(f"Erreur lors de l'exécution de la tâche {task_id}: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "agent_id": agent.id,
                    "execution_time": execution_time
                }
                
        except Exception as e:
            execution_time = time.time() - self.active_tasks.get(task_id, {}).get("start_time", time.time())
            error_msg = str(e)
            
            logger.error(f"Erreur lors de l'exécution de la tâche {task_id}: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "agent_id": agent.id,
                "execution_time": execution_time
            }
        finally:
            # Nettoyer la tâche active
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

# Instance globale du load balancer
load_balancer = LoadBalancer()

# Gestionnaire de contexte pour l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    await load_balancer.initialize()
    
    yield
    
    # Arrêt
    await load_balancer.shutdown()

# Application FastAPI
app = FastAPI(
    title="Swarm Playwright Load Balancer",
    description="Load balancer pour les agents Playwright avec découverte automatique",
    version="2.0.1",
    lifespan=lifespan
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Point d'entrée racine"""
    return {
        "service": "Swarm Playwright Load Balancer",
        "version": "2.0.1",
        "status": "running",
        "agents": len(load_balancer.agents),
        "active_tasks": len(load_balancer.active_tasks)
    }

@app.get("/health")
async def health():
    """Endpoint de santé"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agents": len(load_balancer.agents),
        "active_tasks": len(load_balancer.active_tasks),
        "last_discovery": load_balancer.last_discovery,
        "discovery_count": load_balancer.discovery_count
    }

@app.get("/agents")
async def get_agents():
    """Récupère la liste des agents disponibles"""
    return {
        "agents": [agent.dict() for agent in load_balancer.agents.values()],
        "total": len(load_balancer.agents),
        "healthy": sum(1 for agent in load_balancer.agents.values() if agent.status == "healthy"),
        "last_discovery": load_balancer.last_discovery
    }

@app.post("/execute")
async def execute_task(request: ExecuteRequest):
    """Exécute une tâche sur un agent sélectionné"""
    try:
        # Sélectionner un agent
        agent = await load_balancer.select_agent(
            task_type=request.task.get("type", "default"),
            agent_id=request.agent_id
        )
        
        if not agent:
            raise HTTPException(
                status_code=503,
                detail="Aucun agent disponible pour cette tâche"
            )
        
        # Exécuter la tâche
        result = await load_balancer.execute_task(agent, request.task)
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Erreur de validation: {e}")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/discover")
async def trigger_discovery():
    """Déclenche une découverte manuelle des agents"""
    try:
        await load_balancer.discover_agents()
        return {
            "success": True,
            "message": "Découverte déclenchée",
            "agents_found": len(load_balancer.agents)
        }
    except Exception as e:
        logger.error(f"Erreur lors de la découverte manuelle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def get_active_tasks():
    """Récupère les tâches actives"""
    return {
        "active_tasks": load_balancer.active_tasks,
        "total": len(load_balancer.active_tasks)
    }

@app.get("/metrics")
async def get_metrics():
    """Récupère les métriques du load balancer"""
    healthy_agents = sum(1 for agent in load_balancer.agents.values() if agent.status == "healthy")
    total_load = sum(agent.load for agent in load_balancer.agents.values())
    avg_load = total_load / len(load_balancer.agents) if load_balancer.agents else 0
    
    return {
        "agents": {
            "total": len(load_balancer.agents),
            "healthy": healthy_agents,
            "unhealthy": len(load_balancer.agents) - healthy_agents,
            "average_load": avg_load
        },
        "tasks": {
            "active": len(load_balancer.active_tasks)
        },
        "discovery": {
            "last_discovery": load_balancer.last_discovery,
            "discovery_count": load_balancer.discovery_count,
            "running": load_balancer.running
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_fixed:app",
        host="0.0.0.0",
        port=8080,
        log_level=LOG_LEVEL.lower(),
        reload=False
    )
