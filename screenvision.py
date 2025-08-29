import os
import asyncio
import logging
from dotenv import load_dotenv
from livekit.agents import function_tool
import pyautogui
import io
from google import genai as genai

# Optional OCR
try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY missing in .env")
# Initialize google-genai v1.x client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Default model for vision
DEFAULT_VISION_MODEL = 'gemini-1.5-flash'

@function_tool()
async def screen_vision_tool(query: str) -> str:
    """
    Captures the current screen, analyzes it using Google Gemini Vision API, and returns the description or answer to the query.

    Use this tool after any action (like open_app or close_app) to verify visually if the action succeeded.
    Example prompts:
    - "Is Chrome window visible on screen?"
    - "Describe the current desktop."
    - "Check if Notepad is open and what text is there."

    Args:
        query: The question or description request about the screen (e.g., "Verify if app is open").

    Returns:
        str: The AI's analysis of the screen based on the query.
    """
    if not query.strip():
        return "❌ Please provide a query for screen analysis."

    try:
        # Capture screen using pyautogui
        logger.info("Capturing screen...")
        screenshot = pyautogui.screenshot()
        
        # Convert image to bytes for Gemini API
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        # Prepare content for Gemini (google-genai v1.x)
        parts = [
            genai.types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
            genai.types.Part.from_text(query),
        ]
        contents = [genai.types.Content(role='user', parts=parts)]
        
        # Generate response from Gemini
        logger.info(f"Analyzing screen with query: {query}")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=DEFAULT_VISION_MODEL,
            contents=contents,
        )
        
        if response and getattr(response, 'text', None):
            analysis = response.text.strip()
            logger.info(f"Screen analysis: {analysis[:100]}...")
            return f"✅ Screen analysis: {analysis}"
        else:
            return "⚠ No response from Gemini API. Check API key or quota."
    
    except Exception as e:
        logger.error(f"Error in screen vision: {e}")
        return f"❌ আরে! Screen analyze করতে সমস্যা: {str(e)[:100]}। PyAutoGUI এবং Google GenAI SDK check করো।"

@function_tool()
async def screen_ocr_text() -> str:
    """
    Extract all visible text from the current screen using OCR.

    Returns:
        str: Detected text or a helpful error message.
    """
    try:
        screenshot = pyautogui.screenshot()
        if not pytesseract or not Image:
            return "⚠ OCR not available. Install Tesseract and pytesseract."
        img = screenshot.convert("RGB")
        text = await asyncio.to_thread(pytesseract.image_to_string, img)
        text = text.strip()
        if not text:
            return "⚠ No text detected on screen."
        return text
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return f"❌ OCR কাজ করছে না: {str(e)[:100]}।"

@function_tool()
async def find_text_positions(query_text: str) -> str:
    """
    Find approximate screen positions of a given text string using OCR.

    Args:
        query_text: The text to search for (case-insensitive).

    Returns:
        str: JSON-like list of matches with bounding boxes and centers, or message if none found.
    """
    if not query_text.strip():
        return "❌ Provide text to find."
    try:
        if not pytesseract or not Image:
            return "⚠ OCR not available. Install Tesseract and pytesseract."
        ss = pyautogui.screenshot().convert("RGB")
        data = await asyncio.to_thread(pytesseract.image_to_data, ss, output_type=pytesseract.Output.DICT)
        ql = query_text.strip().lower()
        matches = []
        for i in range(len(data["text"])):
            word = (data["text"][i] or "").strip()
            if not word:
                continue
            if ql in word.lower():
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                cx, cy = x + w // 2, y + h // 2
                matches.append({"text": word, "bbox": [x, y, w, h], "center": [cx, cy]})
        if not matches:
            return "❌ No matching text found."
        import json as _json
        return _json.dumps(matches)
    except Exception as e:
        logger.error(f"find_text_positions error: {e}")
        return f"❌ Text খুঁজে পাচ্ছি না: {str(e)[:100]}।"

@function_tool()
async def click_text(query_text: str) -> str:
    """
    Click the first occurrence of given text on screen using OCR-detected bounding boxes.

    Args:
        query_text: Text to click (case-insensitive).

    Returns:
        str: Result of the click attempt.
    """
    if not query_text.strip():
        return "❌ Provide text to click."
    try:
        pos_json = await find_text_positions(query_text)
        if pos_json.startswith("❌") or pos_json.startswith("⚠"):
            return pos_json
        import json as _json
        matches = _json.loads(pos_json)
        if not matches:
            return "❌ No matching text to click."
        cx, cy = matches[0]["center"]
        pyautogui.moveTo(cx, cy, duration=0.2)
        pyautogui.click()
        return f"✅ Clicked '{query_text}' at ({cx},{cy})"
    except Exception as e:
        logger.error(f"click_text error: {e}")
        return f"❌ Click করতে পারছি না: {str(e)[:100]}।"