import os
import subprocess
import logging
import sys
import asyncio
from fuzzywuzzy import process

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func): 
        return func

try:
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError:
    win32gui = None
    win32con = None
    win32api = None
    win32process = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Setup encoding and logger
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App command map
APP_MAPPINGS = {
    "notepad": "notepad",
    "calculator": "calc",
    "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "vlc": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "command prompt": "cmd",
    "control panel": "control",
    "settings": "start ms-settings:",
    "paint": "mspaint",
    "vs code": "C:\\Users\\gaura\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
    "postman": "C:\\Users\\gaura\\AppData\\Local\\Postman\\Postman.exe"
}

# -------------------------
# Enhanced Window Management
# -------------------------
async def ensure_window_visible(title_keyword: str) -> bool:
    """Ensure window is visible and focused on screen"""
    if not gw:
        logger.warning("⚠ pygetwindow not available")
        return False

    title_keyword = title_keyword.lower().strip()
    
    # Wait for window to appear
    await asyncio.sleep(2)
    
    for attempt in range(3):  # Try 3 times
        for window in gw.getAllWindows():
            if title_keyword in window.title.lower():
                try:
                    # Force window to be visible
                    if window.isMinimized:
                        window.restore()
                        await asyncio.sleep(0.5)
                    
                    # Move window to visible area if off-screen
                    if window.left < 0 or window.top < 0:
                        window.moveTo(100, 100)
                        await asyncio.sleep(0.3)
                    
                    # Ensure window is not too small
                    if window.width < 400 or window.height < 300:
                        window.resizeTo(800, 600)
                        await asyncio.sleep(0.3)
                    
                    # Activate and focus
                    window.activate()
                    await asyncio.sleep(0.5)
                    
                    # Bring to front
                    if win32gui and win32con:
                        try:
                            hwnd = win32gui.FindWindow(None, window.title)
                            if hwnd:
                                win32gui.SetForegroundWindow(hwnd)
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                await asyncio.sleep(0.3)
                        except Exception as e:
                            logger.warning(f"Win32 operations failed: {e}")
                    
                    logger.info(f"✅ Window made visible: {window.title}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error managing window {window.title}: {e}")
                    continue
        
        if attempt < 2:
            await asyncio.sleep(1)
    
    return False

async def focus_window(title_keyword: str) -> bool:
    """Enhanced window focus with visibility checks"""
    return await ensure_window_visible(title_keyword)

# Index files/folders
async def index_items(base_dirs):
    item_index = []
    for base_dir in base_dirs:
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                item_index.append({"name": d, "path": os.path.join(root, d), "type": "folder"})
            for f in files:
                item_index.append({"name": f, "path": os.path.join(root, f), "type": "file"})
    logger.info(f"✅ Indexed {len(item_index)} items.")
    return item_index

async def search_item(query, index, item_type):
    filtered = [item for item in index if item["type"] == item_type]
    choices = [item["name"] for item in filtered]
    if not choices:
        return None
    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' with score {score}")
    if score > 70:
        for item in filtered:
            if item["name"] == best_match:
                return item
    return None

# File/folder actions
async def open_folder(path):
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.call(['xdg-open', path])
        folder_name = os.path.basename(path)
        focused = await focus_window(folder_name)
        if focused:
            return f"✅ Folder opened and focused: {folder_name}"
        else:
            return f"✅ Folder opened: {folder_name} (focus failed)"
    except Exception as e:
        logger.error(f"❌ Error opening folder: {e}")
        return f"❌ Error opening folder: {e}"

async def play_file(path):
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.call(['xdg-open', path])
        file_name = os.path.basename(path)
        focused = await focus_window(file_name)
        if focused:
            return f"✅ File opened and focused: {file_name}"
        else:
            return f"✅ File opened: {file_name} (focus failed)"
    except Exception as e:
        logger.error(f"❌ Error opening file: {e}")
        return f"❌ Error opening file: {e}"

async def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ Folder created: {path}"
    except Exception as e:
        return f"❌ Error creating folder: {e}"

