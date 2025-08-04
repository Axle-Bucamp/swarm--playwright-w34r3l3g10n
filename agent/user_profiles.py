#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - User Profiles
Profils d'utilisateurs réalistes pour simulation de comportements humains
"""

import random
import time
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class DeviceType(Enum):
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"

class BehaviorPattern(Enum):
    CASUAL = "casual"
    FOCUSED = "focused"
    RESEARCHER = "researcher"
    SHOPPER = "shopper"
    SOCIAL = "social"

@dataclass
class UserProfile:
    """Profil d'utilisateur complet"""
    device_type: DeviceType
    behavior_pattern: BehaviorPattern
    user_agent: str
    viewport_size: Tuple[int, int]
    scroll_speed: float
    typing_speed: float
    click_delay_range: Tuple[float, float]
    reading_speed: float
    attention_span: float
    mouse_movement_style: str
    preferences: Dict[str, Any]

class UserAgentGenerator:
    """Générateur d'user agents réalistes"""
    
    # User agents réels collectés récemment
    DESKTOP_AGENTS = [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Chrome macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Firefox Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
        
        # Firefox macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
        
        # Safari macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        
        # Edge Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    MOBILE_AGENTS = [
        # iPhone Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        
        # iPhone Chrome
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/119.0.6045.169 Mobile/15E148 Safari/604.1",
        
        # Android Chrome
        "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-A515F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.193 Mobile Safari/537.36",
        
        # Android Firefox
        "Mozilla/5.0 (Mobile; rv:109.0) Gecko/121.0 Firefox/121.0",
        "Mozilla/5.0 (Mobile; rv:109.0) Gecko/120.0 Firefox/120.0",
        
        # Samsung Internet
        "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    ]
    
    TABLET_AGENTS = [
        # iPad Safari
        "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        
        # iPad Chrome
        "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
        
        # Android Tablet
        "Mozilla/5.0 (Linux; Android 13; SM-T870) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; SM-T725) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.193 Safari/537.36",
    ]
    
    @classmethod
    def get_random_agent(cls, device_type: DeviceType) -> str:
        """Récupère un user agent aléatoire pour le type d'appareil"""
        if device_type == DeviceType.MOBILE:
            return random.choice(cls.MOBILE_AGENTS)
        elif device_type == DeviceType.TABLET:
            return random.choice(cls.TABLET_AGENTS)
        else:
            return random.choice(cls.DESKTOP_AGENTS)

class ViewportGenerator:
    """Générateur de tailles d'écran réalistes"""
    
    DESKTOP_VIEWPORTS = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (1600, 900), (2560, 1440), (1920, 1200),
        (1680, 1050), (1280, 1024), (1024, 768), (1152, 864)
    ]
    
    MOBILE_VIEWPORTS = [
        (375, 667),   # iPhone 6/7/8
        (414, 896),   # iPhone XR/11
        (390, 844),   # iPhone 12/13
        (393, 852),   # iPhone 14
        (360, 640),   # Android standard
        (412, 915),   # Pixel 6
        (384, 854),   # Samsung Galaxy
        (375, 812),   # iPhone X/XS
    ]
    
    TABLET_VIEWPORTS = [
        (768, 1024),  # iPad
        (820, 1180),  # iPad Air
        (1024, 1366), # iPad Pro
        (800, 1280),  # Android tablet
        (962, 601),   # Surface
    ]
    
    @classmethod
    def get_random_viewport(cls, device_type: DeviceType) -> Tuple[int, int]:
        """Récupère une taille d'écran aléatoire pour le type d'appareil"""
        if device_type == DeviceType.MOBILE:
            return random.choice(cls.MOBILE_VIEWPORTS)
        elif device_type == DeviceType.TABLET:
            return random.choice(cls.TABLET_VIEWPORTS)
        else:
            return random.choice(cls.DESKTOP_VIEWPORTS)

