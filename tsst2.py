import ctypes
import random
import re
import time
import uuid
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


REGISTER_URL = "http://8.nat0.cn:49347/register"
LOGIN_URL = "http://8.nat0.cn:49347/login"
TEMP_MAIL_URL = "https://10minutemail.one/"
UNEXPECTED_GITHUB_URL_PREFIX = "https://github.com/QuantumNous/new-api"
PASSWORD = "12345678"
TIMEOUT_SECONDS = 12
EMAIL_LOAD_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 0.15
ACTION_JITTER_MIN_SECONDS = 0.08
ACTION_JITTER_MAX_SECONDS = 0.35
GET_CODE_TEXT = "\u83b7\u53d6\u9a8c\u8bc1\u7801"
MAIL_SUBJECT_TEXT = "\u661f\u7a7a\u65e0\u7a77\u79d1\u6280\u90ae\u7bb1\u9a8c\u8bc1\u90ae\u4ef6"
REGISTER_TEXT = "\u6ce8\u518c"
CONTINUE_TEXT = "\u7ee7\u7eed"
TOKEN_MANAGEMENT_TEXT = "\u4ee4\u724c\u7ba1\u7406"
ADD_TOKEN_TEXT = "\u6dfb\u52a0\u4ee4\u724c"
SUBMIT_TEXT = "\u63d0\u4ea4"
AUTH_FILE = Path("auth.txt")
VK_ENTER = 0x0D
VK_SHIFT = 0x10
VK_TAB = 0x09
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9

user32 = ctypes.windll.user32


def jitter_pause(min_seconds: float = ACTION_JITTER_MIN_SECONDS, max_seconds: float = ACTION_JITTER_MAX_SECONDS) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--incognito")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-features=HttpsFirstBalancedModeAutoEnable,HttpsUpgrades")
    options.add_argument("--allow-running-insecure-content")
    options.page_load_strategy = "eager"

    driver = webdriver.Chrome(options=options)
    driver.get(REGISTER_URL)
    return driver


def _press_key(vk_code: int) -> None:
    user32.keybd_event(vk_code, 0, 0, 0)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _press_shift_tab() -> None:
    user32.keybd_event(VK_SHIFT, 0, 0, 0)
    user32.keybd_event(VK_TAB, 0, 0, 0)
    user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)


def _find_chrome_window() -> Optional[int]:
    windows: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_windows(hwnd: int, lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        title_length = user32.GetWindowTextLengthW(hwnd)
        if title_length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, buffer, title_length + 1)
        title = buffer.value.lower()

        if "8.nat0.cn" in title or "google chrome" in title:
            windows.append(hwnd)

        return True

    user32.EnumWindows(enum_windows, 0)
    return windows[0] if windows else None


def _focus_chrome_window() -> bool:
    hwnd = _find_chrome_window()
    if not hwnd:
        return False

    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True


def _try_continue_warning() -> None:
    if not _focus_chrome_window():
        return

    # Chrome's warning dialog usually focuses the "返回" button first.
    _press_shift_tab()
    _press_key(VK_ENTER)


def _find_visible_element(driver: webdriver.Chrome, element_id: str):
    elements = driver.find_elements(By.ID, element_id)
    for element in elements:
        if element.is_displayed() and element.is_enabled():
            return element
    return None


def wait_for_registration_form(driver: webdriver.Chrome):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    last_continue_attempt = 0.0

    while time.monotonic() < deadline:
        username_input = _find_visible_element(driver, "username")
        if username_input is not None:
            password_input = _find_visible_element(driver, "password")
            confirm_input = _find_visible_element(driver, "password2")
            if password_input is not None and confirm_input is not None:
                return username_input, password_input, confirm_input

        now = time.monotonic()
        if now - last_continue_attempt >= 0.5:
            _try_continue_warning()
            last_continue_attempt = now

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Registration form did not appear in time.")


def wait_for_visible_element(driver: webdriver.Chrome, by: By, value: str):
    deadline = time.monotonic() + TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        elements = driver.find_elements(by, value)
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                return element
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Element not found in time: {by}={value}")


def wait_for_email_value(driver: webdriver.Chrome) -> str:
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        email_input = wait_for_visible_element(
            driver,
            By.CSS_SELECTOR,
            "input[aria-label='Email Address']",
        )
        email_address = (email_input.get_attribute("value") or "").strip()
        if email_address and email_address.lower() != "loading...":
            return email_address
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Temporary email address stayed in Loading... state.")


