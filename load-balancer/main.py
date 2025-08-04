#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - Load Balancer
Load balancer intelligent pour la distribution des tâches entre agents Playwright
"""

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

import socket
from httpx import AsyncClient

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
AGENT_DISCOVERY_INTERVAL = int(os.getenv("AGENT_DISCOVERY_INTERVAL", "30"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "10"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "30"))
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
    last_seen: datetime = datetime.now()
    capabilities: List[str] = []
    performance_metrics: Dict[str, Any] = {}

class Task(BaseModel):
    id: str
    type: str
    payload: Dict[str, Any]
    priority: int = 1
    timeout: int = 30
    retry_count: int = 0
    max_retries: int = 3

class ExecuteRequest(BaseModel):
    agent_id: Optional[str] = None
    task: Dict[str, Any]
    strategy: str = "auto"

class LoadBalancer:
    """Load balancer intelligent pour agents Playwright"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.task_queue: List[Task] = []
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.http_client = httpx.AsyncClient(timeout=AGENT_TIMEOUT)
        self.running = False
        
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
            
        # Découverte initiale des agents
        await self.discover_agents()
        
        # Démarrer les tâches de fond
        self.running = True
        
    async def shutdown(self):
        """Arrêt propre du load balancer"""
        logger.info("Arrêt du load balancer")
        self.running = False
        
        if self.redis_client:
            await self.redis_client.close()
            
        await self.http_client.aclose()

    async def resolve_service_ips(self, hostname: str) -> list[str]:
        """Résout les adresses IP de toutes les répliques d'un service Docker DNSRR"""
        try:
            return socket.gethostbyname_ex(hostname)[2]
        except socket.gaierror as e:
            logger.warning(f"Échec de la résolution DNS pour {hostname}: {e}")
            return []

    async def check_agent(self, ip: str, port: int, service_name: str, client) -> Agent | None:
        """Interroge une réplique d'agent à l'IP donnée"""
        url = f"http://{ip}:{port}/health"
        try:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                agent_info = response.json()
                agent_id = agent_info.get("agent_id", f"{service_name}-{ip}")
                return Agent(
                    id=agent_id,
                    url=url,
                    status="healthy",
                    last_seen=datetime.now(),
                    capabilities=agent_info.get("capabilities", []),
                    performance_metrics=agent_info.get("metrics", {})
                )
        except Exception as e:
            logger.warning(f"Échec de connexion à {url}: {e}")
        return None

    async def discover_agents(self):
        """Découvre les agents disponibles via Docker Swarm DNSRR"""
        logger.info("Découverte des agents...")

        self.agents = {}  # reset before each discovery
        service_names = [
            "agent",
            #"swarm-playwright-agent",
        ]
        discovered_agents = []
        client = self.http_client
        
        tasks = []
        for service_name in service_names:
            ips = await self.resolve_service_ips(service_name)
            logger.info(f"discovered ips: {ips}")
            logger.info(f"{len(ips)} IPs résolues pour {service_name}: {ips}")
            for ip in ips:
                tasks.append(self.check_agent(ip, port=8000, service_name=service_name, client=client))

        results = await asyncio.gather(*tasks)
        for agent in results:
            if agent:
                self.agents[agent.id] = agent
                discovered_agents.append(agent.id)
                logger.info(f"Agent découvert: {agent.id} @ {agent.url}")

        # Sauvegarde dans Redis
        if self.redis_client:
            try:
                agents_data = {
                    agent_id: agent.model_dump(mode="json")
                    for agent_id, agent in self.agents.items()
                }
                await self.redis_client.set(
                    "agents",
                    json.dumps(agents_data, default=str),
                    ex=300  # expire in 5 minutes
                )
            except Exception as e:
                logger.error(f"Erreur sauvegarde agents Redis: {e}")

        logger.info(f"Découverte terminée: {len(self.agents)} agent(s) trouvé(s)")
        
    async def health_check_agents(self):
        """Vérifie la santé des agents"""
        logger.debug("Vérification santé des agents...")
        
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
                else:
                    agent.status = "unhealthy"
                    
            except Exception as e:
                logger.warning(f"Agent {agent_id} non accessible: {e}")
                agent.status = "unreachable"
                
                # Supprimer les agents non accessibles depuis trop longtemps
                if datetime.now() - agent.last_seen > timedelta(minutes=5):
                    logger.info(f"Suppression de l'agent inactif: {agent_id}")
                    del self.agents[agent_id]
                    
    async def select_agent(self, task: Dict[str, Any], strategy: str = "auto") -> Optional[Agent]:
        """Sélectionne l'agent optimal pour une tâche"""
        
        # Filtrer les agents sains
        healthy_agents = [
            agent for agent in self.agents.values()
            if agent.status == "healthy"
        ]
        
        if not healthy_agents:
            logger.warning("Aucun agent sain disponible")
            return None
            
        # Stratégies de sélection
        if strategy == "round_robin":
            # Simple round-robin
            return random.choice(healthy_agents)
            
        elif strategy == "least_loaded":
            # Agent avec la charge la plus faible
            return min(healthy_agents, key=lambda x: x.load)
            
        elif strategy == "random":
            # Sélection aléatoire
            return random.choice(healthy_agents)
            
        else:  # auto
            # Stratégie intelligente basée sur le type de tâche et la performance
            task_type = task.get("type", "default")
            
            # Filtrer par capacités si spécifiées
            capable_agents = [
                agent for agent in healthy_agents
                if not task.get("required_capabilities") or 
                all(cap in agent.capabilities for cap in task.get("required_capabilities", []))
            ]
            
            if not capable_agents:
                capable_agents = healthy_agents
                
            # Scoring basé sur charge et performance
            def score_agent(agent: Agent) -> float:
                base_score = 100 - agent.load  # Plus la charge est faible, mieux c'est
                
                # Bonus pour les métriques de performance
                metrics = agent.performance_metrics
                if metrics:
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
            return random.choice(top_agents)[0]
            
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
            
            if response.status_code == 200:
                result = response.json()
                result["agent_id"] = agent.id
                result["execution_time"] = time.time() - self.active_tasks[task_id]["start_time"]
                
                # Mettre à jour les métriques de l'agent
                agent.load = max(0, agent.load - 1)
                
                # Marquer comme terminé
                self.active_tasks[task_id]["status"] = "completed"
                self.active_tasks[task_id]["result"] = result
                
                logger.info(f"Tâche {task_id} exécutée avec succès sur {agent.id}")
                return result
                
            else:
                error_msg = f"Erreur HTTP {response.status_code}"
                logger.error(f"Erreur exécution tâche {task_id}: {error_msg}")
                
                # Marquer comme échoué
                self.active_tasks[task_id]["status"] = "failed"
                self.active_tasks[task_id]["error"] = error_msg
                
                return {
                    "success": False,
                    "error": error_msg,
                    "agent_id": agent.id,
                    "task_id": task_id
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Exception lors de l'exécution de la tâche {task_id}: {error_msg}")
            
            # Marquer comme échoué
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "failed"
                self.active_tasks[task_id]["error"] = error_msg
            
            return {
                "success": False,
                "error": error_msg,
                "agent_id": agent.id,
                "task_id": task_id
            }
        finally:
            # Nettoyer les tâches anciennes
            if task_id in self.active_tasks:
                # Garder l'historique pendant 1 heure
                if time.time() - self.active_tasks[task_id]["start_time"] > 3600:
                    del self.active_tasks[task_id]

# Instance globale du load balancer
load_balancer = LoadBalancer()

# Tâches de fond
async def background_discovery():
    """Tâche de fond pour la découverte d'agents"""
    while load_balancer.running:
        try:
            await load_balancer.discover_agents()
            await asyncio.sleep(AGENT_DISCOVERY_INTERVAL)
        except Exception as e:
            logger.error(f"Erreur découverte agents: {e}")
            await asyncio.sleep(5)

async def background_health_check():
    """Tâche de fond pour les vérifications de santé"""
    while load_balancer.running:
        try:
            await load_balancer.health_check_agents()
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            await asyncio.sleep(5)

# Gestionnaire de contexte pour l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    await load_balancer.initialize()
    
    # Démarrer les tâches de fond
    discovery_task = asyncio.create_task(background_discovery())
    health_task = asyncio.create_task(background_health_check())
    
    yield
    
    # Arrêt
    await load_balancer.shutdown()
    discovery_task.cancel()
    health_task.cancel()

# Application FastAPI
app = FastAPI(
    title="Swarm Playwright Load Balancer",
    description="Load balancer intelligent pour agents Playwright",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
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
        "version": "1.0.0",
        "status": "running",
        "agents": len(load_balancer.agents),
        "active_tasks": len(load_balancer.active_tasks)
    }

@app.get("/health")
async def health():
    """Endpoint de santé"""
    healthy_agents = len([
        agent for agent in load_balancer.agents.values()
        if agent.status == "healthy"
    ])
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agents": {
            "total": len(load_balancer.agents),
            "healthy": healthy_agents,
            "unhealthy": len(load_balancer.agents) - healthy_agents
        },
        "tasks": {
            "active": len(load_balancer.active_tasks),
            "queued": len(load_balancer.task_queue)
        }
    }