class BehaviorGenerator:
    """Générateur de comportements utilisateur"""
    
    BEHAVIOR_CONFIGS = {
        BehaviorPattern.CASUAL: {
            "scroll_speed": (0.5, 1.5),
            "typing_speed": (80, 150),  # mots par minute
            "click_delay": (0.3, 1.2),
            "reading_speed": (200, 300),  # mots par minute
            "attention_span": (30, 120),  # secondes
            "mouse_movement": "smooth",
            "pause_probability": 0.3,
            "back_probability": 0.1,
        },
        BehaviorPattern.FOCUSED: {
            "scroll_speed": (0.8, 2.0),
            "typing_speed": (120, 200),
            "click_delay": (0.1, 0.5),
            "reading_speed": (250, 400),
            "attention_span": (120, 300),
            "mouse_movement": "direct",
            "pause_probability": 0.1,
            "back_probability": 0.05,
        },
        BehaviorPattern.RESEARCHER: {
            "scroll_speed": (0.3, 1.0),
            "typing_speed": (100, 180),
            "click_delay": (0.2, 0.8),
            "reading_speed": (180, 280),
            "attention_span": (180, 600),
            "mouse_movement": "careful",
            "pause_probability": 0.4,
            "back_probability": 0.2,
        },
        BehaviorPattern.SHOPPER: {
            "scroll_speed": (0.6, 1.8),
            "typing_speed": (90, 160),
            "click_delay": (0.2, 0.9),
            "reading_speed": (220, 350),
            "attention_span": (60, 180),
            "mouse_movement": "exploratory",
            "pause_probability": 0.25,
            "back_probability": 0.15,
        },
        BehaviorPattern.SOCIAL: {
            "scroll_speed": (1.0, 3.0),
            "typing_speed": (60, 120),
            "click_delay": (0.1, 0.6),
            "reading_speed": (300, 500),
            "attention_span": (15, 60),
            "mouse_movement": "quick",
            "pause_probability": 0.2,
            "back_probability": 0.08,
        }
    }
    
    @classmethod
    def generate_behavior_params(cls, pattern: BehaviorPattern, device_type: DeviceType) -> Dict[str, Any]:
        """Génère les paramètres de comportement"""
        config = cls.BEHAVIOR_CONFIGS[pattern]
        
        # Ajustements selon le type d'appareil
        device_multiplier = {
            DeviceType.MOBILE: 0.7,    # Plus lent sur mobile
            DeviceType.TABLET: 0.85,   # Légèrement plus lent sur tablette
            DeviceType.DESKTOP: 1.0    # Vitesse normale sur desktop
        }
        
        multiplier = device_multiplier[device_type]
        
        return {
            "scroll_speed": random.uniform(*config["scroll_speed"]) * multiplier,
            "typing_speed": random.uniform(*config["typing_speed"]) * multiplier,
            "click_delay": random.uniform(*config["click_delay"]) / multiplier,
            "reading_speed": random.uniform(*config["reading_speed"]) * multiplier,
            "attention_span": random.uniform(*config["attention_span"]),
            "mouse_movement": config["mouse_movement"],
            "pause_probability": config["pause_probability"],
            "back_probability": config["back_probability"],
        }

