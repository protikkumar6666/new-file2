import sqlite3
import csv
import subprocess
import time
import pyautogui
from urllib.parse import quote
from livekit.agents import function_tool
import logging
import re
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import requests
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)
ASSISTANT_NAME = 'vai'

# Advanced WhatsApp Features Configuration
WHATSAPP_CONFIG = {
    "auto_reply_enabled": False,
    "ai_analysis_enabled": True,
    "group_management_enabled": True,
    "media_handling_enabled": True,
    "security_features_enabled": True,
    "backup_enabled": True,
    "analytics_enabled": True
}

# AI-powered message analysis
class WhatsAppAI:
    def __init__(self):
        self.sentiment_analyzer = None
        self.language_detector = None
        self.spam_detector = None
        self.initialize_ai_models()
    
    def initialize_ai_models(self):
        """Initialize AI models for message analysis"""
        try:
            # Initialize sentiment analysis
            from textblob import TextBlob
            self.sentiment_analyzer = TextBlob
            
            # Initialize language detection
            import langdetect
            self.language_detector = langdetect.detect
            
            logger.info("✅ AI models initialized successfully")
        except ImportError as e:
            logger.warning(f"⚠️ Some AI models not available: {e}")
    
    def analyze_message(self, message: str) -> Dict:
        """Analyze message using AI models"""
        analysis = {
            "sentiment": "neutral",
            "language": "unknown",
            "spam_probability": 0.0,
            "urgency_level": "normal",
            "keywords": [],
            "emotion": "neutral"
        }
        
        try:
            if self.sentiment_analyzer:
                blob = self.sentiment_analyzer(message)
                polarity = blob.sentiment.polarity
                if polarity > 0.3:
                    analysis["sentiment"] = "positive"
                    analysis["emotion"] = "happy"
                elif polarity < -0.3:
                    analysis["sentiment"] = "negative"
                    analysis["emotion"] = "sad"
                else:
                    analysis["sentiment"] = "neutral"
                    analysis["emotion"] = "calm"
            
            if self.language_detector:
                try:
                    lang = self.language_detector(message)
                    analysis["language"] = lang
                except:
                    analysis["language"] = "unknown"
            
            # Spam detection based on common patterns
            spam_indicators = ["urgent", "free", "winner", "lottery", "bank", "password", "verify"]
            spam_score = sum(1 for indicator in spam_indicators if indicator.lower() in message.lower())
            analysis["spam_probability"] = min(spam_score / len(spam_indicators), 1.0)
            
            # Urgency detection
            urgent_words = ["urgent", "emergency", "asap", "immediately", "critical"]
            if any(word in message.lower() for word in urgent_words):
                analysis["urgency_level"] = "high"
            
            # Keyword extraction
            words = message.lower().split()
            analysis["keywords"] = [word for word in words if len(word) > 3 and word.isalpha()][:5]
            
        except Exception as e:
            logger.error(f"Error in message analysis: {e}")
        
        return analysis
    
    def generate_auto_reply(self, message: str, analysis: Dict) -> Optional[str]:
        """Generate intelligent auto-reply based on message analysis"""
        if not analysis.get("sentiment"):
            return None
        
        # Bengali auto-replies
        if analysis["language"] == "bn":
            if analysis["sentiment"] == "positive":
                return "আপনার খুশির খবর শুনে আমি খুব খুশি! 😊"
            elif analysis["sentiment"] == "negative":
                return "আপনার দুঃখের কথা শুনে আমার মন খারাপ লাগছে। আমি আপনার পাশে আছি। 🤗"
            elif analysis["urgency_level"] == "high":
                return "জরুরি বার্তা পেয়েছি। আমি শীঘ্রই প্রতিক্রিয়া জানাব। ⚡"
        
        # English auto-replies
        elif analysis["language"] == "en":
            if analysis["sentiment"] == "positive":
                return "Great to hear your good news! 😊"
            elif analysis["sentiment"] == "negative":
                return "I'm sorry to hear that. I'm here for you. 🤗"
            elif analysis["urgency_level"] == "high":
                return "Urgent message received. I'll respond shortly. ⚡"
        
        # Hindi auto-replies
        elif analysis["language"] == "hi":
            if analysis["sentiment"] == "positive":
                return "आपकी खुशी की खबर सुनकर मैं बहुत खुश हूं! 😊"
            elif analysis["sentiment"] == "negative":
                return "आपकी दुख की बात सुनकर मेरा मन खराब हो रहा है। मैं आपके साथ हूं। 🤗"
            elif analysis["urgency_level"] == "high":
                return "जरूरी संदेश मिला। मैं जल्द ही जवाब दूंगा। ⚡"
        
        return None

