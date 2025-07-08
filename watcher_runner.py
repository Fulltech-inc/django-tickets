from dotenv import load_dotenv
import os
import sys
import django
import time

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
loaded = load_dotenv(env_path)
print(f"[DEBUG] .env loaded: {loaded}")
print(f"[DEBUG] .env path: {env_path}")
print(f"[DEBUG] DJANGO_TICKET_INBOX_SERVER: {os.getenv('DJANGO_TICKET_INBOX_SERVER')}")

# Set DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tickets.settings")  # adjust if needed

# Initialize Django
django.setup()

from main.email_watcher import start_background_email_watcher

if __name__ == "__main__":
    try:
        start_background_email_watcher()
        print("[✓] Email watcher thread started")
    except Exception as e:
        print(f"[✗] Failed to start email watcher: {e}")
        raise e

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Watcher stopped manually.")
