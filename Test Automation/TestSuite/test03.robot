*** Settings ***
# Import the Python file that contains all ADB-related keywords
# The path ".." means go one level up from current TestSuite folder
Library    ../Keywords/appium_keywords.py
Library    BuiltIn


*** Variables ***
# Robot variable holding DUT (Device Under Test) name
# This matches the INI section [DUT.Phone]
# ${DUT.Phone}    Phone
${DUT}    Phone


*** Test Cases ***
Verify Keywords on DUT using Appium
    verify_text_appium_full    Kids    Phone
    tap_by_coordinates    Playstore.json    search_icon    Phone
    tap_by_text    Action    Phone
    verify_image_element    Books_play.png    Phone
    click_by_image    Games_play.png    Phone
    run_command    getprop ro.build.version.release    Phone
    press_key    BACK    Phone
    Sleep    2s
    scroll_top_bottom    Phone    down
    Sleep    2s
    press_key    HOME    Phone
    Sleep    2s
    swipe_left_right    Phone    right
    Sleep    2s