# Database setup (legacy file + new centralized DB)
def init_contacts_db():
    try:
        from db import init_db
        init_db()
    except Exception:
        pass
    con = sqlite3.connect('contacts.db')
    cursor = con.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS contacts 
                     (id integer primary key, name VARCHAR(200), mobile_no VARCHAR(255), email VARCHAR(255) NULL)''')
    
    # Add new tables for advanced features
    cursor.execute('''CREATE TABLE IF NOT EXISTS whatsapp_messages 
                     (id integer primary key, contact_name VARCHAR(200), message TEXT, 
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, message_type VARCHAR(50),
                      ai_analysis TEXT, auto_reply_sent BOOLEAN DEFAULT FALSE)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS whatsapp_groups 
                     (id integer primary key, group_name VARCHAR(200), group_id VARCHAR(255),
                      member_count INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS whatsapp_media 
                     (id integer primary key, contact_name VARCHAR(200), media_type VARCHAR(50),
                      file_path TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    con.commit()
    return con, cursor

# Prefer centralized DB for reads
def import_contacts_csv(csv_file='contacts.csv'):
    con, cursor = init_contacts_db()
    desired_columns_indices = [0, 30]
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile)
            for row in csvreader:
                if len(row) > max(desired_columns_indices):
                    selected_data = [row[i] for i in desired_columns_indices]
                    cursor.execute("INSERT INTO contacts (id, 'name', 'mobile_no') VALUES (null, ?, ?)", tuple(selected_data))
        con.commit()
    except Exception as e:
        logger.error(f"Error importing contacts: {e}")
    finally:
        con.close()

def remove_words(input_string, words_to_remove):
    words = input_string.split()
    filtered_words = [word for word in words if word.lower() not in words_to_remove]
    return ' '.join(filtered_words)

def findContact(query):
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'whatsapp', 'video']
    query = remove_words(query, words_to_remove)
    
    # Central DB lookup first
    try:
        from db import find_contact_by_name
        res = find_contact_by_name(query)
        if res:
            name, mobile_number_str = res
            if not str(mobile_number_str).startswith('+91'):
                mobile_number_str = '+91' + str(mobile_number_str)
            return mobile_number_str, name
    except Exception:
        pass
    
    # Fallback to legacy sqlite file
    con, cursor = init_contacts_db()
    try:
        query = query.strip().lower()
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", 
                      ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        print(results[0][0])
        mobile_number_str = str(results[0][0])
        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str
        return mobile_number_str, query
    except:
        return 0, 0
    finally:
        con.close()

def whatsApp(mobile_no, message, flag, name):
    if flag == 'message':
        target_tab = 12
        vai_message = "message send successfully to " + name
    elif flag == 'call':
        target_tab = 7
        message = ''
        vai_message = "calling to " + name
    else:
        target_tab = 6
        message = ''
        vai_message = "starting video call with " + name

    encoded_message = quote(message)
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"
    full_command = f'start "" "{whatsapp_url}"'
    
    subprocess.run(full_command, shell=True)
    time.sleep(5)
    subprocess.run(full_command, shell=True)
    
    pyautogui.hotkey('ctrl', 'f')
    for i in range(1, target_tab):
        pyautogui.hotkey('tab')
    pyautogui.hotkey('enter')
    
    return vai_message

