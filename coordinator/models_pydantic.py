"""
Swarm Playwright W34R3L3G10N - Pydantic Models
Modèles de données robustes avec validation Pydantic
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.types import PositiveInt, NonNegativeInt, PositiveFloat

# Constantes
MAX_RETRIES = 3
TASK_TIMEOUT = 30
AGENT_TIMEOUT = 60

class TaskStatus(str, Enum):
    """Statuts possibles d'une tâche"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class TaskPriority(int, Enum):
    """Priorités des tâches"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class AgentStatus(str, Enum):
    """Statuts possibles d'un agent"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    BUSY = "busy"
    UNREACHABLE = "unreachable"

class UserProfileType(str, Enum):
    """Types de profils utilisateur"""
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"

class BehaviorPattern(str, Enum):
    """Patterns de comportement utilisateur"""
    CASUAL = "casual"
    FOCUSED = "focused"
    RESEARCHER = "researcher"
    SHOPPER = "shopper"
    SOCIAL = "social"

class StealthLevel(str, Enum):
    """Niveaux de stealth"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SearchEngine(str, Enum):
    """Moteurs de recherche supportés"""
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"

class ExecutionStrategy(str, Enum):
    """Stratégies d'exécution"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    ROUND_ROBIN = "round_robin"
    AUTO = "auto"

class TaskType(str, Enum):
    """Types de tâches supportées"""
    NAVIGATE = "navigate"
    SEARCH = "search"
    INTERACT = "interact"
    SOCIAL_LOGIN = "social_login"
    SOCIAL_ACTION = "social_action"
    SCREENSHOT = "screenshot"
    EXTRACT_DATA = "extract_data"

class SocialPlatform(str, Enum):
    """Plateformes sociales supportées"""
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"

class SocialAction(str, Enum):
    """Actions sociales supportées"""
    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    SHARE = "share"
    RETWEET = "retweet"
    REPLY = "reply"

class PerformanceMetrics(BaseModel):
    """Métriques de performance d'un agent"""
    cpu_usage: float = Field(default=0.0, ge=0, le=100, description="Utilisation CPU en pourcentage")
    memory_usage: float = Field(default=0.0, ge=0, le=100, description="Utilisation mémoire en pourcentage")
    success_rate: float = Field(default=1.0, ge=0, le=1, description="Taux de succès des tâches")
    avg_response_time: PositiveFloat = Field(default=1000.0, description="Temps de réponse moyen en ms")
    total_tasks: NonNegativeInt = Field(default=0, description="Nombre total de tâches exécutées")
    failed_tasks: NonNegativeInt = Field(default=0, description="Nombre de tâches échouées")
    
    @field_validator('failed_tasks')
    @classmethod
    def failed_tasks_not_greater_than_total(cls, v, info):
        if info.data and 'total_tasks' in info.data and v > info.data['total_tasks']:
            raise ValueError('failed_tasks ne peut pas être supérieur à total_tasks')
        return v

class Agent(BaseModel):
    """Représentation d'un agent Playwright"""
    id: str = Field(description="Identifiant unique de l'agent")
    url: str = Field(description="URL de l'agent")
    status: str = Field(default="unknown", description="Statut de l'agent")
    load: int = Field(default=0, description="Charge actuelle de l'agent")
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Dernière fois vu")
    capabilities: List[str] = Field(default_factory=list, description="Capacités de l'agent")
    # user_profiles: List[UserProfileType] = Field(default_factory=list, description="Profils utilisateur supportés")
    max_concurrent_tasks: int = Field(default=5, description="Nombre max de tâches simultanées")
    current_tasks: int = Field(default=0, description="Nombre de tâches actuelles")
    performance_metrics: Dict[str, Any] = Field(default_factory=Dict, description="Métriques de performance")
    
    @field_validator('current_tasks')
    @classmethod
    def current_tasks_not_greater_than_max(cls, v, info):
        if info.data and 'max_concurrent_tasks' in info.data and v > info.data['max_concurrent_tasks']:
            raise ValueError('current_tasks ne peut pas être supérieur à max_concurrent_tasks')
        return v
    
    @property
    def is_available(self) -> bool:
        """Vérifie si l'agent est disponible pour de nouvelles tâches"""
        return (
            self.status == AgentStatus.HEALTHY and
            self.current_tasks < self.max_concurrent_tasks
        )
    
    @property
    def load_percentage(self) -> float:
        """Calcule le pourcentage de charge de l'agent"""
        return (self.current_tasks / self.max_concurrent_tasks) * 100
    
    def can_handle_task(self, task_type: str) -> bool:
        """Vérifie si l'agent peut gérer un type de tâche"""
        return not self.capabilities or task_type in self.capabilities

