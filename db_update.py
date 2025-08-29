#!/usr/bin/env python3
"""
Quick database update script
Usage: python db_update.py
"""
from db import *

def quick_update():
    """Interactive database update"""
    print("=== Jarvis Database Quick Update ===")
    
    while True:
        print("\n1. Update Profile")
        print("2. Add Contact") 
        print("3. View Recent Events")
        print("4. Exit")
        
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == '1':
            user_id = input("User ID [Protik_22]: ").strip() or "Protik_22"
            
            print("\nCurrent Profile:")
            profile = get_profile(user_id)
            for k, v in profile.items():
                print(f"  {k}: {v}")
            
            print("\nUpdate (press Enter to skip):")
            updates = {}
            
            lang = input("Language: ").strip()
            if lang: updates['preferred_language'] = lang
            
            browser = input("Browser: ").strip()
            if browser: updates['preferred_browser'] = browser
            
            greeting = input("Greeting Style: ").strip()
            if greeting: updates['greeting_style'] = greeting
            
            idle = input("Idle Seconds: ").strip()
            if idle and idle.isdigit(): updates['proactive_idle_seconds'] = int(idle)
            
            if updates:
                upsert_profile(user_id, updates)
                print("✓ Profile updated!")
            else:
                print("No changes made.")
        
        elif choice == '2':
            name = input("Contact Name: ").strip()
            mobile = input("Mobile: ").strip()
            email = input("Email (optional): ").strip() or None
            
            if name and mobile:
                contact_id = add_contact(name, mobile, email)
                print(f"✓ Contact added with ID: {contact_id}")
            else:
                print("Name and mobile are required!")
        
        elif choice == '3':
            print("\nRecent Tool Events:")
            init_db()
            with _lock:
                conn = _connect()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM tool_events ORDER BY created_at DESC LIMIT 5")
                    rows = cur.fetchall()
                    for row in rows:
                        status = "✓" if row['success'] else "✗"
                        print(f"  {status} {row['tool_name']} - {row['created_at']}")
                finally:
                    conn.close()
        
        elif choice == '4':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice!")

if __name__ == '__main__':
    quick_update()