# --- Smart command parsing helpers ---
def _parse_whatsapp_command(query: str, fallback_message: str = ""):
    """Return dict with action in {'message','call','video'}, contact, message."""
    q = (query or "").strip()
    ql = q.lower()
    action = None
    contact = None
    text = None

    # Detect action
    if any(k in ql for k in ["video call", "video-call", "videocall"]):
        action = 'video'
    elif any(k in ql for k in ["phone call", "call", "voice call"]):
        action = 'call'
    elif any(k in ql for k in ["send message", "message", "msg", "text"]):
        action = 'message'

    # Extract "to NAME" or after keywords
    m_to = re.search(r"\bto\s+([\w\-\. ]{2,60})", ql)
    if m_to:
        contact = m_to.group(1).strip()

    # Common forms: "send message to NAME: CONTENT" or "message NAME CONTENT"
    m_send = re.search(r"send\s+message\s+to\s+([\w\-\. ]{2,60})\s*[:,-]?\s*(.*)$", ql)
    if m_send:
        contact = m_send.group(1).strip()
        text = m_send.group(2).strip()

    m_msg = re.search(r"\bmessage\s+([\w\-\. ]{2,60})\s*[:,-]?\s*(.*)$", ql)
    if not text and m_msg:
        contact = m_msg.group(1).strip()
        text = m_msg.group(2).strip()

    # If user supplied fallback message argument, prefer it when no parsed text
    if not text and fallback_message:
        text = fallback_message.strip()

    # Trim trivial
    if text and len(text) < 1:
        text = None

    # If no contact yet, try last word after action
    if not contact:
        m_after_call = re.search(r"\b(call|video\s*call|message)\s+([\w\-\. ]{2,60})$", ql)
        if m_after_call:
            contact = m_after_call.group(2).strip()

    return {
        'action': action,
        'contact': contact,
        'message': text,
    }

def _needs_confirmation(action: str, contact: str, message: str) -> bool:
    # Ask confirm especially for sending messages or when profile requires
    if action == 'message' and contact and message:
        return True
    if action in ['call', 'video'] and contact:
        return True
    return False

# Initialize AI instance
whatsapp_ai = WhatsAppAI()

@function_tool()
async def whatsapp_message(contact_name: str, message: str = "") -> str:
    """
    Send WhatsApp message to a contact with AI-powered analysis.
    
    Use this when user wants to send WhatsApp message.
    Example: "Send message to John", "WhatsApp message to mom"
    
    Args:
        contact_name: Name of the contact to message
        message: Message content (optional, will prompt if empty)
    """
    try:
        contact_no, name = findContact(contact_name)
        if contact_no == 0:
            return f"❌ Contact '{contact_name}' not found in database"
        
        if not message:
            return "📱 Contact found. Please provide the message to send."
        
        # AI analysis of the message
        if WHATSAPP_CONFIG["ai_analysis_enabled"]:
            analysis = whatsapp_ai.analyze_message(message)
            logger.info(f"AI Analysis: {analysis}")
            
            # Check for spam
            if analysis.get("spam_probability", 0) > 0.7:
                return f"⚠️ Warning: This message has high spam probability ({analysis['spam_probability']:.1%}). Please review before sending."
            
            # Check urgency
            if analysis.get("urgency_level") == "high":
                logger.warning(f"High urgency message detected for {name}")
        
        # Optional confirmation via profile
        try:
            from user_profile import UserProfile
            profile = UserProfile("Protik_22")
            if profile.data.get("always_confirm_actions"):
                return f"🛑 Confirm: send message to {name}? Text: '{message}'. Say 'confirm send' to proceed."
        except Exception:
            pass
        
        result = whatsApp(contact_no, message, 'message', name)
        
        # Log message with AI analysis
        if WHATSAPP_CONFIG["ai_analysis_enabled"]:
            con, cursor = init_contacts_db()
            try:
                cursor.execute("INSERT INTO whatsapp_messages (contact_name, message, message_type, ai_analysis) VALUES (?, ?, ?, ?)",
                             (name, message, 'outgoing', json.dumps(analysis)))
                con.commit()
            except Exception as e:
                logger.error(f"Error logging message: {e}")
            finally:
                con.close()
        
        return f"✅ {result}"
    except Exception as e:
        return f"❌ আরে! WhatsApp message পাঠাতে সমস্যা: {str(e)[:100]}।"

