#!/usr/bin/env python3
"""
Swarm Playwright W34R3L3G10N - Playwright Agent
Agent Playwright avancé avec simulation de comportements humains réalistes
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from user_profiles import UserProfile, UserProfileFactory, HumanBehaviorSimulator, DeviceType, BehaviorPattern

# Configuration
PROXY_HOST = os.getenv("TOR_PROXY_HOST", "tor")
PROXY_PORT = int(os.getenv("TOR_PROXY_PORT", "9050"))
STEALTH_LEVEL = os.getenv("STEALTH_LEVEL", "high")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class StealthConfig:
    """Configuration des techniques de stealth"""
    
    # Scripts de stealth avancés
    STEALTH_SCRIPTS = {
        "webdriver": """
            // Masquer les traces de webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Masquer les propriétés Playwright
            delete window.playwright;
            delete window.__playwright;
            delete window._playwright;
        """,
        
        "chrome_runtime": """
            // Simuler chrome.runtime
            if (!window.chrome) {
                window.chrome = {};
            }
            if (!window.chrome.runtime) {
                window.chrome.runtime = {
                    onConnect: {
                        addListener: function() {},
                        removeListener: function() {}
                    },
                    onMessage: {
                        addListener: function() {},
                        removeListener: function() {}
                    }
                };
            }
        """,
        
        "permissions": """
            // Simuler les permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """,
        
        "plugins": """
            // Simuler des plugins réalistes
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        name: 'Chrome PDF Plugin',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format'
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        description: ''
                    }
                ]
            });
        """,
        
        "languages": """
            // Simuler les langues de manière cohérente
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """,
        
        "canvas_fingerprint": """
            // Ajouter du bruit au canvas fingerprinting
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                const context = getContext.apply(this, [type, ...args]);
                if (type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function(text, x, y, ...rest) {
                        // Ajouter un léger bruit
                        const noise = Math.random() * 0.1 - 0.05;
                        return originalFillText.apply(this, [text, x + noise, y + noise, ...rest]);
                    };
                }
                return context;
            };
        """,
        
        "webgl_fingerprint": """
            // Masquer les informations WebGL sensibles
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                    return 'Intel Inc.';
                }
                if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, arguments);
            };
        """
    }

