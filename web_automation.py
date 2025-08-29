import asyncio
import logging
from typing import Optional, List, Dict, Any
from livekit.agents import function_tool

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from playwright.async_api import async_playwright, Page
except Exception:
    async_playwright = None
    Page = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None  # type: ignore

# In-memory singleton browser context
_playwright = None
_browser = None
_page: Optional[Page] = None


async def _ensure_browser(headless: bool = False) -> Optional[Page]:
    global _playwright, _browser, _page
    if async_playwright is None:
        logger.error("Playwright not installed. Install with: pip install playwright && playwright install")
        return None
    if _page:
        return _page
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=headless)
    context = await _browser.new_context()
    _page = await context.new_page()
    _page.set_default_timeout(10000)
    return _page


async def _safe_page() -> Optional[Page]:
    return _page


@function_tool()
async def start_browser(headless: bool = False) -> str:
    """
    Start a Chromium browser session for automation. Install Playwright beforehand.
    """
    try:
        page = await _ensure_browser(headless=headless)
        if page is None:
            return "❌ Playwright not available. Run: pip install playwright && playwright install"
        return "✅ Browser started"
    except Exception as e:
        logger.error(f"start_browser error: {e}")
        return f"❌ Failed to start browser: {e}"


@function_tool()
async def close_browser() -> str:
    """
    Close the running browser session and cleanup.
    """
    global _playwright, _browser, _page
    try:
        if _browser:
            await _browser.close()
        if _playwright:
            await _playwright.stop()
        _playwright = None
        _browser = None
        _page = None
        return "✅ Browser closed"
    except Exception as e:
        logger.error(f"close_browser error: {e}")
        return f"❌ Failed to close browser: {e}"


@function_tool()
async def go_to(url: str) -> str:
    """
    Navigate to a URL in the automated browser.
    """
    try:
        page = await _ensure_browser(headless=False)
        if page is None:
            return "❌ Playwright not available."
        await page.goto(url, wait_until="domcontentloaded")
        return f"✅ Opened {url}"
    except Exception as e:
        logger.error(f"go_to error: {e}")
        return f"❌ Navigation failed: {e}"


@function_tool()
async def wait_for_selector(selector: str, timeout_ms: int = 8000) -> str:
    """
    Wait for an element matching CSS/XPath to appear.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        await page.wait_for_selector(selector, timeout=timeout_ms)
        return f"✅ Selector available: {selector}"
    except Exception as e:
        logger.error(f"wait_for_selector error: {e}")
        return f"❌ Wait failed: {e}"


@function_tool()
async def click(selector: str) -> str:
    """
    Click an element by CSS/XPath selector.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        await page.click(selector)
        return f"✅ Clicked {selector}"
    except Exception as e:
        logger.error(f"click error: {e}")
        return f"❌ Click failed: {e}"


@function_tool()
async def type_text(selector: str, text: str, clear: bool = True) -> str:
    """
    Type text into an input field.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        if clear:
            await page.fill(selector, "")
        await page.type(selector, text, delay=30)
        return f"✅ Typed into {selector}"
    except Exception as e:
        logger.error(f"type_text error: {e}")
        return f"❌ Typing failed: {e}"


@function_tool()
async def press_key(key: str) -> str:
    """
    Press a keyboard key, e.g., Enter, Escape, ArrowDown.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        await page.keyboard.press(key)
        return f"✅ Pressed {key}"
    except Exception as e:
        logger.error(f"press_key error: {e}")
        return f"❌ Key press failed: {e}"


@function_tool()
async def scroll_by(pixels: int = 800) -> str:
    """
    Scroll the page vertically by a number of pixels.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        await page.evaluate("window.scrollBy(0, arguments[0])", pixels)
        return f"✅ Scrolled by {pixels}px"
    except Exception as e:
        logger.error(f"scroll_by error: {e}")
        return f"❌ Scroll failed: {e}"


@function_tool()
async def search_and_click(text: str) -> str:
    """
    Find the first element containing the given text and click it.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        locator = page.get_by_text(text, exact=False)
        count = await locator.count()
        if count == 0:
            return f"❌ Text not found: {text}"
        await locator.nth(0).click()
        return f"✅ Clicked element containing text: {text}"
    except Exception as e:
        logger.error(f"search_and_click error: {e}")
        return f"❌ search_and_click failed: {e}"


@function_tool()
async def extract_page_text(max_chars: int = 2000) -> str:
    """
    Extract visible text from the current page for summarization.
    """
    try:
        page = await _safe_page()
        if not page:
            return "❌ No active page. Start the browser first."
        html = await page.content()
        if not BeautifulSoup:
            return html[:max_chars]
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = " ".join(soup.get_text(" ").split())
        return text[:max_chars]
    except Exception as e:
        logger.error(f"extract_page_text error: {e}")
        return f"❌ Extract failed: {e}"