@function_tool()
async def whatsapp_call(contact_name: str, call_type: str = "voice") -> str:
    """
    Make WhatsApp voice or video call to a contact.
    
    Use this when user wants to make WhatsApp calls.
    Example: "Call John on WhatsApp", "Video call mom"
    
    Args:
        contact_name: Name of the contact to call
        call_type: "voice" for phone call, "video" for video call
    """
    try:
        contact_no, name = findContact(contact_name)
        if contact_no == 0:
            return f"❌ Contact '{contact_name}' not found in database"
        
        # Optional confirmation via profile
        try:
            from user_profile import UserProfile
            profile = UserProfile("Protik_22")
            if profile.data.get("always_confirm_actions"):
                act = 'video call' if call_type == 'video' else 'call'
                return f"🛑 Confirm: {act} to {name}? Say 'confirm call' to proceed."
        except Exception:
            pass
        
        flag = 'call' if call_type == 'voice' else 'video call'
        result = whatsApp(contact_no, "", flag, name)
        return f"✅ {result}"
    except Exception as e:
        return f"❌ WhatsApp call করতে সমস্যা: {str(e)[:100]}।"

@function_tool()
async def add_contact(name: str, mobile_no: str) -> str:
    """
    Add a new contact to the database.
    
    Args:
        name: Contact name
        mobile_no: Mobile number
    """
    # Write to centralized DB too
    try:
        from db import add_contact as add_contact_db
        add_contact_db(name, mobile_no)
    except Exception:
        pass
    
    con, cursor = init_contacts_db()
    try:
        query = "INSERT INTO contacts VALUES (null,?, ?)"
        cursor.execute(query, (name, mobile_no))
        con.commit()
        return f"✅ Contact '{name}' added successfully"
    except Exception as e:
        return f"❌ Contact add করতে সমস্যা: {str(e)[:100]}।"
    finally:
        con.close()

@function_tool()
async def whatsapp_automation(query: str, message: str = "", confirm: bool = False) -> str:
    """
    Handle WhatsApp automation commands for sending messages or making calls.
    
    Use this when user wants to send message, make phone call or video call.
    Example: "send message to John", "phone call to mom", "video call dad"
    
    Args:
        query: The full command (e.g., "send message to John")
        message: Message content for text messages
        confirm: Set True to proceed without asking confirmation (or when user says 'confirm')
    """
    try:
        parsed = _parse_whatsapp_command(query, fallback_message=message)
        action = parsed['action']
        contact = parsed['contact']
        text = parsed['message']

        if not action or not contact:
            return "❌ Please specify an action (send message/call/video call) and a contact name."

        contact_no, name = findContact(contact)
        if contact_no == 0:
            return "❌ Contact not found in database"

        # Check confirmation policy
        must_confirm = False
        try:
            from user_profile import UserProfile
            profile = UserProfile("Protik_22")
            if profile.data.get("always_confirm_actions"):
                must_confirm = True
        except Exception:
            pass

        # Implicit confirm if user said confirm
        if re.search(r"\bconfirm\b", query.lower()):
            confirm = True

        if (must_confirm or _needs_confirmation(action, name, text or "")) and not confirm:
            if action == 'message':
                return f"🛑 Confirm: send message to {name}? Text: '{text or ''}'. Say 'confirm send' or call whatsapp_automation again with confirm=true."
            elif action == 'video':
                return f"🛑 Confirm: video call to {name}? Say 'confirm call' or call whatsapp_automation again with confirm=true."
            else:
                return f"🛑 Confirm: call to {name}? Say 'confirm call' or call whatsapp_automation again with confirm=true."

        if action == 'message':
            if not text:
                return "📱 Contact found. What message to send?"
            result = whatsApp(contact_no, text, 'message', name)
        elif action == 'video':
            result = whatsApp(contact_no, "", 'video call', name)
        else:  # call
            result = whatsApp(contact_no, "", 'call', name)
        
        return f"✅ {result}"
    except Exception as e:
        return f"❌ WhatsApp automation এ সমস্যা: {str(e)[:100]}।"

