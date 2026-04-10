import ctypes
import random
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import winreg
from pathlib import Path
from typing import Optional

import undetected_chromedriver as uc
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.by import By


REGISTER_URL = "http://8.nat0.cn:49347/register"
LOGIN_URL = "http://8.nat0.cn:49347/login"
TEMP_MAIL_URL = "https://10minutemail.one/"
UNEXPECTED_GITHUB_URL_PREFIX = "https://github.com/QuantumNous/new-api"
PASSWORD = "12345678"
TIMEOUT_SECONDS = 12
EMAIL_LOAD_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 0.15
ACTION_JITTER_MIN_SECONDS = 1.5
ACTION_JITTER_MAX_SECONDS = 3.5
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

# ── Fingerprint spoofing constants ──────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome=131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
]

WEBGL_RENDERERS = [
    ("ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (NVIDIA)"),
    ("ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (AMD)"),
    ("ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (AMD)"),
    ("ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (Intel)"),
    ("ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
     "Google Inc. (Intel)"),
]

FAKE_PLUGINS = [
    {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer",
     "description": "Portable Document Format", "mimeTypes": ["application/pdf"]},
    {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
     "description": "", "mimeTypes": ["application/pdf"]},
    {"name": "Native Client", "filename": "internal-nacl-plugin",
     "description": "", "mimeTypes": ["application/x-nacl", "application/x-pnacl"]},
]

WINDOW_SIZES = [
    (1366, 768), (1440, 900), (1536, 864), (1600, 900),
    (1920, 1080), (1280, 720), (1280, 800), (1680, 1050),
]


def _build_fingerprint_js() -> str:
    """Generate a randomised fingerprint-spoofing script for CDP injection."""
    renderer, vendor = random.choice(WEBGL_RENDERERS)
    hardware_concurrency = random.choice([2, 4, 6, 8, 12, 16])
    device_memory = random.choice([2, 4, 8, 16])
    max_touch_points = random.choice([0, 0, 0, 1, 5, 10])
    canvas_noise_seed = random.randint(1, 999999)

    # Pre-build plugins JS string (avoid f-string / .format conflict)
    _plugins_js = ",".join(
        '{{name:"{name}",filename:"{filename}",description:"{description}",length:{length}}}'.format(
            name=p["name"], filename=p["filename"], description=p["description"], length=len(p["mimeTypes"])
        )
        for p in FAKE_PLUGINS
    )

    return f"""
    // ── navigator.webdriver ──
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined,
        configurable: true
    }});

    // ── navigator.plugins ──
    Object.defineProperty(navigator, 'plugins', {{
        get: () => {{
            const plugins = [
                {_plugins_js}
            ];
            plugins.item = (i) => plugins[i] || null;
            plugins.namedItem = (n) => plugins.find(p => p.name === n) || null;
            plugins.refresh = () => {{}};
            return plugins;
        }},
        configurable: true
    }});

    // ── navigator.hardwareConcurrency ──
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {hardware_concurrency},
        configurable: true
    }});

    // ── navigator.deviceMemory ──
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {device_memory},
        configurable: true
    }});

    // ── navigator.maxTouchPoints ──
    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: () => {max_touch_points},
        configurable: true
    }});

    // ── navigator.connection (NetworkInformation) ──
    if (navigator.connection) {{
        Object.defineProperty(navigator.connection, 'rtt', {{get: () => {random.choice([50, 100, 150, 200])}, configurable: true}});
        Object.defineProperty(navigator.connection, 'downlink', {{get: () => {random.choice([1.4, 2.6, 5.6, 10])}, configurable: true}});
        Object.defineProperty(navigator.connection, 'effectiveType', {{get: () => '{random.choice(["4g", "4g", "4g", "3g"])}', configurable: true}});
    }}

    // ── Canvas fingerprint noise ──
    const _toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const shift = {canvas_noise_seed} % 7 - 3;
            const imgData = ctx.getImageData(0, 0, Math.max(1, this.width), Math.max(1, this.height));
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = Math.min(255, Math.max(0, imgData.data[i] + shift));
            }}
            ctx.putImageData(imgData, 0, 0);
        }}
        return _toDataURL.apply(this, arguments);
    }};

    const _toBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const shift = {canvas_noise_seed} % 7 - 3;
            const imgData = ctx.getImageData(0, 0, Math.max(1, this.width), Math.max(1, this.height));
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = Math.min(255, Math.max(0, imgData.data[i] + shift));
            }}
            ctx.putImageData(imgData, 0, 0);
        }}
        return _toBlob.apply(this, arguments);
    }};

    // ── WebGL renderer / vendor ──
    const _getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return '{vendor}';
        if (param === 37446) return '{renderer}';
        return _getParameter.apply(this, arguments);
    }};

    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const _getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return '{vendor}';
            if (param === 37446) return '{renderer}';
            return _getParameter2.apply(this, arguments);
        }};
    }}

    // ── window.chrome ──
    if (!window.chrome) {{
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};
    }}

    // ── Permissions API ──
    const _query = Permissions.prototype.query;
    Permissions.prototype.query = function(parameters) {{
        if (parameters.name === 'notifications') {{
            return Promise.resolve({{state: Notification.permission}});
        }}
        return _query.apply(this, arguments);
    }};

    // ── Remove automation indicators ──
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """


def jitter_pause(min_seconds: float = ACTION_JITTER_MIN_SECONDS, max_seconds: float = ACTION_JITTER_MAX_SECONDS) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def _detect_chrome_binary_and_major_version() -> tuple[Optional[str], Optional[int]]:
    chrome_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
            version_text, _ = winreg.QueryValueEx(key, "version")
            match = re.search(r"^(\d+)\.", version_text)
            if match:
                for chrome_path in chrome_candidates:
                    if chrome_path.exists():
                        return str(chrome_path), int(match.group(1))
    except OSError:
        pass

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon") as key:
            version_text, _ = winreg.QueryValueEx(key, "version")
            match = re.search(r"^(\d+)\.", version_text)
            if match:
                for chrome_path in chrome_candidates:
                    if chrome_path.exists():
                        return str(chrome_path), int(match.group(1))
    except OSError:
        pass

    for chrome_path in chrome_candidates:
        if not chrome_path.exists():
            continue

        try:
            result = subprocess.run(
                [str(chrome_path), "--version"],
                capture_output=True,
                timeout=5,
            )
            raw_output = result.stdout or result.stderr or b""
            try:
                version_text = raw_output.decode("utf-8")
            except UnicodeDecodeError:
                version_text = raw_output.decode("gbk", errors="ignore")
            version_text = version_text.strip()
            match = re.search(r"(\d+)\.", version_text)
            if match:
                return str(chrome_path), int(match.group(1))
        except Exception:
            pass

    return None, None


def _find_local_chromedriver(chrome_major: Optional[int]) -> Optional[str]:
    if not chrome_major:
        return None

    cache_root = Path.home() / ".cache" / "selenium" / "chromedriver" / "win64"
    if not cache_root.exists():
        return None

    matching_drivers = sorted(cache_root.glob(f"{chrome_major}.*\\chromedriver.exe"), reverse=True)
    if matching_drivers:
        return str(matching_drivers[0])

    return None


def _prepare_writable_chromedriver(chrome_major: Optional[int]) -> Optional[str]:
    source_driver = _find_local_chromedriver(chrome_major)
    if not source_driver:
        return None

    target_dir = Path.cwd() / ".local_chromedriver"
    target_dir.mkdir(exist_ok=True)
    target_path = target_dir / f"chromedriver-{chrome_major}.exe"

    if not target_path.exists():
        shutil.copy2(source_driver, target_path)

    return str(target_path)


def _cleanup_driver_artifacts(driver) -> None:
    profile_dir = getattr(driver, "_codex_temp_profile_dir", None)
    if not profile_dir:
        return

    try:
        shutil.rmtree(profile_dir, ignore_errors=True)
    except Exception:
        pass


def build_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    temp_profile_dir = Path(tempfile.mkdtemp(prefix="auto-register-chrome-", dir=str(Path.cwd())))

    options.add_argument("--incognito")
    options.add_argument(f"--user-data-dir={temp_profile_dir}")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disk-cache-size=0")
    options.add_argument("--media-cache-size=0")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-features=AutocompleteServerCommunicator,ChromeWhatsNewUI,HttpsFirstBalancedModeAutoEnable,HttpsUpgrades")
    options.add_argument("--disable-search-engine-choice-screen")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--allow-running-insecure-content")
    options.page_load_strategy = "eager"

    # Randomise window size
    width, height = random.choice(WINDOW_SIZES)
    options.add_argument(f"--window-size={width},{height}")

    # Randomise User-Agent
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")

    chrome_binary, chrome_major = _detect_chrome_binary_and_major_version()
    local_driver = _prepare_writable_chromedriver(chrome_major)
    chrome_kwargs = {"options": options}
    if chrome_binary:
        chrome_kwargs["browser_executable_path"] = chrome_binary
    if chrome_major:
        chrome_kwargs["version_main"] = chrome_major
    if local_driver:
        chrome_kwargs["driver_executable_path"] = local_driver

    driver = uc.Chrome(**chrome_kwargs)
    driver._codex_temp_profile_dir = str(temp_profile_dir)

    # Inject fingerprint spoofing via CDP on every frame
    fingerprint_js = _build_fingerprint_js()

    def _on_frame(frame):
        try:
            driver.execute_cdp_cmd("Page.addScriptToExecuteOnNewDocument", {"source": fingerprint_js})
        except Exception:
            pass

    # Inject for the initial page
    try:
        driver.execute_cdp_cmd("Page.addScriptToExecuteOnNewDocument", {"source": fingerprint_js})
    except Exception:
        pass

    # Override User-Agent via CDP (more thorough than CLI flag)
    try:
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": user_agent,
            "platform": "Win32",
        })
    except Exception:
        pass

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


