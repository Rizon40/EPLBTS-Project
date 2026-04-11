import os
import django
import pytest
import time

# --- Django Setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eplbts.settings")
django.setup()

from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="session", autouse=True)
def create_test_users():
    User = get_user_model()

    para, _ = User.objects.get_or_create(username="para_user")
    para.set_password("TestPass123!")
    para.is_active = True
    para.role = "paramedic"
    para.save()

    hosp, _ = User.objects.get_or_create(username="hosp_admin")
    hosp.set_password("TestPass123!")
    hosp.is_active = True
    hosp.role = "hospital_admin"
    hosp.save()

    yield


def get_driver():
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.implicitly_wait(5)
    return driver


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def do_login(driver, username, password="TestPass123!"):
    driver.get(f"{BASE_URL}/accounts/login/")
    driver.find_element(By.NAME, "username").send_keys(username)
    time.sleep(0.5)
    driver.find_element(By.NAME, "password").send_keys(password)
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)


# TEST 1: Triage page loads for paramedic
def test_triage_page_loads_for_paramedic():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/triage/submit/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Triage" in page
    driver.quit()


# TEST 2: Triage form submit
def test_triage_form_submit_valid():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/triage/submit/")
    time.sleep(1)

    Select(driver.find_element(By.NAME, "case_type")).select_by_value("accident")
    time.sleep(0.5)
    driver.find_element(By.NAME, "description").send_keys("Car accident on road")
    time.sleep(0.5)
    driver.find_element(By.NAME, "patient_age").send_keys("35")
    time.sleep(0.5)
    Select(driver.find_element(By.NAME, "patient_gender")).select_by_value("male")
    time.sleep(0.5)
    driver.find_element(By.NAME, "location_text").send_keys("Mirpur, Dhaka")
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))

    time.sleep(2)
    assert "/triage/success/" in driver.current_url
    driver.quit()


# TEST 3: Triage without login redirects
def test_triage_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/triage/submit/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# TEST 4: Hospital status page loads for hospital admin
def test_status_page_loads_for_hospital_admin():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/hospital/status/update/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Hospital" in page
    driver.quit()


# TEST 5: Hospital status form submit
def test_status_form_submit_valid():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/hospital/status/update/")
    time.sleep(1)

    icu_total = driver.find_element(By.NAME, "icu_total")
    icu_total.clear()
    icu_total.send_keys("20")
    time.sleep(0.5)

    icu_avail = driver.find_element(By.NAME, "icu_available")
    icu_avail.clear()
    icu_avail.send_keys("10")
    time.sleep(0.5)

    bed_total = driver.find_element(By.NAME, "bed_total")
    bed_total.clear()
    bed_total.send_keys("100")
    time.sleep(0.5)

    bed_avail = driver.find_element(By.NAME, "bed_available")
    bed_avail.clear()
    bed_avail.send_keys("50")
    time.sleep(0.5)

    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)
    assert "/hospital/status/update/" in driver.current_url
    driver.quit()


# TEST 6: Hospital status without login redirects
def test_status_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/hospital/status/update/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# TEST 7: Hospital list page loads
def test_hospital_list_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/hospitals/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Hospital" in page
    driver.quit()


# TEST 8: SOS page loads without login
def test_sos_page_loads_without_login():
    driver = get_driver()
    driver.get(f"{BASE_URL}/sos/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "SOS" in page
    driver.quit()


# TEST 9: SOS form submit
def test_sos_form_submit_valid():
    driver = get_driver()
    driver.get(f"{BASE_URL}/sos/")
    time.sleep(1)

    Select(driver.find_element(By.NAME, "case_type")).select_by_value("heart_attack")
    time.sleep(0.5)
    driver.find_element(By.NAME, "description").send_keys("Chest pain, not breathing")
    time.sleep(0.5)
    driver.find_element(By.NAME, "patient_age").send_keys("60")
    time.sleep(0.5)
    Select(driver.find_element(By.NAME, "patient_gender")).select_by_value("male")
    time.sleep(0.5)
    driver.find_element(By.NAME, "location_text").send_keys("Gulshan, Dhaka")
    time.sleep(0.5)
    driver.find_element(By.NAME, "phone_number").send_keys("01799999999")
    time.sleep(0.5)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))

    time.sleep(2)
    assert "/sos/success/" in driver.current_url
    driver.quit()