import pyautogui
import asyncio
import time
from datetime import datetime
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
from typing import List
from livekit.agents import function_tool

# ---------------------
# Enhanced SafeController Class
# ---------------------
class SafeController:
    def __init__(self):
        self.active = False
        self.activation_time = None
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.valid_keys = set("abcdefghijklmnopqrstuvwxyz1234567890")
        self.special_keys = {
            "enter": Key.enter, "space": Key.space, "tab": Key.tab,
            "shift": Key.shift, "ctrl": Key.ctrl, "alt": Key.alt,
            "esc": Key.esc, "backspace": Key.backspace, "delete": Key.delete,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "caps_lock": Key.caps_lock, "cmd": Key.cmd, "win": Key.cmd,
            "home": Key.home, "end": Key.end,
            "page_up": Key.page_up, "page_down": Key.page_down
        }

    def resolve_key(self, key):
        return self.special_keys.get(key.lower(), key)

    def log(self, action: str):
        with open("control_log.txt", "a", encoding='utf-8') as f:
            f.write(f"{datetime.now()}: {action}\n")

    def activate(self, token=None):
        if token != "my_secret_token":
            self.log("Activation attempt failed.")
            return
        self.active = True
        self.activation_time = time.time()
        self.log("Controller auto-activated.")

    def deactivate(self):
        self.active = False
        self.log("Controller auto-deactivated.")

    def is_active(self):
        return self.active

    async def ensure_active_window(self):
        """Ensure the active window is visible and focused"""
        try:
            # Get current mouse position
            current_x, current_y = self.mouse.position
            
            # Move mouse slightly to ensure focus
            self.mouse.position = (current_x + 1, current_y + 1)
            await asyncio.sleep(0.1)
            self.mouse.position = (current_x, current_y)
            await asyncio.sleep(0.1)
            
            # Click to ensure focus
            self.mouse.click(Button.left, 1)
            await asyncio.sleep(0.2)
            
        except Exception as e:
            self.log(f"Error ensuring active window: {e}")

    async def move_cursor(self, direction: str, distance: int = 100):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            x, y = self.mouse.position
            if direction == "left": 
                new_x, new_y = (x - distance, y)
            elif direction == "right": 
                new_x, new_y = (x + distance, y)
            elif direction == "up": 
                new_x, new_y = (x, y - distance)
            elif direction == "down": 
                new_x, new_y = (x, y + distance)
            else:
                return f"❌ Invalid direction: {direction}"
            
            # Move cursor with animation
            self.mouse.position = (new_x, new_y)
            await asyncio.sleep(0.3)
            
            self.log(f"Mouse moved {direction} to ({new_x}, {new_y})")
            return f"🖱️ Moved mouse {direction} to position ({new_x}, {new_y})."
            
        except Exception as e:
            self.log(f"Error moving cursor: {e}")
            return f"❌ Error moving cursor: {e}"

    async def mouse_click(self, button: str = "left"):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            if button == "left": 
                self.mouse.click(Button.left, 1)
            elif button == "right": 
                self.mouse.click(Button.right, 1)
            elif button == "double": 
                self.mouse.click(Button.left, 2)
            else:
                return f"❌ Invalid button: {button}"
            
            await asyncio.sleep(0.3)
            self.log(f"Mouse clicked: {button}")
            return f"🖱️ {button.capitalize()} click performed at current position."
            
        except Exception as e:
            self.log(f"Error clicking mouse: {e}")
            return f"❌ Error clicking mouse: {e}"

    async def scroll_cursor(self, direction: str, amount: int = 10):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            if direction == "up": 
                self.mouse.scroll(0, amount)
            elif direction == "down": 
                self.mouse.scroll(0, -amount)
            else:
                return f"❌ Invalid scroll direction: {direction}"
            
            await asyncio.sleep(0.3)
            self.log(f"Mouse scrolled {direction} by {amount}")
            return f"🖱️ Scrolled {direction} by {amount} units."
            
        except Exception as e:
            self.log(f"Error scrolling: {e}")
            return f"❌ Error scrolling: {e}"

    async def type_text(self, text: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            # Clear any existing text first
            self.keyboard.press(Key.ctrl)
            self.keyboard.press('a')
            self.keyboard.release('a')
            self.keyboard.release(Key.ctrl)
            await asyncio.sleep(0.2)
            
            # Type the new text
            for char in text:
                if not char.isprintable():
                    continue
                try:
                    self.keyboard.press(char)
                    self.keyboard.release(char)
                    await asyncio.sleep(0.05)
                except Exception:
                    continue
            
            await asyncio.sleep(0.3)
            self.log(f"Typed text: {text}")
            return f"⌨️ Typed: '{text}' at current position."
            
        except Exception as e:
            self.log(f"Error typing text: {e}")
            return f"❌ Error typing text: {e}"

    async def press_key(self, key: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            if key.lower() not in self.special_keys and key.lower() not in self.valid_keys:
                return f"❌ Invalid key: {key}"
            
            k = self.resolve_key(key)
            self.keyboard.press(k)
            self.keyboard.release(k)
            
            await asyncio.sleep(0.3)
            self.log(f"Pressed key: {key}")
            return f"⌨️ Key '{key}' pressed successfully."
            
        except Exception as e:
            self.log(f"Error pressing key: {e}")
            return f"❌ Error pressing key: {e}"

    async def press_hotkey(self, keys: List[str]):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            resolved = []
            for k in keys:
                if k.lower() not in self.special_keys and k.lower() not in self.valid_keys:
                    return f"❌ Invalid key in hotkey: {k}"
                resolved.append(self.resolve_key(k))

            # Press all keys together
            for k in resolved: 
                self.keyboard.press(k)
            
            await asyncio.sleep(0.1)
            
            # Release all keys in reverse order
            for k in reversed(resolved): 
                self.keyboard.release(k)
            
            await asyncio.sleep(0.3)
            self.log(f"Pressed hotkey: {' + '.join(keys)}")
            return f"⌨️ Hotkey {' + '.join(keys)} pressed successfully."
            
        except Exception as e:
            self.log(f"Error pressing hotkey: {e}")
            return f"❌ Error pressing hotkey: {e}"

    async def control_volume(self, action: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            if action == "up": 
                pyautogui.press("volumeup")
            elif action == "down": 
                pyautogui.press("volumedown")
            elif action == "mute": 
                pyautogui.press("volumemute")
            else:
                return f"❌ Invalid volume action: {action}"
            
            await asyncio.sleep(0.3)
            self.log(f"Volume control: {action}")
            return f"🔊 Volume {action} successfully."
            
        except Exception as e:
            self.log(f"Error controlling volume: {e}")
            return f"❌ Error controlling volume: {e}"

    async def swipe_gesture(self, direction: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        
        try:
            await self.ensure_active_window()
            
            screen_width, screen_height = pyautogui.size()
            center_x, center_y = screen_width // 2, screen_height // 2
            
            # Define swipe distances
            swipe_distance = 200
            
            if direction == "up":
                start_x, start_y = center_x, center_y + swipe_distance
                end_x, end_y = center_x, center_y - swipe_distance
            elif direction == "down":
                start_x, start_y = center_x, center_y - swipe_distance
                end_x, end_y = center_x, center_y + swipe_distance
            elif direction == "left":
                start_x, start_y = center_x + swipe_distance, center_y
                end_x, end_y = center_x - swipe_distance, center_y
            elif direction == "right":
                start_x, start_y = center_x - swipe_distance, center_y
                end_x, end_y = center_x + swipe_distance, center_y
            else:
                return f"❌ Invalid swipe direction: {direction}"
            
            # Perform swipe with animation
            pyautogui.moveTo(start_x, start_y, duration=0.2)
            pyautogui.dragTo(end_x, end_y, duration=0.5)
            
            await asyncio.sleep(0.5)
            self.log(f"Swipe gesture: {direction}")
            return f"🖱️ Swipe {direction} gesture completed successfully."
            
        except Exception as e:
            self.log(f"Error performing swipe: {e}")
            return f"❌ Error performing swipe: {e}"

controller = SafeController()

async def with_temporary_activation(fn, *args, **kwargs):
    print(f"🔍 TEMP ACTIVATION: {fn.__name__} | args: {args}")
    controller.activate("my_secret_token")
    
    try:
        result = await fn(*args, **kwargs)
        await asyncio.sleep(2)
        return result
    finally:
        controller.deactivate()

@function_tool()
async def move_cursor_tool(direction: str, distance: int = 100):
    """
    Temporarily activates the controller and moves the mouse cursor in a specified direction.

    Args:
        direction (str): Direction to move the cursor. Must be one of ["up", "down", "left", "right"].
        distance (int, optional): Number of pixels to move the cursor. Defaults to 100.

    Returns:
        str: A message describing the mouse movement action.

    Note:
        The controller is automatically activated before the action and deactivated afterward.
    """

    return await with_temporary_activation(controller.move_cursor, direction, distance)

@function_tool()
async def mouse_click_tool(button: str = "left"):
    """
    Temporarily activates the controller and performs a mouse click.

    Simulates clicking behavior for automation or voice command triggers.

    Args:
        button (str, optional): Type of mouse click to perform.
            Must be one of ["left", "right", "double"]. Defaults to "left".

    Returns:
        str: A message indicating the type of mouse click performed.

    Notes:
        - "double" simulates a double left-click.
        - Useful for GUI automation or hands-free system interaction.
    """

    return await with_temporary_activation(controller.mouse_click, button)

@function_tool()
async def scroll_cursor_tool(direction: str, amount: int = 10):
    """
    Scrolls the screen vertically in the specified direction.

    Useful for commands like "scroll down" or "upar karo".

    Args:
        direction (str): The scroll direction. Must be either "up" or "down".
        amount (int, optional): The scroll intensity or number of scroll steps. Defaults to 10.

    Returns:
        str: A message indicating the direction and magnitude of the scroll action.

    Notes:
        - Positive `amount` values scroll further; can be tuned for smooth or fast scrolling.
        - Designed for fuzzy natural language control.
    """

    return await with_temporary_activation(controller.scroll_cursor, direction, amount)

@function_tool()
async def type_text_tool(text: str):
    """
    Simulates typing the given text character by character, as if entered manually from a keyboard.

    Useful for commands like "type hello world" or "hello likho".

    Args:
        text (str): The full string to type, including spaces, punctuation, and symbols.

    Returns:
        str: A message confirming the typed input.
    """

    return await with_temporary_activation(controller.type_text, text)

@function_tool()
async def press_key_tool(key: str):
    """
    Simulates pressing a single key on the keyboard, like Enter, Esc, or any letter/number.

    Useful for commands like "Enter दबाओ", "Escape दबाओ", or "A press करो".

    Args:
        key (str): The name of the key to press (e.g., "enter", "a", "ctrl", "esc").

    Returns:
        str: A message confirming the key press or an error if the key is invalid.
    """

    return await with_temporary_activation(controller.press_key, key)

@function_tool()
async def press_hotkey_tool(keys: List[str]):
    """
    Simulates pressing a keyboard shortcut like Ctrl+S, Alt+F4, etc.

    Use this when the user says something like "save करो", "window बंद करो", 
    or "refresh कर दो".

    Args:
        keys (List[str]): List of key names to press together (e.g., ["ctrl", "s"]).

    Returns:
        str: A message indicating which hotkey combination was pressed.
    """

    return await with_temporary_activation(controller.press_hotkey, keys)

@function_tool()
async def control_volume_tool(action: str):
    """
    Changes the system volume using keyboard emulation.

    Use this when the user says something like "volume बढ़ाओ", "mute कर दो", 
    or "lower the sound".

    Args:
        action (str): One of ["up", "down", "mute"].

    Returns:
        str: A message confirming the volume change.
    """

    return await with_temporary_activation(controller.control_volume, action)

@function_tool()
async def swipe_gesture_tool(direction: str):
    """
    Simulates a swipe gesture on the screen using the mouse.

    Use this when the user wants to swipe in a direction like up, down, left, or right — 
    for example: "नीचे स्क्रॉल करो", "left swipe करो", or "screen ऊपर करो".

    Args:
        direction (str): One of ["up", "down", "left", "right"].

    Returns:
        str: A message describing the swipe action.
    """

    return await with_temporary_activation(controller.swipe_gesture, direction)

