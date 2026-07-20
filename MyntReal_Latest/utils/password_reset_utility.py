"""
Secure Password Reset Utility for Test Accounts
Admin-only utility for resetting passwords with proper security practices
"""

from datetime import datetime
from typing import List, Dict, Any
from werkzeug.security import generate_password_hash

def reset_test_account_passwords(target_accounts: List[Dict[str, str]], new_password: str = "password", actor_id: str = "SYSTEM") -> Dict[str, Any]:
    """
    Securely reset passwords for specified test accounts
    
    Args:
        target_accounts: List of account dicts with 'user_id', 'email', 'name'
        new_password: New password to set (default: "password")
        actor_id: ID of admin performing the reset
        
    Returns:
        dict: Results of password reset operation
    """
    
    try:
        from app import User, db, AuditLog
        
        results = {
            'success': True,
            'accounts_processed': 0,
            'accounts_updated': 0,
            'accounts_not_found': 0,
            'details': [],
            'errors': []
        }
        
        # Start transaction
        db.session.begin()
        
        for account in target_accounts:
            account_result = {
                'user_id': account.get('user_id'),
                'email': account.get('email'),
                'name': account.get('name'),
                'status': 'processing'
            }
            
            try:
                # Find user by BEV ID first, then email as fallback
                user = None
                if account.get('user_id'):
                    user = User.query.get(account['user_id'])
                
                if not user and account.get('email'):
                    user = User.query.filter_by(email=account['email']).first()
                
                if not user:
                    account_result['status'] = 'not_found'
                    account_result['message'] = f"User not found: {account.get('user_id', account.get('email'))}"
                    results['accounts_not_found'] += 1
                    results['details'].append(account_result)
                    continue
                
                # Store old password hash for verification
                old_password_hash = user.password
                
                # Generate new secure password hash
                new_password_hash = generate_password_hash(new_password)
                
                # Update password and security fields
                user.password = new_password_hash
                user.force_password_change = True  # Force password change on next login
                user.password_reset_token = None  # Clear any existing reset tokens
                user.password_reset_expires = None
                user.reset_code = None  # Clear any reset codes
                user.reset_code_expires = None
                
                # Update audit timestamp
                current_time = datetime.utcnow()
                user.last_login = current_time  # Update to invalidate existing sessions
                
                # Verify password hash changed (security check)
                if old_password_hash == new_password_hash:
                    account_result['status'] = 'error'
                    account_result['message'] = 'Password hash did not change - security error'
                    results['errors'].append(account_result)
                    continue
                
                # Create audit log entry (if AuditLog model exists)
                try:
                    from app import AuditLog
                    audit_entry = AuditLog(
                        user_id=user.id,
                        action='PASSWORD_RESET',
                        details=f'Test account password reset by {actor_id} for user {user.id} ({user.name})',
                        ip_address='127.0.0.1',
                        user_agent='Password Reset Utility',
                        timestamp=current_time
                    )
                    db.session.add(audit_entry)
                except ImportError:
                    # AuditLog model doesn't exist, skip audit logging
                    print(f"ℹ️ AuditLog not available, skipping audit entry for {user.id}")
                
                account_result['status'] = 'updated'
                account_result['message'] = f'Password reset successful for {user.name} ({user.id})'
                account_result['actual_user_id'] = user.id
                account_result['actual_name'] = user.name
                account_result['actual_email'] = user.email
                results['accounts_updated'] += 1
                
                print(f"✅ Password reset for: {user.name} ({user.id}) - Email: {user.email}")
                
            except Exception as e:
                account_result['status'] = 'error'
                account_result['message'] = f'Error processing account: {str(e)}'
                results['errors'].append(account_result)
                print(f"❌ Error resetting password for {account.get('user_id', account.get('email'))}: {str(e)}")
            
            results['details'].append(account_result)
            results['accounts_processed'] += 1
        
        # Commit all changes if successful
        if results['accounts_updated'] > 0 and len(results['errors']) == 0:
            db.session.commit()
            results['message'] = f'Successfully reset passwords for {results["accounts_updated"]} test accounts'
            print(f"🔒 Transaction committed: {results['accounts_updated']} passwords reset")
        elif len(results['errors']) > 0:
            db.session.rollback()
            results['success'] = False
            results['message'] = f'Password reset failed due to {len(results["errors"])} errors - rolled back'
            print(f"🚨 Transaction rolled back due to errors")
        else:
            db.session.rollback()
            results['success'] = False
            results['message'] = 'No accounts were updated - rolled back'
            print("ℹ️ No changes made - rolled back")
            
    except Exception as e:
        # Rollback on any system error
        try:
            db.session.rollback()
        except:
            pass
        
        results = {
            'success': False,
            'message': f'System error during password reset: {str(e)}',
            'accounts_processed': 0,
            'accounts_updated': 0,
            'accounts_not_found': 0,
            'details': [],
            'errors': [{'error': str(e)}]
        }
        print(f"💥 System error: {str(e)}")
    
    return results

def verify_password_reset(user_id: str, test_password: str = "password") -> Dict[str, Any]:
    """
    Verify that password reset worked by checking the hash
    
    Args:
        user_id: BEV ID of user to verify
        test_password: Password to test (default: "password")
        
    Returns:
        dict: Verification results
    """
    try:
        from app import User
        from werkzeug.security import check_password_hash
        
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': f'User {user_id} not found'}
        
        # Test password verification
        password_valid = check_password_hash(user.password, test_password)
        
        return {
            'success': True,
            'user_id': user.id,
            'name': user.name,
            'email': user.email,
            'password_valid': password_valid,
            'force_password_change': user.force_password_change,
            'message': f'Password verification {"PASSED" if password_valid else "FAILED"} for {user.name}'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Verification error: {str(e)}'}

# Test accounts to reset (as specified by user)
TEST_ACCOUNTS = [
    {
        'user_id': 'BEV182300990',
        'email': 'test1@testbev.com',
        'name': 'Test Referral 1'
    },
    {
        'user_id': 'BEV182371985', 
        'email': 'user1@test.local',
        'name': 'Test User One'
    },
    {
        'user_id': 'BEV182398365',
        'email': 'user2@test.local', 
        'name': 'Test User Two'
    },
    {
        'user_id': 'BEV182399999',
        'email': 'test@bonanza.local',
        'name': 'Test User for E2E'
    }
]