class UserProfileFactory:
    """Factory pour créer des profils d'utilisateurs réalistes"""
    
    @staticmethod
    def create_random_profile() -> UserProfile:
        """Crée un profil d'utilisateur aléatoire"""
        device_type = random.choice(list(DeviceType))
        behavior_pattern = random.choice(list(BehaviorPattern))
        
        return UserProfileFactory.create_profile(device_type, behavior_pattern)
    
    @staticmethod
    def create_profile(device_type: DeviceType, behavior_pattern: BehaviorPattern) -> UserProfile:
        """Crée un profil d'utilisateur spécifique"""
        
        user_agent = UserAgentGenerator.get_random_agent(device_type)
        viewport_size = ViewportGenerator.get_random_viewport(device_type)
        behavior_params = BehaviorGenerator.generate_behavior_params(behavior_pattern, device_type)
        
        # Préférences spécifiques selon le pattern
        preferences = {
            "language": random.choice(["en-US", "en-GB", "fr-FR", "de-DE", "es-ES"]),
            "timezone": random.choice([
                "America/New_York", "Europe/London", "Europe/Paris", 
                "Europe/Berlin", "Asia/Tokyo", "Australia/Sydney"
            ]),
            "color_scheme": random.choice(["light", "dark", "auto"]),
            "cookies_enabled": random.choice([True, True, True, False]),  # Majorité accepte
            "javascript_enabled": True,
            "images_enabled": random.choice([True, True, False]),  # Rare de désactiver
            "geolocation_enabled": random.choice([True, False, False]),  # Souvent refusé
        }
        
        # Ajustements spécifiques au comportement
        if behavior_pattern == BehaviorPattern.RESEARCHER:
            preferences["ad_blocker"] = random.choice([True, True, False])
            preferences["privacy_mode"] = random.choice([True, False])
        elif behavior_pattern == BehaviorPattern.CASUAL:
            preferences["auto_play_videos"] = random.choice([True, False])
            preferences["notifications_enabled"] = random.choice([True, False, False])
        
        return UserProfile(
            device_type=device_type,
            behavior_pattern=behavior_pattern,
            user_agent=user_agent,
            viewport_size=viewport_size,
            scroll_speed=behavior_params["scroll_speed"],
            typing_speed=behavior_params["typing_speed"],
            click_delay_range=(
                behavior_params["click_delay"] * 0.5,
                behavior_params["click_delay"] * 1.5
            ),
            reading_speed=behavior_params["reading_speed"],
            attention_span=behavior_params["attention_span"],
            mouse_movement_style=behavior_params["mouse_movement"],
            preferences=preferences
        )
    
    @staticmethod
    def create_mobile_profile() -> UserProfile:
        """Crée un profil mobile spécifique"""
        return UserProfileFactory.create_profile(
            DeviceType.MOBILE, 
            random.choice(list(BehaviorPattern))
        )
    
    @staticmethod
    def create_desktop_profile() -> UserProfile:
        """Crée un profil desktop spécifique"""
        return UserProfileFactory.create_profile(
            DeviceType.DESKTOP, 
            random.choice(list(BehaviorPattern))
        )
    
    @staticmethod
    def create_researcher_profile() -> UserProfile:
        """Crée un profil de chercheur spécifique"""
        return UserProfileFactory.create_profile(
            random.choice([DeviceType.DESKTOP, DeviceType.TABLET]),
            BehaviorPattern.RESEARCHER
        )

