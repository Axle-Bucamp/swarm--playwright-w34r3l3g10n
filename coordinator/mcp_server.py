#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - MCP Server Fixed
Serveur MCP corrigé avec Pydantic et gestion robuste de la découverte d'agents
"""

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse
import uuid

import httpx
from pydantic import ValidationError

# Imports MCP avec gestion d'erreur
try:
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
    MCP_AVAILABLE = True
except ImportError:
    # Fallback si MCP n'est pas disponible
    MCP_AVAILABLE = False
    
    # Classes de fallback pour les tests
    class Server:
        def __init__(self, name: str, version: str = "1.0.0"): pass
        def list_tools(self): return lambda f: f
        def call_tool(self): return lambda f: f
        
    class CallToolResult:
        def __init__(self, content): self.content = content
        
    class TextContent:
        def __init__(self, type: str, text: str): 
            self.type = type
            self.text = text
            
    class Tool:
        def __init__(self, name: str, description: str, inputSchema: dict):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema
            
    class ListToolsResult:
        def __init__(self, tools): self.tools = tools
            
    def stdio_server(): pass

# Imports locaux
from models_pydantic import (
    Agent, Task, ExecutionResult, SwarmExecuteRequest, SwarmExecuteResponse,
    TaskStatus, TaskPriority, AgentStatus, ExecutionStrategy,
    CoordinatorConfig, AgentDiscoveryConfig,
    create_navigate_task, create_search_task, create_social_action_task,
    TaskType, SocialPlatform, SocialAction, UserProfileType, BehaviorPattern, StealthLevel
)

# Configuration avec Pydantic
config = CoordinatorConfig(
    agent_pool_size=int(os.getenv("AGENT_POOL_SIZE", "5")),
    load_balancer_url=os.getenv("LOAD_BALANCER_URL", "http://load-balancer:8080"),
    redis_url=os.getenv("REDIS_URL", "redis://redis:6379"),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    discovery_config=AgentDiscoveryConfig(
        discovery_interval=int(os.getenv("AGENT_DISCOVERY_INTERVAL", "30")),
        health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "10")),
        agent_timeout=int(os.getenv("AGENT_TIMEOUT", "5")),
        max_failed_attempts=int(os.getenv("MAX_FAILED_ATTEMPTS", "3"))
    )
)

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SwarmCoordinator:
    """Coordinateur principal avec gestion robuste des agents"""
    
    def __init__(self, config: CoordinatorConfig = config):
        self.config = config
        self.agent_pool: Dict[str, Agent] = {}
        self.task_queue: List[Task] = []
        self.active_tasks: Dict[str, Task] = {}
        self.client = httpx.AsyncClient(timeout=30.0)
        self.discovery_running = False
        self.last_discovery = 0
        self.failed_discovery_count = 0
        
    async def initialize(self):
        """Initialise le coordinateur avec découverte initiale"""
        logger.info("Initialisation du coordinateur Swarm Playwright")
        
        # Découverte initiale des agents
        await self.discover_agents_once()
        
        # Démarrer la découverte périodique en arrière-plan
        if not self.discovery_running:
            asyncio.create_task(self._background_discovery())
        
    async def discover_agents_once(self) -> bool:
        """Effectue une découverte unique des agents"""
        try:
            logger.debug("Découverte des agents via load balancer...")
            
            response = await self.client.get(
                f"{self.config.load_balancer_url}/agents",
                timeout=self.config.discovery_config.agent_timeout
            )
            
            if response.status_code == 200:
                agents_data = response.json().get("agents", [])
                
                # Convertir en objets Agent Pydantic
                new_agents = {}
                for agent_data in agents_data:
                    try:
                        logger.info(agent_data)
                        agent = Agent(**agent_data)
                        new_agents[agent.id] = agent
                    except ValidationError as e:
                        logger.warning(f"Agent invalide ignoré: {e}")
                        continue
                
                # Mettre à jour le pool d'agents
                self.agent_pool = new_agents
                self.failed_discovery_count = 0
                self.last_discovery = time.time()
                
                logger.info(f"Découvert {len(self.agent_pool)} agents disponibles")
                
                # Log détaillé des agents
                for agent in self.agent_pool.values():
                    logger.debug(f"Agent {agent.id}: {agent.status}, charge: {agent.load_percentage:.1f}%")
                
                return True
            else:
                logger.warning(f"Erreur HTTP lors de la découverte: {response.status_code}")
                self.failed_discovery_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la découverte des agents: {e}")
            self.failed_discovery_count += 1
            return False
    
    async def _background_discovery(self):
        """Tâche de fond pour la découverte périodique d'agents"""
        self.discovery_running = True
        logger.info("Démarrage de la découverte périodique d'agents")
        
        while self.discovery_running:
            try:
                # Attendre l'intervalle de découverte
                await asyncio.sleep(self.config.discovery_config.discovery_interval)
                
                # Effectuer la découverte
                success = await self.discover_agents_once()
                
                # Si trop d'échecs consécutifs, augmenter l'intervalle
                if self.failed_discovery_count >= self.config.discovery_config.max_failed_attempts:
                    logger.warning(f"Trop d'échecs de découverte ({self.failed_discovery_count}), "
                                 f"augmentation de l'intervalle")
                    await asyncio.sleep(self.config.discovery_config.discovery_interval * 2)
                    
            except asyncio.CancelledError:
                logger.info("Découverte périodique arrêtée")
                break
            except Exception as e:
                logger.error(f"Erreur dans la découverte périodique: {e}")
                await asyncio.sleep(5)  # Attente courte en cas d'erreur
        
        self.discovery_running = False
    
    async def stop_discovery(self):
        """Arrête la découverte périodique"""
        self.discovery_running = False
        
    async def select_agent(self, task_type: str = "default") -> Optional[Agent]:
        """Sélectionne un agent optimal pour une tâche donnée"""
        # Si pas d'agents ou découverte ancienne, redécouvrir
        if (not self.agent_pool or 
            time.time() - self.last_discovery > self.config.discovery_config.discovery_interval * 2):
            await self.discover_agents_once()
            
        if not self.agent_pool:
            logger.warning("Aucun agent disponible après découverte")
            return None
            
        # Filtrer les agents disponibles et capables
        available_agents = [
            agent for agent in self.agent_pool.values()
            if agent.is_available and agent.can_handle_task(task_type)
        ]
        
        if not available_agents:
            logger.warning(f"Aucun agent disponible pour le type de tâche: {task_type}")
            return None
            
        # Sélection basée sur la charge et les performances
        def score_agent(agent: Agent) -> float:
            base_score = 100 - agent.load_percentage
            
            # Bonus pour les métriques de performance
            if agent.performance_metrics:
                success_rate = agent.performance_metrics.success_rate
                avg_response_time = agent.performance_metrics.avg_response_time
                
                # Bonus pour taux de succès élevé
                base_score += success_rate * 20
                
                # Malus pour temps de réponse élevé (en ms)
                base_score -= min(avg_response_time / 1000, 10)
                
            return max(base_score, 0)
        
        # Sélectionner l'agent avec le meilleur score
        best_agent = max(available_agents, key=score_agent)
        logger.debug(f"Agent sélectionné: {best_agent.id} (score: {score_agent(best_agent):.1f})")
        
        return best_agent
        
    async def execute_task(self, task: Task) -> ExecutionResult:
        """Exécute une tâche sur un agent sélectionné"""
        start_time = time.time()
        
        # Sélectionner un agent
        agent = await self.select_agent(task.type)
        
        if not agent:
            return ExecutionResult(
                task_id=task.id,
                success=False,
                error="Aucun agent disponible",
                execution_time=time.time() - start_time
            )
            
        try:
            # Marquer la tâche comme active
            task.status = TaskStatus.ASSIGNED
            task.assigned_at = time.time()
            task.agent_id = agent.id
            self.active_tasks[task.id] = task
            
            # Envoi de la tâche à l'agent via le load balancer
            response = await self.client.post(
                f"{self.config.load_balancer_url}/execute",
                json={
                    "agent_id": agent.id,
                    "task": task.dict()
                },
                timeout=task.timeout
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                
                # Mettre à jour le statut de la tâche
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result_data
                
                logger.info(f"Tâche {task.id} exécutée avec succès sur l'agent {agent.id}")
                
                return ExecutionResult(
                    task_id=task.id,
                    success=True,
                    result=result_data,
                    execution_time=execution_time,
                    agent_id=agent.id
                )
            else:
                error_msg = f"Erreur HTTP {response.status_code}"
                task.status = TaskStatus.FAILED
                task.error = error_msg
                
                logger.error(f"Erreur lors de l'exécution de la tâche {task.id}: {error_msg}")
                
                return ExecutionResult(
                    task_id=task.id,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time,
                    agent_id=agent.id
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            task.status = TaskStatus.FAILED
            task.error = error_msg
            
            logger.error(f"Erreur lors de l'exécution de la tâche {task.id}: {error_msg}")
            
            return ExecutionResult(
                task_id=task.id,
                success=False,
                error=error_msg,
                execution_time=execution_time,
                agent_id=agent.id if agent else None
            )
        finally:
            # Nettoyer la tâche active
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
    
    async def execute_swarm(self, request: SwarmExecuteRequest) -> SwarmExecuteResponse:
        """Exécute une tâche en mode swarm avec plusieurs répliques"""
        swarm_id = f"swarm_{int(time.time())}_{random.randint(1000, 9999)}"
        start_time = time.time()
        
        logger.info(f"Démarrage swarm {swarm_id}: {request.replicas} répliques, "
                   f"stratégie {request.strategy}")
        
        # Créer les tâches répliquées
        tasks = []
        for i in range(request.replicas):
            replica_task = Task(
                id=f"{request.task.id}_replica_{i}",
                type=request.task.type,
                payload=request.task.payload.copy(),
                priority=request.task.priority,
                timeout=request.task.timeout,
                max_retries=request.task.max_retries,
                metadata={
                    **request.task.metadata,
                    "replica_id": i,
                    "swarm_id": swarm_id,
                    "total_replicas": request.replicas,
                    "strategy": request.strategy.value
                }
            )
            tasks.append(replica_task)
        
        # Exécuter selon la stratégie
        results = []
        
        if request.strategy == ExecutionStrategy.PARALLEL:
            # Exécution parallèle
            execution_tasks = [self.execute_task(task) for task in tasks]
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
        elif request.strategy == ExecutionStrategy.SEQUENTIAL:
            # Exécution séquentielle
            for task in tasks:
                result = await self.execute_task(task)
                results.append(result)
                
        elif request.strategy == ExecutionStrategy.ROUND_ROBIN:
            # Exécution round-robin (parallèle avec distribution)
            execution_tasks = [self.execute_task(task) for task in tasks]
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Traiter les résultats
        valid_results = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                # Gérer les exceptions
                failed_count += 1
                valid_results.append(ExecutionResult(
                    task_id="unknown",
                    success=False,
                    error=str(result),
                    execution_time=0
                ))
            elif isinstance(result, ExecutionResult):
                valid_results.append(result)
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1
        
        execution_time = time.time() - start_time
        overall_success = successful_count > 0
        
        logger.info(f"Swarm {swarm_id} terminé: {successful_count}/{request.replicas} succès "
                   f"en {execution_time:.2f}s")
        
        return SwarmExecuteResponse(
            swarm_id=swarm_id,
            success=overall_success,
            results=valid_results,
            total_replicas=request.replicas,
            successful_replicas=successful_count,
            failed_replicas=failed_count,
            execution_time=execution_time,
            strategy_used=request.strategy
        )
    
    async def get_status(self) -> Dict[str, Any]:
        """Récupère le statut du coordinateur"""
        # Redécouvrir les agents pour avoir un statut à jour
        await self.discover_agents_once()
        
        healthy_agents = sum(1 for agent in self.agent_pool.values() 
                           if agent.status == AgentStatus.HEALTHY)
        
        return {
            "total_agents": len(self.agent_pool),
            "healthy_agents": healthy_agents,
            "active_tasks": len(self.active_tasks),
            "last_discovery": self.last_discovery,
            "failed_discovery_count": self.failed_discovery_count,
            "discovery_running": self.discovery_running,
            "agents": [agent.dict() for agent in self.agent_pool.values()]
        }

# Instance globale du coordinateur
coordinator = SwarmCoordinator()

# Serveur MCP
if MCP_AVAILABLE:
    server = Server("swarm-playwright-w34r3l3g10n", "2.0.1")
else:
    server = Server("swarm-playwright-w34r3l3g10n", "2.0.1")

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
                            "description": "Profil d'utilisateur",
                            "enum": ["mobile", "desktop", "tablet"],
                            "default": "desktop"
                        },
                        "behavior_pattern": {
                            "type": "string",
                            "description": "Pattern de comportement",
                            "enum": ["casual", "focused", "researcher", "shopper", "social"],
                            "default": "casual"
                        },
                        "stealth_level": {
                            "type": "string",
                            "description": "Niveau de furtivité",
                            "enum": ["low", "medium", "high"],
                            "default": "medium"
                        },
                        "screenshot": {
                            "type": "boolean",
                            "description": "Prendre une capture d'écran",
                            "default": False
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
                            "description": "Moteur de recherche",
                            "enum": ["google", "duckduckgo", "bing"],
                            "default": "duckduckgo"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Nombre maximum de résultats",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="social_action",
                description="Effectue une action sur les réseaux sociaux",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "description": "Plateforme sociale",
                            "enum": ["twitter", "facebook", "instagram", "linkedin", "tiktok", "youtube"]
                        },
                        "action": {
                            "type": "string",
                            "description": "Action à effectuer",
                            "enum": ["like", "comment", "follow", "share", "retweet", "reply"]
                        },
                        "target_url": {
                            "type": "string",
                            "description": "URL cible de l'action"
                        },
                        "content": {
                            "type": "string",
                            "description": "Contenu pour les commentaires/réponses"
                        },
                        "account_id": {
                            "type": "string",
                            "description": "ID du compte à utiliser (optionnel)"
                        }
                    },
                    "required": ["platform", "action", "target_url"]
                }
            ),
            Tool(
                name="swarm_execute",
                description="Exécute une tâche en mode swarm avec plusieurs répliques pour simuler plusieurs utilisateurs réels",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "object",
                            "description": "Tâche à exécuter",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["navigate", "search", "interact", "social_login", "social_action"],
                                    "description": "Type de tâche"
                                },
                                "payload": {
                                    "type": "object",
                                    "description": "Données de la tâche"
                                },
                                "priority": {
                                    "type": "integer",
                                    "description": "Priorité (1=low, 2=normal, 3=high, 4=urgent)",
                                    "default": 2,
                                    "minimum": 1,
                                    "maximum": 4
                                }
                            },
                            "required": ["type", "payload"]
                        },
                        "replicas": {
                            "type": "integer",
                            "description": "Nombre de répliques (utilisateurs simulés)",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 20
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
                description="Récupère le statut des agents et du coordinateur",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Inclure les détails des agents",
                            "default": False
                        }
                    }
                }
            )
        ]
    )

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Gère les appels d'outils"""
    try:
        if name == "navigate_url":
            return await handle_navigate_url(arguments)
        elif name == "search_query":
            return await handle_search_query(arguments)
        elif name == "social_action":
            return await handle_social_action(arguments)
        elif name == "swarm_execute":
            return await handle_swarm_execute(arguments)
        elif name == "get_agent_status":
            return await handle_get_agent_status(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Outil inconnu: {name}"
                )]
            )
    except Exception as e:
        logger.error(f"Erreur dans l'outil {name}: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur lors de l'exécution de {name}: {str(e)}"
            )]
        )