@app.get("/agents")
async def get_agents():
    """Récupère la liste des agents"""
    return {
        "agents": [agent.dict() for agent in load_balancer.agents.values()],
        "count": len(load_balancer.agents)
    }

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Récupère les détails d'un agent spécifique"""
    if agent_id not in load_balancer.agents:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
        
    return load_balancer.agents[agent_id].dict()

@app.post("/execute")
async def execute_task(request: ExecuteRequest):
    """Exécute une tâche sur un agent"""
    
    # Sélection de l'agent
    if request.agent_id:
        # Agent spécifique demandé
        if request.agent_id not in load_balancer.agents:
            raise HTTPException(status_code=404, detail="Agent non trouvé")
        agent = load_balancer.agents[request.agent_id]
        if agent.status != "healthy":
            raise HTTPException(status_code=503, detail="Agent non disponible")
    else:
        # Sélection automatique
        agent = await load_balancer.select_agent(request.task, request.strategy)
        if not agent:
            raise HTTPException(status_code=503, detail="Aucun agent disponible")
    
    # Exécution de la tâche
    result = await load_balancer.execute_task(agent, request.task)
    return result

@app.post("/execute/batch")
async def execute_batch(tasks: List[Dict[str, Any]], strategy: str = "auto"):
    """Exécute plusieurs tâches en parallèle"""
    
    if not tasks:
        raise HTTPException(status_code=400, detail="Aucune tâche fournie")
        
    # Exécuter toutes les tâches en parallèle
    async def execute_single_task(task):
        agent = await load_balancer.select_agent(task, strategy)
        if not agent:
            return {
                "success": False,
                "error": "Aucun agent disponible",
                "task_id": task.get("id")
            }
        return await load_balancer.execute_task(agent, task)
    
    results = await asyncio.gather(
        *[execute_single_task(task) for task in tasks],
        return_exceptions=True
    )
    
    # Traiter les exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "error": str(result),
                "task_id": tasks[i].get("id")
            })
        else:
            processed_results.append(result)
    
    return {
        "results": processed_results,
        "total": len(tasks),
        "successful": sum(1 for r in processed_results if r.get("success")),
        "failed": sum(1 for r in processed_results if not r.get("success"))
    }

