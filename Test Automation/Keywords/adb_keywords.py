import configparser          # Used to read configuration.ini file
import os                    # Used for file paths and running ADB commands
import xml.etree.ElementTree as ET   # Used to parse Android UI XML
from robot.api.deco import keyword   # Allows Robot Framework to call Python functions as keywords
import cv2
import numpy as np
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import re
import subprocess
import time
from datetime import datetime



class adb_keywords:

    def __init__(self):
        """
        Constructor — runs automatically when class object is created.
        Loads the configurations.ini file.
        """

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
        return self.config[section]["device_id"]
        
  
    @keyword
    def establish_adb_connection(self, dut_name):
        """
        Establish ADB connection using device_id from configuration.
        If already connected, return status.
        """

        # Get device_id from configuration
        device_id = self.get_device_id(dut_name)

        # Get currently connected adb devices
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise AssertionError("Failed to execute adb devices")

        connected_devices = result.stdout.strip().splitlines()[1:]

        # Check if device already connected
        for device in connected_devices:
            if device.startswith(device_id) and "device" in device:
                status =  f"Device '{device_id}' is already configured to the framework"
                logger.info(status)
                return status

        # Try to connect (for IP-based devices)
        connect_result = subprocess.run(
            ["adb", "connect", device_id],
            capture_output=True,
            text=True
        )

        if connect_result.returncode != 0:
            raise AssertionError(
                f"ADB connect failed for {device_id}: {connect_result.stderr.strip()}"
            )

        # Verify connection again
        verify = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )

        if device_id in verify.stdout:
            msg =  f"ADB connection established successfully for device '{device_id}'"
            logger.info(msg)
            return msg

        raise AssertionError(f"Failed to establish ADB connection for device '{device_id}'")



    @keyword
    def click_element_by_text(self, text, dut_name=None):
        """
        Robot keyword: Click UI element using visible text.
        If dut_name provided → use adb -s <device_id>, else use default ADB.
        """

        # Default no device_id
        device_id = None

        # If user passed DUT name, get device_id from config
        if dut_name:
            device_id = self.get_device_id(dut_name)

        # ---- STEP 1: Dump UI XML from device ----
        if device_id:
            # Dump UI hierarchy into /sdcard/ui.xml
            os.system(f"adb -s {device_id} shell uiautomator dump /sdcard/ui.xml")
            # Pull it from phone → local folder
            os.system(f"adb -s {device_id} pull /sdcard/ui.xml .")
        else:
            # Same but without device id
            os.system("adb shell uiautomator dump /sdcard/ui.xml")
            os.system("adb pull /sdcard/ui.xml .")

        # ---- STEP 2: Parse pulled XML ----
        tree = ET.parse("ui.xml")   # Load XML file
        root = tree.getroot()       # Get root <hierarchy> node

        # ---- STEP 3: Search all nodes for matching text ----
        for node in root.iter():    # Iterate every element in UI tree
            if node.attrib.get("text") == text:   # If node has this text
                bounds = node.attrib["bounds"]    # Example: "[100,200][300,400]"

                # Convert bounds → center tap coordinates
                x, y = self._get_center(bounds)

                # Perform tap on device
                self._tap(x, y, device_id)

                return f"Clicked '{text}' on DUT '{dut_name}'"

        # If not found anywhere →
        raise Exception(f"Text '{text}' not found on screen.")

    def _get_center(self, bounds):
        """
        Convert Android bounds string into center coordinates.
        Example input:  '[100,200][300,400]'
        """

        # Remove [] and split into numbers
        bounds = bounds.replace('[', '').replace(']', ',').split(',')

        # Convert string values to integers
        x1, y1, x2, y2 = map(int, bounds[:4])

        # Calculate center point
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        return center_x, center_y

    def _tap(self, x, y, device_id=None):
        """
        Performs actual tapping on the device screen using ADB input tap.
        """

        # If specific device ID exists, include -s <id>
        if device_id:
            os.system(f"adb -s {device_id} shell input tap {x} {y}")

        # Otherwise use default connected device
        else:
            os.system(f"adb shell input tap {x} {y}")

    @keyword
    def take_android_screenshot(self, filename="screen.png", device_id=None):
        """
        Takes a screenshot from connected Android device using ADB.
        Returns the local path of the image saved.
        """
        import os
        import subprocess

        local_path = os.path.join(os.getcwd(), filename)
        device_arg = ["-s", device_id] if device_id else []

        # Capture screenshot on device
        subprocess.run(["adb"] + device_arg + ["shell", "screencap", "-p", f"/sdcard/{filename}"])

        # Pull screenshot to PC
        subprocess.run(["adb"] + device_arg + ["pull", f"/sdcard/{filename}", local_path])

        return local_path

    @keyword
    def verify_text_on_screen(self, expected_text, screenshot_name="verify_text.png"):
        screenshot_path = self.take_android_screenshot(screenshot_name)

        image = Image.open(screenshot_path)
        gray = image.convert("L")
        gray = gray.point(lambda x: 0 if x < 150 else 255)

        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        draw = ImageDraw.Draw(image)

        expected_words = expected_text.lower().split()   # Split into words
        matched = False

        for i in range(len(data["text"])):
            word = data["text"][i].strip().lower()

            # Check each expected word instead of full sentence
            for ew in expected_words:
                if ew in word and ew != "":
                    matched = True
                    x, y, w, h = (
                        data["left"][i],
                        data["top"][i],
                        data["width"][i],
                        data["height"][i],
                    )
                    draw.rectangle((x, y, x + w, y + h), outline="red", width=4)

        highlighted_path = os.path.join(os.getcwd(), f"highlighted_{screenshot_name}")
        image.save(highlighted_path)

        # LOG INTO ROBOT REPORT
        if matched:
            logger.info(f"Verified text (any word matched): <b>{expected_text}</b>", html=True)
            logger.info(f'<img src="{highlighted_path}" width="450px">', html=True)
        else:
            logger.error(f"No words from '{expected_text}' found in screen!", html=True)
            logger.error(f'<img src="{highlighted_path}" width="450px">', html=True)
            raise AssertionError(f"Text not detected: {expected_text}")

        return highlighted_path
        
    

    @keyword
    def verify_image(self, image_name, dut_name=None, threshold=0.90):
        """
        Verifies full or partial image match AND logs both images in Robot report.
        """
        # device ID from DUT name
        device_id = self.get_device_id(dut_name)

        # Get Robot execution root
        project_root = BuiltIn().get_variable_value("${EXECDIR}")

        # Build reference image path automatically
        reference_image = os.path.join(
            project_root,
            "Resources",
            "images",
            image_name
        )

        if not os.path.isfile(reference_image):
            raise AssertionError(f"Reference image not found: {reference_image}")
        # Take fresh screenshot
        captured_path = self.take_android_screenshot("verify_image_screen.png", device_id)

        # Log captured image in Robot log
        logger.info(f"<b>Captured Screen:</b><br><img src='{captured_path}' width='300px'>", html=True)
        logger.info(f"<b>Reference Image:</b><br><img src='{reference_image}' width='300px'>", html=True)

        screen = cv2.imread(captured_path)
        ref = cv2.imread(reference_image)

        if screen is None:
            raise Exception("Failed to load captured screen.")
        if ref is None:
            raise Exception(f"Reference image not found: {reference_image}")
        
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)


        result = cv2.matchTemplate(
            screen_gray, ref_gray, cv2.TM_CCOEFF_NORMED
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        screen_h, screen_w = screen.shape[:2]
        ref_h, ref_w = ref.shape[:2]

        h, w = ref_gray.shape[:2]
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # Draw RED rectangle
        highlighted = screen.copy()
        cv2.rectangle(
            highlighted,
            top_left,
            bottom_right,
            (0, 0, 255),
            3
        )

        highlighted_path = os.path.join(
            os.getcwd(), "verify_image_highlighted.png"
        )
        cv2.imwrite(highlighted_path, highlighted)
        # Log captured image in Robot log
        logger.info(f"<b>Captured Screen:</b><br><img src='{highlighted_path}' width='300px'>", html=True)

        # --- FULL MATCH ---
        result = cv2.matchTemplate(screen, ref, cv2.TM_CCOEFF_NORMED)
        similarity = float(np.max(result))

        logger.info(f"<b>Similarity Score:</b> {similarity:.3f}", html=True)

        if similarity >= threshold:
            logger.info("<b>Image Verification: PASS</b>", html=True)
            return True
        else:
            logger.info("<b>Image Verification: FAIL</b>", html=True)
            raise AssertionError(
                f"Image mismatch: similarity={similarity:.3f} < {threshold}"
            )


    def get_screen_size(self, dut_name=None):
        """
        Gets the width and height of the connected Android device.
        If dut_name is provided, screen size is fetched for that specific device.
        """

        cmd = ["adb"]

        # Use specific device if provided
        if dut_name:
            device_id = self.get_device_id(dut_name)
            cmd += ["-s", device_id]

        cmd += ["shell", "wm", "size"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        ).stdout

        match = re.search(r"(\d+)x(\d+)", result)
        if not match:
            raise Exception("Unable to get screen size")

        width, height = int(match.group(1)), int(match.group(2))
        return width, height


    @keyword
    def swipe(self, direction: str, dut_name: str = None, duration: int = 300):
        """
        Performs swipe on a specific DUT.

        direction = right | left | up | down
        duration  = swipe speed in ms
        dut_name  = DUT name from config (Phone / Main / Cluster)
        """

        # Get device id if DUT is specified
        device_id = None
        if dut_name:
            device_id = self.get_device_id(dut_name)

        width, height = self.get_screen_size(dut_name)

        start_x = start_y = end_x = end_y = 0

        if direction.lower() == "right":
            start_x = int(width * 0.1)
            end_x = int(width * 0.9)
            start_y = end_y = int(height * 0.5)

        elif direction.lower() == "left":
            start_x = int(width * 0.9)
            end_x = int(width * 0.1)
            start_y = end_y = int(height * 0.5)

        elif direction.lower() == "up":
            start_y = int(height * 0.8)
            end_y = int(height * 0.2)
            start_x = end_x = int(width * 0.5)

        elif direction.lower() == "down":
            start_y = int(height * 0.2)
            end_y = int(height * 0.8)
            start_x = end_x = int(width * 0.5)

        else:
            raise ValueError(f"Invalid direction: {direction}")

        # Build adb command
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]

        cmd += [
            "shell", "input", "swipe",
            str(start_x), str(start_y),
            str(end_x), str(end_y),
            str(duration)
        ]

        subprocess.run(cmd, check=True)
        target = dut_name if dut_name else "default device"
        message = f"Swipe '{direction}' performed successfully on {target} using {start_x, start_y, end_x, end_y}"

        logger.info(message)
        return message
    
    @keyword
    def click_by_image(self, image_name, dut_name, threshold=0.8):
        """
        Takes screenshot using take_android_screenshot(),
        performs template match, clicks, and logs highlighted image on specific device.
        `dut_name`: DUT name as defined in configuration.ini
        """

        # Resolve device ID from config
        device_id = self.get_device_id(dut_name)

        # 1. Get Robot project root
        project_root = BuiltIn().get_variable_value("${EXECDIR}")

        # 2. Build correct reference image path
        reference_image = os.path.join(
            project_root,
            "Resources",
            "images",
            image_name
        )

        if not os.path.isfile(reference_image):
            raise AssertionError(f"Reference image not found: {reference_image}")

        # 1. Take screenshot
        screenshot = self.take_android_screenshot("click_temp_screen.png", device_id)

        screen = cv2.imread(screenshot)
        template = cv2.imread(reference_image)

        if screen is None:
            raise AssertionError("Captured screenshot not found")
        if template is None:
            raise AssertionError(f"Template image not found: {reference_image}")

        # 2. Template matching
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            raise AssertionError(f"Image not found. Match score={max_val}")

        # 3. Rectangle coordinates
        h, w = template.shape[:2]
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # 4. Draw rectangle
        highlighted = screen.copy()
        cv2.rectangle(highlighted, top_left, bottom_right, (0, 0, 255), 3)

        highlighted_path = "highlighted_match.png"
        cv2.imwrite(highlighted_path, highlighted)

        # 5. Log image in Robot report
        logger.info(
            f"<b>Image matched (confidence={max_val:.3f})</b><br>"
            f"<img src='{highlighted_path}' width='40%'>",
            html=True
        )

        # 6. Tap
        tap_x = top_left[0] + w // 2
        tap_y = top_left[1] + h // 2

        subprocess.run(["adb", "-s", device_id, "shell", "input", "tap", str(tap_x), str(tap_y)])

        logger.info(f"Clicked at {tap_x},{tap_y} (match={max_val})")
        return f"Clicked at {tap_x},{tap_y} (match={max_val})"

    
    @keyword
    def input_text(self, text):
        """
        Inputs the given text on the connected Android device
        using ADB input text command.
        """
        # Escape spaces for ADB
        text = text.replace(" ", "%s")

        # adb shell input text "<text>"
        subprocess.run(["adb", "shell", "input", "text", text])

        return f"Entered text: {text}"
    
    @keyword
    def run_command(self, command):
        """
        Runs any shell/adb/system command and returns the output.
        Usage: Run Command    adb devices
        """

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise AssertionError(f"Command failed: {result.stderr.strip()}")

        return result.stdout.strip()


    @keyword
    def start_screen_recording(self, device_id, test_name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_test_name = test_name.replace(" ", "_")
        device_video_path = f"/sdcard/{device_id}_{timestamp}_{safe_test_name}.mp4"

        cmd = ["adb", "-s", device_id, "shell", "screenrecord", device_video_path]
        proc = subprocess.Popen(cmd)
        self._screen_record_proc = proc
        self._device_video_path = device_video_path

        return device_video_path

    @keyword
    def stop_screen_recording(self, device_id, local_video_path):
        """Stop screenrecord and pull video."""
        # Kill recording
        if hasattr(self, "_screen_record_proc"):
            self._screen_record_proc.terminate()
            self._screen_record_proc.wait()
            logger.info(f"Stopped screen recording on {device_id}")

        # Give Android a moment to finalize the file
        time.sleep(1)

        # Pull video from device
        cmd_pull = ["adb", "-s", device_id, "pull", self._device_video_path, local_video_path]
        subprocess.run(cmd_pull, check=True)
        logger.info(f"Video pulled to {local_video_path}")
        return local_video_path
    
    @keyword
    def get_absolute_path(self, path):
        """Return absolute path of a file."""
        return os.path.abspath(path)

    @keyword
    def tap_by_coordinates(self, json_name, key_name, dut_name):
        """
        Tap on screen using X,Y coordinates from JSON key.
        JSON is auto-loaded from Resources/Coordinates/.
        """
        import json
        # import os
        # import subprocess
        # from robot.api import logger, BuiltIn

        device_id = self.get_device_id(dut_name)

        project_root = BuiltIn().get_variable_value("${EXECDIR}")
        json_file = os.path.join(
            project_root,
            "Resources",
            "coordinates",
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

        subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "tap", str(x), str(y)],
            check=True
        )

        msg = f"Tapped {key_name} at ({x},{y}) on device {device_id}"
        logger.info(msg)
        return msg
