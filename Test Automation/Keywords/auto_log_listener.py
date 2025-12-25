import os
import shutil
from datetime import datetime

ROBOT_LISTENER_API_VERSION = 3

class AutoLogListener:

    def close(self):
        # Timestamp for folder
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Robot Framework default logs folder
        base_logs_dir = os.path.join(os.getcwd(), "Logs")

        # New timestamped folder
        new_folder = os.path.join(base_logs_dir, f"Report_{timestamp}")
        os.makedirs(new_folder, exist_ok=True)

        # List of log files to move
        files = ["report.html", "log.html", "output.xml"]

        for f in files:
            src = os.path.join(base_logs_dir, f)
            if os.path.exists(src):
                dest = os.path.join(new_folder, f)
                shutil.move(src, dest)
                print(f"Moved {f} → {new_folder}")
            else:
                print(f"NOT FOUND: {src}")

# Set listener
LISTENER = AutoLogListener()
