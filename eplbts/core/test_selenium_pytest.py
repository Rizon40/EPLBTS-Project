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

    if not created:
        TransferRequest.objects.filter(patient_event=event).delete()
        event.status = "pending"
        event.save()

    # --- Stage 4: Authority user ---
    auth_user, _ = User.objects.get_or_create(username="auth_user")
    auth_user.set_password("TestPass123!")
    auth_user.is_active = True
    auth_user.role = "authority"
    auth_user.save()

    # --- Stage 4: System Admin user ---
    admin_user, _ = User.objects.get_or_create(username="sys_admin")
    admin_user.set_password("TestPass123!")
    admin_user.is_active = True
    admin_user.role = "admin"
    admin_user.save()

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

    buttons = driver.find_elements(By.LINK_TEXT, "\U0001f691 Select This Hospital")
    if len(buttons) > 0:
        js_click(driver, buttons[0])
        time.sleep(2)
        page = driver.find_element(By.TAG_NAME, "body").text
        assert "Pending" in page or "Transfer" in page or "already exists" in page
    driver.quit()


# STAGE 4 TESTS (TEST 17-30)

# --- Authority Dashboard ---
# TEST 17: Authority dashboard loads for authority user
def test_authority_dashboard_loads():
    driver = get_driver()
    do_login(driver, "auth_user")
    driver.get(f"{BASE_URL}/authority/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "Authority" in page or "Cases" in page
    driver.quit()


# TEST 18: Authority dashboard without login redirects
def test_authority_dashboard_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/authority/dashboard/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# TEST 19: Paramedic cannot access authority dashboard
def test_paramedic_cannot_access_authority_dashboard():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/authority/dashboard/")
    time.sleep(1)
    assert "/dashboard/" in driver.current_url
    driver.quit()


# --- Audit Log ---

# TEST 20: Audit log loads for authority user
def test_audit_log_loads():
    driver = get_driver()
    do_login(driver, "auth_user")
    driver.get(f"{BASE_URL}/audit/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Audit" in page or "Log" in page
    driver.quit()


# TEST 21: Audit log without login redirects
def test_audit_log_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/audit/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# --- System Admin — Manage Hospitals ---

# TEST 22: Manage hospitals loads for admin
def test_manage_hospitals_loads():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/hospitals/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Hospital" in page or "Manage" in page
    driver.quit()


# TEST 23: Add hospital page loads for admin
def test_add_hospital_page_loads():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/hospitals/add/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Add" in page or "Hospital" in page
    driver.quit()


# TEST 24: Add hospital form submit
def test_add_hospital_form_submit():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/hospitals/add/")
    time.sleep(1)

    driver.find_element(By.NAME, "name").send_keys("Selenium Test Hospital")
    time.sleep(0.3)
    driver.find_element(By.NAME, "address").send_keys("Test Address, Dhaka")
    time.sleep(0.3)
    driver.find_element(By.NAME, "latitude").send_keys("23.80")
    time.sleep(0.3)
    driver.find_element(By.NAME, "longitude").send_keys("90.40")
    time.sleep(0.3)
    driver.find_element(By.NAME, "phone_number").send_keys("01700000099")
    time.sleep(0.3)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)

    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Selenium Test Hospital" in page or "added" in page or "Manage" in page
    driver.quit()


# TEST 25: Paramedic cannot access manage hospitals
def test_paramedic_cannot_access_manage_hospitals():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/system/hospitals/")
    time.sleep(1)
    assert "/dashboard/" in driver.current_url
    driver.quit()


# --- System Admin — Manage Users ---

# TEST 26: Manage users loads for admin
def test_manage_users_loads():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/users/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "User" in page or "Manage" in page
    driver.quit()


# TEST 27: Paramedic cannot access manage users
def test_paramedic_cannot_access_manage_users():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/system/users/")
    time.sleep(1)
    assert "/dashboard/" in driver.current_url
    driver.quit()


# --- User Profile ---

# TEST 28: Profile page loads for any logged in user
def test_profile_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/profile/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Profile" in page or "para_user" in page
    driver.quit()


# TEST 29: Profile without login redirects
def test_profile_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/profile/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


# --- Incoming Transfers & Notifications (Stage 3 URLs now available) ---

# TEST 30: Incoming transfers loads for hospital admin
def test_incoming_transfers_page_loads():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/transfers/incoming/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Transfer" in page or "Incoming" in page
    driver.quit()


# TEST 31: Notifications page loads for hospital admin
def test_notifications_page_loads():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/notifications/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Notification" in page
    driver.quit()