def wait_until_email_input_ready(driver: webdriver.Chrome):
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        email_input = wait_for_visible_element(driver, By.ID, "email")
        current_value = (email_input.get_attribute("value") or "").strip()
        placeholder = (email_input.get_attribute("placeholder") or "").strip()

        if current_value.lower() != "loading..." and placeholder != "Loading...":
            return email_input

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Register email input stayed in Loading... state.")


def fill_registration_form(driver: webdriver.Chrome) -> str:
    username = str(uuid.uuid4())[:15]
    username_input, password_input, confirm_input = wait_for_registration_form(driver)

    username_input.clear()
    jitter_pause()
    username_input.send_keys(username)

    password_input.clear()
    jitter_pause()
    password_input.send_keys(PASSWORD)

    confirm_input.clear()
    jitter_pause()
    confirm_input.send_keys(PASSWORD)

    return username


def close_unexpected_tabs(driver: webdriver.Chrome, keep_handles: set[str]) -> None:
    current_handle = driver.current_window_handle

    for handle in list(driver.window_handles):
        if handle in keep_handles:
            continue

        driver.switch_to.window(handle)
        current_url = driver.current_url
        if current_url.startswith(UNEXPECTED_GITHUB_URL_PREFIX):
            driver.close()

    if current_handle in driver.window_handles:
        driver.switch_to.window(current_handle)
    elif keep_handles:
        for handle in keep_handles:
            if handle in driver.window_handles:
                driver.switch_to.window(handle)
                break


def open_temp_mail_and_get_address(driver: webdriver.Chrome, register_tab: str) -> tuple[str, str]:
    existing_handles = set(driver.window_handles)
    close_unexpected_tabs(driver, {register_tab})

    driver.switch_to.window(register_tab)
    driver.execute_script("window.open(arguments[0], '_blank');", TEMP_MAIL_URL)

    new_handles = [handle for handle in driver.window_handles if handle not in existing_handles]
    if not new_handles:
        raise RuntimeError("Temporary mail tab was not created.")

    temp_mail_tab = new_handles[-1]
    driver.switch_to.window(temp_mail_tab)

    email_address = wait_for_email_value(driver)

    driver.switch_to.window(register_tab)
    return temp_mail_tab, email_address


def fill_email_and_request_code(driver: webdriver.Chrome, email_address: str) -> None:
    email_input = wait_until_email_input_ready(driver)
    email_input.clear()
    jitter_pause()
    email_input.send_keys(email_address)
    jitter_pause()

    get_code_button = wait_for_visible_element(
        driver,
        By.XPATH,
        f"//button[.//span[contains(@class, 'semi-button-content') and normalize-space()='{GET_CODE_TEXT}']]",
    )
    get_code_button.click()


def wait_for_verification_mail(driver: webdriver.Chrome, temp_mail_tab: str) -> None:
    driver.switch_to.window(temp_mail_tab)
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS
    mail_xpath = (
        f"//div[contains(@class, 'font-medium') and normalize-space()='{MAIL_SUBJECT_TEXT}']"
    )

    while time.monotonic() < deadline:
        mail_subjects = driver.find_elements(By.XPATH, mail_xpath)
        for mail_subject in mail_subjects:
            if not mail_subject.is_displayed():
                continue
            clickable_container = mail_subject.find_element(
                By.XPATH, "./ancestor::div[contains(@class, 'cursor-pointer')][1]"
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                clickable_container,
            )
            try:
                clickable_container.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", clickable_container)
            return
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Verification email did not arrive in time.")


def get_verification_code(driver: webdriver.Chrome, temp_mail_tab: str) -> str:
    wait_for_verification_mail(driver, temp_mail_tab)
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        content = wait_for_visible_element(
            driver,
            By.CSS_SELECTOR,
            "div.prose",
        )
        text = content.text
        match = re.search(r"验证码为[:：]\s*([A-Za-z0-9]+)", text)
        if match:
            return match.group(1)
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Verification code was not found in the email body.")


