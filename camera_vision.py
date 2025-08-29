import os
import asyncio
import logging
import cv2
import io
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from livekit.agents import function_tool
import google.generativeai as genai
try:
    from fer import FER  # Optional dependency
except Exception:
    FER = None

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY missing in .env")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class AdvancedCameraVision:
    def __init__(self):
        self.cap = None
        self.fer = FER(mtcnn=True) if FER is not None else None
        self.monitoring = False
        self.monitor_interval = 3
        self.last_emotion = None
        self.alert_threshold = 0.5

    async def start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                return "❌ Camera access failed."
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        return "✅ Advanced camera started with emotion detection." if self.fer else "✅ Camera started (emotion model unavailable)."

    async def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self.monitoring = False
        return "✅ Camera stopped."

    async def capture_and_detect(self):
        if self.cap is None or not self.cap.isOpened():
            await self.start_camera()
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        emotion_detected = None
        confidence = 0
        if self.fer is not None:
            try:
                emotions = self.fer.top_emotion(rgb_frame)
                emotion_detected = emotions[0] if emotions else None
                confidence = emotions[1] if emotions and len(emotions) > 1 else 0
            except Exception as e:
                logger.warning(f"Emotion detection unavailable: {e}")
                self.fer = None

        gesture = "hand_raised" if len(faces) > 0 and frame.shape[0] > 300 else None

        return pil_image, emotion_detected, gesture

    async def process_with_gemini_advanced(self, image, emotion, gesture, query: str):
        try:
            enhanced_query = f"{query} Detected emotion: {emotion or 'unknown'}, gesture: {gesture or 'none'}. Respond in Bengali if mood is low."
            
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()

            response = model.generate_content([enhanced_query, {"mime_type": "image/png", "data": img_bytes}])
            if response and response.text:
                return response.text.strip()
            return "⚠️ No Gemini response."
        except Exception as e:
            logger.error(f"Advanced Gemini error: {e}")
            return f"❌ Processing error: {e}"

    async def check_alert(self, emotion, confidence):
        if emotion in ['sad', 'angry', 'fear'] and confidence > self.alert_threshold:
            if emotion != self.last_emotion:
                self.last_emotion = emotion
                logger.warning(f"🚨 Alert: Detected {emotion} with confidence {confidence}")
                return f"🚨 আরে, মন খারাপ লাগছে? আমি আছি তোমার পাশে! কী হয়েছে বলো?"
        return None

# Global camera instance
_camera = AdvancedCameraVision()

@function_tool()
async def advanced_camera_vision_tool(query: str = "Analyze my current expression and mood with advanced detection.") -> str:
    """
    Advanced camera analysis with emotion detection and Gemini processing.
    Use for mood checks: "আমার emotion চেক করো", "আমি কেমন লাগছি?"
    """
    try:
        image, emotion, gesture = await _camera.capture_and_detect()
        if image is None:
            return "❌ Camera capture failed."

        analysis = await _camera.process_with_gemini_advanced(image, emotion, gesture, query)
        alert = await _camera.check_alert(emotion, 0.6 if emotion else 0)
        
        result = f"✅ Emotion: {emotion or 'unknown'}, Analysis: {analysis}"
        if alert:
            result += f"\n{alert}"
        if _camera.fer is None:
            result += "\nℹ️ Emotion model not installed; ran without FER."
        return result
    except Exception as e:
        return f"❌ Camera vision এ সমস্যা: {str(e)[:100]}।"

@function_tool()
async def start_advanced_monitoring(interval: int = 5) -> str:
    """
    Starts continuous emotion monitoring with alerts.
    Use: "Advanced monitoring start করো", "আমার mood track করো"
    """
    await _camera.start_camera()
    _camera.monitoring = True
    _camera.monitor_interval = interval
    
    async def monitor_loop():
        while _camera.monitoring:
            try:
                image, emotion, gesture = await _camera.capture_and_detect()
                if image and emotion:
                    alert = await _camera.check_alert(emotion, 0.7)
                    if alert:
                        logger.info(f"Mood Alert: {emotion} - {alert}")
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                break
    
    asyncio.create_task(monitor_loop())
    return f"✅ Advanced emotion monitoring started. Interval: {interval}s. বলো 'stop monitoring' to end."

@function_tool()
async def stop_advanced_monitoring() -> str:
    """
    Stops emotion monitoring.
    """
    _camera.monitoring = False
    await _camera.stop_camera()
    return "✅ Advanced monitoring stopped."