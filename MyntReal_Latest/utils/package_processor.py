"""
VGK Package Processing Utilities
Handles bulk package assignment operations with safety measures
"""

import pandas as pd
import json
from datetime import datetime
import pytz
from utils.safe_string_utils import safe_get_strip, safe_strip
from constants import COUPON_DEFINITIONS

def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)

class PackageProcessor:
    """Process Excel files for package assignments with comprehensive validation"""
    
    # Package value mappings
    PACKAGE_MAPPINGS = {
        '15000': {'label': 'Platinum', 'value': 15000, 'status': 'Activated'},
        '7500': {'label': 'Diamond', 'value': 7500, 'status': 'Activated'},
        '1000': {'label': 'Star', 'value': 1000, 'status': 'Activated'},
        '500': {'label': 'Loyal', 'value': 500, 'status': 'Activated'}
    }
    
    # Text-based package mappings for new format
    TEXT_PACKAGE_MAPPINGS = {
        'platinum coupon': {'label': 'Platinum', 'value': 15000, 'status': 'Activated'},
        'diamond coupon': {'label': 'Diamond', 'value': 7500, 'status': 'Activated'},
        'star coupon': {'label': 'Star', 'value': 1000, 'status': 'Activated'},
        'loyal coupon': {'label': 'Loyal', 'value': 500, 'status': 'Activated'},
        'red coupon': {'label': 'Red Coupon', 'value': 0, 'status': 'Red Coupon'},
        'blue coupon': {'label': 'Blue Coupon', 'value': 0, 'status': 'Blue Coupon'},
        'no package': {'label': 'No Package', 'value': 0, 'status': 'Eligible'}
    }
    
    @classmethod
    def determine_package_type(cls, package_value, package_status=None):
        """Determine package type from Excel package value or package status text"""
        try:
            # Handle empty or None values
            if (package_value == '' or package_value is None or pd.isna(package_value)) and \
               (package_status == '' or package_status is None or pd.isna(package_status)):
                return {'package_type': 'No Package', 'status': 'Eligible'}
            
            # First try text-based mapping (for new format)
            if package_status and str(package_status).strip():
                status_str = safe_strip(package_status).lower()
                if status_str in cls.TEXT_PACKAGE_MAPPINGS:
                    mapping = cls.TEXT_PACKAGE_MAPPINGS[status_str]
                    return {
                        'package_type': mapping['label'],
                        'status': mapping['status'],
                        'value': mapping['value']
                    }
            
            # Then try numeric mapping (for old format)
            if package_value and not pd.isna(package_value):
                package_str = safe_strip(package_value)
                # Clean package value (handle "15000/-" format)
                cleaned_value = package_str.replace('/-', '').replace('-', '').strip()
                if '.' in cleaned_value:
                    try:
                        cleaned_value = str(int(float(cleaned_value)))
                    except:
                        cleaned_value = package_str
                
                if cleaned_value in cls.PACKAGE_MAPPINGS:
                    mapping = cls.PACKAGE_MAPPINGS[cleaned_value]
                    return {
                        'package_type': mapping['label'],
                        'status': mapping['status'],
                        'value': mapping['value']
                    }
            
            return {'package_type': 'Invalid', 'status': 'Error'}
                
        except Exception as e:
            return {'package_type': 'Error', 'status': 'Error'}
    
    @classmethod
    def validate_excel_file(cls, file_path):
        """Validate Excel file structure and content for both old and new formats"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Check for both old and new format columns
            old_format_columns = ['MemberId', 'Name', 'Coupon Type', 'Package Value']
            new_format_columns = ['Member Id', 'Name', 'Package / Coupon status']
            
            # Determine which format we're dealing with
            has_old_format = all(col in df.columns for col in old_format_columns)
            has_new_format = all(col in df.columns for col in new_format_columns)
            
            if not has_old_format and not has_new_format:
                return {
                    'valid': False,
                    'error': 'Excel format not recognized',
                    'details': f'Expected either old format {old_format_columns} or new format {new_format_columns}. Found columns: {list(df.columns)}'
                }
            
            format_type = 'old' if has_old_format else 'new'
            
            # Column validation is already done above, no need for missing_columns check here
            
            # Validate data types and content
            validation_results = {
                'valid': True,
                'total_rows': len(df),
                'valid_rows': 0,
                'invalid_rows': [],
                'package_distribution': {},
                'warnings': []
            }
            
            for index, row in df.iterrows():
                row_num = int(index) + 1
                row_valid = True
                row_issues = []
                
                # Validate MemberId (handle both formats)
                member_id_col = 'MemberId' if format_type == 'old' else 'Member Id'
                member_id = safe_get_strip(row, member_id_col)
                if not member_id or not member_id.startswith('BEV'):
                    row_issues.append(f'Invalid Member ID: {member_id}')
                    row_valid = False
                
                # Validate Name
                name = safe_get_strip(row, 'Name')
                if not name:
                    row_issues.append('Missing Name')
                    row_valid = False
                
                # Validate Package Value/Status (handle both formats)
                if format_type == 'old':
                    package_value_raw = safe_get_strip(row, 'Package Value')
                    raw_package_value = row.get('Package Value')
                    package_status = safe_get_strip(row, 'Coupon Type')
                else:
                    package_value_raw = None
                    raw_package_value = None
                    package_status = safe_get_strip(row, 'Package / Coupon status')
                
                # Determine package info
                package_info = cls.determine_package_type(package_value_raw, package_status)
                
                if package_info['package_type'] in ['Invalid', 'Error']:
                    if format_type == 'old':
                        row_issues.append(f'Invalid Package Value: {package_value_raw}')
                    else:
                        row_issues.append(f'Invalid Package Status: {package_status}')
                    row_valid = False
                
                package_value = package_info['package_type']
                
                if row_valid:
                    validation_results['valid_rows'] += 1
                    # Track package distribution
                    if package_value in validation_results['package_distribution']:
                        validation_results['package_distribution'][package_value] += 1
                    else:
                        validation_results['package_distribution'][package_value] = 1
                else:
                    validation_results['invalid_rows'].append({
                        'row': row_num,
                        'member_id': member_id,
                        'issues': row_issues
                    })
            
            # Check if any valid rows exist
            if validation_results['valid_rows'] == 0:
                validation_results['valid'] = False
                validation_results['error'] = 'No valid rows found in Excel file'
            
            return validation_results
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Error reading Excel file: {str(e)}',
                'details': 'Please ensure the file is a valid Excel (.xlsx) format'
            }
    
    @classmethod
    def parse_excel_for_assignment(cls, file_path):
        """Parse Excel file and prepare data for package assignment (both old and new formats)"""
        try:
            df = pd.read_excel(file_path)
            
            # Determine format
            old_format_columns = ['MemberId', 'Name', 'Coupon Type', 'Package Value']
            new_format_columns = ['Member Id', 'Name', 'Package / Coupon status']
            
            has_old_format = all(col in df.columns for col in old_format_columns)
            has_new_format = all(col in df.columns for col in new_format_columns)
            
            if not has_old_format and not has_new_format:
                return {
                    'success': False,
                    'error': 'Excel format not recognized. Expected columns missing.'
                }
            
            format_type = 'old' if has_old_format else 'new'
            assignment_data = []
            current_time = get_indian_time()
            
            for index, row in df.iterrows():
                # Handle both column formats
                if format_type == 'old':
                    member_id = safe_get_strip(row, 'MemberId')
                    name = safe_get_strip(row, 'Name')
                    package_value_raw = safe_get_strip(row, 'Package Value')
                    coupon_type = safe_get_strip(row, 'Coupon Type')
                    user_status = None
                    sponsor_code = None
                else:  # new format
                    member_id = safe_get_strip(row, 'Member Id')
                    name = safe_get_strip(row, 'Name')
                    package_value_raw = None
                    coupon_type = safe_get_strip(row, 'Package / Coupon status')
                    user_status = safe_get_strip(row, 'User status')
                    sponsor_code = safe_get_strip(row, 'Sponsor Code')
                
                # Skip invalid rows
                if not member_id or not member_id.startswith('BEV'):
                    continue
                
                # Determine package info using updated method
                package_result = cls.determine_package_type(package_value_raw, coupon_type)
                
                # Determine target status based on user status and package
                if format_type == 'new' and user_status:
                    if user_status.lower() == 'activated' and package_result.get('package_type') == 'Platinum':
                        target_status = 'Activated'
                    elif user_status.lower() == 'red coupon':
                        target_status = 'Red Coupon'
                    elif user_status.lower() == 'blue coupon':
                        target_status = 'Blue Coupon'
                    elif user_status.lower() == 'eligible':
                        target_status = 'Eligible'
                    elif user_status.lower() == 'inactive':
                        target_status = 'Inactive'
                    elif user_status.lower() == 'deactivated':
                        target_status = 'Deactivated'
                    else:
                        target_status = package_result.get('status', 'Eligible')
                else:
                    target_status = package_result.get('status', 'Eligible')
                
                assignment_data.append({
                    'member_id': member_id,
                    'name': name,
                    'package_value': package_value_raw,
                    'package_label': package_result.get('package_type', 'Unknown'),
                    'package_amount': package_result.get('value', 0),
                    'target_status': target_status,
                    'coupon_type': coupon_type,
                    'user_status': user_status,
                    'sponsor_code': sponsor_code,
                    'format_type': format_type,
                    'processed_at': current_time.isoformat()
                })
            
            return {
                'success': True,
                'data': assignment_data,
                'summary': {
                    'total_users': len(assignment_data),
                    'package_breakdown': cls._get_package_breakdown(assignment_data)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error parsing Excel file: {str(e)}'
            }
    
    @classmethod
    def _get_package_breakdown(cls, assignment_data):
        """Get breakdown of package assignments"""
        breakdown = {}
        for item in assignment_data:
            label = item['package_label']
            if label in breakdown:
                breakdown[label] += 1
            else:
                breakdown[label] = 1
        return breakdown
    
    @classmethod
    def create_user_backup(cls, user_ids):
        """Create backup of current user states before package assignment"""
        try:
            # CRITICAL FIX: Import and use SQLAlchemy within proper Flask app context
            from app import User, db
            
            backup_data = []
            users = User.query.filter(User.id.in_(user_ids)).all()
            
            for user in users:
                backup_data.append({
                    'user_id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'coupon_status': user.coupon_status,
                    'wallet_balance': float(user.wallet_balance),
                    'upgrade_wallet_balance': float(user.upgrade_wallet_balance),
                    'is_active': user.is_active,
                    'last_package_assigned_at': user.last_package_assigned_at.isoformat() if user.last_package_assigned_at else None,
                    'package_assignment_timer_reset': user.package_assignment_timer_reset,
                    'backup_created_at': get_indian_time().isoformat()
                })
            
            return {
                'success': True,
                'backup_data': backup_data,
                'backup_summary': {
                    'total_users': len(backup_data),
                    'backup_timestamp': get_indian_time().isoformat()
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error creating user backup: {str(e)}'
            }
    
    @classmethod
    def simulate_package_assignment(cls, assignment_data):
        """Simulate package assignment without making changes - TEST MODE"""
        from app import User
        
        try:
            simulation_results = {
                'total_processed': len(assignment_data),
                'users_found': 0,
                'users_not_found': 0,
                'status_changes': [],
                'package_assignments': [],
                'warnings': []
            }
            
            for item in assignment_data:
                user = User.query.get(item['member_id'])
                
                if not user:
                    simulation_results['users_not_found'] += 1
                    simulation_results['warnings'].append(f"User {item['member_id']} not found in system")
                    continue
                
                simulation_results['users_found'] += 1
                
                # Check what would change
                old_status = user.coupon_status
                new_status = item['target_status']
                
                if old_status != new_status:
                    simulation_results['status_changes'].append({
                        'user_id': user.id,
                        'name': user.name,
                        'old_status': old_status,
                        'new_status': new_status,
                        'package_label': item['package_label'],
                        'package_value': item['package_amount']
                    })
                
                if item['package_value']:  # Has package assignment
                    simulation_results['package_assignments'].append({
                        'user_id': user.id,
                        'name': user.name,
                        'package': item['package_label'],
                        'value': item['package_amount']
                    })
            
            simulation_results['success'] = True
            return simulation_results
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error in package assignment simulation: {str(e)}'
            }

class PackageEarningsProcessor:
    """Handle earnings processing after package assignments with complete income cascade"""
    
    @classmethod
    def process_package_assignment_income_cascade(cls, affected_user_ids):
        """Process complete income cascade for users affected by package assignments"""
        try:
            from app import (
                check_and_update_eligibility,
                process_matching_referral_income,
                check_and_create_ved_node,
                distribute_ved_income_upline,
                process_guru_dakshina_income,
                check_direct_awards,
                db, User
            )
            
            print(f"🔄 Processing income cascade for {len(affected_user_ids)} package assignment affected users...")
            
            income_effects_processed = 0
            income_effects_errors = 0
            failed_users = []
            
            for user_id in affected_user_ids:
                user = User.query.get(user_id)
                if not user or not user.referrer_id:
                    continue  # Skip users without sponsors
                
                try:
                    print(f"💰 Processing income effects for user {user_id} (sponsor: {user.referrer_id})")
                    
                    # Execute complete income cascade (same order as VGK migration)
                    # 1. Check and update sponsor's eligibility status
                    check_and_update_eligibility(user.referrer_id)
                    
                    # 2. Check and process pair matching income for new user
                    process_matching_referral_income(user_id)
                    
                    # 3. Check if sponsor should become Ved Node
                    check_and_create_ved_node(user.referrer_id)
                    
                    # 4. Distribute Ved income upline if Ved Nodes are found
                    distribute_ved_income_upline(user_id)
                    
                    # 5. Process Guru Dakshina income for sponsor's sponsor
                    process_guru_dakshina_income(user_id)
                    
                    # 6. Check and update direct awards for the sponsor
                    check_direct_awards(user.referrer_id)
                    
                    # Commit income effects for this user
                    db.session.commit()
                    income_effects_processed += 1
                    print(f"✅ Income effects completed for user {user_id}")
                    
                except Exception as error:
                    # Rollback this user's income effects only
                    db.session.rollback()
                    error_details = {
                        'user_id': user_id,
                        'sponsor_id': user.referrer_id,
                        'error': str(error),
                        'error_type': type(error).__name__
                    }
                    failed_users.append(error_details)
                    income_effects_errors += 1
                    print(f"❌ Income effects failed for user {user_id}: {str(error)}")
            
            return {
                'success': True,
                'income_effects_processed': income_effects_processed,
                'income_effects_errors': income_effects_errors,
                'failed_users': failed_users,
                'timestamp': get_indian_time().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing package assignment income cascade: {str(e)}'
            }
    
    @classmethod
    def rollback_package_assignment_income_effects(cls, operation_key, affected_user_ids):
        """Rollback all income effects from package assignment operation"""
        try:
            from app import db, Transaction, VedIncome, UserMatchingAwardProgress, UserDirectAwardProgress
            
            print(f"🔄 Rolling back income effects for operation {operation_key} affecting {len(affected_user_ids)} users...")
            
            rollback_summary = {
                'transactions_removed': 0,
                'ved_incomes_removed': 0,
                'award_progress_removed': 0,
                'wallet_adjustments': 0,
                'errors': []
            }
            
            # Get operation timestamp for filtering
            from app import PackageAssignmentStorage
            operation = PackageAssignmentStorage.get_operation(operation_key)
            if not operation:
                return {
                    'success': False,
                    'error': 'Operation not found for rollback'
                }
            
            operation_time = operation.get('created_at')
            if not operation_time:
                return {
                    'success': False,
                    'error': 'Operation timestamp not found for rollback filtering'
                }
            
            # Rollback transactions created after package assignment
            transactions_to_remove = Transaction.query.filter(
                Transaction.timestamp >= operation_time,
                Transaction.referrer_id.in_(affected_user_ids)
            ).all()
            
            for transaction in transactions_to_remove:
                # Adjust wallet balance before removing transaction
                user = User.query.get(transaction.referrer_id)
                if user:
                    user.wallet_balance = max(0, user.wallet_balance - transaction.amount)
                    rollback_summary['wallet_adjustments'] += 1
                
                db.session.delete(transaction)
                rollback_summary['transactions_removed'] += 1
            
            # Rollback Ved income records
            ved_incomes_to_remove = VedIncome.query.filter(
                VedIncome.created_at >= operation_time,
                VedIncome.ved_member_id.in_(affected_user_ids)
            ).all()
            
            for ved_income in ved_incomes_to_remove:
                db.session.delete(ved_income)
                rollback_summary['ved_incomes_removed'] += 1
            
            # Rollback award progress updates
            award_progress_to_remove = UserDirectAwardProgress.query.filter(
                UserDirectAwardProgress.last_updated >= operation_time,
                UserDirectAwardProgress.user_id.in_(affected_user_ids)
            ).all()
            
            for award_progress in award_progress_to_remove:
                # Reset progress to previous state or remove if newly created
                if award_progress.current_count > 0:
                    award_progress.current_count = max(0, award_progress.current_count - 1)
                    award_progress.status = 'Not Achieved'
                    award_progress.processed_status = 'Pending'
                else:
                    db.session.delete(award_progress)
                rollback_summary['award_progress_removed'] += 1
            
            # Commit all rollback changes
            db.session.commit()
            
            return {
                'success': True,
                'rollback_summary': rollback_summary,
                'timestamp': get_indian_time().isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'Error during income effects rollback: {str(e)}'
            }
    
    @classmethod
    def trigger_comprehensive_income_calculation(cls, affected_user_ids):
        """Trigger immediate earnings calculation for affected users"""
        try:
            # CRITICAL FIX: Import Flask app and run in proper context
            from app import app, calculate_comprehensive_daily_income
            
            print(f"🎯 TRIGGERING COMPREHENSIVE INCOME CALCULATION for {len(affected_user_ids)} affected users")
            
            # Run comprehensive daily income calculation within Flask app context
            with app.app_context():
                success = calculate_comprehensive_daily_income()
            
            if success:
                return {
                    'success': True,
                    'message': f'Earnings calculation triggered successfully for {len(affected_user_ids)} users',
                    'calculation_timestamp': get_indian_time().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to trigger comprehensive income calculation'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error triggering earnings calculation: {str(e)}'
            }