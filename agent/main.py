#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - Agent Server
Serveur FastAPI pour l'agent Playwright avec API REST
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright_agent import PlaywrightAgent
from user_profiles import UserProfileFactory, DeviceType, BehaviorPattern

# Configuration
AGENT_ID = os.getenv("AGENT_ID", str(uuid.uuid4()))
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "300"))  # 5 minutes
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Modèles Pydantic
class TaskRequest(BaseModel):
    id: Optional[str] = None
    type: str
    payload: Dict[str, Any]
    timeout: Optional[int] = TASK_TIMEOUT
    user_profile: Optional[Dict[str, Any]] = None

class NavigateRequest(BaseModel):
    url: str
    wait_for: str = "networkidle"
    user_profile: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    search_engine: str = "duckduckgo"
    max_results: int = 10
    user_profile: Optional[Dict[str, Any]] = None

class InteractRequest(BaseModel):
    url: str
    actions: List[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]] = None

class ScrollRequest(BaseModel):
    direction: str = "down"
    amount: Optional[int] = None

class ElementInteractionRequest(BaseModel):
    selector: str
    action: str
    kwargs: Dict[str, Any] = {}

# Gestionnaire d'agents
class AgentManager:
    """Gestionnaire des agents Playwright"""
    
    def __init__(self):
        self.agents: Dict[str, PlaywrightAgent] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.agent_pool_size = MAX_CONCURRENT_TASKS
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_session_time": 0,
            "avg_response_time": 0
        }
        
    async def initialize(self):
        """Initialise le gestionnaire d'agents"""
        logger.info(f"Initialisation du gestionnaire d'agents (ID: {AGENT_ID})")
        
        # Pré-créer quelques agents pour réduire la latence
        for i in range(min(2, self.agent_pool_size)):
            agent_id = f"{AGENT_ID}_pool_{i}"
            agent = PlaywrightAgent(agent_id)
            
            try:
                profile = UserProfileFactory.create_random_profile()
                await agent.initialize(profile)
                self.agents[agent_id] = agent
                logger.info(f"Agent de pool créé: {agent_id}")
            except Exception as e:
                logger.error(f"Erreur création agent de pool {agent_id}: {e}")
                
    async def get_or_create_agent(self, user_profile: Optional[Dict[str, Any]] = None) -> PlaywrightAgent:
        """Récupère ou crée un agent disponible"""
        
        # Chercher un agent libre
        for agent_id, agent in self.agents.items():
            if agent_id not in self.active_tasks:
                logger.debug(f"Réutilisation de l'agent: {agent_id}")
                return agent
                
        # Créer un nouvel agent si nécessaire
        if len(self.agents) < self.agent_pool_size:
            agent_id = f"{AGENT_ID}_{len(self.agents)}_{int(time.time())}"
            agent = PlaywrightAgent(agent_id)
            
            # Créer le profil utilisateur
            if user_profile:
                profile = self._create_profile_from_dict(user_profile)
            else:
                profile = UserProfileFactory.create_random_profile()
                
            await agent.initialize(profile)
            self.agents[agent_id] = agent
            logger.info(f"Nouvel agent créé: {agent_id}")
            return agent
            
        # Attendre qu'un agent se libère
        for _ in range(30):  # Attendre max 30 secondes
            await asyncio.sleep(1)
            for agent_id, agent in self.agents.items():
                if agent_id not in self.active_tasks:
                    return agent
                    
        raise HTTPException(status_code=503, detail="Aucun agent disponible")
        
    def _create_profile_from_dict(self, profile_data: Dict[str, Any]):
        """Crée un profil utilisateur à partir d'un dictionnaire"""
        device_type = DeviceType(profile_data.get("device_type", "desktop"))
        behavior_pattern = BehaviorPattern(profile_data.get("behavior_pattern", "casual"))
        
        return UserProfileFactory.create_profile(device_type, behavior_pattern)
        
    async def execute_task(self, task: TaskRequest) -> Dict[str, Any]:
        """Exécute une tâche sur un agent"""
        task_id = task.id or str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Récupérer un agent
            agent = await self.get_or_create_agent(task.user_profile)
            
            # Marquer la tâche comme active
            self.active_tasks[task_id] = {
                "agent_id": agent.agent_id,
                "task_type": task.type,
                "start_time": start_time,
                "status": "running"
            }
            
            # Exécuter la tâche selon le type
            if task.type == "navigate":
                result = await agent.navigate_to(
                    task.payload["url"],
                    task.payload.get("wait_for", "networkidle")
                )
            elif task.type == "search":
                result = await agent.search_query(
                    task.payload["query"],
                    task.payload.get("search_engine", "duckduckgo")
                )
            elif task.type == "interact":
                result = await self._execute_interactions(agent, task.payload)
            elif task.type == "scroll":
                result = await agent.scroll_page(
                    task.payload.get("direction", "down"),
                    task.payload.get("amount")
                )
            elif task.type == "screenshot":
                result = await agent.take_screenshot(task.payload.get("path"))
            elif task.type == "get_content":
                result = await agent.get_page_content()
            else:
                result = {"success": False, "error": f"Type de tâche non supporté: {task.type}"}
                
            # Calculer les métriques
            execution_time = time.time() - start_time
            
            # Mettre à jour les métriques
            if result.get("success"):
                self.metrics["tasks_completed"] += 1
            else:
                self.metrics["tasks_failed"] += 1
                
            self.metrics["avg_response_time"] = (
                (self.metrics["avg_response_time"] * (self.metrics["tasks_completed"] + self.metrics["tasks_failed"] - 1) + execution_time) /
                (self.metrics["tasks_completed"] + self.metrics["tasks_failed"])
            )
            
            # Ajouter les métadonnées
            result.update({
                "task_id": task_id,
                "agent_id": agent.agent_id,
                "execution_time": execution_time,
                "timestamp": time.time()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la tâche {task_id}: {e}")
            self.metrics["tasks_failed"] += 1
            
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        finally:
            # Libérer la tâche
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
    async def _execute_interactions(self, agent: PlaywrightAgent, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une série d'interactions"""
        url = payload.get("url")
        actions = payload.get("actions", [])
        
        results = []
        
        # Naviguer vers l'URL si spécifiée
        if url:
            nav_result = await agent.navigate_to(url)
            results.append({"action": "navigate", "result": nav_result})
            
            if not nav_result.get("success"):
                return {
                    "success": False,
                    "error": "Échec de la navigation",
                    "results": results
                }
                
        # Exécuter les actions
        for action in actions:
            action_type = action.get("type")
            
            try:
                if action_type == "click":
                    result = await agent.interact_with_element(
                        action["selector"], "click"
                    )
                elif action_type == "type":
                    result = await agent.interact_with_element(
                        action["selector"], "type", text=action["text"]
                    )
                elif action_type == "scroll":
                    result = await agent.scroll_page(
                        action.get("direction", "down"),
                        action.get("amount")
                    )
                elif action_type == "wait":
                    duration = action.get("duration", 1000) / 1000  # Convertir en secondes
                    await asyncio.sleep(duration)
                    result = {"success": True, "action": "wait", "duration": duration}
                elif action_type == "screenshot":
                    result = await agent.take_screenshot(action.get("path"))
                else:
                    result = {"success": False, "error": f"Action non supportée: {action_type}"}
                    
                results.append({"action": action_type, "result": result})
                
                # Arrêter en cas d'échec critique
                if not result.get("success") and action.get("critical", False):
                    break
                    
            except Exception as e:
                error_result = {"success": False, "error": str(e)}
                results.append({"action": action_type, "result": error_result})
                
                if action.get("critical", False):
                    break
                    
        # Déterminer le succès global
        success = all(r["result"].get("success", False) for r in results if r.get("result"))
        
        return {
            "success": success,
            "results": results,
            "actions_count": len(results)
        }
        
    async def cleanup_agents(self):
        """Nettoie les agents inactifs"""
        current_time = time.time()
        agents_to_remove = []
        
        for agent_id, agent in self.agents.items():
            # Vérifier si l'agent est inactif depuis trop longtemps
            if agent_id not in self.active_tasks:
                stats = agent.get_session_stats()
                session_duration = stats.get("session_duration", 0)
                
                # Fermer les agents inactifs depuis plus de 30 minutes
                if session_duration > 1800:  # 30 minutes
                    agents_to_remove.append(agent_id)
                    
        # Fermer les agents marqués pour suppression
        for agent_id in agents_to_remove:
            try:
                await self.agents[agent_id].close()
                del self.agents[agent_id]
                logger.info(f"Agent inactif fermé: {agent_id}")
            except Exception as e:
                logger.error(f"Erreur fermeture agent {agent_id}: {e}")
                
    async def shutdown(self):
        """Arrêt propre du gestionnaire"""
        logger.info("Arrêt du gestionnaire d'agents")
        
        # Fermer tous les agents
        for agent_id, agent in self.agents.items():
            try:
                await agent.close()
                logger.info(f"Agent fermé: {agent_id}")
            except Exception as e:
                logger.error(f"Erreur fermeture agent {agent_id}: {e}")
                
        self.agents.clear()
        self.active_tasks.clear()

# Instance globale du gestionnaire
agent_manager = AgentManager()

# Tâche de nettoyage périodique
async def cleanup_task():
    """Tâche de nettoyage périodique"""
    while True:
        try:
            await asyncio.sleep(300)  # Toutes les 5 minutes
            await agent_manager.cleanup_agents()
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")

# Gestionnaire de contexte pour l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    await agent_manager.initialize()
    
    # Démarrer la tâche de nettoyage
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    
    yield
    
    # Arrêt
    cleanup_task_handle.cancel()
    await agent_manager.shutdown()

# Application FastAPI
app = FastAPI(
    title="Swarm Playwright Agent",
    description="Agent Playwright avec simulation de comportements humains",
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
        "service": "Swarm Playwright Agent",
        "version": "1.0.0",
        "agent_id": AGENT_ID,
        "status": "running",
        "active_agents": len(agent_manager.agents),
        "active_tasks": len(agent_manager.active_tasks)
    }

@app.get("/health")
async def health():
    """Endpoint de santé"""
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "timestamp": time.time(),
        "agents": {
            "total": len(agent_manager.agents),
            "active": len(agent_manager.active_tasks),
            "max_concurrent": MAX_CONCURRENT_TASKS
        },
        "metrics": agent_manager.metrics,
        "capabilities": [
            "navigate", "search", "interact", "scroll", 
            "screenshot", "get_content", "human_behavior"
        ],
        "load": len(agent_manager.active_tasks)
    }

@app.post("/execute")
async def execute_task(task: TaskRequest):
    """Exécute une tâche générique"""
    return await agent_manager.execute_task(task)

@app.post("/navigate")
async def navigate(request: NavigateRequest):
    """Navigue vers une URL"""
    task = TaskRequest(
        type="navigate",
        payload={
            "url": request.url,
            "wait_for": request.wait_for
        },
        user_profile=request.user_profile
    )
    return await agent_manager.execute_task(task)

@app.post("/search")
async def search(request: SearchRequest):
    """Effectue une recherche"""
    task = TaskRequest(
        type="search",
        payload={
            "query": request.query,
            "search_engine": request.search_engine,
            "max_results": request.max_results
        },
        user_profile=request.user_profile
    )
    return await agent_manager.execute_task(task)

@app.post("/interact")
async def interact(request: InteractRequest):
    """Interagit avec une page"""
    task = TaskRequest(
        type="interact",
        payload={
            "url": request.url,
            "actions": request.actions
        },
        user_profile=request.user_profile
    )
    return await agent_manager.execute_task(task)

@app.post("/scroll")
async def scroll(request: ScrollRequest):
    """Effectue un scroll"""
    task = TaskRequest(
        type="scroll",
        payload={
            "direction": request.direction,
            "amount": request.amount
        }
    )
    return await agent_manager.execute_task(task)

@app.post("/screenshot")
async def screenshot(path: Optional[str] = None):
    """Prend une capture d'écran"""
    task = TaskRequest(
        type="screenshot",
        payload={"path": path}
    )
    return await agent_manager.execute_task(task)

@app.get("/content")
async def get_content():
    """Récupère le contenu de la page actuelle"""
    task = TaskRequest(
        type="get_content",
        payload={}
    )
    return await agent_manager.execute_task(task)

@app.get("/agents")
async def get_agents():
    """Récupère la liste des agents"""
    agents_info = []
    
    for agent_id, agent in agent_manager.agents.items():
        stats = agent.get_session_stats()
        agents_info.append({
            "agent_id": agent_id,
            "status": "active" if agent_id in agent_manager.active_tasks else "idle",
            "stats": stats
        })
        
    return {
        "agents": agents_info,
        "total": len(agent_manager.agents),
        "active": len(agent_manager.active_tasks)
    }

@app.get("/metrics")
async def get_metrics():
    """Récupère les métriques détaillées"""
    return {
        "agent_id": AGENT_ID,
        "timestamp": time.time(),
        "metrics": agent_manager.metrics,
        "agents": {
            "total": len(agent_manager.agents),
            "active": len(agent_manager.active_tasks),
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "utilization": len(agent_manager.active_tasks) / MAX_CONCURRENT_TASKS
        },
        "tasks": {
            "active": len(agent_manager.active_tasks),
            "completed": agent_manager.metrics["tasks_completed"],
            "failed": agent_manager.metrics["tasks_failed"],
            "success_rate": (
                agent_manager.metrics["tasks_completed"] / 
                max(1, agent_manager.metrics["tasks_completed"] + agent_manager.metrics["tasks_failed"])
            )
        }
    }

@app.delete("/agents/{agent_id}")
async def close_agent(agent_id: str):
    """Ferme un agent spécifique"""
    if agent_id not in agent_manager.agents:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
        
    if agent_id in agent_manager.active_tasks:
        raise HTTPException(status_code=409, detail="Agent occupé")
        
    try:
        await agent_manager.agents[agent_id].close()
        del agent_manager.agents[agent_id]
        
        return {
            "success": True,
            "message": f"Agent {agent_id} fermé avec succès"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur fermeture agent: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=LOG_LEVEL.lower()
    )