class PlaywrightAgent:
    """Agent Playwright avec simulation de comportements humains"""
    
    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.profile: Optional[UserProfile] = None
        self.behavior_simulator: Optional[HumanBehaviorSimulator] = None
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_data = {
            "start_time": time.time(),
            "pages_visited": 0,
            "actions_performed": 0,
            "errors_encountered": 0
        }
        
    async def initialize(self, profile: Optional[UserProfile] = None):
        """Initialise l'agent avec un profil utilisateur"""
        logger.info(f"Initialisation de l'agent {self.agent_id}")
        
        # Créer ou utiliser le profil fourni
        self.profile = profile or UserProfileFactory.create_random_profile()
        self.behavior_simulator = HumanBehaviorSimulator(self.profile)
        
        logger.info(f"Profil: {self.profile.device_type.value} - {self.profile.behavior_pattern.value}")
        
        # Démarrer Playwright
        self.playwright = await async_playwright().start()
        
        # Configuration du navigateur
        browser_args = self._get_browser_args()
        proxy_config = self._get_proxy_config()
        
        # Lancer Firefox (plus difficile à détecter que Chrome)
        self.browser = await self.playwright.firefox.launch(
            headless=HEADLESS,
            args=browser_args,
            proxy=proxy_config
        )
        
        # Créer le contexte avec le profil utilisateur
        context_options = self._get_context_options()
        self.context = await self.browser.new_context(**context_options)
        
        # Appliquer les scripts de stealth
        await self._apply_stealth_scripts()
        
        # Créer la page principale
        self.page = await self.context.new_page()
        
        # Configurer les événements
        await self._setup_page_events()
        
        logger.info(f"Agent {self.agent_id} initialisé avec succès")
        
    def _get_browser_args(self) -> List[str]:
        """Récupère les arguments du navigateur"""
        args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=VizDisplayCompositor",
        ]
        
        # Arguments spécifiques au niveau de stealth
        if STEALTH_LEVEL == "high":
            args.extend([
                "--disable-web-security",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-client-side-phishing-detection",
                "--disable-sync",
                "--disable-default-apps",
                "--hide-scrollbars",
                "--mute-audio",
            ])
            
        return args
        
    def _get_proxy_config(self) -> Dict[str, str]:
        """Configuration du proxy"""
        return {
            "server": f"socks5://{PROXY_HOST}:{PROXY_PORT}"
        }
        
    def _get_context_options(self) -> Dict[str, Any]:
        """Options du contexte navigateur"""
        viewport_width, viewport_height = self.profile.viewport_size
        
        options = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "user_agent": self.profile.user_agent,
            "locale": self.profile.preferences.get("language", "en-US"),
            "timezone_id": self.profile.preferences.get("timezone", "America/New_York"),
            "color_scheme": self.profile.preferences.get("color_scheme", "light"),
            "java_script_enabled": self.profile.preferences.get("javascript_enabled", True),
            "accept_downloads": True,
            "has_touch": self.profile.device_type == DeviceType.MOBILE,
            "is_mobile": self.profile.device_type == DeviceType.MOBILE,
        }
        
        # Permissions
        permissions = []
        if self.profile.preferences.get("geolocation_enabled"):
            permissions.append("geolocation")
        if self.profile.preferences.get("notifications_enabled"):
            permissions.append("notifications")
            
        if permissions:
            options["permissions"] = permissions
            
        return options
        
    async def _apply_stealth_scripts(self):
        """Applique les scripts de stealth"""
        if not self.context:
            return
            
        # Appliquer tous les scripts de stealth
        for script_name, script_content in StealthConfig.STEALTH_SCRIPTS.items():
            try:
                await self.context.add_init_script(script_content)
                logger.debug(f"Script de stealth appliqué: {script_name}")
            except Exception as e:
                logger.warning(f"Erreur lors de l'application du script {script_name}: {e}")
                
    async def _setup_page_events(self):
        """Configure les événements de la page"""
        if not self.page:
            return
            
        # Gérer les dialogues
        self.page.on("dialog", self._handle_dialog)
        
        # Gérer les erreurs
        self.page.on("pageerror", self._handle_page_error)
        
        # Gérer les requêtes
        self.page.on("request", self._handle_request)
        
        # Gérer les réponses
        self.page.on("response", self._handle_response)
        
    async def _handle_dialog(self, dialog):
        """Gère les dialogues (alertes, confirmations)"""
        logger.info(f"Dialogue détecté: {dialog.type} - {dialog.message}")
        
        # Comportement réaliste selon le type de dialogue
        if dialog.type == "alert":
            await asyncio.sleep(random.uniform(0.5, 2.0))  # Temps de lecture
            await dialog.accept()
        elif dialog.type == "confirm":
            # Décision aléatoire mais cohérente avec le profil
            if self.profile.behavior_pattern == BehaviorPattern.CASUAL:
                accept = random.choice([True, False])
            else:
                accept = random.choice([True, True, False])  # Plus souvent accepté
            await asyncio.sleep(random.uniform(1.0, 3.0))
            if accept:
                await dialog.accept()
            else:
                await dialog.dismiss()
        elif dialog.type == "prompt":
            await asyncio.sleep(random.uniform(1.0, 4.0))
            if random.random() < 0.7:  # 70% de chance de répondre
                await dialog.accept("test")  # Réponse générique
            else:
                await dialog.dismiss()
                
    async def _handle_page_error(self, error):
        """Gère les erreurs de page"""
        logger.warning(f"Erreur de page: {error}")
        self.session_data["errors_encountered"] += 1
        
    async def _handle_request(self, request):
        """Gère les requêtes sortantes"""
        # Bloquer certains types de requêtes selon les préférences
        if not self.profile.preferences.get("images_enabled", True):
            if request.resource_type in ["image", "imageset"]:
                await request.abort()
                return
                
        # Continuer normalement
        await request.continue_()
        
    async def _handle_response(self, response):
        """Gère les réponses"""
        if response.status >= 400:
            logger.warning(f"Réponse d'erreur: {response.status} - {response.url}")
            
    async def navigate_to(self, url: str, wait_for: str = "networkidle") -> Dict[str, Any]:
        """Navigue vers une URL avec un comportement humain"""
        if not self.page:
            raise RuntimeError("Agent non initialisé")
            
        logger.info(f"Navigation vers: {url}")
        start_time = time.time()
        
        try:
            # Délai avant navigation (simulation de réflexion)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Navigation
            response = await self.page.goto(
                url,
                wait_until=wait_for,
                timeout=30000
            )
            
            # Attendre que la page soit complètement chargée
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Simulation de temps de lecture initial
            reading_delay = random.uniform(1.0, 3.0)
            await asyncio.sleep(reading_delay)
            
            # Mettre à jour les statistiques
            self.session_data["pages_visited"] += 1
            navigation_time = time.time() - start_time
            
            # Récupérer des informations sur la page
            page_info = await self._get_page_info()
            
            return {
                "success": True,
                "url": url,
                "final_url": self.page.url,
                "status_code": response.status if response else None,
                "navigation_time": navigation_time,
                "page_info": page_info
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la navigation: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "navigation_time": time.time() - start_time
            }
            
    async def _get_page_info(self) -> Dict[str, Any]:
        """Récupère des informations sur la page actuelle"""
        try:
            title = await self.page.title()
            url = self.page.url
            
            # Compter les éléments
            links_count = await self.page.locator("a").count()
            images_count = await self.page.locator("img").count()
            forms_count = await self.page.locator("form").count()
            
            # Taille de la page
            page_height = await self.page.evaluate("document.body.scrollHeight")
            
            return {
                "title": title,
                "url": url,
                "links_count": links_count,
                "images_count": images_count,
                "forms_count": forms_count,
                "page_height": page_height
            }
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des infos de page: {e}")
            return {}
            
    async def search_query(self, query: str, search_engine: str = "duckduckgo") -> Dict[str, Any]:
        """Effectue une recherche avec un comportement humain"""
        logger.info(f"Recherche: '{query}' sur {search_engine}")
        
        # URLs des moteurs de recherche
        search_urls = {
            "duckduckgo": "https://duckduckgo.com",
            "google": "https://www.google.com",
            "bing": "https://www.bing.com"
        }
        
        if search_engine not in search_urls:
            return {"success": False, "error": f"Moteur de recherche non supporté: {search_engine}"}
            
        try:
            # Naviguer vers le moteur de recherche
            await self.navigate_to(search_urls[search_engine])
            
            # Trouver le champ de recherche
            search_selectors = {
                "duckduckgo": "input[name='q']",
                "google": "input[name='q']",
                "bing": "input[name='q']"
            }
            
            search_input = self.page.locator(search_selectors[search_engine])
            await search_input.wait_for(state="visible", timeout=10000)
            
            # Cliquer sur le champ de recherche avec comportement humain
            await self._human_click(search_input)
            
            # Taper la requête avec des délais humains
            await self._human_type(query)
            
            # Appuyer sur Entrée
            await self.page.keyboard.press("Enter")
            
            # Attendre les résultats
            await self.page.wait_for_load_state("networkidle")
            
            # Analyser les résultats
            results = await self._extract_search_results(search_engine)
            
            return {
                "success": True,
                "query": query,
                "search_engine": search_engine,
                "results_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return {
                "success": False,
                "query": query,
                "search_engine": search_engine,
                "error": str(e)
            }
            
    async def _extract_search_results(self, search_engine: str) -> List[Dict[str, Any]]:
        """Extrait les résultats de recherche"""
        results = []
        
        try:
            if search_engine == "duckduckgo":
                result_elements = await self.page.locator("[data-result]").all()
                for element in result_elements[:10]:  # Limiter à 10 résultats
                    try:
                        title_elem = element.locator("h2 a")
                        title = await title_elem.text_content()
                        url = await title_elem.get_attribute("href")
                        
                        snippet_elem = element.locator(".result__snippet")
                        snippet = await snippet_elem.text_content() if await snippet_elem.count() > 0 else ""
                        
                        results.append({
                            "title": title.strip() if title else "",
                            "url": url,
                            "snippet": snippet.strip() if snippet else ""
                        })
                    except Exception as e:
                        logger.debug(f"Erreur extraction résultat: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"Erreur extraction résultats {search_engine}: {e}")
            
        return results
        
    async def _human_click(self, element) -> None:
        """Effectue un clic avec un comportement humain"""
        # Délai avant le clic
        click_delay = self.behavior_simulator.get_click_delay()
        await asyncio.sleep(click_delay)
        
        # Mouvement de souris vers l'élément
        box = await element.bounding_box()
        if box:
            # Point aléatoire dans l'élément
            target_x = box["x"] + random.uniform(box["width"] * 0.2, box["width"] * 0.8)
            target_y = box["y"] + random.uniform(box["height"] * 0.2, box["height"] * 0.8)
            
            # Mouvement de souris réaliste
            await self.page.mouse.move(target_x, target_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
        # Clic
        await element.click()
        self.session_data["actions_performed"] += 1
        
    async def _human_type(self, text: str) -> None:
        """Tape du texte avec un comportement humain"""
        typing_delays = self.behavior_simulator.get_typing_delay(text)
        
        for i, char in enumerate(text):
            await self.page.keyboard.type(char)
            if i < len(typing_delays):
                await asyncio.sleep(typing_delays[i])
                
        self.session_data["actions_performed"] += 1
        
    async def scroll_page(self, direction: str = "down", amount: Optional[int] = None) -> Dict[str, Any]:
        """Effectue un scroll avec un comportement humain"""
        try:
            page_height = await self.page.evaluate("document.body.scrollHeight")
            current_scroll = await self.page.evaluate("window.pageYOffset")
            
            if amount is None:
                # Scroll naturel basé sur le profil
                amount = int(random.randint(100, 400) * self.profile.scroll_speed)
                
            if direction == "up":
                amount = -amount
                
            # Scroll avec animation naturelle
            scroll_steps = max(3, int(abs(amount) / 50))
            step_amount = amount / scroll_steps
            
            for _ in range(scroll_steps):
                await self.page.evaluate(f"window.scrollBy(0, {step_amount})")
                await asyncio.sleep(random.uniform(0.05, 0.15))
                
            # Pause de lecture après le scroll
            reading_pause = random.uniform(0.5, 2.0) / self.profile.scroll_speed
            await asyncio.sleep(reading_pause)
            
            new_scroll = await self.page.evaluate("window.pageYOffset")
            
            return {
                "success": True,
                "direction": direction,
                "amount": amount,
                "previous_position": current_scroll,
                "new_position": new_scroll,
                "page_height": page_height
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du scroll: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def interact_with_element(self, selector: str, action: str, **kwargs) -> Dict[str, Any]:
        """Interagit avec un élément de la page"""
        try:
            element = self.page.locator(selector)
            await element.wait_for(state="visible", timeout=10000)
            
            if action == "click":
                await self._human_click(element)
            elif action == "type":
                text = kwargs.get("text", "")
                await element.click()  # Focus d'abord
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self._human_type(text)
            elif action == "hover":
                await element.hover()
                await asyncio.sleep(random.uniform(0.5, 1.5))
            elif action == "select":
                value = kwargs.get("value", "")
                await element.select_option(value)
            else:
                return {"success": False, "error": f"Action non supportée: {action}"}
                
            return {
                "success": True,
                "selector": selector,
                "action": action,
                "kwargs": kwargs
            }
            
        except Exception as e:
            logger.error(f"Erreur interaction avec {selector}: {e}")
            return {
                "success": False,
                "selector": selector,
                "action": action,
                "error": str(e)
            }
            
    async def take_screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Prend une capture d'écran"""
        try:
            if path is None:
                path = f"/tmp/screenshot_{self.agent_id}_{int(time.time())}.png"
                
            await self.page.screenshot(path=path, full_page=True)
            
            return {
                "success": True,
                "path": path,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Erreur capture d'écran: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_page_content(self) -> Dict[str, Any]:
        """Récupère le contenu de la page"""
        try:
            content = await self.page.content()
            text_content = await self.page.evaluate("document.body.innerText")
            
            return {
                "success": True,
                "html_content": content,
                "text_content": text_content,
                "url": self.page.url,
                "title": await self.page.title()
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération contenu: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def close(self):
        """Ferme l'agent proprement"""
        logger.info(f"Fermeture de l'agent {self.agent_id}")
        
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")
            
    def get_session_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de session"""
        session_duration = time.time() - self.session_data["start_time"]
        
        return {
            "agent_id": self.agent_id,
            "session_duration": session_duration,
            "pages_visited": self.session_data["pages_visited"],
            "actions_performed": self.session_data["actions_performed"],
            "errors_encountered": self.session_data["errors_encountered"],
            "profile": {
                "device_type": self.profile.device_type.value if self.profile else None,
                "behavior_pattern": self.profile.behavior_pattern.value if self.profile else None,
                "user_agent": self.profile.user_agent[:50] + "..." if self.profile else None
            }
        }

# Exemple d'utilisation
async def main():
    """Exemple d'utilisation de l'agent"""
    agent = PlaywrightAgent()
    
    try:
        # Initialiser avec un profil mobile
        profile = UserProfileFactory.create_mobile_profile()
        await agent.initialize(profile)
        
        # Naviguer vers DuckDuckGo
        result = await agent.navigate_to("https://duckduckgo.com")
        print(f"Navigation: {result}")
        
        # Effectuer une recherche
        search_result = await agent.search_query("Playwright automation")
        print(f"Recherche: {search_result}")
        
        # Prendre une capture d'écran
        screenshot_result = await agent.take_screenshot()
        print(f"Capture: {screenshot_result}")
        
        # Statistiques
        stats = agent.get_session_stats()
        print(f"Stats: {stats}")
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())