class Task(BaseModel):
    """Représentation d'une tâche selon les spécifications utilisateur"""
    id: str = Field(description="Identifiant unique de la tâche")
    type: str = Field(description="Type de la tâche")
    payload: Dict[str, Any] = Field(description="Données de la tâche")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Priorité de la tâche")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Statut de la tâche")
    created_at: float = Field(default_factory=time.time, description="Timestamp de création")
    assigned_at: Optional[float] = Field(default=None, description="Timestamp d'assignation")
    started_at: Optional[float] = Field(default=None, description="Timestamp de démarrage")
    completed_at: Optional[float] = Field(default=None, description="Timestamp de completion")
    agent_id: Optional[str] = Field(default=None, description="ID de l'agent assigné")
    retry_count: NonNegativeInt = Field(default=0, description="Nombre de tentatives")
    max_retries: PositiveInt = Field(default=MAX_RETRIES, description="Nombre max de tentatives")
    timeout: PositiveInt = Field(default=TASK_TIMEOUT, description="Timeout en secondes")
    dependencies: List[str] = Field(default_factory=list, description="IDs des tâches dépendantes")
    tags: List[str] = Field(default_factory=list, description="Tags de la tâche")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Résultat de la tâche")
    error: Optional[str] = Field(default=None, description="Message d'erreur")
    
    @field_validator('retry_count')
    @classmethod
    def retry_count_not_greater_than_max(cls, v, info):
        if info.data and 'max_retries' in info.data and v > info.data['max_retries']:
            raise ValueError('retry_count ne peut pas être supérieur à max_retries')
        return v
    
    @model_validator(mode='after')
    def validate_timestamps(self):
        """Valide la cohérence des timestamps"""
        created_at = self.created_at
        assigned_at = self.assigned_at
        started_at = self.started_at
        completed_at = self.completed_at
        
        if assigned_at and created_at and assigned_at < created_at:
            raise ValueError('assigned_at ne peut pas être antérieur à created_at')
        if started_at and assigned_at and started_at < assigned_at:
            raise ValueError('started_at ne peut pas être antérieur à assigned_at')
        if completed_at and started_at and completed_at < started_at:
            raise ValueError('completed_at ne peut pas être antérieur à started_at')
            
        return self
    
    @property
    def duration(self) -> Optional[float]:
        """Calcule la durée d'exécution de la tâche"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_expired(self) -> bool:
        """Vérifie si la tâche a expiré"""
        if self.started_at:
            return time.time() - self.started_at > self.timeout
        return False

class ExecutionResult(BaseModel):
    """Résultat d'exécution d'une tâche"""
    task_id: str = Field(description="ID de la tâche")
    success: bool = Field(description="Succès de l'exécution")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Données de résultat")
    error: Optional[str] = Field(default=None, description="Message d'erreur")
    execution_time: Optional[PositiveFloat] = Field(default=None, description="Temps d'exécution en secondes")
    agent_id: Optional[str] = Field(default=None, description="ID de l'agent exécuteur")
    timestamp: float = Field(default_factory=time.time, description="Timestamp du résultat")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")

class SwarmExecuteRequest(BaseModel):
    """Requête d'exécution en swarm"""
    task: Task = Field(description="Tâche à exécuter")
    replicas: PositiveInt = Field(default=3, ge=1, le=20, description="Nombre de répliques")
    strategy: ExecutionStrategy = Field(default=ExecutionStrategy.PARALLEL, description="Stratégie d'exécution")
    timeout: PositiveInt = Field(default=60, description="Timeout global en secondes")
    