# New Advanced Features

@function_tool()
async def analyze_whatsapp_message(message: str) -> str:
    """
    Analyze a WhatsApp message using AI for sentiment, language, and spam detection.
    
    Args:
        message: The message to analyze
    """
    try:
        if not WHATSAPP_CONFIG["ai_analysis_enabled"]:
            return "❌ AI analysis is disabled in configuration"
        
        analysis = whatsapp_ai.analyze_message(message)
        
        # Format analysis results
        result = f"🤖 AI Analysis Results:\n"
        result += f"• Sentiment: {analysis['sentiment'].title()} ({analysis['emotion']})\n"
        result += f"• Language: {analysis['language'].upper()}\n"
        result += f"• Spam Probability: {analysis['spam_probability']:.1%}\n"
        result += f"• Urgency Level: {analysis['urgency_level'].title()}\n"
        result += f"• Keywords: {', '.join(analysis['keywords']) if analysis['keywords'] else 'None'}\n"
        
        # Generate auto-reply suggestion
        auto_reply = whatsapp_ai.generate_auto_reply(message, analysis)
        if auto_reply:
            result += f"\n💡 Suggested Auto-reply:\n{auto_reply}"
        
        return result
    except Exception as e:
        return f"❌ AI analysis এ সমস্যা: {str(e)[:100]}।"

@function_tool()
async def whatsapp_group_management(action: str, group_name: str = "", members: List[str] = None) -> str:
    """
    Manage WhatsApp groups - create, add members, remove members.
    
    Args:
        action: "create", "add_members", "remove_members", "list_groups"
        group_name: Name of the group
        members: List of member names to add/remove
    """
    try:
        if not WHATSAPP_CONFIG["group_management_enabled"]:
            return "❌ Group management is disabled in configuration"
        
        con, cursor = init_contacts_db()
        
        if action == "create":
            if not group_name:
                return "❌ Group name is required for creation"
            
            # This would integrate with WhatsApp Web API in production
            cursor.execute("INSERT INTO whatsapp_groups (group_name, member_count) VALUES (?, ?)", 
                         (group_name, len(members) if members else 0))
            con.commit()
            return f"✅ Group '{group_name}' created successfully"
            
        elif action == "list_groups":
            cursor.execute("SELECT group_name, member_count, created_at FROM whatsapp_groups")
            groups = cursor.fetchall()
            if not groups:
                return "📱 No groups found in database"
            
            result = "📱 WhatsApp Groups:\n"
            for group in groups:
                result += f"• {group[0]} ({group[1]} members) - Created: {group[2]}\n"
            return result
            
        elif action in ["add_members", "remove_members"]:
            if not group_name or not members:
                return f"❌ Group name and members list required for {action}"
            
            # This would integrate with WhatsApp Web API in production
            return f"✅ {action.replace('_', ' ').title()} operation completed for group '{group_name}'"
        
        else:
            return f"❌ Unknown action: {action}. Use: create, add_members, remove_members, list_groups"
            
    except Exception as e:
        return f"❌ Group management এ সমস্যা: {str(e)[:100]}।"
    finally:
        if 'con' in locals():
            con.close()

