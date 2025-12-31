from appium import webdriver
from robot.api.deco import keyword
from appium.options.android import UiAutomator2Options
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
import configparser
import time
import os 
import json
import cv2
import pytesseract


class appium_keywords:

    def __init__(self):
        self.driver = None
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
        if self.driver:
            return self.driver

        caps = self.get_device_id(dut_name)

        options = UiAutomator2Options()
        options.platform_name = caps.get("platformName")
        options.device_name = caps.get("deviceName")
        options.udid = caps.get("udid")
        options.automation_name = caps.get("automationName")
        options.app_package = caps.get("appPackage")
        options.app_activity = caps.get("appActivity")
        options.no_reset = True

        self.driver = webdriver.Remote(
            command_executor="http://127.0.0.1:4723",
            options=options
        )

        time.sleep(3)
        return self.driver

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