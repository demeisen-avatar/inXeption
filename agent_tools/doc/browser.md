# Browser Automation with Selenium

This document provides guidance for using Selenium with Python to automate browser interactions within the inXeption environment.

## Overview

The container comes pre-configured with:
- Firefox-ESR browser
- GeckoDriver (Firefox WebDriver)
- Selenium Python package

This setup allows for programmatic control of the Firefox browser using Python, enabling more precise and reliable web interactions compared to the pixel-based computer tool.

## Quick Start

```python
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure Firefox options
options = Options()
options.binary_location = '/usr/bin/firefox-esr'  # Specify Firefox binary location

# Choose whether to run in headless mode
# options.add_argument('--headless')  # Uncomment for headless operation

# Set up environment for X display
import os
os.environ['DISPLAY'] = ':1'  # Use the available display

# Initialize the browser
service = Service('/usr/local/bin/geckodriver')
driver = webdriver.Firefox(service=service, options=options)

try:
    # Navigate to a website
    driver.get('https://www.example.com')

    # Get the page title
    print(f'Page title: {driver.title}')

    # Find an element and interact with it
    heading = driver.find_element(By.TAG_NAME, 'h1')
    print(f'Main heading text: {heading.text}')

    # More actions as needed...

finally:
    # Always clean up
    driver.quit()
```

## Common Tasks

### Navigation

```python
# Navigate to a URL
driver.get('https://www.example.com')

# Refresh the page
driver.refresh()

# Go back and forward
driver.back()
driver.forward()
```

### Finding Elements

Selenium offers multiple ways to locate elements:

```python
# Find by ID
element = driver.find_element(By.ID, 'loginButton')

# Find by Class
elements = driver.find_elements(By.CLASS_NAME, 'product-item')

# Find by CSS Selector
element = driver.find_element(By.CSS_SELECTOR, 'div.main-content > h2')

# Find by XPath
element = driver.find_element(By.XPATH, '//button[contains(text(), "Submit")]')

# Find by Link Text
element = driver.find_element(By.LINK_TEXT, 'Click here')

# Find by Tag Name
elements = driver.find_elements(By.TAG_NAME, 'a')
```

### Interacting with Elements

```python
# Click on an element
button = driver.find_element(By.ID, 'submitButton')
button.click()

# Type into an input field
input_field = driver.find_element(By.NAME, 'username')
input_field.clear()  # Clear existing text
input_field.send_keys('myusername')

# Submit a form
form = driver.find_element(By.ID, 'loginForm')
form.submit()

# Get element text
text = element.text

# Get element attribute
attribute = element.get_attribute('href')
```

### Waiting for Elements

Selenium provides mechanisms to wait for elements to appear or change state:

```python
# Explicit wait
wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
element = wait.until(EC.element_to_be_clickable((By.ID, 'dynamicButton')))

# Common expected conditions
element = wait.until(EC.presence_of_element_located((By.ID, 'myElement')))
element = wait.until(EC.visibility_of_element_located((By.ID, 'myElement')))
element = wait.until(EC.element_to_be_clickable((By.ID, 'myElement')))
```

### Handling Alerts

```python
# Switch to an alert
alert = driver.switch_to.alert

# Get alert text
text = alert.text

# Accept the alert (click OK)
alert.accept()

# Dismiss the alert (click Cancel)
alert.dismiss()

# Enter text into a prompt
alert.send_keys('input text')
```

### JavaScript Execution

```python
# Execute JavaScript
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

# Get return value from JavaScript
title = driver.execute_script("return document.title;")

# Modify the DOM
driver.execute_script("arguments[0].style.backgroundColor = 'yellow'", element)
```

### Working with Frames and Windows

```python
# Switch to an iframe
driver.switch_to.frame('frame_name')
driver.switch_to.frame(0)  # By index
driver.switch_to.frame(iframe_element)  # By element

# Switch back to default content
driver.switch_to.default_content()

# Handle multiple windows
original_window = driver.current_window_handle
driver.switch_to.new_window('tab')  # or 'window'

# Switch between windows
for window_handle in driver.window_handles:
    if window_handle != original_window:
        driver.switch_to.window(window_handle)
        break
```

### Taking Screenshots

```python
# Take screenshot of entire page
driver.save_screenshot('/tmp/screenshot.png')

# Take screenshot of specific element
element.screenshot('/tmp/element-screenshot.png')
```

## Browser Profiles and Data Persistence

To persist browser data (cookies, login sessions, etc.) between sessions:

```python
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

# Setup a custom profile path
profile_path = '/host/.firefox_profile'
import os
if not os.path.exists(profile_path):
    os.makedirs(profile_path)

# Configure options to use the profile
options = Options()
options.binary_location = '/usr/bin/firefox-esr'
options.add_argument('-profile')
options.add_argument(profile_path)

# Initialize the browser with profile
service = Service('/usr/local/bin/geckodriver')
driver = webdriver.Firefox(service=service, options=options)
```

## Tips and Best Practices

1. **Clean up resources**: Always use `driver.quit()` in a `finally` block to ensure the browser is closed properly.

2. **Use explicit waits**: Avoid using `time.sleep()` in favor of explicit waits, which make your automation more robust.

3. **Handle errors gracefully**: Use try/except blocks to catch and handle Selenium exceptions.

4. **Log actions**: Consider logging your automation steps for debugging purposes.

5. **Test selector stability**: Ensure your element selectors are robust against UI changes.

6. **Headless vs. visible**: Use headless mode for speed, but visible mode can be helpful for debugging.

7. **Firefox-specific**: Remember that Firefox-ESR is the installed version, which may differ slightly from regular Firefox.

## Troubleshooting

### Common Issues

1. **Element not found**: Use explicit waits or check if your selector is correct.

2. **Element not interactable**: Wait for the element to be clickable or scroll to it.

3. **Stale element reference**: Re-fetch the element if the page has been refreshed or navigated.

4. **Permission denied**: Ensure the script has proper permissions to the profile directory.

5. **Display issues**: Confirm the `DISPLAY` environment variable is set correctly.

## Example Use Cases

### Form Filling

```python
# Navigate to login page
driver.get('https://example.com/login')

# Fill in credentials
driver.find_element(By.ID, 'username').send_keys('myusername')
driver.find_element(By.ID, 'password').send_keys('mypassword')

# Click login button
driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

# Wait for dashboard to load
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, 'dashboard'))
)
```

### Scraping Data

```python
# Navigate to page
driver.get('https://example.com/products')

# Get all product elements
products = driver.find_elements(By.CLASS_NAME, 'product-item')

# Extract data from each product
product_data = []
for product in products:
    name = product.find_element(By.CLASS_NAME, 'product-name').text
    price = product.find_element(By.CLASS_NAME, 'product-price').text
    product_data.append({'name': name, 'price': price})

print(product_data)
```

## Resources

- [Selenium Documentation](https://www.selenium.dev/documentation/en/)
- [Selenium with Python API](https://selenium-python.readthedocs.io/)
- [GeckoDriver GitHub](https://github.com/mozilla/geckodriver)
- [Firefox Browser Profiles](https://support.mozilla.org/en-US/kb/profiles-where-firefox-stores-user-data)