class SwarmExecuteResponse(BaseModel):
    """Réponse d'exécution en swarm"""
    swarm_id: str = Field(description="ID du swarm")
    success: bool = Field(description="Succès global")
    results: List[ExecutionResult] = Field(description="Résultats individuels")
    total_replicas: int = Field(description="Nombre total de répliques")
    successful_replicas: int = Field(description="Nombre de répliques réussies")
    failed_replicas: int = Field(description="Nombre de répliques échouées")
    execution_time: PositiveFloat = Field(description="Temps d'exécution total")
    strategy_used: ExecutionStrategy = Field(description="Stratégie utilisée")

class AgentDiscoveryConfig(BaseModel):
    """Configuration de la découverte d'agents"""
    discovery_interval: PositiveInt = Field(default=30, description="Intervalle de découverte en secondes")
    health_check_interval: PositiveInt = Field(default=10, description="Intervalle de health check en secondes")
    agent_timeout: PositiveInt = Field(default=5, description="Timeout pour les agents en secondes")
    max_failed_attempts: PositiveInt = Field(default=3, description="Nombre max d'échecs avant suppression")
    service_names: List[str] = Field(default_factory=lambda: ["agent"], description="Noms des services à découvrir")

class CoordinatorConfig(BaseModel):
    """Configuration du coordinateur"""
    agent_pool_size: PositiveInt = Field(default=5, description="Taille du pool d'agents")
    load_balancer_url: str = Field(default="http://load-balancer:8080", description="URL du load balancer")
    redis_url: str = Field(default="redis://redis:6379", description="URL Redis")
    log_level: str = Field(default="INFO", description="Niveau de log")
    discovery_config: AgentDiscoveryConfig = Field(default_factory=AgentDiscoveryConfig, description="Config découverte")

# Fonctions utilitaires pour créer des tâches
def create_navigate_task(
    url: str,
    user_profile: UserProfileType = UserProfileType.DESKTOP,
    behavior_pattern: BehaviorPattern = BehaviorPattern.CASUAL,
    stealth_level: StealthLevel = StealthLevel.MEDIUM,
    screenshot: bool = False,
    save_cookies: bool = False,
    account_id: Optional[str] = None,
    task_id: Optional[str] = None,
    priority: TaskPriority = TaskPriority.NORMAL
) -> Task:
    """Crée une tâche de navigation avec validation Pydantic"""
    return Task(
        id=task_id or str(uuid.uuid4()),
        type=TaskType.NAVIGATE,
        payload={
            "url": url,
            "user_profile": user_profile.value,
            "behavior_pattern": behavior_pattern.value,
            "stealth_level": stealth_level.value,
            "screenshot": screenshot,
            "save_cookies": save_cookies,
            "account_id": account_id
        },
        priority=priority
    )

def create_search_task(
    query: str,
    search_engine: SearchEngine = SearchEngine.DUCKDUCKGO,
    user_profile: UserProfileType = UserProfileType.DESKTOP,
    max_results: PositiveInt = 10,
    screenshot: bool = False,
    task_id: Optional[str] = None,
    priority: TaskPriority = TaskPriority.NORMAL
) -> Task:
    """Crée une tâche de recherche avec validation Pydantic"""
    return Task(
        id=task_id or str(uuid.uuid4()),
        type=TaskType.SEARCH,
        payload={
            "query": query,
            "search_engine": search_engine.value,
            "user_profile": user_profile.value,
            "max_results": max_results,
            "screenshot": screenshot
        },
        priority=priority
    )

def create_social_action_task(
    platform: Union[SocialPlatform, str],
    action: Union[SocialAction, str],
    target_url: str,
    content: Optional[str] = None,
    account_id: Optional[str] = None,
    task_id: Optional[str] = None,
    priority: TaskPriority = TaskPriority.NORMAL
) -> Task:
    """Crée une tâche d'action sociale avec validation Pydantic"""
    # Convertir en enum si nécessaire
    if isinstance(platform, str):
        platform = SocialPlatform(platform)
    if isinstance(action, str):
        action = SocialAction(action)
        
    return Task(
        id=task_id or str(uuid.uuid4()),
        type=TaskType.SOCIAL_ACTION,
        payload={
            "social_platform": platform.value,
            "action": action.value,
            "target_url": target_url,
            "content": content,
            "account_id": account_id
        },
        priority=priority
    )