async def rename_item(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return f"✅ Renamed to: {new_path}"
    except Exception as e:
        return f"❌ Rename failed: {e}"

async def delete_item(path):
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        return f"🗑️ Deleted: {path}"
    except Exception as e:
        return f"❌ Delete failed: {e}"

# vai command logic
@function_tool()
async def folder_file(command: str) -> str:
    """
    Handles folder and file actions like open, create, rename, or delete based on user command.

    Use this tool when the user wants to manage folders or files using natural language.
    Example prompts:
    - "Projects folder बनाओ"
    - "OldName को NewName में rename करो"
    - "xyz.mp4 delete कर दो"
    - "Music folder खोलो"
    - "Resume.pdf चलाओ"
    """

    folders_to_index = ["D:/"]
    index = await index_items(folders_to_index)
    command_lower = command.lower()

    if "create folder" in command_lower:
        folder_name = command.replace("create folder", "").strip()
        path = os.path.join("D:/", folder_name)
        return await create_folder(path)

    if "rename" in command_lower:
        parts = command_lower.replace("rename", "").strip().split("to")
        if len(parts) == 2:
            old_name = parts[0].strip()
            new_name = parts[1].strip()
            item = await search_item(old_name, index, "folder")
            if item:
                new_path = os.path.join(os.path.dirname(item["path"]), new_name)
                return await rename_item(item["path"], new_path)
        return "❌ Invalid rename command."

    if "delete" in command_lower:
        item = await search_item(command, index, "folder") or await search_item(command, index, "file")
        if item:
            return await delete_item(item["path"])
        return "❌ Item not found for deletion."

    if "folder" in command_lower or "open folder" in command_lower:
        item = await search_item(command, index, "folder")
        if item:
            return await open_folder(item["path"])
        return "❌ Folder not found."

    item = await search_item(command, index, "file")
    if item:
        return await play_file(item["path"])

    return "⚠️ No matches found. Please check the file/folder name and try again." 

# App control
@function_tool()
async def open_app(app_title: str) -> str:
    """
    Opens a desktop app like Notepad, Chrome, VLC, etc.

    Use this tool when the user asks to launch an application on their computer.
    Example prompts:
    - "Notepad खोलो"
    - "Chrome open करो"
    - "VLC media player चलाओ"
    - "Calculator launch करो"
    """

    app_title = app_title.lower().strip()
    app_command = APP_MAPPINGS.get(app_title, app_title)
    
    try:
        # Launch app
        process = await asyncio.create_subprocess_shell(
            f'start "" "{app_command}"', 
            shell=True,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for process to complete
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return f"❌ Failed to launch {app_title}. Error: {stderr.decode() if stderr else 'Unknown error'}"
        
        # Wait for app to start
        await asyncio.sleep(3)
        
        # Try to ensure window is visible
        focused = await ensure_window_visible(app_title)
        
        # Return status without claiming success - let screen_vision_tool verify
        if focused:
            return f"⏳ {app_title} launch command executed. Window management attempted. Please verify visually."
        else:
            return f"⏳ {app_title} launch command executed. Window not found yet. Please verify visually."
            
    except Exception as e:
        return f"❌ Failed to launch {app_title}: {e}"

@function_tool()
async def close_app(window_title: str) -> str:
    """
    Closes the applications window by its title.

    Use this tool when the user wants to close any app or window on their desktop.
    Example prompts:
    - "Notepad बंद करो"
    - "Close VLC"
    - "Chrome की window बंद कर दो"
    - "Calculator को बंद करो"
    """

    if not win32gui:
        return "❌ win32gui not available"

    windows_closed = 0
    errors = []

    def enumHandler(hwnd, _):
        nonlocal windows_closed, errors
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if window_title.lower() in window_text.lower():
                try:
                    # Try graceful close first
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    
                    # Wait a moment
                    import time
                    time.sleep(1)
                    
                    # Check if still exists, then force close
                    if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid:
                            result = os.system(f'taskkill /PID {pid} /F')
                            if result == 0:
                                windows_closed += 1
                            else:
                                errors.append(f"Failed to force close {window_text}")
                    else:
                        windows_closed += 1
                        
                except Exception as e:
                    errors.append(f"Error closing {window_text}: {e}")
                    logger.error(f"Error closing window: {e}")

    win32gui.EnumWindows(enumHandler, None)
    
    # Return status without claiming success - let screen_vision_tool verify
    if windows_closed > 0:
        return f"⏳ Close command executed for {windows_closed} window(s) matching '{window_title}'. Please verify visually."
    elif errors:
        return f"❌ Errors occurred while closing '{window_title}': {'; '.join(errors)}"
    else:
        return f"⚠️ No visible windows found matching '{window_title}'. Please verify the application name." 