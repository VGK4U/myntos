# Menu Seeding System - Initialize 13 functional modules with existing menu items
# This system analyzes current menu structures and maps them to the modular framework

import json
from datetime import datetime
from flask import current_app
from app import db, MenuModule, MenuItem, Permission, MenuConfiguration, MenuAuditLog

class MenuSeedingService:
    """Service for seeding and initializing the menu management system"""
    
    # 13 Functional Modules as recommended by architect
    FUNCTIONAL_MODULES = [
        {
            'module_key': 'overview_dashboard',
            'module_name': 'Overview & Dashboard', 
            'module_icon': 'bi-speedometer2',
            'module_description': 'Main dashboard, overview stats, and quick actions',
            'display_order': 1,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'identity_profile',
            'module_name': 'Identity & Profile',
            'module_icon': 'bi-person-circle',
            'module_description': 'User profile, KYC documents, personal information management',
            'display_order': 2,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'user_management',
            'module_name': 'User Management',
            'module_icon': 'bi-people-fill',
            'module_description': 'User accounts, registrations, roles, and account administration',
            'display_order': 3,
            'target_interfaces': ['admin', 'super_admin']
        },
        {
            'module_key': 'coupons_activation',
            'module_name': 'Coupons & Activation',
            'module_icon': 'bi-ticket-perforated',
            'module_description': 'Coupon management, activations, Red ID system, bulk operations',
            'display_order': 4,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'earnings_finance',
            'module_name': 'Earnings & Finance',
            'module_icon': 'bi-cash-coin',
            'module_description': 'Income tracking, wallet management, withdrawals, financial reports',
            'display_order': 5,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'team_referrals',
            'module_name': 'Team & Referrals',
            'module_icon': 'bi-diagram-3',
            'module_description': 'Team tree, referral tracking, matching system, team management',
            'display_order': 6,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'awards_achievements',
            'module_name': 'Awards & Achievements',
            'module_icon': 'bi-trophy',
            'module_description': 'Award systems, bonanza rewards, achievement tracking, field allowances',
            'display_order': 7,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'communication_alerts',
            'module_name': 'Communication & Alerts',
            'module_icon': 'bi-bell',
            'module_description': 'Notifications, messaging, alert preferences, communication logs',
            'display_order': 8,
            'target_interfaces': ['user', 'admin', 'super_admin']
        },
        {
            'module_key': 'reports_analytics',
            'module_name': 'Reports & Analytics',
            'module_icon': 'bi-graph-up',
            'module_description': 'Comprehensive reporting, data analytics, business intelligence',
            'display_order': 9,
            'target_interfaces': ['admin', 'super_admin']
        },
        {
            'module_key': 'operations_tools',
            'module_name': 'Operations & Tools',
            'module_icon': 'bi-tools',
            'module_description': 'Bulk operations, system tools, maintenance functions',
            'display_order': 10,
            'target_interfaces': ['admin', 'super_admin']
        },
        {
            'module_key': 'system_configuration',
            'module_name': 'System Configuration',
            'module_icon': 'bi-gear',
            'module_description': 'System settings, rate configurations, global controls',
            'display_order': 11,
            'target_interfaces': ['super_admin']
        },
        {
            'module_key': 'vgk_management',
            'module_name': 'VGK Management',
            'module_icon': 'bi-shield-check',
            'module_description': 'VGK ID exclusive controls, role management, menu configuration',
            'display_order': 12,
            'target_interfaces': ['vgk_id']
        },
        {
            'module_key': 'support_services',
            'module_name': 'Support & Services',
            'module_icon': 'bi-headset',
            'module_description': 'Help desk, service tickets, customer support, documentation',
            'display_order': 13,
            'target_interfaces': ['user', 'admin', 'super_admin']
        }
    ]
    
    # Existing menu items mapped to modules
    MENU_ITEM_MAPPING = {
        'overview_dashboard': [
            {'item_key': 'dashboard', 'item_name': 'Dashboard', 'route_endpoint': 'user.dashboard', 'icon': 'bi-house', 'order': 1},
            {'item_key': 'admin_dashboard', 'item_name': 'Admin Dashboard', 'route_endpoint': 'admin.dashboard', 'icon': 'bi-speedometer2', 'order': 1},
        ],
        'identity_profile': [
            {'item_key': 'profile', 'item_name': 'My Profile', 'route_endpoint': 'user.profile', 'icon': 'bi-person', 'order': 1},
            {'item_key': 'edit_profile', 'item_name': 'Edit Profile', 'route_endpoint': 'user.edit_profile', 'icon': 'bi-person-gear', 'order': 2},
            {'item_key': 'kyc_documents', 'item_name': 'KYC Documents', 'route_endpoint': 'user.kyc_documents', 'icon': 'bi-file-earmark-check', 'order': 3},
            {'item_key': 'kyc_management', 'item_name': 'KYC Management', 'route_endpoint': 'admin.kyc_management', 'icon': 'bi-file-earmark-medical', 'order': 4},
        ],
        'user_management': [
            {'item_key': 'manage_users', 'item_name': 'Manage Users', 'route_endpoint': 'admin.manage_users', 'icon': 'bi-people', 'order': 1},
            {'item_key': 'user_search', 'item_name': 'User Search', 'route_endpoint': 'admin.user_search', 'icon': 'bi-search', 'order': 2},
            {'item_key': 'user_registration', 'item_name': 'User Registration', 'route_endpoint': 'admin.user_registration', 'icon': 'bi-person-plus', 'order': 3},
            {'item_key': 'admin_users', 'item_name': 'Admin Users', 'route_endpoint': 'admin.admin_users', 'icon': 'bi-shield-check', 'order': 4},
        ],
        'coupons_activation': [
            {'item_key': 'my_coupon', 'item_name': 'My Coupon', 'route_endpoint': 'user.my_coupon', 'icon': 'bi-ticket', 'order': 1},
            {'item_key': 'coupon_management', 'item_name': 'Coupon Management', 'route_endpoint': 'admin.coupon_management', 'icon': 'bi-ticket-perforated', 'order': 2},
            {'item_key': 'red_id_system', 'item_name': 'Red ID System', 'route_endpoint': 'admin.red_id_system', 'icon': 'bi-exclamation-triangle', 'order': 3},
            {'item_key': 'bulk_coupon_actions', 'item_name': 'Bulk Coupon Actions', 'route_endpoint': 'admin.bulk_coupon_actions', 'icon': 'bi-stack', 'order': 4},
        ],
        'earnings_finance': [
            {'item_key': 'my_wallet', 'item_name': 'My Wallet', 'route_endpoint': 'user.my_wallet', 'icon': 'bi-wallet2', 'order': 1},
            {'item_key': 'earning_reports', 'item_name': 'Earning Reports', 'route_endpoint': 'user.earning_reports', 'icon': 'bi-graph-up', 'order': 2},
            {'item_key': 'withdrawal_history', 'item_name': 'Withdrawal History', 'route_endpoint': 'user.withdrawal_history', 'icon': 'bi-clock-history', 'order': 3},
            {'item_key': 'financial_management', 'item_name': 'Financial Management', 'route_endpoint': 'admin.financial_management', 'icon': 'bi-cash-stack', 'order': 4},
            {'item_key': 'transaction_reports', 'item_name': 'Transaction Reports', 'route_endpoint': 'admin.transaction_reports', 'icon': 'bi-file-earmark-spreadsheet', 'order': 5},
        ],
        'team_referrals': [
            {'item_key': 'my_referred_team', 'item_name': 'My Referred Team', 'route_endpoint': 'user.my_referred_team', 'icon': 'bi-people', 'order': 1},
            {'item_key': 'my_matching_team', 'item_name': 'My Matching Team', 'route_endpoint': 'user.my_matching_team', 'icon': 'bi-diagram-3', 'order': 2},
            {'item_key': 'team_management', 'item_name': 'Team Management', 'route_endpoint': 'admin.team_management', 'icon': 'bi-diagram-2', 'order': 3},
            {'item_key': 'placement_management', 'item_name': 'Placement Management', 'route_endpoint': 'admin.placement_management', 'icon': 'bi-grid', 'order': 4},
        ],
        'awards_achievements': [
            {'item_key': 'my_awards', 'item_name': 'My Awards', 'route_endpoint': 'user.my_awards', 'icon': 'bi-award', 'order': 1},
            {'item_key': 'field_allowances', 'item_name': 'Field Allowances', 'route_endpoint': 'user.field_allowances', 'icon': 'bi-briefcase', 'order': 2},
            {'item_key': 'bonanza_rewards', 'item_name': 'Bonanza Rewards', 'route_endpoint': 'user.bonanza_rewards', 'icon': 'bi-gift', 'order': 3},
            {'item_key': 'awards_management', 'item_name': 'Awards Management', 'route_endpoint': 'admin.awards_management', 'icon': 'bi-trophy', 'order': 4},
        ],
        'communication_alerts': [
            {'item_key': 'notifications', 'item_name': 'Notifications', 'route_endpoint': 'user.notifications', 'icon': 'bi-bell', 'order': 1},
            {'item_key': 'alert_preferences', 'item_name': 'Alert Preferences', 'route_endpoint': 'user.alert_preferences', 'icon': 'bi-bell-slash', 'order': 2},
            {'item_key': 'communication_logs', 'item_name': 'Communication Logs', 'route_endpoint': 'admin.communication_logs', 'icon': 'bi-chat-dots', 'order': 3},
        ],
        'reports_analytics': [
            {'item_key': 'user_reports', 'item_name': 'User Reports', 'route_endpoint': 'admin.user_reports', 'icon': 'bi-file-text', 'order': 1},
            {'item_key': 'financial_reports', 'item_name': 'Financial Reports', 'route_endpoint': 'admin.financial_reports', 'icon': 'bi-graph-down', 'order': 2},
            {'item_key': 'system_analytics', 'item_name': 'System Analytics', 'route_endpoint': 'admin.system_analytics', 'icon': 'bi-bar-chart', 'order': 3},
            {'item_key': 'export_data', 'item_name': 'Export Data', 'route_endpoint': 'admin.export_data', 'icon': 'bi-download', 'order': 4},
        ],
        'operations_tools': [
            {'item_key': 'bulk_operations', 'item_name': 'Bulk Operations', 'route_endpoint': 'admin.bulk_operations', 'icon': 'bi-layers', 'order': 1},
            {'item_key': 'data_migration', 'item_name': 'Data Migration', 'route_endpoint': 'admin.data_migration', 'icon': 'bi-arrow-repeat', 'order': 2},
            {'item_key': 'system_maintenance', 'item_name': 'System Maintenance', 'route_endpoint': 'admin.system_maintenance', 'icon': 'bi-wrench', 'order': 3},
        ],
        'system_configuration': [
            {'item_key': 'app_settings', 'item_name': 'App Settings', 'route_endpoint': 'admin.app_settings', 'icon': 'bi-sliders', 'order': 1},
            {'item_key': 'rate_configuration', 'item_name': 'Rate Configuration', 'route_endpoint': 'admin.rate_configuration', 'icon': 'bi-percent', 'order': 2},
            {'item_key': 'system_controls', 'item_name': 'System Controls', 'route_endpoint': 'admin.system_controls', 'icon': 'bi-toggles', 'order': 3},
        ],
        'vgk_management': [
            {'item_key': 'role_management', 'item_name': 'Role Management', 'route_endpoint': 'vgk.role_management', 'icon': 'bi-person-badge', 'order': 1},
            {'item_key': 'menu_configuration', 'item_name': 'Menu Configuration', 'route_endpoint': 'vgk.menu_configuration', 'icon': 'bi-list-ul', 'order': 2},
            {'item_key': 'permission_matrix', 'item_name': 'Permission Matrix', 'route_endpoint': 'vgk.permission_matrix', 'icon': 'bi-grid-3x3', 'order': 3},
        ],
        'support_services': [
            {'item_key': 'help_center', 'item_name': 'Help Center', 'route_endpoint': 'user.help_center', 'icon': 'bi-question-circle', 'order': 1},
            {'item_key': 'contact_support', 'item_name': 'Contact Support', 'route_endpoint': 'user.contact_support', 'icon': 'bi-headset', 'order': 2},
            {'item_key': 'service_tickets', 'item_name': 'Service Tickets', 'route_endpoint': 'admin.service_tickets', 'icon': 'bi-ticket-detailed', 'order': 3},
        ]
    }
    
    # Core permissions for the system
    CORE_PERMISSIONS = [
        # User Management Permissions
        {'key': 'users.view', 'name': 'View Users', 'category': 'user_management', 'action': 'view'},
        {'key': 'users.create', 'name': 'Create Users', 'category': 'user_management', 'action': 'create'},
        {'key': 'users.edit', 'name': 'Edit Users', 'category': 'user_management', 'action': 'edit'},
        {'key': 'users.delete', 'name': 'Delete Users', 'category': 'user_management', 'action': 'delete'},
        
        # Financial Permissions
        {'key': 'finance.view', 'name': 'View Financial Data', 'category': 'financial', 'action': 'view'},
        {'key': 'finance.approve', 'name': 'Approve Financial Transactions', 'category': 'financial', 'action': 'approve'},
        {'key': 'finance.reports', 'name': 'Generate Financial Reports', 'category': 'financial', 'action': 'report'},
        
        # KYC Permissions
        {'key': 'kyc.view', 'name': 'View KYC Documents', 'category': 'kyc_management', 'action': 'view'},
        {'key': 'kyc.approve', 'name': 'Approve KYC Documents', 'category': 'kyc_management', 'action': 'approve'},
        {'key': 'kyc.reject', 'name': 'Reject KYC Documents', 'category': 'kyc_management', 'action': 'reject'},
        
        # Coupon Permissions
        {'key': 'coupons.manage', 'name': 'Manage Coupons', 'category': 'coupon_management', 'action': 'manage'},
        {'key': 'coupons.bulk_ops', 'name': 'Bulk Coupon Operations', 'category': 'coupon_management', 'action': 'bulk'},
        
        # System Permissions
        {'key': 'system.config', 'name': 'System Configuration', 'category': 'system_admin', 'action': 'config'},
        {'key': 'system.maintenance', 'name': 'System Maintenance', 'category': 'system_admin', 'action': 'maintain'},
        
        # VGK Exclusive Permissions
        {'key': 'vgk.roles', 'name': 'Manage Roles', 'category': 'vgk_exclusive', 'action': 'manage'},
        {'key': 'vgk.menus', 'name': 'Configure Menus', 'category': 'vgk_exclusive', 'action': 'configure'},
        {'key': 'vgk.permissions', 'name': 'Assign Permissions', 'category': 'vgk_exclusive', 'action': 'assign'},
        
        # Reporting Permissions
        {'key': 'reports.view', 'name': 'View Reports', 'category': 'reporting', 'action': 'view'},
        {'key': 'reports.generate', 'name': 'Generate Reports', 'category': 'reporting', 'action': 'generate'},
        {'key': 'reports.export', 'name': 'Export Data', 'category': 'reporting', 'action': 'export'},
    ]
    
    @classmethod
    def seed_modules(cls, vgk_user_id=None):
        """Seed the 13 functional modules"""
        try:
            current_app.logger.info("🌱 Starting menu module seeding...")
            
            seeded_modules = []
            for module_data in cls.FUNCTIONAL_MODULES:
                # Check if module already exists
                existing_module = MenuModule.query.filter_by(module_key=module_data['module_key']).first()
                if existing_module:
                    current_app.logger.info(f"   ⏭️  Module '{module_data['module_key']}' already exists")
                    seeded_modules.append(existing_module)
                    continue
                
                # Create new module
                module = MenuModule(
                    module_key=module_data['module_key'],
                    module_name=module_data['module_name'],
                    module_icon=module_data['module_icon'],
                    module_description=module_data['module_description'],
                    display_order=module_data['display_order'],
                    created_by_id=vgk_user_id
                )
                
                db.session.add(module)
                seeded_modules.append(module)
                current_app.logger.info(f"   ✅ Created module: {module_data['module_name']}")
            
            db.session.commit()
            current_app.logger.info(f"🌱 Successfully seeded {len(seeded_modules)} modules")
            return seeded_modules
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error seeding modules: {str(e)}")
            raise
    
    @classmethod
    def seed_permissions(cls):
        """Seed core permissions"""
        try:
            current_app.logger.info("🔐 Starting permission seeding...")
            
            seeded_permissions = []
            for perm_data in cls.CORE_PERMISSIONS:
                # Check if permission already exists
                existing_perm = Permission.query.filter_by(permission_key=perm_data['key']).first()
                if existing_perm:
                    current_app.logger.info(f"   ⏭️  Permission '{perm_data['key']}' already exists")
                    seeded_permissions.append(existing_perm)
                    continue
                
                # Create new permission
                permission = Permission(
                    permission_key=perm_data['key'],
                    permission_name=perm_data['name'],
                    category=perm_data['category'],
                    action_type=perm_data['action'],
                    permission_description=f"Permission to {perm_data['action']} {perm_data['category'].replace('_', ' ')}"
                )
                
                db.session.add(permission)
                seeded_permissions.append(permission)
                current_app.logger.info(f"   ✅ Created permission: {perm_data['name']}")
            
            db.session.commit()
            current_app.logger.info(f"🔐 Successfully seeded {len(seeded_permissions)} permissions")
            return seeded_permissions
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error seeding permissions: {str(e)}")
            raise
    
    @classmethod
    def seed_menu_items(cls, vgk_user_id=None):
        """Seed menu items for all modules"""
        try:
            current_app.logger.info("📝 Starting menu item seeding...")
            
            seeded_items = []
            modules = {module.module_key: module for module in MenuModule.query.all()}
            
            for module_key, items in cls.MENU_ITEM_MAPPING.items():
                if module_key not in modules:
                    current_app.logger.warning(f"   ⚠️  Module '{module_key}' not found, skipping items")
                    continue
                
                module = modules[module_key]
                
                for item_data in items:
                    # Check if item already exists
                    existing_item = MenuItem.query.filter_by(
                        module_id=module.id, 
                        item_key=item_data['item_key']
                    ).first()
                    
                    if existing_item:
                        current_app.logger.info(f"   ⏭️  Item '{item_data['item_key']}' already exists")
                        seeded_items.append(existing_item)
                        continue
                    
                    # Create new menu item
                    menu_item = MenuItem(
                        module_id=module.id,
                        item_key=item_data['item_key'],
                        item_name=item_data['item_name'],
                        item_icon=item_data['icon'],
                        route_endpoint=item_data['route_endpoint'],
                        display_order=item_data['order'],
                        created_by_id=vgk_user_id
                    )
                    
                    db.session.add(menu_item)
                    seeded_items.append(menu_item)
                    current_app.logger.info(f"   ✅ Created item: {item_data['item_name']} in {module.module_name}")
            
            db.session.commit()
            current_app.logger.info(f"📝 Successfully seeded {len(seeded_items)} menu items")
            return seeded_items
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error seeding menu items: {str(e)}")
            raise
    
    @classmethod
    def initialize_system(cls, vgk_user_id=None):
        """Complete system initialization"""
        try:
            current_app.logger.info("🚀 Initializing Menu Management System...")
            
            # Seed modules first
            modules = cls.seed_modules(vgk_user_id)
            
            # Seed permissions
            permissions = cls.seed_permissions()
            
            # Seed menu items
            items = cls.seed_menu_items(vgk_user_id)
            
            # Create audit log entry
            if vgk_user_id:
                audit_log = MenuAuditLog(
                    action_type='system_initialize',
                    target_type='menu_system',
                    target_id=0,
                    actor_user_id=vgk_user_id,
                    actor_role='VGK ID',
                    new_value=json.dumps({
                        'modules_created': len(modules),
                        'permissions_created': len(permissions),
                        'items_created': len(items)
                    }),
                    change_reason='Initial system setup and menu structure creation'
                )
                db.session.add(audit_log)
                db.session.commit()
            
            current_app.logger.info("🚀 Menu Management System initialized successfully!")
            return {
                'modules': len(modules),
                'permissions': len(permissions),
                'items': len(items),
                'success': True
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error initializing system: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }
    
    @classmethod
    def get_module_statistics(cls):
        """Get statistics about the current menu system"""
        try:
            stats = {
                'modules': MenuModule.query.count(),
                'menu_items': MenuItem.query.count(),
                'permissions': Permission.query.count(),
                'active_modules': MenuModule.query.filter_by(is_active=True).count(),
                'visible_items': MenuItem.query.filter_by(is_visible=True).count(),
                'module_breakdown': {}
            }
            
            # Get breakdown by module
            for module in MenuModule.query.all():
                stats['module_breakdown'][module.module_key] = {
                    'name': module.module_name,
                    'items_count': module.menu_items.count(),
                    'active_items': module.menu_items.filter_by(is_active=True).count()
                }
            
            return stats
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting statistics: {str(e)}")
            return {'error': str(e)}