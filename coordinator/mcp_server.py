#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - MCP Server
Serveur MCP principal pour la coordination et le load balancing des agents Playwright
"""

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse
from pydantic import BaseModel
import datetime

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)

class Agent(BaseModel):
    id: str
    url: str
    status: str = "unknown"
    load: int = 0
    last_seen: datetime
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

# Configuration
AGENT_POOL_SIZE = int(os.getenv("AGENT_POOL_SIZE", "5"))
LOAD_BALANCER_URL = os.getenv("LOAD_BALANCER_URL", "http://load-balancer:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SwarmCoordinator:
    """Coordinateur principal pour la gestion des agents Playwright"""
    
    def __init__(self):
        self.agent_pool: List[Dict[str, Any]] = []
        self.task_queue: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def initialize(self):
        """Initialise le coordinateur et découvre les agents disponibles"""
        logger.info("Initialisation du coordinateur Swarm Playwright")
        await self.discover_agents()
        
    async def discover_agents(self):
        """Découvre les agents disponibles via le load balancer"""
        try:
            response = await self.client.get(f"{LOAD_BALANCER_URL}/agents")
            if response.status_code == 200:
                self.agent_pool = response.json().get("agents", [])
                logger.info(f"Découvert {len(self.agent_pool)} agents disponibles")
            else:
                logger.warning(f"Impossible de découvrir les agents: {response.status_code}")
        except Exception as e:
            logger.error(f"Erreur lors de la découverte des agents: {e}")
            
    async def select_agent(self, task_type: str = "default") -> Optional[Dict[str, Any]]:
        """Sélectionne un agent optimal pour une tâche donnée"""
        if not self.agent_pool:
            await self.discover_agents()
            
        if not self.agent_pool:
            return None
            
        # Stratégie de sélection: round-robin avec health check
        available_agents = [
            agent for agent in self.agent_pool 
            if agent.get("status") == "healthy"
        ]
        
        if not available_agents:
            logger.warning("Aucun agent sain disponible")
            return None
            
        # Sélection basée sur la charge
        return min(available_agents, key=lambda x: x.get("load", 0))
        
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une tâche sur un agent sélectionné"""
        agent = await self.select_agent(str(task.get("type")))
        
        if not agent:
            return {
                "success": False,
                "error": "Aucun agent disponible",
                "task_id": task.get("id")
            }
            
        try:
            # Envoi de la tâche à l'agent via le load balancer
            response = await self.client.post(
                f"{LOAD_BALANCER_URL}/execute",
                json={
                    "agent_id": agent["id"],
                    "task": task
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Tâche {task.get("id")} exécutée avec succès sur l'agent {agent['id']}")
                return result
            else:
                logger.error(f"Erreur lors de l'exécution de la tâche: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Erreur HTTP {response.status_code}",
                    "task_id": task.get("id")
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la tâche: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task.get("id")
            }

# Instance globale du coordinateur
coordinator = SwarmCoordinator()

# Serveur MCP
server = Server("swarm-playwright-w34r3l3g10n")

@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """Liste les outils disponibles"""
    return ListToolsResult(
        tools=[
            Tool(
                name="navigate_url",
                description="Navigue vers une URL avec un comportement d'utilisateur réel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL à visiter"
                        },
                        "user_profile": {
                            "type": "string",
                            "description": "Profil d'utilisateur (mobile, desktop, tablet)",
                            "enum": ["mobile", "desktop", "tablet"],
                            "default": "desktop"
                        },
                        "behavior_pattern": {
                            "type": "string",
                            "description": "Pattern de comportement (casual, focused, researcher)",
                            "enum": ["casual", "focused", "researcher"],
                            "default": "casual"
                        },
                        "stealth_level": {
                            "type": "string",
                            "description": "Niveau de furtivité (low, medium, high)",
                            "enum": ["low", "medium", "high"],
                            "default": "medium"
                        }
                    },
                    "required": ["url"]
                }
            ),
            Tool(
                name="search_query",
                description="Effectue une recherche avec un comportement humain réaliste",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Requête de recherche"
                        },
                        "search_engine": {
                            "type": "string",
                            "description": "Moteur de recherche à utiliser",
                            "enum": ["google", "duckduckgo", "bing"],
                            "default": "duckduckgo"
                        },
                        "user_profile": {
                            "type": "string",
                            "description": "Profil d'utilisateur",
                            "enum": ["mobile", "desktop", "tablet"],
                            "default": "desktop"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Nombre maximum de résultats à récupérer",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="interact_page",
                description="Interagit avec une page web de manière naturelle",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL de la page"
                        },
                        "actions": {
                            "type": "array",
                            "description": "Liste des actions à effectuer",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["click", "type", "scroll", "wait", "screenshot"]
                                    },
                                    "selector": {
                                        "type": "string",
                                        "description": "Sélecteur CSS pour l'élément"
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Texte à saisir (pour type)"
                                    },
                                    "duration": {
                                        "type": "integer",
                                        "description": "Durée en millisecondes (pour wait)"
                                    }
                                },
                                "required": ["type"]
                            }
                        },
                        "user_profile": {
                            "type": "string",
                            "enum": ["mobile", "desktop", "tablet"],
                            "default": "desktop"
                        }
                    },
                    "required": ["url", "actions"]
                }
            ),
            Tool(
                name="swarm_execute",
                description="Exécute une tâche sur plusieurs agents en parallèle",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "object",
                            "description": """
                                    Dict Tâche à exécuter class Task(BaseModel):
                                        id: str
                                        type: str
                                        payload: Dict[str, Any]
                                        priority: int = 1
                                        timeout: int = 30
                                        retry_count: int = 0
                                        max_retries: int = 3
                            """
                        },
                        "replicas": {
                            "type": "integer",
                            "description": "Nombre de répliques à exécuter",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 10
                        },
                        "strategy": {
                            "type": "string",
                            "description": "Stratégie d'exécution",
                            "enum": ["parallel", "sequential", "round_robin"],
                            "default": "parallel"
                        }
                    },
                    "required": ["task"]
                }
            ),
            Tool(
                name="get_agent_status",
                description="Récupère le statut des agents du swarm",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Inclure les détails de performance",
                            "default": False
                        }
                    }
                }
            )
        ]
    )

