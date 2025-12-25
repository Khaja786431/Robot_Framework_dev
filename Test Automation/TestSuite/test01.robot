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

Swipe screen
    swipe   left
    swipe   right

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
    Sleep    2s

verify captured image
    verify_image    C:/Users/nadik/Robot_Framework_dev/aut/Resources/images/Playstore_home.png
    Sleep    3s

verify text
    verify_text_on_screen    Kids
    Sleep    3s

Swipe screen
    swipe   up
    swipe   up
    swipe   down
    swipe   down
    sleep   3s
Click by image
    click_by_image  C:/Users/nadik/Robot_Framework_dev/aut/Resources/images/Games_play.png

Click Element On Phone DUT
    click_element_by_text    Search    ${DUT.Phone}
    click_element_by_text    Search    ${DUT.Phone}
    Sleep    2s

Input text
    input_text  bgmi

# Run command
#     run_command     adb shell screencap -p /sdcard/screen.png
#     run_command     adb pull /sdcard/screen.png 

Click by image
    click_by_image  C:/Users/nadik/Robot_Framework_dev/aut/Resources/images/Search_play.png




