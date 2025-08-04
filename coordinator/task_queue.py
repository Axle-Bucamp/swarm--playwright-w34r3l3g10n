#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - Task Queue
Système de queue de tâches distribuées avec Redis pour la coordination des agents
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

# Configuration
REDIS_URL = "redis://redis:6379"
TASK_TIMEOUT = 300  # 5 minutes
RETRY_DELAY = 60    # 1 minute
MAX_RETRIES = 3

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Task:
    """Représentation d'une tâche"""
    id: str
    type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = 0
    assigned_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    agent_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    timeout: int = TASK_TIMEOUT
    dependencies: List[str] = []
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la tâche en dictionnaire"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Crée une tâche à partir d'un dictionnaire"""
        data = data.copy()
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        return cls(**data)

class TaskQueue:
    """Queue de tâches distribuées avec Redis"""
    
    def __init__(self, redis_url: str = REDIS_URL, namespace: str = "swarm_playwright"):
        self.redis_url = redis_url
        self.namespace = namespace
        self.redis: Optional[Redis] = None
        
        # Clés Redis
        self.keys = {
            'pending': f"{namespace}:tasks:pending",
            'assigned': f"{namespace}:tasks:assigned",
            'running': f"{namespace}:tasks:running",
            'completed': f"{namespace}:tasks:completed",
            'failed': f"{namespace}:tasks:failed",
            'task_data': f"{namespace}:tasks:data",
            'agent_heartbeat': f"{namespace}:agents:heartbeat",
            'agent_tasks': f"{namespace}:agents:tasks",
            'task_dependencies': f"{namespace}:tasks:dependencies",
            'task_results': f"{namespace}:tasks:results",
            'metrics': f"{namespace}:metrics"
        }
        
        # Callbacks
        self.task_callbacks: Dict[str, List[Callable]] = {
            'on_task_created': [],
            'on_task_assigned': [],
            'on_task_started': [],
            'on_task_completed': [],
            'on_task_failed': [],
            'on_task_cancelled': []
        }
        
    async def initialize(self):
        """Initialise la connexion Redis"""
        self.redis = redis.from_url(self.redis_url)
        await self.redis.ping()
        logger.info("Connexion Redis établie pour la queue de tâches")
        
    async def close(self):
        """Ferme la connexion Redis"""
        if self.redis:
            await self.redis.close()
            
    def add_callback(self, event: str, callback: Callable):
        """Ajoute un callback pour un événement"""
        if event in self.task_callbacks:
            self.task_callbacks[event].append(callback)
            
    async def _trigger_callbacks(self, event: str, task: Task):
        """Déclenche les callbacks pour un événement"""
        for callback in self.task_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Erreur dans le callback {event}: {e}")
                
    async def submit_task(self, task: Task) -> str:
        """Soumet une nouvelle tâche"""
        if not task.id:
            task.id = str(uuid.uuid4())
            
        # Sauvegarder les données de la tâche
        await self.redis.hset(
            self.keys['task_data'],
            task.id,
            json.dumps(task.to_dict())
        )
        
        # Ajouter à la queue selon la priorité
        priority_score = task.priority.value * 1000000 + (1000000 - int(task.created_at))
        await self.redis.zadd(
            self.keys['pending'],
            {task.id: priority_score}
        )
        
        # Gérer les dépendances
        if task.dependencies:
            await self.redis.sadd(
                f"{self.keys['task_dependencies']}:{task.id}",
                *task.dependencies
            )
            
        # Mettre à jour les métriques
        await self._update_metrics('tasks_submitted', 1)
        
        # Déclencher les callbacks
        await self._trigger_callbacks('on_task_created', task)
        
        logger.info(f"Tâche soumise: {task.id} (type: {task.type}, priorité: {task.priority.name})")
        return task.id
        
    async def get_next_task(self, agent_id: str, capabilities: List[str] = None) -> Optional[Task]:
        """Récupère la prochaine tâche disponible pour un agent"""
        
        # Mettre à jour le heartbeat de l'agent
        await self._update_agent_heartbeat(agent_id)
        
        # Récupérer les tâches par ordre de priorité
        task_ids = await self.redis.zrevrange(self.keys['pending'], 0, 100)
        
        for task_id in task_ids:
            task_data = await self.redis.hget(self.keys['task_data'], task_id)
            if not task_data:
                # Nettoyer les tâches orphelines
                await self.redis.zrem(self.keys['pending'], task_id)
                continue
                
            task = Task.from_dict(json.loads(task_data))
            
            # Vérifier les capacités requises
            if capabilities and task.metadata.get('required_capabilities'):
                required = task.metadata['required_capabilities']
                if not all(cap in capabilities for cap in required):
                    continue
                    
            # Vérifier les dépendances
            if await self._check_dependencies(task):
                # Assigner la tâche
                await self._assign_task(task, agent_id)
                return task
                
        return None
        
    async def _check_dependencies(self, task: Task) -> bool:
        """Vérifie si les dépendances d'une tâche sont satisfaites"""
        if not task.dependencies:
            return True
            
        dependency_key = f"{self.keys['task_dependencies']}:{task.id}"
        
        # Vérifier chaque dépendance
        for dep_id in task.dependencies:
            dep_data = await self.redis.hget(self.keys['task_data'], dep_id)
            if not dep_data:
                continue
                
            dep_task = Task.from_dict(json.loads(dep_data))
            if dep_task.status != TaskStatus.COMPLETED:
                return False
                
        return True
        
    async def _assign_task(self, task: Task, agent_id: str):
        """Assigne une tâche à un agent"""
        task.status = TaskStatus.ASSIGNED
        task.assigned_at = time.time()
        task.agent_id = agent_id
        
        # Déplacer de pending vers assigned
        await self.redis.zrem(self.keys['pending'], task.id)
        await self.redis.zadd(
            self.keys['assigned'],
            {task.id: task.assigned_at}
        )
        
        # Associer la tâche à l'agent
        await self.redis.sadd(f"{self.keys['agent_tasks']}:{agent_id}", task.id)
        
        # Sauvegarder les modifications
        await self.redis.hset(
            self.keys['task_data'],
            task.id,
            json.dumps(task.to_dict())
        )
        
        # Déclencher les callbacks
        await self._trigger_callbacks('on_task_assigned', task)
        
        logger.info(f"Tâche {task.id} assignée à l'agent {agent_id}")
        
    async def start_task(self, task_id: str, agent_id: str) -> bool:
        """Marque une tâche comme démarrée"""
        task_data = await self.redis.hget(self.keys['task_data'], task_id)
        if not task_data:
            return False
            
        task = Task.from_dict(json.loads(task_data))
        
        if task.agent_id != agent_id or task.status != TaskStatus.ASSIGNED:
            return False
            
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        # Déplacer vers running
        await self.redis.zrem(self.keys['assigned'], task_id)
        await self.redis.zadd(
            self.keys['running'],
            {task_id: task.started_at}
        )
        
        # Sauvegarder
        await self.redis.hset(
            self.keys['task_data'],
            task_id,
            json.dumps(task.to_dict())
        )
        
        # Déclencher les callbacks
        await self._trigger_callbacks('on_task_started', task)
        
        logger.info(f"Tâche {task_id} démarrée par l'agent {agent_id}")
        return True
        
    async def complete_task(self, task_id: str, agent_id: str, result: Dict[str, Any]) -> bool:
        """Marque une tâche comme terminée"""
        task_data = await self.redis.hget(self.keys['task_data'], task_id)
        if not task_data:
            return False
            
        task = Task.from_dict(json.loads(task_data))
        
        if task.agent_id != agent_id or task.status != TaskStatus.RUNNING:
            return False
            
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        
        # Déplacer vers completed
        await self.redis.zrem(self.keys['running'], task_id)
        await self.redis.zadd(
            self.keys['completed'],
            {task_id: task.completed_at}
        )
        
        # Sauvegarder le résultat
        await self.redis.hset(
            self.keys['task_results'],
            task_id,
            json.dumps(result)
        )
        
        # Nettoyer l'association agent-tâche
        await self.redis.srem(f"{self.keys['agent_tasks']}:{agent_id}", task_id)
        
        # Sauvegarder
        await self.redis.hset(
            self.keys['task_data'],
            task_id,
            json.dumps(task.to_dict())
        )
        
        # Mettre à jour les métriques
        execution_time = task.completed_at - (task.started_at or task.assigned_at or task.created_at)
        await self._update_metrics('tasks_completed', 1)
        await self._update_metrics('total_execution_time', execution_time)
        
        # Déclencher les callbacks
        await self._trigger_callbacks('on_task_completed', task)
        
        logger.info(f"Tâche {task_id} terminée par l'agent {agent_id}")
        return True
        
    async def fail_task(self, task_id: str, agent_id: str, error: str, retry: bool = True) -> bool:
        """Marque une tâche comme échouée"""
        task_data = await self.redis.hget(self.keys['task_data'], task_id)
        if not task_data:
            return False
            
        task = Task.from_dict(json.loads(task_data))
        
        if task.agent_id != agent_id:
            return False
            
        task.error = error
        task.retry_count += 1
        
        # Nettoyer l'association agent-tâche
        await self.redis.srem(f"{self.keys['agent_tasks']}:{agent_id}", task_id)
        
        # Décider si on doit réessayer
        if retry and task.retry_count <= task.max_retries:
            task.status = TaskStatus.RETRY
            task.agent_id = None
            task.assigned_at = None
            task.started_at = None
            
            # Remettre en queue avec délai
            retry_time = time.time() + RETRY_DELAY * task.retry_count
            await self.redis.zadd(
                self.keys['pending'],
                {task_id: retry_time}
            )
            
            logger.info(f"Tâche {task_id} programmée pour retry #{task.retry_count}")
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            
            # Déplacer vers failed
            await self.redis.zadd(
                self.keys['failed'],
                {task_id: task.completed_at}
            )
            
            await self._update_metrics('tasks_failed', 1)
            logger.error(f"Tâche {task_id} échouée définitivement: {error}")
            
        # Nettoyer des queues actives
        await self.redis.zrem(self.keys['assigned'], task_id)
        await self.redis.zrem(self.keys['running'], task_id)
        
        # Sauvegarder
        await self.redis.hset(
            self.keys['task_data'],
            task_id,
            json.dumps(task.to_dict())
        )
        
        # Déclencher les callbacks
        await self._trigger_callbacks('on_task_failed', task)
        
        return True
        
    async def cancel_task(self, task_id: str) -> bool:
        """Annule une tâche"""
        task_data = await self.redis.hget(self.keys['task_data'], task_id)
        if not task_data:
            return False
            
        task = Task.from_dict(json.loads(task_data))
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
            
        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()
        
        # Nettoyer de toutes les queues
        await self.redis.zrem(self.keys['pending'], task_id)
        await self.redis.zrem(self.keys['assigned'], task_id)
        await self.redis.zrem(self.keys['running'], task_id)
        
        # Nettoyer l'association agent si nécessaire
        if task.agent_id:
            await self.redis.srem(f"{self.keys['agent_tasks']}:{task.agent_id}", task_id)
            
        # Sauvegarder
        await self.redis.hset(
            self.keys['task_data'],
            task_id,
            json.dumps(task.to_dict())
        )
        
        # Déclencher les callbacks
        await self._trigger_callbacks('on_task_cancelled', task)
        
        logger.info(f"Tâche {task_id} annulée")
        return True
        
    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Récupère le statut d'une tâche"""
        task_data = await self.redis.hget(self.keys['task_data'], task_id)
        if not task_data:
            return None
            
        return Task.from_dict(json.loads(task_data))
        
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le résultat d'une tâche"""
        result_data = await self.redis.hget(self.keys['task_results'], task_id)
        if not result_data:
            return None
            
        return json.loads(result_data)
        
    async def _update_agent_heartbeat(self, agent_id: str):
        """Met à jour le heartbeat d'un agent"""
        await self.redis.hset(
            self.keys['agent_heartbeat'],
            agent_id,
            time.time()
        )
        
    async def _update_metrics(self, metric: str, value: float):
        """Met à jour une métrique"""
        await self.redis.hincrby(self.keys['metrics'], metric, int(value))
        
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la queue"""
        stats = {
            'pending': await self.redis.zcard(self.keys['pending']),
            'assigned': await self.redis.zcard(self.keys['assigned']),
            'running': await self.redis.zcard(self.keys['running']),
            'completed': await self.redis.zcard(self.keys['completed']),
            'failed': await self.redis.zcard(self.keys['failed']),
        }
        
        # Métriques additionnelles
        metrics = await self.redis.hgetall(self.keys['metrics'])
        for key, value in metrics.items():
            stats[key] = int(value)
            
        # Agents actifs
        heartbeats = await self.redis.hgetall(self.keys['agent_heartbeat'])
        current_time = time.time()
        active_agents = sum(
            1 for timestamp in heartbeats.values()
            if current_time - float(timestamp) < 300  # 5 minutes
        )
        stats['active_agents'] = active_agents
        
        return stats
        
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Nettoie les anciennes tâches terminées"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # Nettoyer les tâches terminées anciennes
        for queue_key in [self.keys['completed'], self.keys['failed']]:
            old_tasks = await self.redis.zrangebyscore(queue_key, 0, cutoff_time)
            
            if old_tasks:
                # Supprimer des queues
                await self.redis.zremrangebyscore(queue_key, 0, cutoff_time)
                
                # Supprimer les données
                await self.redis.hdel(self.keys['task_data'], *old_tasks)
                await self.redis.hdel(self.keys['task_results'], *old_tasks)
                
                logger.info(f"Nettoyé {len(old_tasks)} anciennes tâches")
                
    async def monitor_timeouts(self):
        """Surveille les tâches qui ont dépassé leur timeout"""
        current_time = time.time()
        
        # Vérifier les tâches assignées
        assigned_tasks = await self.redis.zrangebyscore(
            self.keys['assigned'], 0, current_time - TASK_TIMEOUT
        )
        
        for task_id in assigned_tasks:
            await self.fail_task(task_id, "system", "Timeout d'assignation", retry=True)
            
        # Vérifier les tâches en cours
        running_tasks = await self.redis.zrangebyscore(
            self.keys['running'], 0, current_time - TASK_TIMEOUT
        )
        
        for task_id in running_tasks:
            task_data = await self.redis.hget(self.keys['task_data'], task_id)
            if task_data:
                task = Task.from_dict(json.loads(task_data))
                await self.fail_task(task_id, task.agent_id or "system", "Timeout d'exécution", retry=True)

