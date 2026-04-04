import os
import django
import pytest
import time
import uuid

# ---Django Setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eplbts.settings")
django.setup()

from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="session", autouse=True)
def create_test_user():
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="testuser")
    user.set_password("TestPass123!")
    user.is_active = True
    user.save()
    yield

def get_driver():
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.implicitly_wait(5)
    return driver


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def do_login(driver, username="testuser", password="TestPass123!"):
    driver.get(f"{BASE_URL}/accounts/login/")
    driver.find_element(By.NAME, "username").send_keys(username)
    time.sleep(0.5)
    driver.find_element(By.NAME, "password").send_keys(password)
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)


# TEST 1: Register page
def test_register_page_loads():
    driver = get_driver()
    driver.get(f"{BASE_URL}/accounts/register/")
    time.sleep(1)
    assert "Create Account" in driver.find_element(By.TAG_NAME, "h4").text
    driver.quit()


# TEST 2: user register test
def test_register_new_user():
    driver = get_driver()
    unique_user = f"user_{uuid.uuid4().hex[:6]}"
    driver.get(f"{BASE_URL}/accounts/register/")

    driver.find_element(By.NAME, "username").send_keys(unique_user)
    time.sleep(0.5)
    driver.find_element(By.NAME, "email").send_keys(f"{unique_user}@test.com")
    time.sleep(0.5)
    driver.find_element(By.NAME, "password1").send_keys("StrongPass123!")
    time.sleep(0.5)
    driver.find_element(By.NAME, "password2").send_keys("StrongPass123!")
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))

    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()

# TEST 3: Login Valid credentials
def test_login_valid_credentials():
    driver = get_driver()
    do_login(driver)
    assert "/dashboard/" in driver.current_url
    driver.quit()

# TEST 4: Wrong password test login
def test_login_wrong_password():
    driver = get_driver()
    do_login(driver, password="WrongPass!")
    assert "/accounts/login/" in driver.current_url
    driver.quit()

# TEST 5: Test dashboard without login redirect
def test_dashboard_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/dashboard/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# TEST 6: Show dashboard
def test_dashboard_shows_welcome_message():
    driver = get_driver()
    do_login(driver)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Welcome, testuser" in page
    driver.quit()

# TEST 7: Logout test
    driver = get_driver()
    do_login(driver)
    driver.find_element(By.LINK_TEXT, "Logout").click()
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