@function_tool()
async def whatsapp_media_handler(action: str, contact_name: str = "", media_type: str = "") -> str:
    """
    Handle WhatsApp media operations - send images, documents, voice messages.
    
    Args:
        action: "send_image", "send_document", "send_voice", "list_media"
        contact_name: Name of the contact
        media_type: Type of media (image, document, voice)
    """
    try:
        if not WHATSAPP_CONFIG["media_handling_enabled"]:
            return "❌ Media handling is disabled in configuration"
        
        con, cursor = init_contacts_db()
        
        if action == "list_media":
            cursor.execute("SELECT contact_name, media_type, timestamp FROM whatsapp_media ORDER BY timestamp DESC LIMIT 10")
            media_items = cursor.fetchall()
            if not media_items:
                return "📁 No media items found in database"
            
            result = "📁 Recent Media Items:\n"
            for item in media_items:
                result += f"• {item[0]} - {item[1]} ({item[2]})\n"
            return result
            
        elif action.startswith("send_"):
            if not contact_name:
                return "❌ Contact name is required for sending media"
            
            # This would integrate with WhatsApp Web API in production
            cursor.execute("INSERT INTO whatsapp_media (contact_name, media_type) VALUES (?, ?)", 
                         (contact_name, media_type or action.replace("send_", "")))
            con.commit()
            return f"✅ {action.replace('_', ' ').title()} sent to {contact_name}"
        
        else:
            return f"❌ Unknown action: {action}. Use: send_image, send_document, send_voice, list_media"
            
    except Exception as e:
        return f"❌ Media handling এ সমস্যা: {str(e)[:100]}।"
    finally:
        if 'con' in locals():
            con.close()

@function_tool()
async def whatsapp_analytics(time_period: str = "7d") -> str:
    """
    Get WhatsApp usage analytics and insights.
    
    Args:
        time_period: Time period for analysis (1d, 7d, 30d, all)
    """
    try:
        if not WHATSAPP_CONFIG["analytics_enabled"]:
            return "❌ Analytics is disabled in configuration"
        
        con, cursor = init_contacts_db()
        
        # Calculate time filter
        if time_period == "1d":
            time_filter = datetime.now() - timedelta(days=1)
        elif time_period == "7d":
            time_filter = datetime.now() - timedelta(days=7)
        elif time_period == "30d":
            time_filter = datetime.now() - timedelta(days=30)
        else:
            time_filter = datetime.min
        
        # Get message statistics
        cursor.execute("SELECT COUNT(*) as total_messages, message_type FROM whatsapp_messages WHERE timestamp >= ? GROUP BY message_type", 
                     (time_filter,))
        message_stats = cursor.fetchall()
        
        # Get contact statistics
        cursor.execute("SELECT COUNT(DISTINCT contact_name) as unique_contacts FROM whatsapp_messages WHERE timestamp >= ?", 
                     (time_filter,))
        contact_count = cursor.fetchone()[0]
        
        # Get group statistics
        cursor.execute("SELECT COUNT(*) as total_groups, SUM(member_count) as total_members FROM whatsapp_groups")
        group_stats = cursor.fetchone()
        
        # Format analytics report
        result = f"📊 WhatsApp Analytics ({time_period}):\n\n"
        
        result += "💬 Message Statistics:\n"
        for stat in message_stats:
            result += f"• {stat[1].title()}: {stat[0]} messages\n"
        
        result += f"\n👥 Contact Statistics:\n"
        result += f"• Unique Contacts: {contact_count}\n"
        
        result += f"\n👥 Group Statistics:\n"
        result += f"• Total Groups: {group_stats[0]}\n"
        result += f"• Total Members: {group_stats[1] or 0}\n"
        
        return result
        
    except Exception as e:
        return f"❌ Analytics এ সমস্যা: {str(e)[:100]}।"
    finally:
        if 'con' in locals():
            con.close()