@function_tool()
async def youtube_search_play(query: str) -> str:
    """
    Open YouTube, search for a query, and play the first result.
    """
    try:
        page = await _ensure_browser(headless=False)
        if not page:
            return "❌ Playwright not available."
        await page.goto("https://www.youtube.com", wait_until="domcontentloaded")
        await page.fill("input#search", query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector("ytd-video-renderer a#video-title")
        await page.click("ytd-video-renderer a#video-title")
        return f"✅ Playing: {query}"
    except Exception as e:
        logger.error(f"youtube_search_play error: {e}")
        return f"❌ YouTube play failed: {e}"


@function_tool()
async def amazon_search_summary(query: str) -> str:
    """
    Search Amazon for a product and summarize top few results (title, price, rating if available).
    """
    try:
        page = await _ensure_browser(headless=False)
        if not page:
            return "❌ Playwright not available."
        await page.goto("https://www.amazon.in", wait_until="domcontentloaded")
        await page.fill("input[type='text'][name='field-keywords']", query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector("div.s-main-slot")
        html = await page.content()
        if not BeautifulSoup:
            return "⚠ Parsing library not available. Install bs4."
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for card in soup.select("div.s-main-slot div[data-component-type='s-search-result']")[:5]:
            title = (card.select_one("h2 a span") or {}).get_text(strip=True) if card.select_one("h2 a span") else None
            price_whole = (card.select_one("span.a-price-whole") or {}).get_text(strip=True) if card.select_one("span.a-price-whole") else None
            price_frac = (card.select_one("span.a-price-fraction") or {}).get_text(strip=True) if card.select_one("span.a-price-fraction") else None
            price = None
            if price_whole:
                price = price_whole + (price_frac or "")
            rating = (card.select_one("span.a-icon-alt") or {}).get_text(strip=True) if card.select_one("span.a-icon-alt") else None
            if title:
                items.append({"title": title, "price": price, "rating": rating})
        if not items:
            return "❌ No results parsed."
        lines = [f"- {i+1}. {it['title']} | Price: {it.get('price') or 'NA'} | Rating: {it.get('rating') or 'NA'}" for i, it in enumerate(items)]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"amazon_search_summary error: {e}")
        return f"❌ Amazon search failed: {e}" 

# ===== Robotic autonomous web agent architecture (appended) =====
import os
import json
import traceback
import re as _re
import time as _time
from datetime import datetime as _dt
from enum import Enum
from typing import Callable, Tuple

# Optional AI engine
try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # type: ignore

try:
    import pytesseract as _pytesseract  # type: ignore
    from PIL import Image as _PILImage  # type: ignore
except Exception:  # pragma: no cover
    _pytesseract = None  # type: ignore
    _PILImage = None  # type: ignore

try:
    import pyttsx3 as _pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    _pyttsx3 = None  # type: ignore


class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class PlatformType(Enum):
    SOCIAL_MEDIA = "social_media"
    ECOMMERCE = "ecommerce"
    MEDIA = "media"


class RoboticAgent:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.ai_engine = AIEngine()
        self.data_processor = DataProcessor()
        self.task_executor = TaskExecutor()
        self.persistence = PersistenceManager()
        self.voice_interface = VoiceInterface()
        self._initialized = False
        self._initialize_components()

    def _initialize_components(self):
        if self._initialized:
            return
        self.browser_manager.initialize()
        self.ai_engine.initialize()
        self.persistence.initialize()
        self.voice_interface.initialize()
        self._initialized = True

    async def execute_complex_workflow(self, workflow_config: Dict[str, Any]):
        try:
            await self.browser_manager.start_new_session()
            tasks = self._parse_workflow(workflow_config)
            results = await self.task_executor.execute_with_priority(tasks)
            summary = await self.ai_engine.generate_summary(results)
            self.voice_interface.speak(summary)
            return results
        except Exception as e:
            self._handle_error(e, "Workflow Execution Failed")
            raise

    def _parse_workflow(self, config: Dict[str, Any]) -> List[Tuple[TaskPriority, Callable]]:
        tasks: List[Tuple[TaskPriority, Callable]] = []
        for step in config.get('steps', []):
            platform = step.get('platform')
            action = step.get('action')
            params = step.get('params', {})
            priority = step.get('priority', TaskPriority.MEDIUM)
            if platform == PlatformType.SOCIAL_MEDIA.value:
                task = self._create_social_media_task(action, params)
            elif platform == PlatformType.ECOMMERCE.value:
                task = self._create_ecommerce_task(action, params)
            elif platform == PlatformType.MEDIA.value:
                task = self._create_media_task(action, params)
            else:
                continue
            tasks.append((priority, task))
        return tasks

    def _create_social_media_task(self, action: str, params: Dict) -> Callable:
        async def task():
            await self.browser_manager.navigate(params['url'])
            if action == 'check_notifications':
                return await self._handle_social_media_notifications(params)
            elif action == 'reply_messages':
                return await self._handle_message_replies(params)
        return task

    def _create_ecommerce_task(self, action: str, params: Dict) -> Callable:
        async def task():
            await self.browser_manager.navigate(params['url'])
            if action == 'compare_products':
                return await self._handle_product_comparison(params)
            elif action == 'check_availability':
                return await self._handle_stock_check(params)
        return task

    def _create_media_task(self, action: str, params: Dict) -> Callable:
        async def task():
            await self.browser_manager.navigate(params['url'])
            if action == 'play_video':
                return await self._handle_media_control(params)
            elif action == 'queue_songs':
                return await self._handle_song_queue(params)
        return task

    async def _handle_dynamic_content(self, page: Page, timeout: int = 5000):
        try:
            await page.wait_for_load_state('domcontentloaded')
            ajax_elements = await page.query_selector_all('[data-ajax]')
            if ajax_elements:
                await page.wait_for_function(
                    '''() => { const ajaxEls = document.querySelectorAll('[data-ajax]'); return Array.from(ajaxEls).every(el => el.dataset.ajax === 'complete'); }'''
                )
            await page.evaluate('''() => { const lazy = document.querySelectorAll('img[data-src]'); lazy.forEach(img => img.src = img.dataset.src); }''')
        except Exception as e:
            self._log_debug(f"Dynamic content handling failed: {str(e)}")

    async def _auto_fill_form(self, page: Page, form_data: Dict[str, str]):
        try:
            for field_name, value in form_data.items():
                input_field = await page.query_selector(f'input[name="{field_name}"], textarea[name="{field_name}"]')
                if not input_field:
                    labels = await page.query_selector_all('label')
                    for label in labels:
                        text = await label.inner_text()
                        if field_name.lower() in text.lower():
                            input_id = await label.get_attribute('for')
                            input_field = await page.query_selector(f'#{input_id}')
                            break
                if input_field:
                    await input_field.fill(value)
        except Exception as e:
            self._log_info(f"Form filling issue: {str(e)}")

    def _handle_error(self, error: Exception, context: str):
        error_info = {
            'timestamp': _dt.now().isoformat(),
            'context': context,
            'error_type': type(error).__name__,
            'message': str(error),
            'stack_trace': traceback.format_exc()
        }
        self.persistence.log_error(error_info)
        self.voice_interface.speak(f"Error occurred: {error_info['message']}")

    def _log_debug(self, message: str):
        logger.debug(f"[DEBUG][{_dt.now()}]: {message}")

    def _log_info(self, message: str):
        logger.info(f"[INFO][{_dt.now()}]: {message}")

    # Placeholder handlers (implement as needed)
    async def _handle_social_media_notifications(self, params: Dict[str, Any]):
        page = await _ensure_browser(False)
        await self.data_processor.sleep_small()
        return "checked_notifications"

    async def _handle_message_replies(self, params: Dict[str, Any]):
        return "replied_messages"

    async def _handle_product_comparison(self, params: Dict[str, Any]):
        return "compared_products"

    async def _handle_stock_check(self, params: Dict[str, Any]):
        return "stock_checked"

    async def _handle_media_control(self, params: Dict[str, Any]):
        return "played_media"

    async def _handle_song_queue(self, params: Dict[str, Any]):
        return "queued_songs"


class BrowserManager:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None
        self.viewport_size = {'width': 1280, 'height': 800}

    def initialize(self):
        pass

    async def start_new_session(self):
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        self.context = await self.browser.new_context(viewport=self.viewport_size)
        self.page = await self.context.new_page()
        await self._configure_stealth()

    async def _configure_stealth(self):
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    async def navigate(self, url: str, wait_time: int = 3000):
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(wait_time / 1000)

    async def interact_element(self, selector: str, action: str = 'click'):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                element = await self.page.query_selector(selector)
                if element:
                    if action == 'click':
                        await element.click()
                    elif action == 'type':
                        await element.type('test')
                    return True
                else:
                    logger.debug(f"Element not found: {selector}")
            except Exception as e:
                logger.debug(f"Interaction failed (attempt {attempt+1}): {str(e)}")
                await asyncio.sleep(1)
        return False


class AIEngine:
    def __init__(self):
        self.model = None
        self.memory: Dict[str, Any] = {}

    def initialize(self):
        if genai is None:
            logger.warning("google.generativeai not installed; AI summaries disabled")
            return
        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = getattr(genai, 'GenerativeModel', None)('gemini-2.0-flash') if getattr(genai, 'GenerativeModel', None) else None
        except Exception as e:
            logger.warning(f"AI init failed: {e}")

    async def generate_summary(self, results: Dict[str, Any]) -> str:
        if not self.model:
            return "Tasks completed. AI summary unavailable."
        prompt = f"Summarize these task results succinctly and list next steps:\n{json.dumps(results, indent=2)}"
        try:
            resp = await self.model.generate_content_async(prompt)  # type: ignore
            return getattr(resp, 'text', None) or "Summary generated."
        except Exception as e:
            return f"Summary unavailable: {e}"

    async def predict_next_action(self, current_state: Dict[str, Any]) -> str:
        if not self.model:
            return ""
        prompt = f"Suggest next action given state:\n{json.dumps(current_state, indent=2)}"
        try:
            resp = await self.model.generate_content_async(prompt)  # type: ignore
            return getattr(resp, 'text', None) or ""
        except Exception:
            return ""

    def store_memory(self, key: str, value: Any):
        self.memory[key] = value

    def retrieve_memory(self, key: str) -> Optional[Any]:
        return self.memory.get(key)


class DataProcessor:
    def __init__(self):
        self.parsers = {
            'html': self._parse_html,
            'json': self._parse_json,
            'text': self._parse_text
        }

    async def sleep_small(self):
        await asyncio.sleep(0.25)

    def _parse_html(self, html_content: str) -> Dict[str, Any]:
        if not BeautifulSoup:
            return {"title": "", "headings": [], "links": [], "images": []}
        soup = BeautifulSoup(html_content, 'lxml')
        return {
            'title': soup.title.string if soup.title else '',
            'headings': [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])],
            'links': [a['href'] for a in soup.find_all('a', href=True)],
            'images': [img['src'] for img in soup.find_all('img', src=True)]
        }

    def _parse_json(self, json_content: str) -> Dict[str, Any]:
        try:
            return json.loads(json_content)
        except Exception:
            return {}

    def _parse_text(self, text_content: str) -> Dict[str, Any]:
        return {
            'word_count': len(text_content.split()),
            'sentence_count': len(_re.findall(r'\w+[.!?]', text_content)),
            'key_phrases': self._extract_key_phrases(text_content)
        }

    def _extract_key_phrases(self, text: str) -> List[str]:
        words = text.split()
        return [word for word in words if len(word) > 5][:5]