async def handle_navigate_url(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère la navigation vers une URL"""
    url = arguments.get("url")
    user_profile = arguments.get("user_profile", "desktop")
    behavior_pattern = arguments.get("behavior_pattern", "casual")
    stealth_level = arguments.get("stealth_level", "medium")
    screenshot = arguments.get("screenshot", False)
    
    try:
        task = create_navigate_task(
            url=url,
            user_profile=UserProfileType(user_profile),
            behavior_pattern=BehaviorPattern(behavior_pattern),
            stealth_level=StealthLevel(stealth_level),
            screenshot=screenshot
        )
        
        result = await coordinator.execute_task(task)
        
        if result.success:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Navigation vers {url} réussie. Résultat: {json.dumps(result.dict(), indent=2)}"
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Erreur lors de la navigation: {result.error}"
                )]
            )
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur de validation: {e}"
            )]
        )

async def handle_search_query(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère les requêtes de recherche"""
    query = arguments.get("query")
    search_engine = arguments.get("search_engine", "duckduckgo")
    max_results = arguments.get("max_results", 10)
    
    try:
        task = create_search_task(
            query=query,
            search_engine=search_engine,
            max_results=max_results
        )
        
        result = await coordinator.execute_task(task)
        
        if result.success:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Recherche '{query}' effectuée. Résultats: {json.dumps(result.dict(), indent=2)}"
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Erreur lors de la recherche: {result.error}"
                )]
            )
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur de validation: {e}"
            )]
        )