def fill_verification_code(driver: webdriver.Chrome, register_tab: str, code: str) -> None:
    driver.switch_to.window(register_tab)
    verification_input = wait_for_visible_element(driver, By.ID, "verification_code")
    verification_input.clear()
    jitter_pause()
    verification_input.send_keys(code)
    jitter_pause()


def click_register(driver: webdriver.Chrome) -> None:
    register_button = wait_for_visible_element(
        driver,
        By.XPATH,
        f"//button[@type='submit' and .//span[normalize-space()='{REGISTER_TEXT}']]",
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        register_button,
    )
    try:
        register_button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", register_button)


def append_auth_info(username: str, email_address: str, token: str) -> None:
    with AUTH_FILE.open("a", encoding="utf-8") as auth_file:
        auth_file.write(
            f"username: {username}, password: {PASSWORD}, email: {email_address}, token: {token}\n"
        )


def wait_for_login_page(driver: webdriver.Chrome) -> None:
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if driver.current_url.rstrip("/") == LOGIN_URL:
            return
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Did not navigate to the login page in time.")


def fill_login_form(driver: webdriver.Chrome, email_address: str) -> None:
    username_input = wait_for_visible_element(driver, By.ID, "username")
    password_input = wait_for_visible_element(driver, By.ID, "password")

    username_input.clear()
    jitter_pause()
    username_input.send_keys(email_address)

    password_input.clear()
    jitter_pause()
    password_input.send_keys(PASSWORD)
    jitter_pause()


def click_button_by_text(driver: webdriver.Chrome, text: str) -> None:
    button = wait_for_visible_element(
        driver,
        By.XPATH,
        f"//button[.//span[normalize-space()='{text}']]",
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        button,
    )
    try:
        button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", button)


def click_continue_after_login(driver: webdriver.Chrome) -> None:
    click_button_by_text(driver, CONTINUE_TEXT)


def open_token_management(driver: webdriver.Chrome) -> None:
    nav_item = wait_for_visible_element(
        driver,
        By.XPATH,
        f"//span[contains(@class, 'semi-navigation-item-text')]//span[normalize-space()='{TOKEN_MANAGEMENT_TEXT}']",
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        nav_item,
    )
    try:
        nav_item.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", nav_item)


def add_token(driver: webdriver.Chrome) -> str:
    click_button_by_text(driver, ADD_TOKEN_TEXT)

    name_input = wait_for_visible_element(driver, By.ID, "name")
    name_input.clear()
    jitter_pause()
    name_input.send_keys("aaa")
    jitter_pause()

    submit_button = wait_for_visible_element(
        driver,
        By.XPATH,
        f"//button[.//span[normalize-space()='{SUBMIT_TEXT}']]",
    )
    try:
        submit_button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", submit_button)

    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        token_input = wait_for_visible_element(
            driver,
            By.XPATH,
            "//div[contains(@class, 'semi-input-wrapper__with-suffix')]//input[contains(@class, 'semi-input-small')]",
        )
        current_value = (token_input.get_attribute("value") or "").strip()
        if current_value.startswith("sk-") and "*" not in current_value:
            return current_value

        reveal_button = token_input.find_element(
            By.XPATH,
            "./ancestor::div[contains(@class, 'semi-input-wrapper__with-suffix')][1]"
            "//button[@aria-label='toggle token visibility']",
        )
        try:
            reveal_button.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", reveal_button)

        time.sleep(POLL_INTERVAL_SECONDS)

    raise RuntimeError("Token value is still masked or empty.")


def main() -> None:
    driver = build_driver()
    register_tab = driver.current_window_handle

    try:
        username = fill_registration_form(driver)
        close_unexpected_tabs(driver, {register_tab})
        temp_mail_tab, email_address = open_temp_mail_and_get_address(driver, register_tab)
        fill_email_and_request_code(driver, email_address)
        verification_code = get_verification_code(driver, temp_mail_tab)
        fill_verification_code(driver, register_tab, verification_code)
        click_register(driver)
        wait_for_login_page(driver)
        fill_login_form(driver, email_address)
        click_continue_after_login(driver)
        open_token_management(driver)
        token = add_token(driver)
        append_auth_info(username, email_address, token)
        print(
            f"Filled registration form with username: {username}, "
            f"email: {email_address}, verification code: {verification_code}, token: {token}"
        )
    except Exception:
        driver.quit()
        raise
    else:
        driver.quit()


if __name__ == "__main__":
    main()
