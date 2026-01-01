*** Settings ***
# Import the Python file that contains all ADB-related keywords
# The path ".." means go one level up from current TestSuite folder
Library    ../Keywords/appium_keywords.py
Library    BuiltIn


*** Variables ***
# Robot variable holding DUT (Device Under Test) name
# This matches the INI section [DUT.Phone]
${DUT.Phone}    Phone


*** Test Cases ***
Verify Keywords on DUT using Appium
    start_screen_recording    ${DUT.Phone}    Swipe_Test
    verify_text_appium_full    Kids    ${DUT.Phone}
    tap_by_coordinates    Playstore.json    search_icon    ${DUT.Phone}
    tap_by_text    Action    ${DUT.Phone}
    verify_image_element    Books_play.png    ${DUT.Phone}
    click_by_image    Games_play.png    ${DUT.Phone}
    run_command    getprop ro.build.version.release    ${DUT.Phone}
    press_key    BACK    ${DUT.Phone}
    Sleep    2s
    scroll_top_bottom    ${DUT.Phone}    down
    Sleep    2s
    press_key    HOME    ${DUT.Phone}
    Sleep    2s
    swipe_left_right    ${DUT.Phone}    right
    Sleep    2s
    Stop Screen Recording     ${DUT.Phone}    ${EXECDIR}/videos/swipe_test.mp4
    Test_Video    ${EXECDIR}/videos/swipe_test.mp4