async def handle_social_action(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère les actions sur les réseaux sociaux"""
    platform = arguments.get("platform")
    action = arguments.get("action")
    target_url = arguments.get("target_url")
    content = arguments.get("content")
    account_id = arguments.get("account_id")
    
    try:
        task = create_social_action_task(
            platform=SocialPlatform(platform),
            action=SocialAction(action),
            target_url=target_url,
            content=content,
            account_id=account_id
        )
        
        result = await coordinator.execute_task(task)
        
        if result.success:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Action {action} sur {platform} réussie. Résultat: {json.dumps(result.dict(), indent=2)}"
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Erreur lors de l'action sociale: {result.error}"
                )]
            )
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur de validation: {e}"
            )]
        )

async def handle_swarm_execute(arguments: Dict[str, Any]) -> CallToolResult:
    """Gère l'exécution en mode swarm"""
    try:
        # Valider et créer la requête
        request = SwarmExecuteRequest(**arguments)
        
        # Exécuter le swarm
        response = await coordinator.execute_swarm(request)
        
        # Formater la réponse
        success_rate = (response.successful_replicas / response.total_replicas) * 100
        
        summary = f"""
🎯 **Swarm {response.swarm_id} Terminé**

📊 **Résultats:**
- Répliques totales: {response.total_replicas}
- Succès: {response.successful_replicas}
- Échecs: {response.failed_replicas}
- Taux de succès: {success_rate:.1f}%
- Temps d'exécution: {response.execution_time:.2f}s
- Stratégie: {response.strategy_used}

✅ **Statut global:** {"Succès" if response.success else "Échec"}
"""
        
        # Ajouter les détails des résultats
        if response.results:
            summary += "\n📋 **Détails des résultats:**\n"
            for i, result in enumerate(response.results):
                status = "✅" if result.success else "❌"
                summary += f"{status} Réplique {i+1}: "
                if result.success:
                    summary += f"Succès en {result.execution_time:.2f}s"
                else:
                    summary += f"Échec - {result.error}"
                summary += "\n"
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=summary
            )]
        )
        
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur de validation de la requête swarm: {e}"
            )]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur lors de l'exécution swarm: {e}"
            )]
        )

