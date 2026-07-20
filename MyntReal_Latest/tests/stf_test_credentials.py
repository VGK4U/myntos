"""
STF PROTOCOL - Test Credentials Configuration
Reusable test accounts for Selenium-based frontend testing

All accounts use password: TestPass123!

STAFF ACCOUNTS (login via /staff/login):
- STF-TEST-VGK: VGK4U Supreme Admin (full access, role_code=vgk4u)
- STF-TEST-MGR: Manager role (role_code=key_leadership)
- STF-TEST-EMP: Regular employee (role_code=employee)

PARTNER ACCOUNTS (login via /partner/login):
- STF-VENDOR-001: Vendor partner
- STF-DEALER-001: Dealer partner  
- STF-DIST-001: Distributor partner
- STF-RDREAM-001: Real Dream partner

TEST RESULTS (Dec 21, 2025):
- Menu Access Matrix Test: 88.4% pass rate (38/43 tests)
- Phases 1-7 (core functionality): 100% pass
- VGK4U login, page load, UI verification, permissions, save: All pass
- View/Edit dependency rules verified (Edit→View, ViewOFF→EditOFF)

Created: Dec 2025
Updated: Dec 21, 2025
DC Protocol Compliant
"""

STF_DEFAULT_PASSWORD = "TestPass123!"

STF_STAFF_ACCOUNTS = {
    "VGK4U": {
        "employee_id": "STF-TEST-VGK",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test VGK4U",
        "staff_type": "VGK4U",
        "db_id": 41,
        "description": "Supreme Admin with full system access"
    },
    "MANAGER": {
        "employee_id": "STF-TEST-MGR",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test Manager",
        "staff_type": "MN_MANAGER",
        "db_id": 43,
        "description": "Manager role with department oversight"
    },
    "EMPLOYEE": {
        "employee_id": "STF-TEST-EMP",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test Employee",
        "staff_type": "MN_STAFF",
        "db_id": 42,
        "description": "Regular employee with basic access"
    }
}

STF_PARTNER_ACCOUNTS = {
    "VENDOR": {
        "partner_id": "STF-VENDOR-001",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test Vendor",
        "partner_type": "VENDOR",
        "db_id": 80,
        "description": "Vendor partner for supply chain testing"
    },
    "DEALER": {
        "partner_id": "STF-DEALER-001",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test Dealer",
        "partner_type": "DEALER",
        "db_id": 81,
        "description": "Dealer partner for distribution testing"
    },
    "DISTRIBUTOR": {
        "partner_id": "STF-DIST-001",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test Distributor",
        "partner_type": "DISTRIBUTOR",
        "db_id": 82,
        "description": "Distributor partner for wholesale testing"
    },
    "REAL_DREAM": {
        "partner_id": "STF-RDREAM-001",
        "password": STF_DEFAULT_PASSWORD,
        "name": "STF Test RealDream Partner",
        "partner_type": "REAL_DREAM_PARTNER",
        "db_id": 83,
        "description": "Real estate partner for property listing testing"
    }
}

ALL_STF_ACCOUNTS = {
    "staff": STF_STAFF_ACCOUNTS,
    "partners": STF_PARTNER_ACCOUNTS
}


def get_staff_credentials(role: str = "VGK4U") -> dict:
    """Get staff credentials by role name"""
    return STF_STAFF_ACCOUNTS.get(role.upper(), STF_STAFF_ACCOUNTS["VGK4U"])


def get_partner_credentials(partner_type: str = "VENDOR") -> dict:
    """Get partner credentials by type"""
    return STF_PARTNER_ACCOUNTS.get(partner_type.upper(), STF_PARTNER_ACCOUNTS["VENDOR"])


def print_all_credentials():
    """Print all available test credentials"""
    print("\n" + "="*60)
    print("STF TEST CREDENTIALS")
    print("="*60)
    
    print("\nSTAFF ACCOUNTS (login: /staff/login)")
    print("-"*60)
    for role, creds in STF_STAFF_ACCOUNTS.items():
        print(f"  {role}:")
        print(f"    ID: {creds['employee_id']}")
        print(f"    Password: {creds['password']}")
        print(f"    Type: {creds['staff_type']}")
    
    print("\nPARTNER ACCOUNTS (login: /partner/login)")
    print("-"*60)
    for ptype, creds in STF_PARTNER_ACCOUNTS.items():
        print(f"  {ptype}:")
        print(f"    ID: {creds['partner_id']}")
        print(f"    Password: {creds['password']}")
        print(f"    Type: {creds['partner_type']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print_all_credentials()
