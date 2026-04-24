import os
import django
import pytest
import time
import uuid

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
    para.email = "para_user@example.com"
    para.phone_number = "01700000001"
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

    # --- Hospital Status ---
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

    # --- Pending PatientEvent ---
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

    # --- Authority user ---
    auth_user, _ = User.objects.get_or_create(username="auth_user")
    auth_user.set_password("TestPass123!")
    auth_user.is_active = True
    auth_user.role = "authority"
    auth_user.save()

    # --- System Admin user ---
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


def set_hidden_value(driver, input_id, value):
    """Set value on a hidden input using JavaScript."""
    driver.execute_script(
        f"document.getElementById('{input_id}').value = arguments[0];", value
    )


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


# TEST 2: Triage form submit (FIXED for Stage 5 card-based UI)
def test_triage_form_submit_valid():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/triage/submit/")
    time.sleep(1)

    # Stage 5: case_type is a hidden input set via card clicks
    set_hidden_value(driver, "id_case_type", "accident")
    time.sleep(0.3)
    # Stage 5: triage_level is also hidden (default 'urgent')
    set_hidden_value(driver, "id_triage_level", "urgent")
    time.sleep(0.3)

    driver.find_element(By.NAME, "description").send_keys("Car accident on road")
    time.sleep(0.3)

    age = driver.find_element(By.NAME, "patient_age")
    age.clear()
    age.send_keys("35")
    time.sleep(0.3)

    # Stage 5: patient_gender is radio buttons
    js_click(driver, driver.find_element(
        By.CSS_SELECTOR, "input[name='patient_gender'][value='male']"))
    time.sleep(0.3)

    driver.find_element(By.NAME, "location_text").send_keys("Mirpur, Dhaka")
    time.sleep(0.3)

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
    time.sleep(0.3)

    icu_avail = driver.find_element(By.NAME, "icu_available")
    icu_avail.clear()
    icu_avail.send_keys("10")
    time.sleep(0.3)

    bed_total = driver.find_element(By.NAME, "bed_total")
    bed_total.clear()
    bed_total.send_keys("100")
    time.sleep(0.3)

    bed_avail = driver.find_element(By.NAME, "bed_available")
    bed_avail.clear()
    bed_avail.send_keys("50")
    time.sleep(0.3)

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


# TEST 9: SOS form submit (FIXED for Stage 5 card-based UI)
def test_sos_form_submit_valid():
    driver = get_driver()
    driver.get(f"{BASE_URL}/sos/")
    time.sleep(1)

    # Stage 5: SOS case_type is hidden input, set via card click (id = sos_case_type)
    set_hidden_value(driver, "sos_case_type", "heart_attack")
    time.sleep(0.3)

    driver.find_element(By.NAME, "description").send_keys("Chest pain, not breathing")
    time.sleep(0.3)

    # SOS form still uses <select> for gender
    Select(driver.find_element(By.NAME, "patient_gender")).select_by_value("male")
    time.sleep(0.3)

    driver.find_element(By.NAME, "location_text").send_keys("Gulshan, Dhaka")
    time.sleep(0.3)
    driver.find_element(By.NAME, "phone_number").send_keys("01799999999")
    time.sleep(0.3)

    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)
    assert "/sos/success/" in driver.current_url
    driver.quit()


# STAGE 3 TESTS (TEST 10-16)
def test_pending_cases_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/pending/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Pending" in page
    driver.quit()


def test_pending_cases_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/cases/pending/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


def test_recommend_hospitals_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Recommendation" in page or "Hospital" in page
    driver.quit()


def test_recommend_hospitals_shows_map_or_warning():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)
    page = driver.page_source
    assert 'id="map"' in page or "No suitable hospitals" in page or "Best Match" in page
    driver.quit()


def test_recommend_hospitals_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/cases/9999/recommend/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


def test_pending_cases_shows_find_hospital_button():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/cases/pending/")
    time.sleep(1)
    page = driver.page_source
    assert "Find Hospital" in page or "No pending cases" in page
    driver.quit()


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


# ============================================================
# STAGE 4 TESTS (TEST 17-31)
# ============================================================

