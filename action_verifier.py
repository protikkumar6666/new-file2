import asyncio
import logging
from screenvision import screen_vision_tool

logger = logging.getLogger(__name__)

# Optional local window inspection to reduce reliance on vision
try:
    import pygetwindow as gw
except Exception:
    gw = None


def _list_visible_window_titles_lower() -> list[str]:
    if not gw:
        return []
    try:
        titles: list[str] = []
        for w in gw.getAllWindows():
            try:
                if getattr(w, "isMinimized", False):
                    continue
                title = (w.title or "").strip()
                if title:
                    titles.append(title.lower())
            except Exception:
                continue
        return titles
    except Exception:
        return []


def _title_matches(keyword: str, titles: list[str]) -> bool:
    key = (keyword or "").lower().strip()
    if not key:
        return False
    return any(key in t for t in titles)


async def _double_screen_check(queries: list[str]) -> str:
    """Run up to two differently phrased checks and merge into one narrative string."""
    analyses = []
    for q in queries[:2]:
        try:
            resp = await screen_vision_tool(q)
            analyses.append(resp or "")
            await asyncio.sleep(0.3)
        except Exception as e:
            analyses.append(f"vision error: {e}")
    return " \n".join(analyses).strip()


class ActionVerifier:
    """
    Centralized action verification system to prevent hallucination
    """
    
    @staticmethod
    async def verify_app_opened(app_name: str) -> tuple[bool, str]:
        """
        Verify if an application is actually opened and visible
        Returns: (success: bool, message: str)
        """
        try:
            titles = _list_visible_window_titles_lower()
            local_hit = _title_matches(app_name, titles)

            queries = [
                f"Check strictly: Is a window for '{app_name}' visible and active? Answer explicitly visible/not visible.",
                f"Look for the '{app_name}' app UI or title bar. Is it currently on screen? Answer clearly visible/not visible."
            ]
            vision_text = await _double_screen_check(queries)
            vision_l = vision_text.lower()

            positive_indicators = ["visible", "open", "active"]
            negative_indicators = ["not visible", "not found", "closed", "no"]
            positive = any(ind in vision_l for ind in positive_indicators) and app_name.lower() in vision_l
            negative = any(ind in vision_l for ind in negative_indicators)

            # Consensus: prefer negative if conflicting; require at least one strong positive (local or vision) with no negatives
            if (local_hit or positive) and not negative:
                return True, f"✅ {app_name} appears open. Local={local_hit}, Vision says: {vision_text[:200]}"
            if negative and not local_hit:
                return False, f"❌ {app_name} not confirmed open. Vision says: {vision_text[:200]}"
            # Unclear
            return False, f"⚠️ Could not confidently confirm {app_name} is open. Local={local_hit}. Vision: {vision_text[:200]}"
                
        except Exception as e:
            logger.error(f"Error verifying app opened: {e}")
            return False, f"❌ আরে! App verify করতে সমস্যা হয়েছে: {str(e)[:100]}। আবার try করি?"
    
    @staticmethod
    async def verify_app_closed(app_name: str) -> tuple[bool, str]:
        """
        Verify if an application is actually closed
        Returns: (success: bool, message: str)
        """
        try:
            titles = _list_visible_window_titles_lower()
            local_hit = _title_matches(app_name, titles)

            queries = [
                f"Check strictly: Is any '{app_name}' window visible? Answer clearly: visible/not visible.",
                f"Do you see '{app_name}' interface or title anywhere? Answer clearly: visible/not visible."
            ]
            vision_text = await _double_screen_check(queries)
            vision_l = vision_text.lower()

            negative_indicators = ["not visible", "not found", "closed", "no"]
            positive_indicators = ["visible", "open", "active"]
            negative = any(ind in vision_l for ind in negative_indicators)
            positive = any(ind in vision_l for ind in positive_indicators) and app_name.lower() in vision_l

            if (negative and not local_hit):
                return True, f"✅ {app_name} appears closed. Local={local_hit}, Vision: {vision_text[:200]}"
            if local_hit or positive:
                return False, f"❌ {app_name} seems still present. Local={local_hit}. Vision: {vision_text[:200]}"
            return False, f"⚠️ Could not confidently confirm {app_name} is closed. Local={local_hit}. Vision: {vision_text[:200]}"
                
        except Exception as e:
            logger.error(f"Error verifying app closed: {e}")
            return False, f"❌ দুঃখিত! App close verify করতে পারছি না: {str(e)[:100]}।"
    
    @staticmethod
    async def verify_file_opened(file_name: str) -> tuple[bool, str]:
        """
        Verify if a file is actually opened
        Returns: (success: bool, message: str)
        """
        try:
            titles = _list_visible_window_titles_lower()
            local_hit = _title_matches(file_name, titles)

            queries = [
                f"Is there a window showing the file '{file_name}' content? Answer visible/not visible.",
                f"Check viewers/players/editors for '{file_name}'. Is it on screen? Answer visible/not visible."
            ]
            vision_text = await _double_screen_check(queries)
            vision_l = vision_text.lower()

            positive = ("visible" in vision_l or "open" in vision_l) and file_name.lower() in vision_l
            negative = ("not visible" in vision_l or "not found" in vision_l or "closed" in vision_l)

            if (local_hit or positive) and not negative:
                return True, f"✅ File '{file_name}' appears open. Local={local_hit}. Vision: {vision_text[:200]}"
            if negative and not local_hit:
                return False, f"❌ File '{file_name}' not confirmed open. Vision: {vision_text[:200]}"
            return False, f"⚠️ Could not confirm file open. Local={local_hit}. Vision: {vision_text[:200]}"
                
        except Exception as e:
            logger.error(f"Error verifying file opened: {e}")
            return False, f"❌ File verify করতে সমস্যা: {str(e)[:100]}। File টা আছে তো?"
    
    @staticmethod
    async def verify_folder_opened(folder_name: str) -> tuple[bool, str]:
        """
        Verify if a folder is actually opened
        Returns: (success: bool, message: str)
        """
        try:
            titles = _list_visible_window_titles_lower()
            local_hit = _title_matches(folder_name, titles) or _title_matches("explorer", titles)

            queries = [
                f"Is a file explorer showing '{folder_name}' visible? Answer visible/not visible.",
                f"Look for Windows Explorer window with '{folder_name}'. Answer visible/not visible."
            ]
            vision_text = await _double_screen_check(queries)
            vision_l = vision_text.lower()

            positive = ("explorer" in vision_l or "folder" in vision_l or "visible" in vision_l) and folder_name.lower() in vision_l
            negative = ("not visible" in vision_l or "not found" in vision_l)

            if (local_hit or positive) and not negative:
                return True, f"✅ Folder '{folder_name}' appears open. Local={local_hit}. Vision: {vision_text[:200]}"
            if negative and not local_hit:
                return False, f"❌ Folder '{folder_name}' not confirmed open. Vision: {vision_text[:200]}"
            return False, f"⚠️ Could not confirm folder open. Local={local_hit}. Vision: {vision_text[:200]}"
                
        except Exception as e:
            logger.error(f"Error verifying folder opened: {e}")
            return False, f"❌ Folder verify করতে পারছি না: {str(e)[:100]}।"
    
    @staticmethod
    async def verify_action_with_retry(action_func, verify_func, max_retries: int = 2) -> str:
        """
        Execute an action and verify it with retries
        """
        for attempt in range(max_retries + 1):
            try:
                # Execute the action
                action_result = await action_func()
                
                # Wait for action to complete
                await asyncio.sleep(2)
                
                # Verify the action
                success, verify_message = await verify_func()
                
                if success:
                    return verify_message
                elif attempt < max_retries:
                    logger.info(f"Action failed, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)
                else:
                    return f"❌ Action failed after {max_retries + 1} attempts. {verify_message}"
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.error(f"Error in action attempt {attempt + 1}: {e}")
                    await asyncio.sleep(1)
                else:
                    return f"❌ Action failed with error: {e}"
        
        return "❌ Action failed after all retry attempts"