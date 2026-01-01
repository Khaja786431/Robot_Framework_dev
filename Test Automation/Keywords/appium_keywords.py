from appium import webdriver
from robot.api.deco import keyword
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from datetime import datetime
import subprocess
import configparser
import time
import os 
import json
import cv2
import pytesseract


class appium_keywords:

    def __init__(self):
        self.drivers = {}
        # self.driver = None
        # Get folder path where this .py file exists
        base_path = os.path.dirname(os.path.abspath(__file__))

        # Move to ../Configurations/configurations.ini
        ini_path = os.path.join(base_path, "..", "Configurations", "configurations.ini")

        # Prepare parser object
        self.config = configparser.ConfigParser()

        # Read the INI file into memory
        self.config.read(ini_path)

        #Set tesseract path
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
    @keyword
    def get_device_id(self, dut_name):
        """
        Robot Framework keyword.
        Returns the device_id for the requested DUT (Phone / Main / Cluster).
        """

        # Section names inside INI look like: [DUT.Phone], [DUT.Main]
        section = f"DUT.{dut_name}"

        # If section not found → throw error
        if section not in self.config:
            raise Exception(f"DUT section '{section}' not found in configuration.ini")

        # Return "device_id" value inside that section
        # return self.config[section]["device_id"]
        return self.config[section]

    @keyword
    def start_appium_session(self, dut_name):
        if dut_name in self.drivers:
            return self.drivers[dut_name]

        caps = self.get_device_id(dut_name)  # must return dict

        options = UiAutomator2Options().load_capabilities(caps)

        driver = webdriver.Remote(
            command_executor="http://127.0.0.1:4723",
            options=options
        )

        self.drivers[dut_name] = driver
        return driver


    @keyword
    def stop_appium_session(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    @keyword
    def verify_text_appium_full(self, expected_text, dut_name):
        """
        Verifies FULL visible text using Appium (exact match).
        Fails if only partial text is found.
        """

        driver = self.start_appium_session(dut_name)

        logger.info(f"<b>Verifying text:</b> '{expected_text}'", html=True)

        elements = driver.find_elements(
            by="xpath",
            value="//*[normalize-space(@text) != '']"
        )

        visible_texts = []
        for el in elements:
            text = el.text.strip()
            if text:
                visible_texts.append(text)

        logger.info(
            "<b>Visible texts on screen:</b><br>" +
            "<br>".join(visible_texts),
            html=True
        )

        if expected_text in visible_texts:
            logger.info(
                f"<b style='color:green'>TEXT VERIFIED: {expected_text}</b>",
                html=True
            )
            return True

        raise AssertionError(
            f"Exact text '{expected_text}' not found on screen"
        )
    
    
    @keyword
    def tap_by_coordinates(self, json_name, key_name, dut_name):
        """
        Tap on screen using X,Y coordinates from JSON key using Appium (mobile: tap).
        """

        driver = self.start_appium_session(dut_name)

        project_root = BuiltIn().get_variable_value("${EXECDIR}")
        json_file = os.path.join(
            project_root,
            "Resources",
            "Coordinates",
            json_name
        )

        if not os.path.isfile(json_file):
            raise AssertionError(f"JSON file not found: {json_file}")

        with open(json_file, "r") as f:
            data = json.load(f)

        if key_name not in data:
            raise AssertionError(f"Key '{key_name}' not found in {json_name}")

        x = data[key_name].get("x")
        y = data[key_name].get("y")

        if x is None or y is None:
            raise AssertionError("JSON key must contain 'x' and 'y'")

        # Appium-native tap
        driver.execute_script(
            "mobile: clickGesture",
            {"x": int(x), "y": int(y)}
        )

        msg = f"Tapped '{key_name}' at ({x},{y}) on DUT '{dut_name}'"
        logger.info(f"<b>{msg}</b>", html=True)
        return msg
    
    @keyword
    def tap_by_text(self, expected_text, dut_name):
        """
        Tap on visible text using OCR and Appium clickGesture.
        Works without XML / UI dump.
        """

        driver = self.start_appium_session(dut_name)

        # Take screenshot using Appium
        screenshot_path = os.path.join(
            BuiltIn().get_variable_value("${OUTPUT DIR}"),
            "ocr_screen.png"
        )
        driver.save_screenshot(screenshot_path)

        img = cv2.imread(screenshot_path)
        if img is None:
            raise AssertionError("Failed to load screenshot for OCR")

        # OCR
        ocr_data = pytesseract.image_to_data(
            img, output_type=pytesseract.Output.DICT
        )

        found = False
        highlighted = img.copy()

        for i, text in enumerate(ocr_data["text"]):
            if text.strip() == expected_text:
                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]
                h = ocr_data["height"][i]

                tap_x = int(x + w / 2)
                tap_y = int(y + h / 2)

                # Highlight rectangle
                cv2.rectangle(
                    highlighted,
                    (x, y),
                    (x + w, y + h),
                    (0, 0, 255),
                    3
                )

                highlighted_path = os.path.join(
                    BuiltIn().get_variable_value("${OUTPUT DIR}"),
                    "ocr_highlighted.png"
                )
                cv2.imwrite(highlighted_path, highlighted)

                # Appium tap
                driver.execute_script(
                    "mobile: clickGesture",
                    {
                        "x": tap_x,
                        "y": tap_y
                    }
                )

                logger.info(
                    f"<b style='color:green'>Tapped on text:</b> {expected_text}<br>"
                    f"<img src='ocr_highlighted.png' width='40%'>",
                    html=True
                )

                found = True
                return True

        # Not found
        logger.info(
            f"<b style='color:red'>Text '{expected_text}' not found via OCR</b>",
            html=True
        )
        raise AssertionError(f"Text '{expected_text}' not found on screen")
    

    @keyword
    def verify_image_element(self, image_name, dut_name, threshold=0.90):
        """
        Verifies image on screen using Appium screenshot + OpenCV template matching.
        Logs highlighted match image in Robot report.
        """

        driver = self.start_appium_session(dut_name)

        project_root = BuiltIn().get_variable_value("${EXECDIR}")
        output_dir = BuiltIn().get_variable_value("${OUTPUTDIR}")  # ✅ BIN / OUTPUT FOLDER

        reference_image = os.path.join(
            project_root,
            "Resources",
            "images",
            image_name
        )

        if not os.path.isfile(reference_image):
            raise AssertionError(f"Reference image not found: {reference_image}")

        # ✅ Screenshot stored in output folder
        screenshot_path = os.path.join(
            output_dir,
            f"appium_verify_image_{int(time.time())}.png"
        )
        driver.save_screenshot(screenshot_path)

        logger.info(
            f"<b>Captured Screen:</b><br>"
            f"<img src='{os.path.basename(screenshot_path)}' width='300px'>",
            html=True
        )
        logger.info(
            f"<b>Reference Image:</b><br>"
            f"<img src='{reference_image}' width='300px'>",
            html=True
        )

        screen = cv2.imread(screenshot_path)
        ref = cv2.imread(reference_image)

        if screen is None:
            raise AssertionError("Failed to load captured screenshot")
        if ref is None:
            raise AssertionError("Failed to load reference image")

        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(
            screen_gray,
            ref_gray,
            cv2.TM_CCOEFF_NORMED
        )
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        logger.info(
            f"<b>Similarity Score:</b> {max_val:.3f}",
            html=True
        )

        h, w = ref_gray.shape[:2]
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        highlighted = screen.copy()
        cv2.rectangle(
            highlighted,
            top_left,
            bottom_right,
            (0, 0, 255),
            3
        )

        # ✅ Highlighted image stored in output folder
        highlighted_path = os.path.join(
            output_dir,
            f"verify_image_highlighted_{int(time.time())}.png"
        )
        cv2.imwrite(highlighted_path, highlighted)

        logger.info(
            f"<b>Matched Area:</b><br>"
            f"<img src='{os.path.basename(highlighted_path)}' width='300px'>",
            html=True
        )

        if max_val >= threshold:
            logger.info(
                "<b style='color:green'>Image Verification: PASS</b>",
                html=True
            )
            return True
        else:
            logger.info(
                "<b style='color:red'>Image Verification: FAIL</b>",
                html=True
            )
            raise AssertionError(
                f"Image mismatch: similarity={max_val:.3f} < threshold={threshold}"
            )

    
    @keyword
    def click_by_image(self, image_name, dut_name, threshold=0.8):
        """
        Takes screenshot using Appium,
        performs template match, clicks on matched area,
        and logs highlighted image in Robot report.
        """

        driver = self.start_appium_session(dut_name)

        project_root = BuiltIn().get_variable_value("${EXECDIR}")
        output_dir = BuiltIn().get_variable_value("${OUTPUTDIR}")  # ✅ BIN / OUTPUT FOLDER

        reference_image = os.path.join(
            project_root,
            "Resources",
            "images",
            image_name
        )

        if not os.path.isfile(reference_image):
            raise AssertionError(f"Reference image not found: {reference_image}")

        # ✅ Screenshot stored in bin/output folder
        screenshot_path = os.path.join(
            output_dir,
            f"appium_click_image_{int(time.time())}.png"
        )
        driver.save_screenshot(screenshot_path)

        screen = cv2.imread(screenshot_path)
        template = cv2.imread(reference_image)

        if screen is None:
            raise AssertionError("Failed to load captured screenshot")
        if template is None:
            raise AssertionError(f"Failed to load template image: {reference_image}")

        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(
            screen_gray,
            template_gray,
            cv2.TM_CCOEFF_NORMED
        )
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        logger.info(f"<b>Image Match Score:</b> {max_val:.3f}", html=True)

        if max_val < threshold:
            raise AssertionError(
                f"Image not found. Match score={max_val:.3f}, threshold={threshold}"
            )

        h, w = template_gray.shape[:2]
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        tap_x = top_left[0] + w // 2
        tap_y = top_left[1] + h // 2

        highlighted = screen.copy()
        cv2.rectangle(highlighted, top_left, bottom_right, (0, 0, 255), 3)

        # ✅ Highlighted image stored in bin/output folder
        highlighted_path = os.path.join(
            output_dir,
            f"click_image_highlighted_{int(time.time())}.png"
        )
        cv2.imwrite(highlighted_path, highlighted)

        logger.info(
            f"<b>Matched Image (confidence={max_val:.3f})</b><br>"
            f"<img src='{os.path.basename(highlighted_path)}' width='40%'>",
            html=True
        )

        driver.execute_script(
            "mobile: clickGesture",
            {
                "x": int(tap_x),
                "y": int(tap_y)
            }
        )

        msg = f"Clicked at ({tap_x},{tap_y}) | match={max_val:.3f}"
        logger.info(msg)
        return msg

    
    @keyword
    def run_command(self, command, dut_name, timeout_ms=5000):
        """
        Executes shell command on a DUT using Appium mobile:shell
        Works across Appium versions (dict or string return)
        """

        driver = self.start_appium_session(dut_name)

        parts = command.strip().split()
        base_cmd = parts[0]
        args = parts[1:]

        logger.info(f"Executing command on {dut_name}: {command}")

        result = driver.execute_script(
            "mobile: shell",
            {
                "command": base_cmd,
                "args": args,
                "timeout": timeout_ms
            }
        )

        if isinstance(result, dict):
            stdout = result.get("stdout", "").strip()
            stderr = result.get("stderr", "")
            code = result.get("code", 0)

            if code != 0:
                raise AssertionError(stderr)

            return stdout

        # Older Appium versions return string directly
        if isinstance(result, str):
            logger.info(f"OUTPUT:{result}")
            return result.strip()

        raise AssertionError(f"Unexpected result from mobile:shell: {result}")
    

    @keyword
    def press_key(self, keycode, dut_name):
        """
        Press Android hardware/system key using keyevent.
        Ex: HOME, BACK, POWER, VOLUME_UP, VOLUME_DOWN, ENTER..
        """

        driver = self.start_appium_session(dut_name)

        logger.info(
            f"<b>Pressing Keyevent:</b> {keycode} on {dut_name}",
            html=True
        )

        driver.execute_script(
            "mobile: shell",
            {
                "command": "input",
                "args": ["keyevent", str(keycode)]
            }
        )

    @keyword
    def swipe_left_right(self, dut_name, direction="left", percent=0.9):
        """
        Safe horizontal swipe avoiding Android back gestures.
        """
        driver = self.start_appium_session(dut_name)
        size = driver.get_window_size()
        width = size["width"]
        height = size["height"]

        # SAFE SWIPE AREA
        left = int(width * 0.1)
        top = int(height * 0.35)
        area_width = int(width * 0.8)
        area_height = int(height * 0.3)

        if direction.lower() not in ["left", "right"]:
            raise ValueError("direction must be 'left' or 'right'")

        driver.execute_script(
            "mobile: scrollGesture",
            {
                "direction": direction.lower(),
                "percent": percent,
                "left": left,
                "top": top,
                "width": area_width,
                "height": area_height,
                "speed": 3000
            }
        )
        logger.info(
        f"Swiped {direction.upper()} | percent={percent} | DUT={dut_name}"
    )


    

    @keyword
    def scroll_top_bottom(self, dut_name, direction="down", percent=0.9):
        """
        Safe scroll that avoids Android system gestures.
        """
        driver = self.start_appium_session(dut_name)
        size = driver.get_window_size()
        width = size["width"]
        height = size["height"]

        # SAFE SCROLL AREA (center of screen)
        left = int(width * 0.1)
        top = int(height * 0.15)
        area_width = int(width * 0.8)
        area_height = int(height * 0.7)

        if direction.lower() not in ["up", "down"]:
            raise ValueError("direction must be 'up' or 'down'")

        driver.execute_script(
            "mobile: scrollGesture",
            {
                "direction": direction.lower(),
                "percent": percent,
                "left": left,
                "top": top,
                "width": area_width,
                "height": area_height,
                "speed": 1800
            }
        )
        logger.info(
        f"Scrolled {direction.upper()} | percent={percent} | DUT={dut_name}"
    )
        
    
    @keyword
    def start_screen_recording(self, dut_name, test_name):
        """
        Start Android screen recording using adb screenrecord.
        """

        device_info = self.get_device_id(dut_name)
        device_id = self._resolve_dut_name(device_info)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_test_name = test_name.replace(" ", "_")
        device_video_path = f"/sdcard/{device_id}_{timestamp}_{safe_test_name}.mp4"

        logger.info(f"🎥 DUT name resolved to: {dut_name}")
        logger.info(f"📱 Device ID resolved to: {device_id}")
        logger.info(f"📁 Device video path: {device_video_path}")

        cmd = [
            "adb", "-s", device_id,
            "shell", "screenrecord",
            "--bit-rate", "8000000",
            "--time-limit", "180",
            device_video_path
        ]

        self._screen_record_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        self._device_video_path = device_video_path
        self._screen_record_device_id = device_id

        time.sleep(0.5)

        if self._screen_record_proc.poll() is not None:
            raise RuntimeError("❌ Screen recording failed to start")

        logger.info("✅ Screen recording started successfully")
        return device_video_path

    @keyword
    def stop_screen_recording(self, dut_name, local_video_path):
        """
        Stop Android screen recording and pull the video.
        """
        device_info = self.get_device_id(dut_name)
        device_id = self._resolve_dut_name(device_info)

        logger.info(f"🛑 Stopping recording on DUT: {dut_name}")
        logger.info(f"📱 Device ID: {device_id}")

        if hasattr(self, "_screen_record_proc") and self._screen_record_proc:
            self._screen_record_proc.terminate()
            self._screen_record_proc.wait(timeout=5)

        time.sleep(1)

        local_video_path = os.path.abspath(local_video_path)
        os.makedirs(os.path.dirname(local_video_path), exist_ok=True)

        subprocess.run(
            ["adb", "-s", device_id, "pull", self._device_video_path, local_video_path],
            check=True
        )

        logger.info(f"✅ Screen recording saved: {local_video_path}")
        return local_video_path


    def _resolve_dut_name(self, device_info):
        """
        Convert Robot SectionProxy / variable into a usable string.
        """
        if hasattr(device_info, "get"):
            device_id = device_info.get("device_id")

        # Case 2: Dict-like
        elif isinstance(device_info, dict):
            device_id = device_info.get("device_id")

        else:
            device_id = device_info

        if not device_id:
            raise RuntimeError("❌ device_id not found in DUT config")

        return str(device_id).strip()
    
    @keyword
    def Test_Video(self, video_path, width=480, title="Screen Recording"):
        video_path = os.path.abspath(video_path)

        if not os.path.exists(video_path):
            logger.warn(f"⚠️ Video not found: {video_path}")
            return

        html = f"""
        <div style="margin:10px 0">
            <b>🎬 {title}</b><br>
            <video width="{width}" controls>
                <source src="{video_path}" type="video/mp4">
                Your browser does not support the video tag.
            </video><br>
            <a href="{video_path}" target="_blank">⬇️ Download video</a>
        </div>
        """

        logger.info(html, html=True)