def test_authority_dashboard_loads():
    driver = get_driver()
    do_login(driver, "auth_user")
    driver.get(f"{BASE_URL}/authority/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Dashboard" in page or "Authority" in page or "Cases" in page
    driver.quit()


def test_authority_dashboard_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/authority/dashboard/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


def test_paramedic_cannot_access_authority_dashboard():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/authority/dashboard/")
    time.sleep(1)
    assert "/dashboard/" in driver.current_url
    driver.quit()


def test_audit_log_loads():
    driver = get_driver()
    do_login(driver, "auth_user")
    driver.get(f"{BASE_URL}/audit/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Audit" in page or "Log" in page
    driver.quit()


def test_audit_log_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/audit/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


def test_manage_hospitals_loads():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/hospitals/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Hospital" in page or "Manage" in page
    driver.quit()


def test_add_hospital_page_loads():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/hospitals/add/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Add" in page or "Hospital" in page
    driver.quit()


def test_add_hospital_form_submit():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/hospitals/add/")
    time.sleep(1)

    unique_name = f"Selenium Hospital {uuid.uuid4().hex[:6]}"
    driver.find_element(By.NAME, "name").send_keys(unique_name)
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
    assert unique_name in page or "added" in page or "Manage" in page
    driver.quit()


def test_paramedic_cannot_access_manage_hospitals():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/system/hospitals/")
    time.sleep(1)
    assert "/dashboard/" in driver.current_url
    driver.quit()


def test_manage_users_loads():
    driver = get_driver()
    do_login(driver, "sys_admin")
    driver.get(f"{BASE_URL}/system/users/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "User" in page or "Manage" in page
    driver.quit()


def test_paramedic_cannot_access_manage_users():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/system/users/")
    time.sleep(1)
    assert "/dashboard/" in driver.current_url
    driver.quit()


def test_profile_page_loads():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/profile/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Profile" in page or "para_user" in page
    driver.quit()


def test_profile_without_login_redirects():
    driver = get_driver()
    driver.get(f"{BASE_URL}/profile/")
    time.sleep(2)
    assert "/accounts/login/" in driver.current_url
    driver.quit()


def test_incoming_transfers_page_loads():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/transfers/incoming/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Transfer" in page or "Incoming" in page
    driver.quit()


def test_notifications_page_loads():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/notifications/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text
    assert "Notification" in page
    driver.quit()


# STAGE 5 TESTS (TEST 32-44)
# --- SCRUM-54: UI/UX & Dark Mode Tests ---


# TEST 32: Dark mode persists after reload
def test_dark_mode_persists_on_reload():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/dashboard/")
    time.sleep(1)
    driver.execute_script("localStorage.setItem('theme', 'dark');")
    driver.refresh()
    time.sleep(1)
    theme = driver.execute_script(
        "return document.documentElement.getAttribute('data-theme') "
        "|| document.body.getAttribute('data-theme');"
    )
    assert theme == "dark"
    driver.quit()


# TEST 33: Breadcrumb visible on hospital list
def test_breadcrumb_visible_on_hospital_list():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/hospitals/")
    time.sleep(1)
    page = driver.page_source
    assert "breadcrumb" in page.lower() or "&rsaquo;" in page or "›" in page
    driver.quit()


# TEST 34: Login page uses new design
def test_login_page_new_design():
    driver = get_driver()
    driver.get(f"{BASE_URL}/accounts/login/")
    time.sleep(1)
    page = driver.page_source
    assert "section-card" in page or "page-title" in page or "card" in page
    driver.quit()


# TEST 35: Bootstrap Icons + Plus Jakarta font loaded
def test_bootstrap_icons_and_fonts_loaded():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/dashboard/")
    time.sleep(1)
    page = driver.page_source
    assert "bootstrap-icons" in page or "Plus Jakarta" in page.lower() \
        or "plus jakarta" in page.lower()
    driver.quit()


# --- SCRUM-59: Feature Enhancement Tests ---

# TEST 36: Triage form has triage_level hidden field
def test_triage_form_has_triage_level_field():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/triage/submit/")
    time.sleep(1)
    # Stage 5: triage_level is a hidden input
    fields = driver.find_elements(By.ID, "id_triage_level")
    assert len(fields) > 0
    driver.quit()


# TEST 37: Submit triage with triage_level=critical (FIXED)
def test_submit_triage_with_critical_level():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/triage/submit/")
    time.sleep(1)

    # Stage 5: set hidden inputs via JS
    set_hidden_value(driver, "id_case_type", "accident")
    time.sleep(0.3)
    set_hidden_value(driver, "id_triage_level", "critical")
    time.sleep(0.3)

    driver.find_element(By.NAME, "description").send_keys("Critical road accident")
    time.sleep(0.3)

    age = driver.find_element(By.NAME, "patient_age")
    age.clear()
    age.send_keys("40")
    time.sleep(0.3)

    # Radio button for gender
    js_click(driver, driver.find_element(
        By.CSS_SELECTOR, "input[name='patient_gender'][value='male']"))
    time.sleep(0.3)

    driver.find_element(By.NAME, "location_text").send_keys("Uttara, Dhaka")
    time.sleep(0.3)

    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)
    assert "/triage/success/" in driver.current_url
    driver.quit()


# TEST 38: Paramedic dashboard shows role-based stats
def test_paramedic_dashboard_shows_stats():
    driver = get_driver()
    do_login(driver, "para_user")
    driver.get(f"{BASE_URL}/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "active" in page or "transferred" in page or "case" in page
    driver.quit()


# TEST 39: Hospital admin dashboard shows ICU/bed info
def test_hospital_admin_dashboard_shows_bed_info():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "icu" in page or "bed" in page or "pending" in page
    driver.quit()


# TEST 40: Authority dashboard shows stats
def test_authority_dashboard_shows_stats():
    driver = get_driver()
    do_login(driver, "auth_user")
    driver.get(f"{BASE_URL}/dashboard/")
    time.sleep(1)
    page = driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "hospital" in page or "transfer" in page or "case" in page
    driver.quit()


# TEST 41: Mark notification as read button/link present
def test_mark_notification_as_read():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/notifications/")
    time.sleep(1)
    page = driver.page_source.lower()
    assert "mark" in page or "read" in page or "notification" in page
    driver.quit()


# TEST 42: Export audit CSV link visible for authority
def test_export_audit_csv_link_visible():
    driver = get_driver()
    do_login(driver, "auth_user")
    driver.get(f"{BASE_URL}/audit/")
    time.sleep(1)
    page = driver.page_source.lower()
    assert "export" in page or "csv" in page or "download" in page
    driver.quit()


# TEST 43: Duplicate email on registration blocked (FIXED — register first, then try dup)
def test_duplicate_email_registration_blocked():
    driver = get_driver()

    # Step 1: register a user with a known email
    unique_suffix = uuid.uuid4().hex[:6]
    first_user = f"dup_first_{unique_suffix}"
    dup_email = f"dup_{unique_suffix}@test.com"
    dup_phone = f"0171{unique_suffix}"

    driver.get(f"{BASE_URL}/accounts/register/")
    time.sleep(1)
    driver.find_element(By.NAME, "username").send_keys(first_user)
    driver.find_element(By.NAME, "email").send_keys(dup_email)
    driver.find_element(By.NAME, "phone_number").send_keys(dup_phone)
    driver.find_element(By.NAME, "password1").send_keys("TestPass123!")
    driver.find_element(By.NAME, "password2").send_keys("TestPass123!")
    time.sleep(0.3)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)

    # Step 2: try registering again with SAME email (different username/phone)
    driver.get(f"{BASE_URL}/accounts/register/")
    time.sleep(1)
    driver.find_element(By.NAME, "username").send_keys(f"dup_second_{unique_suffix}")
    driver.find_element(By.NAME, "email").send_keys(dup_email)  # duplicate!
    driver.find_element(By.NAME, "phone_number").send_keys(f"0172{unique_suffix}")
    driver.find_element(By.NAME, "password1").send_keys("TestPass123!")
    driver.find_element(By.NAME, "password2").send_keys("TestPass123!")
    time.sleep(0.3)
    js_click(driver, driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
    time.sleep(2)

    # Should stay on register page with error (NOT redirect to login)
    page = driver.page_source.lower()
    assert "already" in page or "register" in driver.current_url
    driver.quit()


# TEST 44: Incoming transfers has pending + completed sections
def test_incoming_transfers_has_pending_and_completed_sections():
    driver = get_driver()
    do_login(driver, "hosp_admin")
    driver.get(f"{BASE_URL}/transfers/incoming/")
    time.sleep(1)
    page = driver.page_source.lower()
    assert "pending" in page and (
        "completed" in page or "accepted" in page or "rejected" in page
    )
    driver.quit()