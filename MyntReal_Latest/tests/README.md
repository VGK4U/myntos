# End-to-End Testing System

## Overview

This directory contains the infrastructure for automated end-to-end testing of the BeV 2.0 system. RVZ ID administrators can run full system tests with a single click from the VGK dashboard.

## Directory Structure

```
tests/
├── e2e/                    # End-to-end test suites
├── fixtures/               # Test data generation scripts
│   ├── create_test_data.py    # Creates test users, bonanzas, etc.
│   └── test_manifest.json     # Tracks created test data
├── cleanup/                # Test data cleanup scripts
│   └── reset_test_data.py     # Removes test data after testing
├── reports/                # HTML test reports (generated)
├── logs/                   # Test execution logs (generated)
└── run_tests.sh            # Main test orchestration script
```

## Usage

### From VGK Dashboard (Recommended)

1. Log in as RVZ ID user
2. Go to VGK Dashboard
3. Click "▶️ Run System Test" button
4. Wait for completion (status updates in real-time)
5. Click "View Report" link when done
6. View historical reports at `/rvz/test-reports`

### From Command Line

```bash
# Run full test suite
bash tests/run_tests.sh

# Run individual components
python3 tests/fixtures/create_test_data.py
python3 tests/cleanup/reset_test_data.py
```

## Test Scripts (Templates)

### ⚠️ IMPORTANT: Database Integration Required

The current test scripts (`create_test_data.py` and `reset_test_data.py`) are **templates** that:
- Generate test data structures
- Log operations
- Track data in manifest files

**They do NOT yet interact with the actual database.**

To make them functional, you need to extend them with:

1. **Database Operations** (via SQLAlchemy ORM):
```python
from app.models.user import User
from app.core.database import SessionLocal

# In create_test_data.py:
db = SessionLocal()
new_user = User(
    bev_id=test_user['bev_id'],
    first_name=test_user['first_name'],
    # ... other fields
)
db.add(new_user)
db.commit()
```

2. **API Integration** (via requests):
```python
import requests

# Alternative: Use FastAPI endpoints
response = requests.post(
    'http://localhost:8000/api/users',
    json=test_user_data
)
```

3. **Cleanup Operations**:
```python
# In reset_test_data.py:
db = SessionLocal()
db.query(User).filter(User.bev_id.like('BEVTEST%')).delete()
db.commit()
```

## API Endpoints

### `/api/run-system-test` (POST)
Triggers test execution in background.

**Security**: RVZ ID only

**Request**:
```json
{
  "user_id": "BEV182364369"
}
```

**Response**:
```json
{
  "message": "System tests started in background",
  "status": "running",
  "check_status_url": "/api/test-status"
}
```

### `/api/test-status` (GET)
Get current test execution status.

**Parameters**: `user_id` (required)

**Response**:
```json
{
  "running": false,
  "last_run": "2025-10-10T14:00:00",
  "last_result": {
    "status": "completed",
    "report_url": "/api/test-reports/20251010_140000",
    "summary": {
      "passed": 112,
      "failed": 3,
      "skipped": 0,
      "duration": "4m 35s"
    }
  }
}
```

### `/api/test-reports` (GET)
List all available test reports.

**Parameters**: `user_id` (required)

### `/api/test-logs` (GET)
List all available test logs.

**Parameters**: `user_id` (required)

## Test Report Format

Test reports are generated as HTML files with:
- Timestamp and duration
- Pass/fail/skip counts
- Detailed execution logs
- Color-coded status indicators

## Security

- All testing endpoints require RVZ ID role
- Authorization checked via `user_id` parameter
- Tests run in isolated environment
- Test data tagged with `BEVTEST` prefix for safety

## Adding New Tests

1. Create test file in `tests/e2e/`
2. Follow naming convention: `test_*.py`
3. Use pytest or unittest framework
4. Tests will automatically run via `run_tests.sh`

Example:
```python
# tests/e2e/test_user_registration.py
def test_user_registration():
    # Your test code here
    assert True
```

## Maintenance

- Reports are kept in `tests/reports/` (last 10)
- Logs are kept in `tests/logs/` (last 10)
- Cleanup reports in `tests/logs/cleanup_report_*.json`
- Old files should be manually archived or deleted

## Troubleshooting

### Tests not running
- Check workflow status in Replit
- Verify bash is available
- Check file permissions: `chmod +x tests/run_tests.sh`

### Path issues
- All paths are relative to project root
- Backend runs script with `cwd=project_root`

### Authorization errors
- Verify RVZ ID role in database
- Check `user_id` is passed to API calls

## Future Enhancements

- [ ] Add Playwright for browser testing
- [ ] Integrate with CI/CD pipeline
- [ ] Email notifications on test failure
- [ ] Slack integration for alerts
- [ ] Performance benchmarking
- [ ] Database snapshot/restore
- [ ] Parallel test execution
