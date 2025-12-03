import configparser          # Used to read configuration.ini file
import os                    # Used for file paths and running ADB commands
import xml.etree.ElementTree as ET   # Used to parse Android UI XML
from robot.api.deco import keyword   # Allows Robot Framework to call Python functions as keywords
import cv2
import numpy as np
from robot.api import logger



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


    # def verify_image(self, reference_image, threshold=0.90):
    #         """
    #         ONE API that verifies:
    #         - FULL image match (if reference size == screen size)
    #         - PARTIAL image match (if reference smaller than screen)

    #         Automatically detects full vs partial.
    #         """

    #         # Take fresh screenshot
    #         captured_path = self.take_android_screenshot("verify_image_screen.png")

    #         screen = cv2.imread(captured_path)
    #         ref = cv2.imread(reference_image)

    #         if screen is None:
    #             raise Exception("Failed to load captured screen.")
    #         if ref is None:
    #             raise Exception(f"Reference image not found: {reference_image}")

    #         screen_h, screen_w = screen.shape[:2]
    #         ref_h, ref_w = ref.shape[:2]

    #         # --- FULL SCREEN MATCH (same size) ---
    #         if screen_h == ref_h and screen_w == ref_w:
    #             result = cv2.matchTemplate(screen, ref, cv2.TM_CCOEFF_NORMED)
    #             similarity = float(np.max(result))

    #             if similarity >= threshold:
    #                 return True
    #             else:
    #                 raise AssertionError(
    #                     f"Full screen mismatch: similarity={similarity:.3f} < {threshold}"
    #                 )

    #         # --- PARTIAL IMAGE MATCH (small reference) ---
    #         else:
    #             result = cv2.matchTemplate(screen, ref, cv2.TM_CCOEFF_NORMED)
    #             similarity = float(np.max(result))

    #             if similarity >= threshold:
    #                 return True
    #             else:
    #                 raise AssertionError(
    #                     f"Partial image not found: similarity={similarity:.3f} < {threshold}"
    #                 )


    def verify_image(self, reference_image, threshold=0.90):
        """
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