@server.call_tool()
async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
    """Gère les appels d'outils"""
    
    try:
        if request.name == "navigate_url":
            return await handle_navigate_url(request.arguments)
        elif request.name == "search_query":
            return await handle_search_query(request.arguments)
        elif request.name == "interact_page":
            return await handle_interact_page(request.arguments)
        elif request.name == "swarm_execute":
            return await handle_swarm_execute(request.arguments)
        elif request.name == "get_agent_status":
            return await handle_get_agent_status(request.arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Outil inconnu: {request.name}")]
            )
            
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de l'outil {request.name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Erreur: {str(e)}")]
        )

async def handle_navigate_url(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère la navigation vers une URL"""
    url = arguments.get("url")
    user_profile = arguments.get("user_profile", "desktop")
    behavior_pattern = arguments.get("behavior_pattern", "casual")
    stealth_level = arguments.get("stealth_level", "medium")
    
    task = {
        "id": f"nav_{int(time.time())}_{random.randint(1000, 9999)}",
        "type": "navigate",
        "url": url,
        "user_profile": user_profile,
        "behavior_pattern": behavior_pattern,
        "stealth_level": stealth_level,
        "timestamp": time.time()
    }
    
    result = await coordinator.execute_task(task)
    
    if result.get("success"):
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Navigation réussie vers {url}. Résultat: {json.dumps(result, indent=2)}"
            )]
        )
    else:
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Erreur lors de la navigation: {result.get('error', 'Erreur inconnue')}"
            )]
        )

async def handle_search_query(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère les requêtes de recherche"""
    query = arguments.get("query")
    search_engine = arguments.get("search_engine", "duckduckgo")
    user_profile = arguments.get("user_profile", "desktop")
    max_results = arguments.get("max_results", 10)
    
    task = {
        "id": f"search_{int(time.time())}_{random.randint(1000, 9999)}",
        "type": "search",
        "query": query,
        "search_engine": search_engine,
        "user_profile": user_profile,
        "max_results": max_results,
        "timestamp": time.time()
    }
    
    result = await coordinator.execute_task(task)
    
    if result.get("success"):
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Recherche effectuée pour '{query}'. Résultats: {json.dumps(result, indent=2)}"
            )]
        )
    else:
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Erreur lors de la recherche: {result.get('error', 'Erreur inconnue')}"
            )]
        )

async def handle_interact_page(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère les interactions avec une page"""
    url = arguments.get("url")
    actions = arguments.get("actions", [])
    user_profile = arguments.get("user_profile", "desktop")
    
    task = {
        "id": f"interact_{int(time.time())}_{random.randint(1000, 9999)}",
        "type": "interact",
        "url": url,
        "actions": actions,
        "user_profile": user_profile,
        "timestamp": time.time()
    }
    
    result = await coordinator.execute_task(task)
    
    if result.get("success"):
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Interactions effectuées sur {url}. Résultat: {json.dumps(result, indent=2)}"
            )]
        )
    else:
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Erreur lors des interactions: {result.get('error', 'Erreur inconnue')}"
            )]
        )

async def handle_swarm_execute(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère l'exécution en swarm"""
    task = arguments.get("task")
    replicas = arguments.get("replicas", 3)
    strategy = arguments.get("strategy", "parallel")
    
    # Créer des tâches répliquées
    tasks = []
    for i in range(replicas):
        replica_task = task.copy()
        replica_task["id"] = f"swarm_{int(time.time())}_{i}_{random.randint(1000, 9999)}"
        replica_task["replica_id"] = i
        replica_task["timestamp"] = time.time()
        tasks.append(replica_task)
    
    # Exécuter selon la stratégie
    if strategy == "parallel":
        results = await asyncio.gather(
            *[coordinator.execute_task(t) for t in tasks],
            return_exceptions=True
        )
    elif strategy == "sequential":
        results = []
        for task in tasks:
            result = await coordinator.execute_task(task)
            results.append(result)
    else:  # round_robin
        results = []
        for task in tasks:
            result = await coordinator.execute_task(task)
            results.append(result)
            await asyncio.sleep(0.5)  # Délai entre les tâches
    
    # Analyser les résultats
    successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    failed = len(results) - successful
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Exécution swarm terminée. Succès: {successful}/{len(results)}, Échecs: {failed}. Résultats: {json.dumps(results, indent=2)}"
        )]
    )

async def handle_get_agent_status(arguments: Dict[str, Any]) -> CallToolResult:
    """Récupère le statut des agents"""
    detailed = arguments.get("detailed", False)
    
    await coordinator.discover_agents()
    
    status = {
        "total_agents": len(coordinator.agent_pool),
        "healthy_agents": len([a for a in coordinator.agent_pool if a.get("status") == "healthy"]),
        "active_tasks": len(coordinator.active_tasks),
        "timestamp": time.time()
    }
    
    if detailed:
        status["agents"] = coordinator.agent_pool
        status["active_tasks_details"] = coordinator.active_tasks
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Statut du swarm: {json.dumps(status, indent=2)}"
        )]
    )

async def main():
    """Point d'entrée principal"""
    # Initialiser le coordinateur
    await coordinator.initialize()
    
    # Démarrer le serveur MCP
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="swarm-playwright-w34r3l3g10n",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())