class HumanBehaviorSimulator:
    """Simulateur de comportements humains avancés"""
    
    def __init__(self, profile: UserProfile):
        self.profile = profile
        self.session_start_time = time.time()
        self.actions_count = 0
        self.fatigue_factor = 1.0
        
    def get_typing_delay(self, text: str) -> List[float]:
        """Calcule les délais de frappe réalistes"""
        base_delay = 60.0 / self.profile.typing_speed  # secondes par caractère
        delays = []
        
        for i, char in enumerate(text):
            delay = base_delay
            
            # Variations selon le caractère
            if char == ' ':
                delay *= random.uniform(1.2, 1.8)  # Pause plus longue pour les espaces
            elif char in '.,!?;:':
                delay *= random.uniform(1.5, 2.5)  # Pause pour la ponctuation
            elif char.isupper():
                delay *= random.uniform(1.1, 1.4)  # Légèrement plus lent pour les majuscules
            elif char.isdigit():
                delay *= random.uniform(0.9, 1.2)  # Chiffres
            
            # Erreurs de frappe occasionnelles
            if random.random() < 0.02:  # 2% de chance d'erreur
                delays.append(delay)
                delays.append(random.uniform(0.1, 0.3))  # Temps pour réaliser l'erreur
                delays.append(random.uniform(0.05, 0.15))  # Backspace
                delays.append(delay * 1.2)  # Retaper plus lentement
            else:
                delays.append(delay * random.uniform(0.7, 1.3))
                
        return delays
    
    def get_scroll_behavior(self, page_height: int) -> List[Dict[str, Any]]:
        """Génère un comportement de scroll réaliste"""
        scrolls = []
        current_position = 0
        
        while current_position < page_height * 0.8:  # Ne scroll pas jusqu'en bas
            # Distance de scroll variable
            scroll_distance = random.uniform(100, 400) * self.profile.scroll_speed
            
            # Pause de lecture
            reading_pause = random.uniform(1.0, 5.0) / self.profile.scroll_speed
            
            # Parfois scroll vers le haut (relecture)
            if random.random() < 0.1 and current_position > 200:
                scroll_distance = -random.uniform(50, 150)
                reading_pause *= 0.5
            
            scrolls.append({
                "action": "scroll",
                "distance": scroll_distance,
                "pause_after": reading_pause,
                "position": current_position
            })
            
            current_position += scroll_distance
            
            # Fatigue - ralentissement progressif
            self.fatigue_factor *= 0.999
            
        return scrolls
    
    def get_mouse_movement_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Génère un chemin de souris réaliste"""
        start_x, start_y = start
        end_x, end_y = end
        
        # Nombre de points intermédiaires
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        num_points = max(3, int(distance / 50))
        
        points = [(start_x, start_y)]
        
        for i in range(1, num_points):
            progress = i / num_points
            
            # Interpolation avec courbe de Bézier simplifiée
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress
            
            # Ajout de variations naturelles
            if self.profile.mouse_movement_style == "smooth":
                variation = 5
            elif self.profile.mouse_movement_style == "direct":
                variation = 2
            elif self.profile.mouse_movement_style == "careful":
                variation = 8
            elif self.profile.mouse_movement_style == "exploratory":
                variation = 12
            else:  # quick
                variation = 3
            
            x += random.uniform(-variation, variation)
            y += random.uniform(-variation, variation)
            
            points.append((int(x), int(y)))
        
        points.append((end_x, end_y))
        return points
    
    def should_take_break(self) -> bool:
        """Détermine si l'utilisateur devrait prendre une pause"""
        session_duration = time.time() - self.session_start_time
        
        # Probabilité de pause augmente avec le temps
        break_probability = min(0.3, session_duration / 3600)  # Max 30% après 1h
        
        # Ajustement selon le pattern de comportement
        if self.profile.behavior_pattern == BehaviorPattern.FOCUSED:
            break_probability *= 0.5
        elif self.profile.behavior_pattern == BehaviorPattern.CASUAL:
            break_probability *= 1.5
            
        return random.random() < break_probability
    
    def get_break_duration(self) -> float:
        """Calcule la durée d'une pause"""
        if self.profile.behavior_pattern == BehaviorPattern.FOCUSED:
            return random.uniform(5, 30)
        elif self.profile.behavior_pattern == BehaviorPattern.CASUAL:
            return random.uniform(10, 120)
        else:
            return random.uniform(15, 60)
    
    def update_fatigue(self):
        """Met à jour le facteur de fatigue"""
        self.actions_count += 1
        session_duration = time.time() - self.session_start_time
        
        # Fatigue basée sur la durée et le nombre d'actions
        base_fatigue = 1.0 - min(0.3, session_duration / 7200)  # Max 30% après 2h
        action_fatigue = 1.0 - min(0.2, self.actions_count / 1000)  # Max 20% après 1000 actions
        
        self.fatigue_factor = base_fatigue * action_fatigue
        
    def get_click_delay(self) -> float:
        """Calcule le délai avant un clic"""
        base_delay = random.uniform(*self.profile.click_delay_range)
        return base_delay / self.fatigue_factor

# Exemples d'utilisation
if __name__ == "__main__":
    # Créer quelques profils d'exemple
    profiles = [
        UserProfileFactory.create_random_profile(),
        UserProfileFactory.create_mobile_profile(),
        UserProfileFactory.create_researcher_profile()
    ]
    
    for i, profile in enumerate(profiles):
        print(f"\n=== Profil {i+1} ===")
        print(f"Device: {profile.device_type.value}")
        print(f"Behavior: {profile.behavior_pattern.value}")
        print(f"Viewport: {profile.viewport_size}")
        print(f"User Agent: {profile.user_agent[:80]}...")
        print(f"Typing Speed: {profile.typing_speed:.1f} WPM")
        print(f"Scroll Speed: {profile.scroll_speed:.2f}")
        
        # Simuler quelques comportements
        simulator = HumanBehaviorSimulator(profile)
        typing_delays = simulator.get_typing_delay("Hello World!")
        print(f"Typing delays: {[f'{d:.3f}' for d in typing_delays[:5]]}...")
        
        mouse_path = simulator.get_mouse_movement_path((100, 100), (300, 200))
        print(f"Mouse path points: {len(mouse_path)}")
        print(f"Should take break: {simulator.should_take_break()}")