def _find_visible_element(driver, element_id: str):
    elements = driver.find_elements(By.ID, element_id)
    for element in elements:
        if element.is_displayed() and element.is_enabled():
            return element
    return None


def wait_for_registration_form(driver):
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


def wait_for_visible_element(driver, by: By, value: str):
    deadline = time.monotonic() + TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        elements = driver.find_elements(by, value)
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                return element
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Element not found in time: {by}={value}")


def wait_for_email_value(driver) -> str:
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


def wait_until_email_input_ready(driver):
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        email_input = wait_for_visible_element(driver, By.ID, "email")
        current_value = (email_input.get_attribute("value") or "").strip()
        placeholder = (email_input.get_attribute("placeholder") or "").strip()

        if current_value.lower() != "loading..." and placeholder != "Loading...":
            return email_input

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Register email input stayed in Loading... state.")


def fill_registration_form(driver) -> str:
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


def close_unexpected_tabs(driver, keep_handles: set[str]) -> None:
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


def open_temp_mail_and_get_address(driver, register_tab: str) -> tuple[str, str]:
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


def fill_email_and_request_code(driver, email_address: str) -> None:
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
    jitter_pause()
    get_code_button.click()


def wait_for_verification_mail(driver, temp_mail_tab: str) -> None:
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
                jitter_pause()
                clickable_container.click()
            except ElementClickInterceptedException:
                jitter_pause()
                driver.execute_script("arguments[0].click();", clickable_container)
            return
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Verification email did not arrive in time.")


def get_verification_code(driver, temp_mail_tab: str) -> str:
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


def fill_verification_code(driver, register_tab: str, code: str) -> None:
    driver.switch_to.window(register_tab)
    verification_input = wait_for_visible_element(driver, By.ID, "verification_code")
    verification_input.clear()
    jitter_pause()
    verification_input.send_keys(code)
    jitter_pause()


def click_register(driver) -> None:
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
        jitter_pause()
        register_button.click()
    except ElementClickInterceptedException:
        jitter_pause()
        driver.execute_script("arguments[0].click();", register_button)


def append_auth_info(username: str, email_address: str, token: str) -> None:
    with AUTH_FILE.open("a", encoding="utf-8") as auth_file:
        auth_file.write(
            f"username: {username}, password: {PASSWORD}, email: {email_address}, token: {token}\n"
        )


def wait_for_login_page(driver) -> None:
    deadline = time.monotonic() + EMAIL_LOAD_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if driver.current_url.rstrip("/") == LOGIN_URL:
            return
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Did not navigate to the login page in time.")


def fill_login_form(driver, email_address: str) -> None:
    username_input = wait_for_visible_element(driver, By.ID, "username")
    password_input = wait_for_visible_element(driver, By.ID, "password")

    username_input.clear()
    jitter_pause()
    username_input.send_keys(email_address)

    password_input.clear()
    jitter_pause()
    password_input.send_keys(PASSWORD)
    jitter_pause()


def click_button_by_text(driver, text: str) -> None:
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
        jitter_pause()
        button.click()
    except ElementClickInterceptedException:
        jitter_pause()
        driver.execute_script("arguments[0].click();", button)


def click_continue_after_login(driver) -> None:
    click_button_by_text(driver, CONTINUE_TEXT)


def open_token_management(driver) -> None:
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
        jitter_pause()
        nav_item.click()
    except ElementClickInterceptedException:
        jitter_pause()
        driver.execute_script("arguments[0].click();", nav_item)


def add_token(driver) -> str:
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
        jitter_pause()
        submit_button.click()
    except ElementClickInterceptedException:
        jitter_pause()
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
            jitter_pause()
            reveal_button.click()
        except ElementClickInterceptedException:
            jitter_pause()
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
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        _cleanup_driver_artifacts(driver)


if __name__ == "__main__":
    main()
