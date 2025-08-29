import os
import time
import asyncio
import logging
import requests
import json
from pathlib import Path
from typing import Optional
from PIL import Image
from livekit.agents import function_tool
from dotenv import load_dotenv
from random import randint

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HFImageGenerator:
    """Hugging Face AI powered image generator for vai."""
    
    def __init__(self, output_dir: str = "Database/Images"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # AI Configuration
        self.api_key = os.getenv("HF_API_KEY")
        self.base_url = "https://api-inference.huggingface.co/models/"
        
        # Models
        self.text_model = "mistralai/Mistral-7B-Instruct-v0.1"
        self.image_model = "stabilityai/stable-diffusion-xl-base-1.0"
        
        # Default settings
        self.config = {
            "width": 1024,
            "height": 1024,
            "quality": "hd",
            "style": "natural"
        }
        
        # Enhanced negative prompts for better quality
        self.default_negative = (
            "low quality, blurry, pixelated, distorted, deformed, ugly, "
            "bad anatomy, extra limbs, watermark, text, signature, "
            "cartoon, anime, sketch, drawing"
        )
        
        if not self.api_key:
            logger.warning("⚠️ HF_API_KEY not found in environment variables")
        
        logger.info(f"✅ HFImageGenerator initialized. Output: {self.output_dir}")
    
    async def enhance_prompt_with_grok(self, user_prompt: str) -> str:
        """
        Use AI to enhance and optimize the user's prompt for better image generation.
        """
        if not self.api_key:
            return user_prompt
        
        try:
            system_content = "You are an expert image prompt enhancer. Take the user's simple prompt and optimize it for detailed, artistic and high-quality image generation. Respond with only the enhanced prompt, no extra text."
            user_content = f"Enhance this prompt for image generation: {user_prompt}"
            full_prompt = f"[INST] {system_content}\n{user_content} [/INST]"
            
            enhancement_request = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make async request to AI API
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(
                    self.base_url + self.text_model,
                    headers=headers,
                    json=enhancement_request,
                    timeout=10
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                enhanced_prompt = result[0]['generated_text'].strip()
                logger.info(f"🚀 Prompt enhanced by AI: {enhanced_prompt[:100]}...")
                return enhanced_prompt
            else:
                logger.warning(f"⚠️ AI API error: {response.status_code}")
                return user_prompt
                
        except Exception as e:
            logger.error(f"❌ Error enhancing prompt with AI: {e}")
            return user_prompt
    
    async def generate_image_with_hf(self, prompt: str) -> Optional[str]:
        """
        Generate image using Hugging Face API with Stable Diffusion XL.
        """
        try:
            if not self.api_key:
                logger.warning("❌ AI API key not available")
                return None
            
            timestamp = int(time.time())
            filename = f"ai_generated_{timestamp}.png"
            filepath = self.output_dir / filename
            
            seed = randint(0, 1000000)
            enhanced_prompt = f"{prompt}, quality=4k, sharpness=maximum, Ultra High details, high resolution, seed={seed}"
            
            # Create image generation request
            image_request = {
                "inputs": enhanced_prompt,
                "parameters": {
                    "negative_prompt": self.default_negative,
                    "width": self.config["width"],
                    "height": self.config["height"]
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"🎨 Generating image with AI: {prompt[:50]}...")
            
            # Make request to AI API
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.base_url + self.image_model,
                    headers=headers,
                    json=image_request,
                    timeout=60
                )
            )
            
            if response.status_code == 200:
                try:
                    # Try to parse as JSON (in case of base64 response)
                    response_json = response.json()
                    if isinstance(response_json, list) and "generated_text" in response_json[0]:
                        # Handle if it's text response by mistake
                        logger.warning("Received text response instead of image")
                        return None
                    # Assuming it might return {'image': base64}
                    image_bytes = base64.b64decode(response_json.get('image', ''))
                except ValueError:
                    # If not JSON, assume raw image bytes
                    image_bytes = response.content
                
                if image_bytes:
                    # Save the generated image
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    
                    logger.info(f"✅ Image successfully generated with AI: {filepath}")
                    return str(filepath)
                else:
                    logger.warning("No image data in response")
                    return None
            else:
                logger.warning(f"⚠️ AI image generation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error with AI image generation: {e}")
            return None
    
    async def generate_image_async(self, prompt: str, enhance_prompt: bool = True) -> Optional[str]:
        """
        Main image generation method with AI integration.
        """
        if not prompt.strip():
            logger.error("❌ Empty prompt provided")
            return None
        
        try:
            # Enhance prompt using AI if enabled
            if enhance_prompt:
                enhanced_prompt = await self.enhance_prompt_with_grok(prompt)
            else:
                enhanced_prompt = prompt
            
            # Generate image using AI
            filepath = await self.generate_image_with_hf(enhanced_prompt)
            
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Error in main generation method: {e}")
            return None
    
    async def open_image_async(self, filepath: str) -> bool:
        """
        Open generated image with system default viewer.
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"❌ Image file not found: {filepath}")
                return False
            
            # Open in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._open_image_sync, filepath)
            
            logger.info(f"✅ Image opened: {os.path.basename(filepath)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error opening image: {e}")
            return False
    
    def _open_image_sync(self, filepath: str):
        """Synchronous image opening helper."""
        if os.name == 'nt':  # Windows
            os.startfile(filepath)
        else:  # Linux/Mac
            import subprocess
            subprocess.call(['xdg-open' if os.name == 'posix' else 'open', filepath])
    
    def get_latest_image(self) -> Optional[str]:
        """Get the most recently generated image."""
        images = list(self.output_dir.glob("*.png"))
        if not images:
            return None
        
        latest = max(images, key=lambda p: p.stat().st_mtime)
        return str(latest)
    
    def list_generated_images(self):
        """List all generated images."""
        images = list(self.output_dir.glob("*.png"))
        if images:
            logger.info(f"📸 {len(images)} images found in database")
            for img in sorted(images)[-10:]:  # Show last 10
                logger.info(f"  - {img.name}")
        else:
            logger.info("📸 No generated images found")
        return images


# Global instance
_hf_generator = HFImageGenerator()

@function_tool()
async def generate_image_tool(prompt: str, enhance_with_ai: bool = True) -> str:
    """
    Generates high-quality image with AI.
    
    Use this tool when user asks to make an image.
    Example commands:
    - "Make a beautiful sunset picture"
    - "Generate mountain and river image"
    - "Make a rose flower picture"
    - "Create a beautiful landscape picture"
    
    Args:
        prompt: Image description to make
        enhance_with_ai: Whether to enhance prompt with AI
    """
    
    if not prompt.strip():
        return "❌ Please tell what picture to make."
    
    try:
        logger.info(f"🎨 Image generation starting: {prompt}")
        
        # Generate image with AI
        filepath = await _hf_generator.generate_image_async(
            prompt=prompt,
            enhance_prompt=enhance_with_ai
        )
        
        if filepath:
            # Auto-open the generated image
            await _hf_generator.open_image_async(filepath)
            filename = os.path.basename(filepath)
            return f"✅ Picture successfully made and opened: {filename}"
        else:
            return "❌ Could not make picture. Please try again."
            
    except Exception as e:
        logger.error(f"❌ Error in generate image tool: {e}")
        return f"❌ আরে! Picture বানাতে সমস্যা: {str(e)[:100]}।"

@function_tool()
async def show_latest_image_tool() -> str:
    """
    Shows the latest generated image.
    
    Use this tool when user wants to see last image.
    Example commands:
    - "Show last picture"
    - "Open previous image"
    - "Show last generated photo"
    """
    
    try:
        latest_image = _hf_generator.get_latest_image()
        
        if latest_image:
            success = await _hf_generator.open_image_async(latest_image)
            if success:
                filename = os.path.basename(latest_image)
                return f"✅ Latest picture opened: {filename}"
            else:
                return "❌ Problem opening picture."
        else:
            return "❌ No picture found in database."
            
    except Exception as e:
        logger.error(f"❌ Error in show latest image: {e}")
        return f"❌ Latest picture দেখাতে সমস্যা: {str(e)[:100]}।"

@function_tool()
async def list_images_tool() -> str:
    """
    Shows list of all generated images.
    
    Use this tool when user wants to see all images.
    Example commands:
    - "Show all pictures"
    - "List all generated images"
    - "How many pictures made?"
    - "Show me all pictures"
    """
    
    try:
        images = _hf_generator.list_generated_images()
        
        if images:
            count = len(images)
            recent_names = [img.name for img in sorted(images)[-5:]]  # Last 5
            
            result = f"📸 Total {count} pictures in database.\n"
            result += "Recent 5 pictures:\n"
            result += "\n".join(f"• {name}" for name in recent_names)
            
            return result
        else:
            return "📸 No pictures made yet."
            
    except Exception as e:
        logger.error(f"❌ Error in list images: {e}")
        return f"❌ Picture list দেখাতে সমস্যা: {str(e)[:100]}।"

@function_tool()
async def image_status_tool() -> str:
    """
    Checks status of AI and image generation system.
    
    Example commands:
    - "Check image system status"
    - "AI connected?"
    - "How is picture making system?"
    """
    
    try:
        status_info = []
        
        # Check AI API key
        if _hf_generator.api_key:
            status_info.append("✅ AI: Connected")
        else:
            status_info.append("⚠️ AI: API key not found")
        
        # Check output directory
        if _hf_generator.output_dir.exists():
            status_info.append(f"✅ Output Directory: {_hf_generator.output_dir}")
        else:
            status_info.append("❌ Output Directory: not found")
        
        # Count existing images
        images = _hf_generator.list_generated_images()
        status_info.append(f"📸 Total Images: {len(images)}")
        
        # System info
        status_info.append(f"🖥️ Platform: {os.name}")
        
        return "🔧 Image Generation System Status:\n" + "\n".join(status_info)
        
    except Exception as e:
        logger.error(f"❌ Error in status check: {e}")
        return f"❌ Status check এ সমস্যা: {str(e)[:100]}।"

def interactive_mode():
    """Interactive mode for testing image generation."""
    print("🎨 vai AI Image Generator - Interactive Mode")
    print("Commands: 'quit' to exit, 'status' for system info\n")
    
    while True:
        try:
            user_input = input("Give picture description: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Closing image generator...")
                break
            
            if user_input.lower() == 'status':
                # Run status check
                import asyncio
                status = asyncio.run(image_status_tool())
                print(status)
                continue
                
            if not user_input:
                print("❌ Please give picture description.")
                continue
            
            # Generate image
            print(f"🎨 Making picture: {user_input}")
            
            import asyncio
            result = asyncio.run(generate_image_tool(user_input))
            print(result)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main function for standalone usage."""
    print("🚀 AI Image Generator for vai")
    interactive_mode()

if __name__ == "__main__":
    main()