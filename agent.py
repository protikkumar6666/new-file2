from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation
import os

# Import your custom modules
from vai_prompts import instructions_prompt, Reply_prompts
from vai_google_search import google_search, get_current_datetime
from vai_get_whether import get_weather
from vai_window_CTRL import folder_file
from keyboard_mouse_CTRL import (
    move_cursor_tool, mouse_click_tool, scroll_cursor_tool, 
    type_text_tool, press_key_tool, swipe_gesture_tool, 
    press_hotkey_tool, control_volume_tool
)
from memory_loop import MemoryExtractor
from image import (
    generate_image_tool, 
    show_latest_image_tool, 
    list_images_tool,
    image_status_tool
)
from screenvision import screen_vision_tool
from enhanced_tools import verified_open_app, verified_close_app, verified_play_file
from camera_vision import advanced_camera_vision_tool, start_advanced_monitoring, stop_advanced_monitoring

from whatsapp import (
    whatsapp_message, whatsapp_call, whatsapp_automation, add_contact,
    analyze_whatsapp_message, whatsapp_group_management, whatsapp_media_handler,
    whatsapp_analytics, whatsapp_backup, whatsapp_security_check
)
from web_automation import (
    start_browser, close_browser, go_to, wait_for_selector, click, type_text, press_key, scroll_by,
    search_and_click, extract_page_text, youtube_search_play, amazon_search_summary
)
from analytics_engine import (
    get_performance_dashboard, optimize_performance, analyze_user_behavior, start_performance_monitoring
)

load_dotenv()


class Assistant(Agent):
    def __init__(self, chat_ctx) -> None:
        from user_profile import UserProfile
        profile = UserProfile("Protik_22")
        personalization = profile.get_context_string()
        super().__init__(chat_ctx = chat_ctx,
                        instructions=instructions_prompt + personalization,
                        llm=google.beta.realtime.RealtimeModel(voice="Aoede"),
                        tools=[
                                google_search,
                                get_current_datetime,
                                get_weather,
                                verified_open_app,
                                verified_close_app,
                                folder_file,
                                verified_play_file,
                                move_cursor_tool,
                                mouse_click_tool,
                                scroll_cursor_tool,
                                type_text_tool,
                                press_key_tool,
                                press_hotkey_tool,
                                control_volume_tool,
                                swipe_gesture_tool,
                                generate_image_tool,
                                show_latest_image_tool, 
                                list_images_tool,
                                image_status_tool,
                                screen_vision_tool,
                                advanced_camera_vision_tool,
                                start_advanced_monitoring,
                                stop_advanced_monitoring,
                                whatsapp_message,
                                whatsapp_call,
                                whatsapp_automation,
                                add_contact,
                                analyze_whatsapp_message,
                                whatsapp_group_management,
                                whatsapp_media_handler,
                                whatsapp_analytics,
                                whatsapp_backup,
                                whatsapp_security_check,
                                start_browser, close_browser, go_to, wait_for_selector, click, type_text, press_key, scroll_by,
                                search_and_click, extract_page_text, youtube_search_play, amazon_search_summary,
                                get_performance_dashboard, optimize_performance, analyze_user_behavior]
                                )