@app.get("/tasks")
async def get_tasks():
    """Récupère les tâches actives"""
    return {
        "active_tasks": load_balancer.active_tasks,
        "queued_tasks": [task.dict() for task in load_balancer.task_queue],
        "count": {
            "active": len(load_balancer.active_tasks),
            "queued": len(load_balancer.task_queue)
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Récupère les métriques du load balancer"""
    
    # Calculer les métriques
    total_agents = len(load_balancer.agents)
    healthy_agents = len([a for a in load_balancer.agents.values() if a.status == "healthy"])
    
    # Métriques des tâches
    completed_tasks = len([
        t for t in load_balancer.active_tasks.values() 
        if t.get("status") == "completed"
    ])
    failed_tasks = len([
        t for t in load_balancer.active_tasks.values() 
        if t.get("status") == "failed"
    ])
    running_tasks = len([
        t for t in load_balancer.active_tasks.values() 
        if t.get("status") == "running"
    ])
    
    return {
        "timestamp": datetime.now().isoformat(),
        "agents": {
            "total": total_agents,
            "healthy": healthy_agents,
            "unhealthy": total_agents - healthy_agents,
            "utilization": healthy_agents / max(total_agents, 1)
        },
        "tasks": {
            "completed": completed_tasks,
            "failed": failed_tasks,
            "running": running_tasks,
            "queued": len(load_balancer.task_queue),
            "success_rate": completed_tasks / max(completed_tasks + failed_tasks, 1)
        },
        "performance": {
            "avg_load": sum(a.load for a in load_balancer.agents.values()) / max(total_agents, 1),
            "total_capacity": total_agents * 10,  # Estimation
            "used_capacity": sum(a.load for a in load_balancer.agents.values())
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level=LOG_LEVEL.lower()
    )

