import json
import os
import re
from typing import Dict, Any


class UserProfile:
    def __init__(self, user_id: str, storage_path: str = "conversations"):
        self.user_id = user_id
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.profile_file = os.path.join(storage_path, f"{user_id}_profile.json")
        self.data: Dict[str, Any] = {
            "preferred_language": "bangla",     # e.g., hinglish, hindi, english, bangla
            "preferred_browser": None,          # chrome, edge, firefox
            "greeting_style": None,             # formal, informal
            "always_confirm_actions": None,     # True/False
            "nicknames": {},                    # name -> nickname
            "proactive_idle_seconds": 30,       # silence before proactive follow-up
        }
        self.load()

    def load(self) -> None:
        # Load from DB if available
        try:
            from db import get_profile, init_db
            init_db()
            db_data = get_profile(self.user_id)
            if db_data:
                # merge DB data first
                self.data.update({k: v for k, v in db_data.items() if k != "user_id"})
        except Exception:
            pass
        # Load from JSON file (fallback/override)
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self) -> None:
        # Save to JSON (legacy)
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        # Upsert to DB
        try:
            from db import upsert_profile
            upsert_profile(self.user_id, self.data)
        except Exception:
            pass

    def update_from_text(self, text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        text_l = text.lower()
        updated = False

        # Language preference - default to bangla
        if "bangla" in text_l or "bengali" in text_l or not self.data.get("preferred_language"):
            updated |= self._set("preferred_language", "bangla")
        elif any(k in text_l for k in ["hinglish", "hingl", "mix hindi english"]):
            updated |= self._set("preferred_language", "hinglish")
        elif "hindi" in text_l and "english" not in text_l:
            updated |= self._set("preferred_language", "hindi")
        elif "english" in text_l and "hindi" not in text_l:
            updated |= self._set("preferred_language", "english")

        # Browser preference
        for b in ["chrome", "edge", "firefox", "brave"]:
            if re.search(rf"\buse\s+{b}\b|\bprefer\s+{b}\b|\bdefault\s+browser\b.*{b}|{b}\s+use\b", text_l):
                updated |= self._set("preferred_browser", b)
                break

        # Greeting style
        if "formal" in text_l:
            updated |= self._set("greeting_style", "formal")
        elif "informal" in text_l or "casual" in text_l:
            updated |= self._set("greeting_style", "informal")

        # Confirmation policy
        if any(p in text_l for p in ["always confirm", "ask before", "first confirm", "pehle pucho", "agey jiggesh"]):
            updated |= self._set("always_confirm_actions", True)
        if any(p in text_l for p in ["dont ask", "no confirmation", "without asking", "seedha karo", "direct kor"]):
            updated |= self._set("always_confirm_actions", False)

        # Nickname extraction: "call me X" or "mera naam X" or "my name is X"
        m = re.search(r"\b(call\s+me|my\s+name\s+is|mera\s+naam|amar\s+nam)\s+([\w\-\. ]{2,40})", text_l)
        if m:
            name = m.group(2).strip().title()
            if name:
                self.data["nicknames"]["self"] = name
                updated = True

        # Proactive idle timing (e.g., "15s", "45 sec", "30 seconds", "৩০ সেকেন্ড")
        tm = re.search(r"(\d{1,3})\s*(s|sec|secs|second|seconds|সেকেন্ড)?", text_l)
        if tm:
            try:
                val = int(tm.group(1))
                if 5 <= val <= 600:
                    updated |= self._set("proactive_idle_seconds", val)
            except Exception:
                pass

        if updated:
            self.save()
        return updated

    def _set(self, key: str, value: Any) -> bool:
        if self.data.get(key) != value:
            self.data[key] = value
            return True
        return False

    def get_context_string(self) -> str:
        chunks = []
        if self.data.get("preferred_language"):
            chunks.append(f"User prefers language: {self.data['preferred_language']}")
        if self.data.get("preferred_browser"):
            chunks.append(f"User preferred browser: {self.data['preferred_browser']}")
        if isinstance(self.data.get("always_confirm_actions"), bool):
            val = "always confirm" if self.data["always_confirm_actions"] else "no confirmation needed"
            chunks.append(f"Action policy: {val}")
        if self.data.get("greeting_style"):
            chunks.append(f"Greeting style: {self.data['greeting_style']}")
        if self.data.get("nicknames"):
            if self.data["nicknames"].get("self"):
                chunks.append(f"User nickname: {self.data['nicknames']['self']}")
        if self.data.get("proactive_idle_seconds"):
            chunks.append(f"Proactive idle: {self.data['proactive_idle_seconds']}s")
        if not chunks:
            return ""
        return "\n" + "\n".join(chunks) + "\n" 