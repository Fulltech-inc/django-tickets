# main/email_watcher.py
import time
import threading
from main.management.commands.get_email import process_inbox

def watch_inbox_loop(interval_seconds=30):
    while True:
        try:
            process_inbox(quiet=True)
        except Exception as e:
            print(f"[!] Email watcher error: {e}")
        time.sleep(interval_seconds)

def start_background_email_watcher():
    thread = threading.Thread(target=watch_inbox_loop, daemon=True)
    thread.start()
