*** Settings ***
# Import the Python file that contains all ADB-related keywords
# The path ".." means go one level up from current TestSuite folder
Library    ../Keywords/adb_keywords.py


*** Variables ***
# Robot variable holding DUT (Device Under Test) name
# This matches the INI section [DUT.Phone]
${DUT.Phone}    Phone


*** Test Cases ***

Get Device Id Test
    # Call Python keyword: get_device_id("Phone")
    # Returns device ID from configurations.ini → Example: 10BF3122K4000JT
    ${id}=    get_device_id    ${DUT.Phone}

    # Print device ID in Robot logs
    Log    ${id}


Click Element On Phone DUT
    # Calls Python keyword: click_element_by_text("Play Store", "Phone")
    # Steps internally:
    # - Loads device_id for Phone
    # - Runs adb uiautomator dump
    # - Pulls /sdcard/ui.xml
    # - Searches XML for text="Play Store"
    # - Calculates tap coordinates
    # - Performs adb tap X Y
    click_element_by_text    Play Store    ${DUT.Phone}
