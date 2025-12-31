*** Settings ***
# Import the Python file that contains all ADB-related keywords
# The path ".." means go one level up from current TestSuite folder
Library    ../Keywords/appium_keywords.py


*** Variables ***
# Robot variable holding DUT (Device Under Test) name
# This matches the INI section [DUT.Phone]
${DUT.Phone}    Phone


*** Test Cases ***
Verify Text on DUT using Appium
    verify_text_appium_full    Kids    ${DUT.Phone}
    tap_by_coordinates    Playstore.json    search_icon    ${DUT.Phone}
    tap_by_text    Action    ${DUT.Phone}