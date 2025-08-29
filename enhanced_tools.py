"""
Enhanced tool wrappers with built-in verification to prevent hallucination
"""
import asyncio
import logging
from livekit.agents import function_tool
from action_verifier import ActionVerifier
from vai_window_CTRL import open_app as original_open_app, close_app as original_close_app
from vai_file_opner import Play_file as original_play_file

logger = logging.getLogger(__name__)


def _log_event(tool_name: str, args: dict, success: bool, result: str):
    try:
        from db import log_tool_event
        log_tool_event(user_id="Protik_22", tool_name=tool_name, args=args, success=success, result_snippet=(result or "")[:200])
    except Exception:
        pass

@function_tool()
async def verified_open_app(app_title: str) -> str:
    """
    Opens an application with automatic verification to prevent hallucination.
    
    This tool will:
    1. Execute the open command
    2. Wait for the app to load
    3. Use screen vision to verify the app is actually open
    4. Report accurate status to user
    
    Args:
        app_title: Name of the application to open
    """
    try:
        # Step 1: Execute the original open command
        logger.info(f"Attempting to open {app_title}")
        open_result = await original_open_app(app_title)
        
        # Step 2: Wait for app to fully load
        await asyncio.sleep(3)
        
        # Step 3: Verify with screen vision
        logger.info(f"Verifying {app_title} is open")
        success, verify_message = await ActionVerifier.verify_app_opened(app_title)
        
        # Step 4: Return accurate status
        if success:
            msg = f"✅ SUCCESS: {app_title} is confirmed open and visible on screen!"
            _log_event("verified_open_app", {"app_title": app_title}, True, msg)
            return msg
        else:
            # Try one more time if failed
            logger.info(f"First attempt failed, retrying {app_title}")
            await asyncio.sleep(2)
            retry_success, retry_message = await ActionVerifier.verify_app_opened(app_title)
            
            if retry_success:
                msg = f"✅ SUCCESS: {app_title} is now confirmed open (took a moment to load)!"
                _log_event("verified_open_app", {"app_title": app_title}, True, msg)
                return msg
            else:
                msg = f"❌ দুঃখিত! {app_title} খুলতে পারছি না। {retry_message}। App টা install আছে তো?"
                _log_event("verified_open_app", {"app_title": app_title}, False, msg)
                return msg
                
    except Exception as e:
        msg = f"❌ আরে! {app_title} খুলতে পারছি না: {str(e)[:100]}। আবার try করি?"
        logger.error(f"Error in verified_open_app: {e}")
        _log_event("verified_open_app", {"app_title": app_title}, False, msg)
        return msg

@function_tool()
async def verified_close_app(window_title: str) -> str:
    """
    Closes an application with automatic verification to prevent hallucination.
    
    This tool will:
    1. Execute the close command
    2. Wait for the app to close
    3. Use screen vision to verify the app is actually closed
    4. Report accurate status to user
    
    Args:
        window_title: Name/title of the window to close
    """
    try:
        # Step 1: Execute the original close command
        logger.info(f"Attempting to close {window_title}")
        close_result = await original_close_app(window_title)
        
        # Step 2: Wait for app to close
        await asyncio.sleep(2)
        
        # Step 3: Verify with screen vision
        logger.info(f"Verifying {window_title} is closed")
        success, verify_message = await ActionVerifier.verify_app_closed(window_title)
        
        # Step 4: Return accurate status
        if success:
            msg = f"✅ SUCCESS: {window_title} is confirmed closed!"
            _log_event("verified_close_app", {"window_title": window_title}, True, msg)
            return msg
        else:
            # Try force close if still visible
            logger.info(f"App still visible, attempting force close for {window_title}")
            await original_close_app(window_title)  # Try again
            await asyncio.sleep(2)
            
            retry_success, retry_message = await ActionVerifier.verify_app_closed(window_title)
            
            if retry_success:
                msg = f"✅ SUCCESS: {window_title} is now confirmed closed!"
                _log_event("verified_close_app", {"window_title": window_title}, True, msg)
                return msg
            else:
                msg = f"❌ দুঃখিত! {window_title} বন্ধ করতে পারছি না। {retry_message}। Manual বন্ধ করতে হবে।"
                _log_event("verified_close_app", {"window_title": window_title}, False, msg)
                return msg
                
    except Exception as e:
        msg = f"❌ আরে! {window_title} বন্ধ করতে সমস্যা: {str(e)[:100]}।"
        logger.error(f"Error in verified_close_app: {e}")
        _log_event("verified_close_app", {"window_title": window_title}, False, msg)
        return msg

@function_tool()
async def verified_play_file(name: str) -> str:
    """
    Opens/plays a file with automatic verification to prevent hallucination.
    
    This tool will:
    1. Search for and open the file
    2. Wait for the file to load
    3. Use screen vision to verify the file is actually open
    4. Report accurate status to user
    
    Args:
        name: Name of the file to open/play
    """
    try:
        # Step 1: Execute the original file open command
        logger.info(f"Attempting to open file: {name}")
        file_result = await original_play_file(name)
        
        # Step 2: Wait for file to load
        await asyncio.sleep(3)
        
        # Step 3: Verify with screen vision
        logger.info(f"Verifying file {name} is open")
        success, verify_message = await ActionVerifier.verify_file_opened(name)
        
        # Step 4: Return accurate status
        if success:
            msg = f"✅ SUCCESS: File '{name}' is confirmed open and visible!"
            _log_event("verified_play_file", {"name": name}, True, msg)
            return msg
        else:
            msg = f"❌ দুঃখিত! File '{name}' খুলতে পারছি না। {verify_message}। File টা আছে তো?"
            _log_event("verified_play_file", {"name": name}, False, msg)
            return msg
                
    except Exception as e:
        msg = f"❌ আরে! File '{name}' খুলতে সমস্যা: {str(e)[:100]}।"
        logger.error(f"Error in verified_play_file: {e}")
        _log_event("verified_play_file", {"name": name}, False, msg)
        return msg