class TaskExecutor:
    def __init__(self):
        self.active_tasks: Dict[str, Callable] = {}
        self.completed_tasks: List[str] = []

    async def execute_with_priority(self, tasks: List[Tuple[TaskPriority, Callable]]) -> Dict[str, Any]:
        sorted_tasks = sorted(tasks, key=lambda x: x[0].value)
        results: Dict[str, Any] = {}
        for priority, task_func in sorted_tasks:
            task_id = f"{priority.name}_{len(self.active_tasks)}"
            self.active_tasks[task_id] = task_func
            try:
                result = await task_func()
                results[task_id] = {'status': 'completed', 'result': result, 'priority': priority.name}
            except Exception as e:
                results[task_id] = {'status': 'failed', 'error': str(e), 'priority': priority.name}
            del self.active_tasks[task_id]
            self.completed_tasks.append(task_id)
        return results

    def get_progress(self) -> float:
        total_tasks = len(self.completed_tasks) + len(self.active_tasks)
        return 0.0 if total_tasks == 0 else (len(self.completed_tasks) / total_tasks * 100)


class PersistenceManager:
    def __init__(self):
        self.conn = None

    def initialize(self):
        import sqlite3 as _sqlite3
        self.conn = _sqlite3.connect('robot_agent.db')
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                task_name TEXT,
                status TEXT,
                result TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                error_type TEXT,
                message TEXT,
                stack_trace TEXT
            )
        ''')
        self.conn.commit()

    def log_session(self, task_name: str, status: str, result: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO sessions (task_name, status, result) VALUES (?, ?, ?)', (task_name, status, result))
        self.conn.commit()

    def log_error(self, error_info: Dict[str, Any]):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO errors (error_type, message, stack_trace) VALUES (?, ?, ?)', (
            error_info.get('error_type', ''), error_info.get('message', ''), error_info.get('stack_trace', '')
        ))
        self.conn.commit()


class VoiceInterface:
    def __init__(self):
        self.engine = None
        self.voices = []

    def initialize(self):
        if _pyttsx3:
            try:
                self.engine = _pyttsx3.init()
                self.voices = self.engine.getProperty('voices')
                if self.voices:
                    self.engine.setProperty('voice', self.voices[0].id)
            except Exception:
                self.engine = None

    def set_voice(self, voice_id: int):
        if self.engine and 0 <= voice_id < len(self.voices):
            self.engine.setProperty('voice', self.voices[voice_id].id)

    def speak(self, text: str, rate: int = 150):
        if not self.engine:
            return
        self.engine.setProperty('rate', rate)
        self.engine.say(text)
        self.engine.runAndWait()

    def speak_async(self, text: str):
        self.speak(text) 