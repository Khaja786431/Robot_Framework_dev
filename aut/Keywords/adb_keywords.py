import configparser          # Used to read configuration.ini file
import os                    # Used for file paths and running ADB commands
import xml.etree.ElementTree as ET   # Used to parse Android UI XML
from robot.api.deco import keyword   # Allows Robot Framework to call Python functions as keywords
import cv2
import numpy as np
from robot.api import logger
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import re
import subprocess


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
    def take_android_screenshot(self, filename="screen.png"):
        """
        Takes a screenshot from connected Android device using ADB.
        Returns the local path of the image saved.
        """
        import os
        import subprocess

        local_path = os.path.join(os.getcwd(), filename)

        # Capture screenshot on device
        subprocess.run(["adb", "shell", "screencap", "-p", f"/sdcard/{filename}"])

        # Pull screenshot to PC
        subprocess.run(["adb", "pull", f"/sdcard/{filename}", local_path])

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
    def verify_image(self, reference_image, threshold=0.90):
        """]
        Verifies full or partial image match AND logs both images in Robot report.
        """

        # Take fresh screenshot
        captured_path = self.take_android_screenshot("verify_image_screen.png")

        # Log captured image in Robot log
        logger.info(f"<b>Captured Screen:</b><br><img src='{captured_path}' width='300px'>", html=True)
        logger.info(f"<b>Reference Image:</b><br><img src='{reference_image}' width='300px'>", html=True)

        screen = cv2.imread(captured_path)
        ref = cv2.imread(reference_image)

        if screen is None:
            raise Exception("Failed to load captured screen.")
        if ref is None:
            raise Exception(f"Reference image not found: {reference_image}")

        screen_h, screen_w = screen.shape[:2]
        ref_h, ref_w = ref.shape[:2]

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

    def get_screen_size(self):
        """Gets the width and height of the connected Android device."""
        result = subprocess.run(
            ["adb", "shell", "wm", "size"],
            capture_output=True,
            text=True
        ).stdout

        match = re.search(r"(\d+)x(\d+)", result)
        if not match:
            raise Exception("Unable to get screen size")

        width, height = int(match.group(1)), int(match.group(2))
        return width, height

    @keyword
    def swipe(self, direction: str, duration: int = 300):
        """
        Performs swipe on DUT.
        direction = right | left | up | down
        duration = swipe speed in ms
        """
        width, height = self.get_screen_size()

        # Default coordinates
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

        # Perform swipe
        cmd = [
            "adb", "shell", "input", "swipe",
            str(start_x), str(start_y),
            str(end_x), str(end_y),
            str(duration)
        ]

        subprocess.run(cmd)
        print(f"Swiped {direction} successfully")

  
    @keyword
    def click_by_image(self, reference_image, threshold=0.8):
        """
        Takes screenshot using take_android_screenshot(),
        performs template match, clicks, and logs highlighted image.
        """

        # 1. Take screenshot
        screenshot = self.take_android_screenshot("click_temp_screen.png")

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

        subprocess.run(["adb", "shell", "input", "tap", str(tap_x), str(tap_y)])

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

        # If user passes string, split to list for subprocess
        if isinstance(command, str):
            command = command.split()

        result = subprocess.run(command, capture_output=True, text=True)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            raise AssertionError(f"Command failed: {stderr}")

        return stdout