async def _proactive_reengagement_loop(session: AgentSession, check_interval_s: int = 5, idle_s: int = 30):
    """After 30s of no new messages, proactively talk about the last user topic."""
    import asyncio
    last_len = len(session.history.items)
    last_change = asyncio.get_event_loop().time()
    # Load dynamic preferences
    pref_lang = "bangla"
    formality = None
    idle_override = None
    try:
        from user_profile import UserProfile as _UP
        _prof = _UP("Protik_22")
        pref_lang = (_prof.data or {}).get("preferred_language") or pref_lang
        formality = (_prof.data or {}).get("greeting_style")
        idle_override = (_prof.data or {}).get("proactive_idle_seconds")
    except Exception:
        pass
    if isinstance(idle_override, int) and 5 <= idle_override <= 600:
        idle_s = idle_override
    while True:
        await asyncio.sleep(check_interval_s)
        try:
            items = session.history.items
            if len(items) != last_len:
                last_len = len(items)
                last_change = asyncio.get_event_loop().time()
                continue
            idle_for = asyncio.get_event_loop().time() - last_change
            if idle_for >= idle_s:
                # Find last user message content to continue the topic
                last_user_msg = None
                for msg in reversed(items):
                    role = getattr(msg, "role", None)
                    content = getattr(msg, "content", None)
                    if str(role).lower() in ["user", "client"] and isinstance(content, str) and content.strip():
                        last_user_msg = content.strip()
                        break
                topic_hint = (last_user_msg or "our last topic").split("\n")[0][:200]
                # Style tuning via profile (formal/informal + language)
                if (pref_lang or "").lower() == "hinglish":
                    if formality == "formal":
                        prompt_text = (
                            f"{idle_s} seconds ho gaye bina baat ke, main respectfully follow-up kar raha/rahi hoon. "
                            f"Jo hum baat kar rahe the — \"{topic_hint}\" — wahi se continue karein? "
                            "Chahein to main short next steps suggest kar doon. Ek line me batayiye."
                        )
                    else:
                        prompt_text = (
                            f"Arey, {idle_s}s se sab quiet! Main hi ping kar deta/deti hoon \n"
                            f"Wahin se continue karein — \"{topic_hint}\"?\n"
                            "- Bolo: 'continue' — main aage badhta/badhti hoon\n"
                            "- Ya main chhota next steps bana doon?\n"
                            "Ek line me bolo, kya karu?"
                        )
                else:
                    if formality == "formal":
                        prompt_text = (
                            "গত কিছুক্ষণ কোনো বার্তা পাইনি, তাই ভদ্রভাবে খোঁজ নিচ্ছি। "
                            "আমরা যে বিষয়টি নিয়ে আলোচনা করছিলাম — \"" + topic_hint + "\" — সেখান থেকেই কি এগোবো? "
                            "ইচ্ছা করলে আমি সংক্ষিপ্ত পরবর্তী ধাপ প্রস্তাব করতে পারি। এক লাইনে জানালেই শুরু করছি।"
                        )
                    else:
                        prompt_text = (
                            f"এই যে, {idle_s} সেকেন্ড ধরে চুপচাপ! তাই আমি নিজেই ঢুঁ মারলাম \n"
                            "আমরা যেটা নিয়ে কথা বলছিলাম — \"" + topic_hint + "\" — সেখান থেকেই চালিয়ে দেব?\n"
                            "- বলো: ‘চালিয়ে যাও’ — আমি এগিয়ে নিই\n"
                            "- না হলে ছোট্ট এক্টা next steps সাজিয়ে দিই?\n"
                            "এক লাইনে বলো, কী করব?"
                        )
                await session.generate_reply(
                    instructions=prompt_text
                )
                last_change = asyncio.get_event_loop().time()
        except Exception:
            # Keep loop resilient
            continue

async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        preemptive_generation=True
    )
    
    #getting the current memory chat
    current_ctx = session.history.items
    

    await session.start(
        room=ctx.room,
        agent=Assistant(chat_ctx=current_ctx), #sending currenet chat to llm in realtime
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )
    # Start proactive re-engagement watcher
    import asyncio as _asyncio
    _asyncio.create_task(_proactive_reengagement_loop(session))
    
    # Start performance monitoring
    _asyncio.create_task(start_performance_monitoring())

    await session.generate_reply(
        instructions=Reply_prompts
    )
    conv_ctx = MemoryExtractor()
    await conv_ctx.run(current_ctx)
    


if __name__ == "__main__":
    # Suppress PortAudio exit handler noise during Ctrl+C
    os.environ.setdefault("SD_IGNORE_EXIT_HANDLER", "1")
    try:
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
    except KeyboardInterrupt:
        pass

    