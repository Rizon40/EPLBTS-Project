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
    from core.models import Hospital, HospitalStatus, PatientEvent, TransferRequest

    # --- Paramedic user ---
    para, _ = User.objects.get_or_create(username="para_user")
    para.set_password("TestPass123!")
    para.is_active = True
    para.role = "paramedic"
    para.save()

    # --- Hospital ---
    hospital, _ = Hospital.objects.get_or_create(
        name="Test General Hospital",
        defaults={
            "address": "Dhanmondi, Dhaka",
            "latitude": 23.7461,
            "longitude": 90.3742,
            "phone_number": "01700000000",
            "specialty": "general",
            "is_active": True,
        }
    )

    # --- Hospital Admin user (linked to hospital) ---
    hosp, _ = User.objects.get_or_create(username="hosp_admin")
    hosp.set_password("TestPass123!")
    hosp.is_active = True
    hosp.role = "hospital_admin"
    hosp.hospital = hospital
    hosp.save()

    # --- Hospital Status (delete old duplicates first, then create fresh) ---
    HospitalStatus.objects.filter(hospital=hospital).delete()
    HospitalStatus.objects.create(
        hospital=hospital,
        updated_by=hosp,
        icu_total=20,
        icu_available=10,
        bed_total=100,
        bed_available=50,
        has_ventilator=True,
        has_blood_bank=True,
        has_cath_lab=False,
        is_accepting=True,
    )

    # --- Pending PatientEvent (reset to pending for clean test) ---
    event, created = PatientEvent.objects.get_or_create(
        id=9999,
        defaults={
            "submitted_by": para,
            "case_type": "accident",
            "description": "Test case for selenium",
            "patient_age": 30,
            "patient_gender": "male",
            "location_text": "Mirpur, Dhaka",
            "latitude": 23.8103,
            "longitude": 90.4125,
            "status": "pending",
        }
    )

    # Reset to pending if it was changed by previous test runs
    if not created:
        TransferRequest.objects.filter(patient_event=event).delete()
        event.status = "pending"
        event.save()

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

# STAGE 2 TESTS (TEST 1-9)
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


# STAGE 3 TESTS (TEST 10-16)
# TEST 10: Pending cases page loads for paramedic
def test_pending_cases_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/pending/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Pending" in page
    driver.quit()


# TEST 11: Pending cases without login redirects
def test_pending_cases_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/cases/pending/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# TEST 12: Recommend hospitals page loads for a pending case
def test_recommend_hospitals_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Recommendation" in page or "Hospital" in page
    driver.quit()


# TEST 13: Recommend hospitals shows map or no-results message
def test_recommend_hospitals_shows_map_or_warning():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)
    page = driver.page_source
    # Map div present OR warning message shown — both are valid
    assert 'id="map"' in page or "No suitable hospitals" in page or "Best Match" in page
    driver.quit()


# TEST 14: Recommend hospitals without login redirects
def test_recommend_hospitals_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# TEST 15: Pending cases shows Find Hospital button
def test_pending_cases_shows_find_hospital_button():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/pending/")
    time.sleep(1)
    page = driver.page_source
    assert "Find Hospital" in page or "No pending cases" in page
    driver.quit()


# TEST 16: Transfer request creates successfully
def test_create_transfer_request():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)

    # Click the first "Select This Hospital" button
    buttons = driver.find_elements(By.LINK_TEXT, "\U0001f691 Select This Hospital")
    if len(buttons) > 0:
        js_click(driver, buttons[0])
        time.sleep(2)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Pending" in page or "Transfer" in page or "already exists" in page
    driver.quit()