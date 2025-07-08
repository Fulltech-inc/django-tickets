import os
from dotenv import load_dotenv
import time
from main.email_watcher import start_background_email_watcher

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

if __name__ == "__main__":
    try:
        start_background_email_watcher()
        print("[✓] Email watcher thread started")
    except Exception as e:
        print(f"[✗] Failed to start email watcher: {e}")
        raise e

    # Keep process alive so systemd doesn't think it's dead
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Watcher stopped manually.")
