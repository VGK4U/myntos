"""
DC Protocol: Selenium Test Configuration Settings
Frontend Visible Browser Testing - Real-time Chrome Execution
"""

import os

BASE_URL = os.environ.get('REPLIT_DEV_DOMAIN', 'http://localhost:5000')
if BASE_URL and not BASE_URL.startswith('http'):
    BASE_URL = f"https://{BASE_URL}"

CHROMIUM_PATH = "/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium"
CHROMEDRIVER_PATH = "/nix/store/8zj50jw4w0hby47167kqqsaqw4mm5bkd-chromedriver-unwrapped-138.0.7204.100/bin/chromedriver"

BROWSER_CONFIG = {
    'window_size': (1920, 1080),
    'implicit_wait': 15,
    'page_load_timeout': 60,
    'script_timeout': 60,
}

TEST_CREDENTIALS = {
    'staff': {
        'employee_id': 'MR20001',
        'password': 'Test@123',
    },
    'staff_vgk': {
        'employee_id': 'MR20001',
        'password': 'Test@123',
    },
    'staff_key_leadership': {
        'employee_id': 'MR20002',
        'password': 'Test@123',
    },
    'rvz': {
        'username': 'MNR182335005',
        'password': 'Test@123',
    },
    'mnr_user': {
        'mnr_id': 'MNR182345842',
        'password': 'Test@123',
    },
    'mnr_staff': {
        'mnr_id': 'MNR182380679',
        'password': 'Test@123',
    },
    'mnr_superadmin': {
        'mnr_id': 'MNR182344375',
        'password': 'Test@123',
    },
    'partner': {
        'username': 'DLR001',
        'password': 'Test@123',
    }
}

CRM_TEST_DATA = {
    'sample_lead': {
        'name': 'Selenium Test Lead',
        'phone': '9876543210',
        'email': 'selenium.test@example.com',
        'pincode': '400001',
        'status': 'new',
        'priority': 'medium',
    }
}

ERROR_SEVERITY = {
    'CRITICAL': 1,
    'ERROR': 2,
    'WARNING': 3,
    'INFO': 4,
}

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
SCREENSHOTS_DIR = os.path.join(REPORTS_DIR, 'screenshots')
LOGS_DIR = os.path.join(REPORTS_DIR, 'logs')

for directory in [REPORTS_DIR, SCREENSHOTS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)
