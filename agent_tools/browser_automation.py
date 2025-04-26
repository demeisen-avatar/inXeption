'''
Utility functions for browser automation with Selenium.
Uses the same Firefox profile as the desktop icon for persistence.
'''

import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Persistent profile path - matches desktop Firefox launcher
DEFAULT_PROFILE_PATH = '/host/.persist/.firefox/default'


def get_browser(profile_path=DEFAULT_PROFILE_PATH, force_new_window=True, visible=True):
    '''
    Get a Firefox browser instance with predictable window handling.

    Behavior:
    - If Firefox is not running, starts a new Firefox process with our profile
    - If Firefox is already running, connects to the existing process

    Window handling:
    - If no windows exist: Creates and returns a new window
    - If windows exist and force_new_window=False: Returns control of the current active
      window in Selenium (not necessarily the visually topmost window)
    - If windows exist and force_new_window=True: Creates a new window and returns
      control of that window

    Args:
        profile_path: Path to Firefox profile directory
        force_new_window: Whether to always create a fresh window
        visible: If True, run in visible mode (not headless)

    Returns:
        WebDriver: Configured Firefox instance focused on the target window
    '''
    # Ensure profile directory exists
    os.makedirs(profile_path, exist_ok=True)

    # Configure Firefox options
    options = Options()
    options.binary_location = '/usr/bin/firefox-esr'

    # Set profile path
    options.add_argument('-profile')
    options.add_argument(profile_path)

    # Only set headless mode if requested (default is visible)
    if not visible:
        options.add_argument('--headless')
        os.environ['MOZ_HEADLESS'] = '1'

    # Set display environment variable
    os.environ['DISPLAY'] = ':1'

    # Initialize the browser
    service = Service('/usr/local/bin/geckodriver')
    driver = webdriver.Firefox(service=service, options=options)

    # Handle window management based on force_new_window flag
    # If force_new_window is True and we have windows, create a new one
    if force_new_window and len(driver.window_handles) > 1:
        # Open a new window and switch to it
        driver.switch_to.new_window('window')

    return driver


def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    '''
    Wait for an element to be present and visible.

    Args:
        driver: WebDriver instance
        selector: Element selector
        by: Selector type (from selenium.webdriver.common.By)
        timeout: Maximum wait time in seconds

    Returns:
        The web element when found
    '''
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.visibility_of_element_located((by, selector)))


def wait_for_clickable(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    '''
    Wait for an element to be clickable.

    Args:
        driver: WebDriver instance
        selector: Element selector
        by: Selector type (from selenium.webdriver.common.By)
        timeout: Maximum wait time in seconds

    Returns:
        The web element when clickable
    '''
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.element_to_be_clickable((by, selector)))


def safe_click(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    '''
    Wait for an element to be clickable and then click it.

    Args:
        driver: WebDriver instance
        selector: Element selector
        by: Selector type (from selenium.webdriver.common.By)
        timeout: Maximum wait time in seconds
    '''
    element = wait_for_clickable(driver, selector, by, timeout)
    element.click()
    return element
