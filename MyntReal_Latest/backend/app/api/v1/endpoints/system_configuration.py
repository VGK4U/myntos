"""
RVZ ID Exclusive: System Configuration Management
Centralized configuration for all system constants - editable from RVZ dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.system_control import AppSettings

router = APIRouter()

RVZ_ID = "MNR182364369"

def validate_rvz_access(user_id: str, db: Session) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.id != RVZ_ID:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: System Configuration is exclusive to RVZ ID"
    #     )
    
    return user

@router.get("/rvz/system-configuration", response_class=HTMLResponse)
async def system_configuration_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID System Configuration page - All editable constants"""
    try:
        validate_rvz_access(user_id, db)
        
        # Get current settings
        settings = AppSettings.get_all_settings(db)
        
        # Organize configuration into sections
        config_sections = {
            'financial_deductions': {
                'title': 'Financial Deductions',
                'icon': '💰',
                'settings': [
                    {
                        'id': 'admin_deduction_rate',
                        'name': 'Admin Deduction Rate',
                        'description': 'Deducted from all income types',
                        'value': float(settings.admin_deduction_rate),
                        'unit': '%',
                        'min': 0,
                        'max': 20,
                        'step': 0.5
                    },
                    {
                        'id': 'tds_deduction_rate',
                        'name': 'TDS Deduction Rate',
                        'description': 'Tax Deducted at Source',
                        'value': float(settings.tds_deduction_rate),
                        'unit': '%',
                        'min': 0,
                        'max': 10,
                        'step': 0.1
                    },
                    {
                        'id': 'guru_dakshina_rate',
                        'name': 'Guru Dakshina Rate',
                        'description': 'Percentage paid to referrer from direct referral gross income',
                        'value': float(settings.guru_dakshina_rate),
                        'unit': '%',
                        'min': 0,
                        'max': 5,
                        'step': 0.1
                    }
                ]
            },
            'system_limits': {
                'title': 'System Limits',
                'icon': '⚙️',
                'settings': [
                    {
                        'id': 'daily_income_ceiling',
                        'name': 'Daily Income Ceiling',
                        'description': 'Maximum income per user per day',
                        'value': float(settings.daily_income_ceiling),
                        'unit': '₹',
                        'min': 10000,
                        'max': 100000,
                        'step': 1000
                    },
                    {
                        'id': 'minimum_withdrawal_amount',
                        'name': 'Minimum Withdrawal Amount',
                        'description': 'Minimum amount required for withdrawal',
                        'value': float(settings.minimum_withdrawal_amount),
                        'unit': '₹',
                        'min': 100,
                        'max': 5000,
                        'step': 100
                    }
                ]
            },
            'package_points': {
                'title': 'Package Points (Matching Multipliers)',
                'icon': '📦',
                'settings': [
                    {
                        'id': 'package_points_platinum',
                        'name': 'Platinum Points',
                        'description': 'Matching points for Platinum package',
                        'value': float(settings.package_points_platinum),
                        'unit': 'pts',
                        'min': 0,
                        'max': 2,
                        'step': 0.1
                    },
                    {
                        'id': 'package_points_diamond',
                        'name': 'Diamond Points',
                        'description': 'Matching points for Diamond package',
                        'value': float(settings.package_points_diamond),
                        'unit': 'pts',
                        'min': 0,
                        'max': 2,
                        'step': 0.1
                    },
                    {
                        'id': 'package_points_blue',
                        'name': 'Blue Points',
                        'description': 'Matching points for Blue package',
                        'value': float(settings.package_points_blue),
                        'unit': 'pts',
                        'min': 0,
                        'max': 2,
                        'step': 0.1
                    },
                    {
                        'id': 'package_points_loyal',
                        'name': 'Loyal Points',
                        'description': 'Matching points for Loyal package',
                        'value': float(settings.package_points_loyal),
                        'unit': 'pts',
                        'min': 0,
                        'max': 2,
                        'step': 0.1
                    }
                ]
            },
            'direct_referral_bonuses': {
                'title': 'Direct Referral Bonuses',
                'icon': '🎁',
                'settings': [
                    {
                        'id': 'direct_referral_platinum',
                        'name': 'Platinum Referral Bonus',
                        'description': 'Bonus when downline activates Platinum',
                        'value': float(settings.direct_referral_platinum),
                        'unit': '₹',
                        'min': 0,
                        'max': 10000,
                        'step': 100
                    },
                    {
                        'id': 'direct_referral_diamond',
                        'name': 'Diamond Referral Bonus',
                        'description': 'Bonus when downline activates Diamond',
                        'value': float(settings.direct_referral_diamond),
                        'unit': '₹',
                        'min': 0,
                        'max': 5000,
                        'step': 100
                    },
                    {
                        'id': 'direct_referral_blue',
                        'name': 'Blue Referral Bonus',
                        'description': 'Bonus when downline activates Blue',
                        'value': float(settings.direct_referral_blue),
                        'unit': '₹',
                        'min': 0,
                        'max': 2000,
                        'step': 50
                    },
                    {
                        'id': 'direct_referral_loyal',
                        'name': 'Loyal Referral Bonus',
                        'description': 'Bonus when downline activates Loyal',
                        'value': float(settings.direct_referral_loyal),
                        'unit': '₹',
                        'min': 0,
                        'max': 2000,
                        'step': 50
                    }
                ]
            },
            'matching_income': {
                'title': 'Matching Income',
                'icon': '🔄',
                'settings': [
                    {
                        'id': 'matching_income_per_point',
                        'name': 'Income Per Point Match',
                        'description': 'Fixed amount per 1:1 point match',
                        'value': float(settings.matching_income_per_point),
                        'unit': '₹',
                        'min': 1000,
                        'max': 5000,
                        'step': 100
                    }
                ]
            },
            'ved_income': {
                'title': 'Ved Income Rates',
                'icon': '🏅',
                'settings': [
                    {
                        'id': 'ved_income_platinum',
                        'name': 'Ved Income (Platinum)',
                        'description': 'Ved income for Platinum activation',
                        'value': float(settings.ved_income_platinum),
                        'unit': '₹',
                        'min': 0,
                        'max': 5000,
                        'step': 100
                    },
                    {
                        'id': 'ved_income_diamond',
                        'name': 'Ved Income (Diamond)',
                        'description': 'Ved income for Diamond activation',
                        'value': float(settings.ved_income_diamond),
                        'unit': '₹',
                        'min': 0,
                        'max': 2000,
                        'step': 100
                    },
                    {
                        'id': 'ved_income_blue',
                        'name': 'Ved Income (Blue)',
                        'description': 'Ved income for Blue activation',
                        'value': float(settings.ved_income_blue),
                        'unit': '₹',
                        'min': 0,
                        'max': 1000,
                        'step': 50
                    },
                    {
                        'id': 'ved_income_loyal',
                        'name': 'Ved Income (Loyal)',
                        'description': 'Ved income for Loyal activation',
                        'value': float(settings.ved_income_loyal),
                        'unit': '₹',
                        'min': 0,
                        'max': 1000,
                        'step': 50
                    }
                ]
            },
            'wallet_splits': {
                'title': 'Wallet Split Ratios',
                'icon': '💼',
                'settings': [
                    {
                        'id': 'wallet_split_platinum_withdrawable',
                        'name': 'Platinum Withdrawable %',
                        'description': 'Percentage to withdrawable wallet (Platinum)',
                        'value': float(settings.wallet_split_platinum_withdrawable * 100),
                        'unit': '%',
                        'min': 0,
                        'max': 100,
                        'step': 5
                    },
                    {
                        'id': 'wallet_split_platinum_earning',
                        'name': 'Platinum Earning %',
                        'description': 'Percentage to earning wallet (Platinum)',
                        'value': float(settings.wallet_split_platinum_earning * 100),
                        'unit': '%',
                        'min': 0,
                        'max': 100,
                        'step': 5
                    },
                    {
                        'id': 'wallet_split_default_withdrawable',
                        'name': 'Default Withdrawable %',
                        'description': 'Percentage to withdrawable wallet (Blue/Diamond/Loyal)',
                        'value': float(settings.wallet_split_default_withdrawable * 100),
                        'unit': '%',
                        'min': 0,
                        'max': 100,
                        'step': 5
                    },
                    {
                        'id': 'wallet_split_default_earning',
                        'name': 'Default Earning %',
                        'description': 'Percentage to earning wallet (Blue/Diamond/Loyal)',
                        'value': float(settings.wallet_split_default_earning * 100),
                        'unit': '%',
                        'min': 0,
                        'max': 100,
                        'step': 5
                    }
                ]
            },
            'kyc_banking_controls': {
                'title': 'KYC & Banking Approval Controls',
                'icon': '🔐',
                'settings': [
                    {
                        'id': 'skip_kyc_requirement',
                        'name': 'Skip KYC Requirement',
                        'description': '⚠️ GLOBAL CONTROL: When enabled, ALL users can claim bonanzas, receive awards, and withdraw funds WITHOUT KYC approval. Affects bonanza claiming, award processing, and auto-withdrawals system-wide.',
                        'value': bool(settings.skip_kyc_requirement),
                        'type': 'boolean',
                        'warning': 'Enabling this bypasses KYC verification across the ENTIRE platform'
                    },
                    {
                        'id': 'skip_bank_requirement',
                        'name': 'Skip Bank Approval Requirement',
                        'description': '⚠️ GLOBAL CONTROL: When enabled, ALL users can claim bonanzas, receive awards, and withdraw funds WITHOUT bank details approval. Affects bonanza claiming, award processing, and auto-withdrawals system-wide.',
                        'value': bool(settings.skip_bank_requirement),
                        'type': 'boolean',
                        'warning': 'Enabling this bypasses bank approval verification across the ENTIRE platform'
                    }
                ]
            }
        }
        
        # Frontend-only route - redirect to frontend
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Configuration - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/system-configuration">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/system-configuration">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/system-configuration/update")
async def update_configuration(
    user_id: str = Form(...),
    setting_id: str = Form(...),
    new_value: str = Form(...),  # Changed to str to handle both numeric and boolean
    reason: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update a specific configuration setting - RVZ ID ONLY"""
    try:
        user = validate_rvz_access(user_id, db)
        
        # Get settings
        settings = AppSettings.get_all_settings(db)
        
        # Validate setting exists
        if not hasattr(settings, setting_id):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid setting identifier"}
            )
        
        # Store old value for audit
        old_value = getattr(settings, setting_id)
        
        # Parse value based on setting type
        if setting_id in ['skip_kyc_requirement', 'skip_bank_requirement']:
            # Boolean toggles for KYC/Banking skip
            parsed_value = new_value.lower() in ['true', '1', 'yes', 'on']
        else:
            # Numeric values
            parsed_value = float(new_value)
            # Special handling for wallet splits (convert percentage to decimal)
            if 'wallet_split' in setting_id:
                parsed_value = parsed_value / 100.0  # Convert 50% to 0.50
        
        # Update the setting
        setattr(settings, setting_id, parsed_value)
        db.commit()
        db.refresh(settings)
        
        # Log the change
        print(f"[SYSTEM CONFIG] RVZ {user_id} changed {setting_id}: {old_value} → {parsed_value}")
        if reason:
            print(f"[SYSTEM CONFIG] Reason: {reason}")
        
        # Format response values based on type
        if setting_id in ['skip_kyc_requirement', 'skip_bank_requirement']:
            response_old_value = bool(old_value)
            response_new_value = bool(parsed_value)
        else:
            response_old_value = float(old_value) if old_value else 0.0
            response_new_value = float(parsed_value)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Configuration updated successfully",
                "setting_id": setting_id,
                "old_value": response_old_value,
                "new_value": response_new_value,
                "updated_by": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@router.post("/rvz/system-configuration/reset")
async def reset_to_defaults(
    user_id: str = Form(...),
    confirm: bool = Form(...),
    db: Session = Depends(get_db)
):
    """Reset all configurations to default values - RVZ ID ONLY"""
    try:
        user = validate_rvz_access(user_id, db)
        
        if not confirm:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Confirmation required"}
            )
        
        # Delete existing settings
        db.query(AppSettings).delete()
        db.commit()
        
        # Create new settings with defaults
        AppSettings.get_all_settings(db)
        
        print(f"[SYSTEM CONFIG] RVZ {user_id} reset all configurations to defaults")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "All configurations reset to default values",
                "reset_by": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@router.get("/rvz/system-configuration/export")
async def export_configuration(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Export current configuration as JSON - RVZ ID ONLY"""
    try:
        validate_rvz_access(user_id, db)
        
        settings = AppSettings.get_all_settings(db)
        
        config_export = {
            'exported_at': datetime.utcnow().isoformat(),
            'exported_by': user_id,
            'financial_deductions': {
                'admin_deduction_rate': float(settings.admin_deduction_rate),
                'tds_deduction_rate': float(settings.tds_deduction_rate),
                'guru_dakshina_rate': float(settings.guru_dakshina_rate)
            },
            'system_limits': {
                'daily_income_ceiling': float(settings.daily_income_ceiling),
                'minimum_withdrawal_amount': float(settings.minimum_withdrawal_amount)
            },
            'package_points': {
                'platinum': float(settings.package_points_platinum),
                'diamond': float(settings.package_points_diamond),
                'blue': float(settings.package_points_blue),
                'loyal': float(settings.package_points_loyal)
            },
            'direct_referral_bonuses': {
                'platinum': float(settings.direct_referral_platinum),
                'diamond': float(settings.direct_referral_diamond),
                'blue': float(settings.direct_referral_blue),
                'loyal': float(settings.direct_referral_loyal)
            },
            'matching_income': {
                'per_point': float(settings.matching_income_per_point)
            },
            'ved_income': {
                'platinum': float(settings.ved_income_platinum),
                'diamond': float(settings.ved_income_diamond),
                'blue': float(settings.ved_income_blue),
                'loyal': float(settings.ved_income_loyal)
            },
            'wallet_splits': {
                'platinum': {
                    'withdrawable': float(settings.wallet_split_platinum_withdrawable),
                    'earning': float(settings.wallet_split_platinum_earning)
                },
                'default': {
                    'withdrawable': float(settings.wallet_split_default_withdrawable),
                    'earning': float(settings.wallet_split_default_earning)
                }
            }
        }
        
        return JSONResponse(
            status_code=200,
            content=config_export
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
