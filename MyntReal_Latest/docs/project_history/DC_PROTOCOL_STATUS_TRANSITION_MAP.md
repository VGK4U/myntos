# DC Protocol: Complete Status Transition Map
## Generated: November 2, 2025
## Purpose: Document EVERY status change in the system

## Verification Status Changes (57 locations across 9 files)

### Files That Change verification_status:
1. backend/app/api/v1/endpoints/financial_reports.py
2. backend/app/api/v1/endpoints/income_verification.py  
3. backend/app/api/v1/endpoints/scaffolds/api_routes.py
4. backend/app/api/v1/endpoints/users.py
5. backend/app/api/v1/endpoints/withdrawal.py
6. backend/app/core/scheduler.py
7. backend/app/models/ev_discount.py
8. backend/app/models/transaction.py
9. backend/app/services/ev_benefit_service.py

## Production Statuses (Current)

### pending_income table:
- **Accounts Paid**: 1 record
- **Finance Paid**: 166 records  
- **Pending**: 2 records

### withdrawal_request table:
- **Bank Sent**: 2 records
- **Completed**: 81 records

## Next Steps: Systematic Audit

Checking EACH file to map complete workflows...