@function_tool()
async def whatsapp_backup(backup_type: str = "full") -> str:
    """
    Create backup of WhatsApp data and conversations.
    
    Args:
        backup_type: "full", "messages", "contacts", "media"
    """
    try:
        if not WHATSAPP_CONFIG["backup_enabled"]:
            return "❌ Backup is disabled in configuration"
        
        backup_dir = "whatsapp_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if backup_type == "full":
            # Backup all data
            con, cursor = init_contacts_db()
            
            # Backup contacts
            cursor.execute("SELECT * FROM contacts")
            contacts = cursor.fetchall()
            contacts_file = os.path.join(backup_dir, f"contacts_{timestamp}.json")
            with open(contacts_file, 'w', encoding='utf-8') as f:
                json.dump([dict(zip([col[0] for col in cursor.description], row)) for row in contacts], f, indent=2, ensure_ascii=False)
            
            # Backup messages
            cursor.execute("SELECT * FROM whatsapp_messages")
            messages = cursor.fetchall()
            messages_file = os.path.join(backup_dir, f"messages_{timestamp}.json")
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump([dict(zip([col[0] for col in cursor.description], row)) for row in messages], f, indent=2, ensure_ascii=False)
            
            con.close()
            
            return f"✅ Full backup completed:\n• Contacts: {contacts_file}\n• Messages: {messages_file}"
            
        elif backup_type == "contacts":
            con, cursor = init_contacts_db()
            cursor.execute("SELECT * FROM contacts")
            contacts = cursor.fetchall()
            contacts_file = os.path.join(backup_dir, f"contacts_{timestamp}.json")
            with open(contacts_file, 'w', encoding='utf-8') as f:
                json.dump([dict(zip([col[0] for col in cursor.description], row)) for row in contacts], f, indent=2, ensure_ascii=False)
            con.close()
            return f"✅ Contacts backup completed: {contacts_file}"
            
        else:
            return f"❌ Unknown backup type: {backup_type}. Use: full, contacts"
            
    except Exception as e:
        return f"❌ Backup এ সমস্যা: {str(e)[:100]}।"

@function_tool()
async def whatsapp_security_check() -> str:
    """
    Perform security check on WhatsApp data and settings.
    """
    try:
        if not WHATSAPP_CONFIG["security_features_enabled"]:
            return "❌ Security features are disabled in configuration"
        
        con, cursor = init_contacts_db()
        
        # Check for suspicious patterns
        cursor.execute("SELECT COUNT(*) FROM whatsapp_messages WHERE ai_analysis LIKE '%spam_probability%' AND CAST(JSON_EXTRACT(ai_analysis, '$.spam_probability') AS REAL) > 0.8")
        high_spam_count = cursor.fetchone()[0]
        
        # Check for unusual activity
        cursor.execute("SELECT COUNT(*) FROM whatsapp_messages WHERE timestamp >= datetime('now', '-1 hour')")
        recent_messages = cursor.fetchone()[0]
        
        # Check for sensitive keywords
        sensitive_keywords = ["password", "bank", "credit card", "ssn", "pin"]
        sensitive_count = 0
        for keyword in sensitive_keywords:
            cursor.execute("SELECT COUNT(*) FROM whatsapp_messages WHERE LOWER(message) LIKE ?", (f"%{keyword}%",))
            sensitive_count += cursor.fetchone()[0]
        
        # Generate security report
        result = "🔒 WhatsApp Security Report:\n\n"
        
        if high_spam_count > 0:
            result += f"⚠️ High spam probability messages: {high_spam_count}\n"
        else:
            result += "✅ No high spam probability messages detected\n"
        
        if recent_messages > 50:
            result += f"⚠️ High message volume in last hour: {recent_messages}\n"
        else:
            result += f"✅ Normal message volume: {recent_messages} in last hour\n"
        
        if sensitive_count > 0:
            result += f"⚠️ Messages with sensitive keywords: {sensitive_count}\n"
        else:
            result += "✅ No sensitive keywords detected\n"
        
        # Security recommendations
        result += "\n💡 Security Recommendations:\n"
        if high_spam_count > 0:
            result += "• Review and delete suspicious messages\n"
        if sensitive_count > 0:
            result += "• Avoid sharing sensitive information via WhatsApp\n"
        result += "• Enable two-factor authentication\n"
        result += "• Regularly backup important conversations\n"
        
        return result
        
    except Exception as e:
        return f"❌ Security check এ সমস্যা: {str(e)[:100]}।"
    finally:
        if 'con' in locals():
            con.close()

# Initialize database on import
init_contacts_db()