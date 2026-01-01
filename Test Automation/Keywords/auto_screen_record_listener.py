import os
import time
import subprocess
# from configparser import ConfigParser
import configparser
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

class AutoScreenRecordingListener:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        # Load config.ini from same folder
        folder = os.path.dirname(__file__)
        self.config_file = os.path.join(folder, "config.ini")
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"INI file not found: {self.config_file}")
        self._load_config()
        logger.info(f"✅ Listener initialized with config: {self.config_file}")

    def _load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        self.device_id = config.get("DUT.Phone", "device_id", fallback=None)
        if not self.device_id:
            raise ValueError("DUT.Phone section or device_id not found in INI")
        

    # --- Robot Listeners ---
    def start_test(self, name, attrs):
        """Called automatically at the start of each test."""
        if self._screen_recording_mode in ["Yes", "Always"]:
            self._start_recording(name)

    def end_test(self, name, attrs):
        """Called automatically at the end of each test."""
        test_status = attrs.get('status', 'PASS')  # PASS / FAIL
        if self._screen_recording_mode == "Always" or (self._screen_recording_mode == "Yes" and test_status != "PASS"):
            self._stop_recording(name)

    # --- Private Methods ---
    def _start_recording(self, test_name):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_test_name = test_name.replace(" ", "_")
        self._device_video_path = f"/sdcard/{self._device_id}_{timestamp}_{safe_test_name}.mp4"

        logger.info(f"🎬 Auto-starting screen recording for test: {test_name}")
        logger.info(f"📁 Device video path: {self._device_video_path}")

        self._record_proc = subprocess.Popen(
            ["adb", "-s", self._device_id, "shell", "screenrecord",
             "--bit-rate", "8000000", "--time-limit", "180",
             self._device_video_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Small delay to ensure recording starts
        time.sleep(0.5)

    def _stop_recording(self, test_name):
        if not self._record_proc:
            logger.warn("⚠️ No active screen recording process found")
            return

        logger.info(f"🛑 Stopping screen recording for test: {test_name}")
        self._record_proc.terminate()
        self._record_proc.wait(timeout=5)

        # Pull video from device to local workspace
        local_video_path = os.path.join(self._workspace, "videos", f"{test_name.replace(' ', '_')}.mp4")
        logger.info(f"⬇️ Pulling video to: {local_video_path}")

        subprocess.run(
            ["adb", "-s", self._device_id, "pull", self._device_video_path, local_video_path],
            check=True
        )

        # Embed video in Robot log
        html = f"""
        <div style="margin:10px 0">
            <b>🎬 {test_name} Recording</b><br>
            <video width="480" controls>
                <source src="{os.path.abspath(local_video_path)}" type="video/mp4">
                Your browser does not support the video tag.
            </video><br>
            <a href="{os.path.abspath(local_video_path)}" target="_blank">⬇️ Download video</a>
        </div>
        """
        logger.info(html, html=True)

        # Reset process and path
        self._record_proc = None
        self._device_video_path = None
