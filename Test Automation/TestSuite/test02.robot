*** Settings ***
# Import the Python file that contains all ADB-related keywords
# The path ".." means go one level up from current TestSuite folder
Library    String
Library    OperatingSystem
Library    BuiltIn
Library    ../Keywords/adb_keywords.py


*** Variables ***
# Robot variable holding DUT (Device Under Test) name
# This matches the INI section [DUT.Phone]
${DUT.Phone}    Phone
${VIDEO_DIR}    videos



*** Test Cases ***
Establish adb connection
    ${DEVICE_ID}=    get_device_id    Phone
    ${VIDEO_DIR}=        Set Variable    videos
    ${SAFE_TEST_NAME}=   Replace String    ${TEST NAME}    ${SPACE}    _
    ${VIDEO_NAME}=       Set Variable    ${SAFE_TEST_NAME}.mp4
    ${DEVICE_VIDEO}=     Set Variable    /sdcard/${VIDEO_NAME}
    ${LOCAL_VIDEO}=      Set Variable    ${VIDEO_DIR}/${VIDEO_NAME}

    run_command    if not exist ${VIDEO_DIR} mkdir ${VIDEO_DIR}
    ${DEVICE_VIDEO}=    start_screen_recording    ${DEVICE_ID}    ${TEST NAME}
    Sleep    2s
    establish_adb_connection    ${DUT.Phone}
    click_by_image    Games_play.png    ${DUT.Phone}
    Sleep    2s
    verify_image    Books_play.png    ${DUT.Phone}
    Sleep    2s
    swipe   up    ${DUT.Phone}
    Sleep    2s
    tap_by_coordinates    Playstore.json    search_icon    ${DUT.Phone}
    Sleep    2s
    tap_by_text    Action    ${DUT.Phone}
    Sleep    2s
    verify_text_ocr    Shooter action games    ${DUT.Phone}
    Sleep    2s
    ${LOCAL_VIDEO}=    stop_screen_recording    ${DEVICE_ID}    ${VIDEO_DIR}

    ${ABS_LOCAL_VIDEO}=    get_absolute_path    ${LOCAL_VIDEO}
    Log    <a href="file://${ABS_LOCAL_VIDEO}">📹 Failure Video</a>    html=True

    