async def handle_get_agent_status(arguments: Dict[str, Any]) -> CallToolResult:
    """Récupère le statut des agents"""
    detailed = arguments.get("detailed", False)
    
    try:
        status = await coordinator.get_status()
        
        if detailed:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(status, indent=2, default=str)
                )]
            )
        else:
            summary = f"""
🤖 **Statut du Coordinateur**

📊 **Agents:**
- Total: {status['total_agents']}
- Sains: {status['healthy_agents']}
- Tâches actives: {status['active_tasks']}

🔍 **Découverte:**
- Dernière découverte: {time.ctime(status['last_discovery']) if status['last_discovery'] else 'Jamais'}
- Échecs consécutifs: {status['failed_discovery_count']}
- Découverte active: {"Oui" if status['discovery_running'] else "Non"}
"""
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=summary
                )]
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Erreur lors de la récupération du statut: {e}"
            )]
        )

async def main():
    """Point d'entrée principal"""
    # Initialiser le coordinateur
    await coordinator.initialize()

    if MCP_AVAILABLE:
        from mcp.server import NotificationOptions

        experimental_capabilities = {
            "playwright": {
                "trace": True,
                "record_video": False,
                "screenshot_on_failure": True
            },
            "automation": {
                "headless": True,
                "proxy_enabled": True,
                "custom_user_agent": "swarmbot/2.0"
            },
            "diagnostics": {
                "cpu_usage": True,
                "memory_usage": True,
                "network_debug": False
            }
        }
        
        # Démarrer le serveur MCP
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="swarm-playwright-w34r3l3g10n",
                    server_version="2.0.1",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities=experimental_capabilities,
                    ),
                ),
            )
    else:
        logger.info("MCP non disponible, mode test activé")
        # Mode test sans MCP
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt du coordinateur")
    finally:
        # Arrêter la découverte
        if coordinator.discovery_running:
            asyncio.create_task(coordinator.stop_discovery())