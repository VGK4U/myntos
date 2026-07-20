"""
Email service utility using Replit Mail integration
Adapted from replitmail blueprint for Python Flask
"""
import os
import json
import requests
from typing import List, Optional, Dict, Any
import base64
from datetime import datetime


def get_auth_token() -> str:
    """Get authentication token for Replit mail service"""
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
    
    if repl_identity:
        return f"Bearer {repl_identity}"
    elif web_repl_renewal:
        return f"Bearer {web_repl_renewal}"
    else:
        raise ValueError(
            "No authentication token found. Please set REPL_IDENTITY or ensure you're running in Replit environment."
        )


def send_email(
    to: str | List[str],
    subject: str,
    text: Optional[str] = None,
    html: Optional[str] = None,
    cc: Optional[str | List[str]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Send email using Replit Mail service
    
    Args:
        to: Recipient email address(es)
        subject: Email subject
        text: Plain text body (optional)
        html: HTML body (optional)
        cc: CC recipient email address(es) (optional)
        attachments: List of attachments (optional)
        
    Returns:
        Dict with accepted, rejected, messageId, and response
        
    Raises:
        ValueError: If authentication token not found
        requests.RequestException: If email sending fails
    """
    try:
        auth_token = get_auth_token()
        
        # Prepare email data
        email_data = {
            "to": to,
            "subject": subject
        }
        
        if text:
            email_data["text"] = text
        if html:
            email_data["html"] = html
        if cc:
            email_data["cc"] = cc
        if attachments:
            email_data["attachments"] = attachments
            
        # Send request to Replit mail service
        response = requests.post(
            "https://connectors.replit.com/api/v2/mailer/send",
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_token,
            },
            json=email_data,
            timeout=30
        )
        
        if not response.ok:
            # Handle both JSON and non-JSON error responses properly
            error_message = "Unknown error"
            try:
                if response.content:
                    error_data = response.json()
                    error_message = error_data.get('message', f"HTTP {response.status_code}")
                else:
                    error_message = f"HTTP {response.status_code}: Empty response"
            except (ValueError, json.JSONDecodeError):
                # If response is not valid JSON, use status code and text
                error_message = f"HTTP {response.status_code}: {response.text[:100] if response.text else 'No response body'}"
            
            raise requests.RequestException(f"Failed to send email: {error_message}")
            
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError):
            # If success response is not valid JSON, return basic success info
            return {
                "status": "success",
                "messageId": "unknown",
                "accepted": [to] if isinstance(to, str) else to,
                "rejected": []
            }
        
    except Exception as e:
        print(f"Email sending error: {str(e)}")
        raise


def send_password_reset_email(email: str, reset_code: str, reset_url: str) -> bool:
    """
    Send password reset email with 6-digit code
    
    Args:
        email: User's email address
        reset_code: 6-digit password reset code
        reset_url: Base URL for password reset page
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_email = email or "user@unknown.com"
        safe_reset_code = str(reset_code or "000000")
        safe_reset_url = str(reset_url or "https://evprogram.com")
        safe_reset_page_link = f"{safe_reset_url}/reset_password"
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .code-box {{ background: #f8f9fa; border: 2px solid #007bff; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .reset-code {{ font-size: 36px; font-weight: bold; color: #007bff; letter-spacing: 3px; margin: 10px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .instructions {{ background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>EV Reference Program</h1>
                <h2>Password Reset Code</h2>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>You have requested to reset your password for your EV Reference Program account. Use the 6-digit code below to reset your password:</p>
                
                <div class="code-box">
                    <p style="margin: 5px 0; color: #666;">Your Password Reset Code:</p>
                    <div class="reset-code">{safe_reset_code}</div>
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">Enter this code on the password reset page</p>
                </div>
                
                <div class="instructions">
                    <h4 style="margin-top: 0;">How to Reset Your Password:</h4>
                    <ol>
                        <li>Go to the <a href="{safe_reset_page_link}" style="color: #007bff;">Password Reset Page</a></li>
                        <li>Enter your Member ID or Email address</li>
                        <li>Enter the 6-digit code: <strong>{safe_reset_code}</strong></li>
                        <li>Create your new password</li>
                    </ol>
                </div>
                
                <div class="warning">
                    <strong>Important:</strong> This code will expire in 15 minutes for security purposes. If you did not request this password reset, please ignore this email.
                </div>
                
                <p>If you have any questions, please don't hesitate to contact our support team.</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This is an automated email. Please do not reply to this message.</p>
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - Password Reset Code
    
    Hello,
    
    You have requested to reset your password for your EV Reference Program account.
    
    Your 6-digit password reset code is: {safe_reset_code}
    
    How to Reset Your Password:
    1. Go to: {safe_reset_page_link}
    2. Enter your Member ID or Email address
    3. Enter the 6-digit code: {safe_reset_code}
    4. Create your new password
    
    IMPORTANT: This code will expire in 15 minutes for security purposes.
    
    If you did not request this password reset, please ignore this email.
    
    If you have any questions, please contact our support team.
    
    Best regards,
    EV Reference Program Team
    
    ---
    This is an automated email. Please do not reply to this message.
    """
    
        # Send email with protected content
        result = send_email(
            to=safe_email,
            subject="Password Reset Request - EV Reference Program",
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send password reset email to {safe_email}: {str(e)}")
        return False


def send_new_member_welcome_email(email: str, username: str, bev_id: str, temporary_password: str, login_url: str) -> bool:
    """
    Send welcome email to admin-created members with login credentials
    
    Args:
        email: User's email address
        username: User's name
        bev_id: User's BEV ID for login
        temporary_password: 6-digit temporary password
        login_url: Login page URL
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # SECURITY: Require valid email - never send credentials to fallback addresses
        if not email or not email.strip():
            print("Email sending skipped: No valid email address provided")
            return False
            
        # DEFENSIVE PROGRAMMING - Safe field access with None guards (except email)
        safe_email = email.strip()
        safe_username = str(username or "Valued Member")
        safe_bev_id = str(bev_id or "BEV000000000")
        safe_password = str(temporary_password or "123456")
        safe_login_url = str(login_url or "https://evprogram.com/login")
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to EV Reference Program - Account Created</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .credentials-box {{ background: #f8f9fa; border: 2px solid #28a745; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .bev-id {{ font-size: 24px; font-weight: bold; color: #28a745; letter-spacing: 1px; margin: 10px 0; font-family: monospace; }}
            .password {{ font-size: 32px; font-weight: bold; color: #007bff; letter-spacing: 3px; margin: 10px 0; font-family: monospace; }}
            .login-button {{ display: inline-block; background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
            .login-button:hover {{ background: #0056b3; }}
            .instructions {{ background: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .important {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .highlight {{ background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to EV Reference Program!</h1>
                <h2>Your Account Has Been Created</h2>
            </div>
            <div class="content">
                <p>Dear {safe_username},</p>
                <p>Your account has been successfully created by our admin team. We're excited to welcome you to the EV Reference Program community!</p>
                
                <div class="credentials-box">
                    <h3 style="margin-top: 0; color: #495057;">🔑 Your Login Credentials</h3>
                    <p style="margin: 5px 0; color: #666;">Your BEV ID:</p>
                    <div class="bev-id">{safe_bev_id}</div>
                    <p style="margin: 5px 0; color: #666;">Temporary Password:</p>
                    <div class="password">{safe_password}</div>
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">Keep these credentials secure</p>
                </div>
                
                <div class="important">
                    <h4 style="margin-top: 0;">🚨 Password Change Required</h4>
                    <p><strong>You must change your password on first login.</strong> This temporary password is only valid for your initial login and must be updated for security purposes.</p>
                </div>
                
                <div class="instructions">
                    <h3 style="margin-top: 0; color: #495057;">📋 How to Get Started:</h3>
                    <ol>
                        <li><strong>Login:</strong> Click the button below to access your account</li>
                        <li><strong>Enter your BEV ID:</strong> {safe_bev_id}</li>
                        <li><strong>Enter temporary password:</strong> {safe_password}</li>
                        <li><strong>Change password:</strong> You'll be prompted to create a new password</li>
                        <li><strong>Complete your profile:</strong> Add any missing information</li>
                        <li><strong>Activate your coupon:</strong> Start earning rewards immediately</li>
                    </ol>
                </div>
                
                <div style="text-align: center;">
                    <a href="{safe_login_url}" class="login-button">🚀 Login to Your Account</a>
                </div>
                
                <div class="highlight">
                    <h3>What You Can Do Next:</h3>
                    <ul>
                        <li>Complete your KYC verification to unlock full features</li>
                        <li>Refer friends and family to grow your network</li>
                        <li>Track your earnings through our comprehensive dashboard</li>
                        <li>Participate in our multi-stream income program</li>
                    </ul>
                </div>
                
                <div class="warning">
                    <h4 style="margin-top: 0;">🔒 Security Reminders:</h4>
                    <ul>
                        <li><strong>Never share your login credentials</strong> with anyone</li>
                        <li><strong>Change your password immediately</strong> after first login</li>
                        <li><strong>Use a strong password</strong> with mixed characters</li>
                        <li><strong>Keep your account information</strong> up to date</li>
                    </ul>
                </div>
                
                <p>Our referral system offers multiple income streams including direct referrals, matching referral bonuses, Ved Income, and Guru Dakshina rewards.</p>
                
                <p>If you have any questions or need assistance, our support team is here to help you get started.</p>
                
                <p>Thank you for joining the EV Reference Program!</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This is an automated email containing your login credentials. Please keep this email secure.</p>
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - Welcome & Login Credentials
    
    Dear {safe_username},
    
    Your account has been successfully created by our admin team. Welcome to the EV Reference Program!
    
    YOUR LOGIN CREDENTIALS:
    ======================
    BEV ID: {safe_bev_id}
    Temporary Password: {safe_password}
    
    🚨 PASSWORD CHANGE REQUIRED:
    You must change your password on first login. This temporary password is only valid for your initial login.
    
    HOW TO GET STARTED:
    ==================
    1. Go to: {safe_login_url}
    2. Enter your BEV ID: {safe_bev_id}
    3. Enter temporary password: {safe_password}
    4. You'll be prompted to create a new password
    5. Complete your profile and activate your coupon
    
    WHAT YOU CAN DO NEXT:
    ====================
    - Complete your KYC verification to unlock full features
    - Refer friends and family to grow your network
    - Track your earnings through our comprehensive dashboard
    - Participate in our multi-stream income program
    
    SECURITY REMINDERS:
    ==================
    🔒 Never share your login credentials with anyone
    🔒 Change your password immediately after first login
    🔒 Use a strong password with mixed characters
    🔒 Keep your account information up to date
    
    Our referral system offers multiple income streams including direct referrals, matching referral bonuses, Ved Income, and Guru Dakshina rewards.
    
    If you have any questions or need assistance, our support team is here to help.
    
    Thank you for joining the EV Reference Program!
    
    Best regards,
    EV Reference Program Team
    
    ---
    This email contains your login credentials. Please keep it secure.
    """
    
        # Send email with protected content
        result = send_email(
            to=safe_email,
            subject="Welcome to EV Reference Program - Your Login Credentials",
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send new member welcome email to {safe_email}: {str(e)}")
        return False


def send_welcome_email(email: str, username: str) -> bool:
    """
    Send welcome email to new users
    
    Args:
        email: User's email address
        username: User's name
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_email = email or "user@unknown.com"
        safe_username = str(username or "Valued Customer")
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .highlight {{ background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to EV Reference Program!</h1>
            </div>
            <div class="content">
                <p>Dear {safe_username},</p>
                <p>Welcome to the EV Reference Program! We're excited to have you join our community.</p>
                
                <div class="highlight">
                    <h3>Next Steps:</h3>
                    <ul>
                        <li>Complete your KYC verification to unlock full features</li>
                        <li>Activate your coupon to start earning rewards</li>
                        <li>Refer friends and family to grow your network</li>
                        <li>Track your progress through our comprehensive dashboard</li>
                    </ul>
                </div>
                
                <p>Our referral system offers multiple income streams including direct referrals, matching referral bonuses, Ved Income, and Guru Dakshina rewards.</p>
                
                <p>If you have any questions or need assistance, our support team is here to help.</p>
                
                <p>Thank you for joining us on this exciting journey!</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    Welcome to EV Reference Program!
    
    Dear {safe_username},
    
    Welcome to the EV Reference Program! We're excited to have you join our community.
    
    Next Steps:
    - Complete your KYC verification to unlock full features
    - Activate your coupon to start earning rewards
    - Refer friends and family to grow your network
    - Track your progress through our comprehensive dashboard
    
    Our referral system offers multiple income streams including direct referrals, matching referral bonuses, Ved Income, and Guru Dakshina rewards.
    
    If you have any questions or need assistance, our support team is here to help.
    
    Thank you for joining us on this exciting journey!
    
    Best regards,
    EV Reference Program Team
    """
    
        # Send email with protected content
        result = send_email(
            to=safe_email,
            subject="Welcome to EV Reference Program!",
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send welcome email to {safe_email}: {str(e)}")
        return False


def send_coupon_receipt_email(email: str, coupon, user_name: str) -> bool:
    """
    Send coupon receipt email with code and usage instructions when Enhanced Coupons are generated
    
    Args:
        email: User's email address
        coupon: EnhancedCoupon object
        user_name: User's name
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_user_name = user_name or "Valued User"
        safe_coupon_code = getattr(coupon, 'coupon_code', None) or "UNKNOWN"
        safe_coupon_value = float(getattr(coupon, 'coupon_value', None) or 0)
        safe_status = (getattr(coupon, 'status', None) or 'pending').title()
        safe_admin_status = (getattr(coupon, 'admin_claim_status', None) or 'pending').title()
        
        # Safe date formatting with fallbacks
        issue_date_obj = getattr(coupon, 'issue_date', None) or datetime.utcnow()
        safe_issue_date = issue_date_obj.strftime('%B %d, %Y at %I:%M %p') if hasattr(issue_date_obj, 'strftime') else 'Today'
        
        ev_expiry_obj = getattr(coupon, 'ev_expiry_date', None)
        safe_ev_expiry = ev_expiry_obj.strftime('%B %d, %Y') if ev_expiry_obj and hasattr(ev_expiry_obj, 'strftime') else 'Not set'
        
        training_expiry_obj = getattr(coupon, 'training_expiry_date', None)
        safe_training_expiry = training_expiry_obj.strftime('%B %d, %Y') if training_expiry_obj and hasattr(training_expiry_obj, 'strftime') else 'Not set'
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EV Purchase Coupon Receipt - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .coupon-box {{ background: #f8f9fa; border: 2px solid #28a745; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-pin {{ font-size: 32px; font-weight: bold; color: #28a745; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .coupon-value {{ font-size: 24px; font-weight: bold; color: #007bff; margin: 10px 0; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .usage-steps {{ background: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .important-note {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 EV Purchase Coupon Received!</h1>
                <h2>Your Digital Receipt</h2>
            </div>
            <div class="content">
                <p>Dear {safe_user_name},</p>
                <p>Congratulations! Your EV Purchase Coupon has been successfully generated. Below are your coupon details:</p>
                
                <div class="coupon-box">
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">Your Coupon Code:</p>
                    <div class="coupon-pin">{safe_coupon_code}</div>
                    <div class="coupon-value">₹{safe_coupon_value:,.2f} Value</div>
                    <span class="badge">ENHANCED COUPON</span>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Coupon Details</th>
                        <th>Information</th>
                    </tr>
                    <tr>
                        <td>Coupon Code</td>
                        <td><strong>{safe_coupon_code}</strong></td>
                    </tr>
                    <tr>
                        <td>Coupon Value</td>
                        <td><strong>₹{safe_coupon_value:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>Status</td>
                        <td><strong>{safe_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Admin Claim Status</td>
                        <td><strong>{safe_admin_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Issue Date</td>
                        <td><strong>{safe_issue_date}</strong></td>
                    </tr>
                    <tr>
                        <td>EV Expiry</td>
                        <td><strong>{safe_ev_expiry}</strong></td>
                    </tr>
                    <tr>
                        <td>Training Expiry</td>
                        <td><strong>{safe_training_expiry}</strong></td>
                    </tr>
                </table>
                
                <div class="usage-steps">
                    <h3 style="margin-top: 0; color: #495057;">📋 How to Use Your Enhanced Coupon:</h3>
                    <ol>
                        <li><strong>Wait for Admin Approval:</strong> Your coupon needs admin approval before redemption</li>
                        <li><strong>Choose Redemption Type:</strong> Use for EV Purchase (₹15,000 LFP / ₹7,500 Graphene) or Training (20% cashback)</li>
                        <li><strong>Submit Redemption Request:</strong> Apply through your dashboard with required details</li>
                        <li><strong>Admin Processing:</strong> Our team will review and approve/reject your request</li>
                        <li><strong>Complete Redemption:</strong> Follow instructions after approval for final redemption</li>
                    </ol>
                </div>
                
                <div class="important-note">
                    <h4 style="margin-top: 0;">🚨 Important Information:</h4>
                    <ul>
                        <li><strong>Non-Transferable:</strong> This coupon is tied to your account and cannot be transferred</li>
                        <li><strong>EV Redemption:</strong> ₹15,000 value for LFP models, ₹7,500 for Graphene models</li>
                        <li><strong>Training Redemption:</strong> 20% cashback on course fees, remaining value preserved</li>
                        <li><strong>Admin Approval Required:</strong> All redemption requests need admin approval</li>
                        <li><strong>Expiry Tracking:</strong> Different expiry dates for EV vs Training redemptions</li>
                        <li><strong>Keep Code Safe:</strong> Store your coupon code securely - you'll need it for redemption</li>
                    </ul>
                </div>
                
                <p>If you have any questions about your coupon or need assistance with redemption, please contact our support team.</p>
                
                <p>Thank you for choosing EV Reference Program!</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This is an automated receipt. Please keep this email for your records.</p>
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - Enhanced Coupon Receipt
    
    Dear {safe_user_name},
    
    Congratulations! Your Enhanced Coupon has been successfully generated.
    
    COUPON DETAILS:
    ===============
    Coupon Code: {safe_coupon_code}
    Coupon Value: ₹{safe_coupon_value:,.2f}
    Status: {safe_status}
    Admin Claim Status: {safe_admin_status}
    Issue Date: {safe_issue_date}
    EV Expiry: {safe_ev_expiry}
    Training Expiry: {safe_training_expiry}
    
    HOW TO USE YOUR ENHANCED COUPON:
    ================================
    1. Wait for Admin Approval: Your coupon needs admin approval before redemption
    2. Choose Redemption Type: Use for EV Purchase (₹15,000 LFP / ₹7,500 Graphene) or Training (20% cashback)
    3. Submit Redemption Request: Apply through your dashboard with required details
    4. Admin Processing: Our team will review and approve/reject your request
    5. Complete Redemption: Follow instructions after approval for final redemption
    
    IMPORTANT INFORMATION:
    =====================
    * Non-Transferable: This coupon is tied to your account and cannot be transferred
    * EV Redemption: ₹15,000 value for LFP models, ₹7,500 for Graphene models
    * Training Redemption: 20% cashback on course fees, remaining value preserved
    * Admin Approval Required: All redemption requests need admin approval
    * Expiry Tracking: Different expiry dates for EV vs Training redemptions
    * Keep Code Safe: Store your coupon code securely - you'll need it for redemption
    
    If you have any questions about your coupon or need assistance with redemption, please contact our support team.
    
    Thank you for choosing EV Reference Program!
    
    Best regards,
    EV Reference Program Team
    
    ---
    This is an automated receipt. Please keep this email for your records.
    """
    
        # Safe subject construction
        safe_subject = f"Enhanced Coupon Receipt - Code: {safe_coupon_code}"
        
        # Send email with protected content
        result = send_email(
            to=email,
            subject=safe_subject,
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send coupon receipt email to {email}: {str(e)}")
        return False


def send_coupon_tagged_email(email: str, coupon, user_name: str, tagged_by_admin: str) -> bool:
    """
    Send confirmation email for Enhanced Coupon admin claim workflow
    
    Args:
        email: User's email address
        coupon: EnhancedCoupon object
        user_name: User's name
        tagged_by_admin: Name of admin who processed the coupon
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_user_name = user_name or "Valued User"
        safe_tagged_by_admin = tagged_by_admin or "Admin Team"
        safe_coupon_code = getattr(coupon, 'coupon_code', None) or "UNKNOWN"
        safe_coupon_value = float(getattr(coupon, 'coupon_value', None) or 0)
        safe_status = (getattr(coupon, 'status', None) or 'pending').title()
        safe_admin_status = (getattr(coupon, 'admin_claim_status', None) or 'pending').title()
        
        # Safe date formatting with fallbacks
        issue_date_obj = getattr(coupon, 'issue_date', None) or datetime.utcnow()
        safe_issue_date = issue_date_obj.strftime('%B %d, %Y') if hasattr(issue_date_obj, 'strftime') else 'Today'
        safe_issue_date_full = issue_date_obj.strftime('%B %d, %Y at %I:%M %p') if hasattr(issue_date_obj, 'strftime') else 'Today'
        
        ev_expiry_obj = getattr(coupon, 'ev_expiry_date', None)
        safe_ev_expiry = ev_expiry_obj.strftime('%B %d, %Y') if ev_expiry_obj and hasattr(ev_expiry_obj, 'strftime') else 'Not set'
        
        training_expiry_obj = getattr(coupon, 'training_expiry_date', None)
        safe_training_expiry = training_expiry_obj.strftime('%B %d, %Y') if training_expiry_obj and hasattr(training_expiry_obj, 'strftime') else 'Not set'
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced Coupon Status Update - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .tagged-box {{ background: #d4edda; border: 2px solid #28a745; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-pin {{ font-size: 28px; font-weight: bold; color: #28a745; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .activation-steps {{ background: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .important-note {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏷️ Enhanced Coupon Update!</h1>
                <h2>Admin Claim Status: {safe_admin_status}</h2>
            </div>
            <div class="content">
                <p>Dear {safe_user_name},</p>
                <p>Your Enhanced Coupon has been processed by our admin team. Here are the updated details:</p>
                
                <div class="tagged-box">
                    <h3 style="margin-top: 0; color: #155724;">✅ Coupon Status Updated</h3>
                    <div class="coupon-pin">{safe_coupon_code}</div>
                    <p style="margin: 5px 0; color: #155724; font-size: 16px;">₹{safe_coupon_value:,.2f} Value • <span class="badge">ENHANCED COUPON</span></p>
                    <p style="margin: 10px 0; color: #155724; font-size: 14px;">Processed by: <strong>{safe_tagged_by_admin}</strong> on {safe_issue_date}</p>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Coupon Information</th>
                        <th>Details</th>
                    </tr>
                    <tr>
                        <td>Coupon Code</td>
                        <td><strong>{safe_coupon_code}</strong></td>
                    </tr>
                    <tr>
                        <td>Current Status</td>
                        <td><strong>{safe_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Admin Claim Status</td>
                        <td><strong>{safe_admin_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Coupon Value</td>
                        <td><strong>₹{safe_coupon_value:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>Issue Date</td>
                        <td><strong>{safe_issue_date_full}</strong></td>
                    </tr>
                    <tr>
                        <td>EV Expiry Date</td>
                        <td><strong>{safe_ev_expiry}</strong></td>
                    </tr>
                    <tr>
                        <td>Training Expiry Date</td>
                        <td><strong>{safe_training_expiry}</strong></td>
                    </tr>
                </table>
                
                <div class="activation-steps">
                    <h3 style="margin-top: 0; color: #495057;">🚀 Next Steps - Enhanced Coupon Workflow:</h3>
                    <ol>
                        <li><strong>Check Admin Status:</strong> Your admin claim status is currently <strong>{safe_admin_status}</strong></li>
                        <li><strong>Choose Redemption Type:</strong> Decide between EV Purchase or Training courses</li>
                        <li><strong>EV Option:</strong> ₹15,000 for LFP models or ₹7,500 for Graphene models</li>
                        <li><strong>Training Option:</strong> 20% cashback on course fees, remaining value preserved</li>
                        <li><strong>Submit Request:</strong> Apply for redemption through your dashboard when ready</li>
                    </ol>
                    <p style="text-align: center;"><a href="/dashboard" class="button">📊 Go to Dashboard</a></p>
                </div>
                
                <div class="important-note">
                    <h4 style="margin-top: 0;">💡 Important Information:</h4>
                    <ul>
                        <li><strong>Admin Approval Required:</strong> All redemption requests require admin approval</li>
                        <li><strong>Dual Redemption Types:</strong> Choose between EV purchase or Training courses</li>
                        <li><strong>EV Expiry:</strong> {safe_ev_expiry}</li>
                        <li><strong>Training Expiry:</strong> {safe_training_expiry}</li>
                        <li><strong>Non-Transferable:</strong> This coupon is tied to your account only</li>
                        <li><strong>Contact Support:</strong> Reach out if you have questions about the redemption process</li>
                    </ul>
                </div>
                
                <p>If you have questions about your coupon status or the Enhanced Coupon system, please contact our support team.</p>
                
                <p>Thank you for being part of the EV Reference Program!</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This coupon was processed by {safe_tagged_by_admin} from our admin team.</p>
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - Enhanced Coupon Status Update
    
    Dear {safe_user_name},
    
    Your Enhanced Coupon has been processed by our admin team.
    
    COUPON DETAILS:
    ===============
    Coupon Code: {safe_coupon_code}
    Current Status: {safe_status}
    Admin Claim Status: {safe_admin_status}
    Coupon Value: ₹{safe_coupon_value:,.2f}
    Issue Date: {safe_issue_date_full}
    Processed by: {safe_tagged_by_admin}
    EV Expiry Date: {safe_ev_expiry}
    Training Expiry Date: {safe_training_expiry}
    
    NEXT STEPS - ENHANCED COUPON WORKFLOW:
    =====================================
    1. Check Admin Status: Your admin claim status is currently {safe_admin_status}
    2. Choose Redemption Type: Decide between EV Purchase or Training courses
    3. EV Option: ₹15,000 for LFP models or ₹7,500 for Graphene models
    4. Training Option: 20% cashback on course fees, remaining value preserved
    5. Submit Request: Apply for redemption through your dashboard when ready
    
    IMPORTANT INFORMATION:
    =====================
    * Admin Approval Required: All redemption requests require admin approval
    * Dual Redemption Types: Choose between EV purchase or Training courses
    * EV Expiry: {safe_ev_expiry}
    * Training Expiry: {safe_training_expiry}
    * Non-Transferable: This coupon is tied to your account only
    * Contact Support: Reach out if you have questions about the redemption process
    
    If you have questions about your coupon status or the Enhanced Coupon system, please contact our support team.
    
    Thank you for being part of the EV Reference Program!
    
    Best regards,
    EV Reference Program Team
    
    ---
    This coupon was processed by {safe_tagged_by_admin} from our admin team.
    """
    
        # Safe subject construction
        safe_subject = f"Enhanced Coupon Update - Code: {safe_coupon_code} (₹{safe_coupon_value:,.0f})"
        
        # Send email with protected content
        result = send_email(
            to=email,
            subject=safe_subject,
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send coupon tagged email to {email}: {str(e)}")
        return False


def send_ev_redemption_request_email(admin_email: str, coupon, user, ev_model: str, redemption_amount: float) -> bool:
    """
    Send admin notification for EV redemption request
    
    Args:
        admin_email: Admin's email address
        coupon: EnhancedCoupon object
        user: User object who made the request
        ev_model: Selected EV model (LFP or Graphene)
        redemption_amount: Amount being redeemed (15000 or 7500)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_admin_email = admin_email or "admin@evprogram.com"
        safe_coupon_code = getattr(coupon, 'coupon_code', None) or "UNKNOWN"
        safe_coupon_value = float(getattr(coupon, 'coupon_value', None) or 0)
        safe_status = (getattr(coupon, 'status', None) or 'pending').title()
        safe_admin_status = (getattr(coupon, 'admin_claim_status', None) or 'pending').title()
        
        # Safe user field access
        safe_user_name = getattr(user, 'name', None) or "Unknown User"
        safe_user_id = getattr(user, 'id', None) or "UNKNOWN"
        safe_user_email = getattr(user, 'email', None) or "unknown@email.com"
        
        # Safe numeric values
        safe_redemption_amount = float(redemption_amount or 0)
        safe_ev_model = str(ev_model or 'Unknown')
        
        # Model details with safe access
        model_details = {
            'LFP': {'amount': 15000, 'name': 'LFP Model', 'description': 'Lithium Iron Phosphate Battery'},
            'Graphene': {'amount': 7500, 'name': 'Graphene Model', 'description': 'Advanced Graphene Battery Technology'}
        }
        model_info = model_details.get(safe_ev_model, {'amount': safe_redemption_amount, 'name': safe_ev_model, 'description': 'Selected Model'})
        
        # Safe date formatting
        ev_expiry_obj = getattr(coupon, 'ev_expiry_date', None)
        safe_ev_expiry = ev_expiry_obj.strftime('%B %d, %Y') if ev_expiry_obj and hasattr(ev_expiry_obj, 'strftime') else 'Not set'
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EV Redemption Request - Admin Notification</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .request-box {{ background: #fff3cd; border: 2px solid #ffc107; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-code {{ font-size: 24px; font-weight: bold; color: #856404; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .urgent {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; color: #721c24; }}
            .action-buttons {{ text-align: center; margin: 20px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 0 10px; }}
            .approve {{ background: #28a745; }}
            .reject {{ background: #dc3545; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #ffc107; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚗 EV Redemption Request</h1>
                <h2>Admin Action Required</h2>
            </div>
            <div class="content">
                <p>A user has submitted an EV redemption request that requires your approval.</p>
                
                <div class="request-box">
                    <h3 style="margin-top: 0; color: #856404;">⚠️ New EV Redemption Request</h3>
                    <div class="coupon-code">{safe_coupon_code}</div>
                    <p style="margin: 5px 0; color: #856404; font-size: 16px;">₹{safe_redemption_amount:,.0f} for {model_info['name']}</p>
                    <span class="badge">PENDING APPROVAL</span>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Request Details</th>
                        <th>Information</th>
                    </tr>
                    <tr>
                        <td>User</td>
                        <td><strong>{safe_user_name} ({safe_user_id})</strong></td>
                    </tr>
                    <tr>
                        <td>Email</td>
                        <td><strong>{safe_user_email}</strong></td>
                    </tr>
                    <tr>
                        <td>Coupon Code</td>
                        <td><strong>{safe_coupon_code}</strong></td>
                    </tr>
                    <tr>
                        <td>Original Value</td>
                        <td><strong>₹{safe_coupon_value:,.0f}</strong></td>
                    </tr>
                    <tr>
                        <td>EV Model Selected</td>
                        <td><strong>{model_info['name']}</strong></td>
                    </tr>
                    <tr>
                        <td>Model Description</td>
                        <td><strong>{model_info['description']}</strong></td>
                    </tr>
                    <tr>
                        <td>Redemption Amount</td>
                        <td><strong>₹{safe_redemption_amount:,.0f}</strong></td>
                    </tr>
                    <tr>
                        <td>Current Status</td>
                        <td><strong>{safe_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Admin Claim Status</td>
                        <td><strong>{safe_admin_status}</strong></td>
                    </tr>
                    <tr>
                        <td>EV Expiry Date</td>
                        <td><strong>{safe_ev_expiry}</strong></td>
                    </tr>
                </table>
                
                <div class="urgent">
                    <h4 style="margin-top: 0;">🚨 Admin Action Required</h4>
                    <p><strong>This EV redemption request requires your immediate review and approval.</strong></p>
                    <ul>
                        <li>Review the user's eligibility and coupon validity</li>
                        <li>Verify the selected EV model and redemption amount</li>
                        <li>Check coupon expiry dates and usage status</li>
                        <li>Approve or reject with detailed admin notes</li>
                    </ul>
                </div>
                
                <div class="action-buttons">
                    <a href="/admin/coupon-approvals" class="button approve">✅ Review & Approve</a>
                    <a href="/admin/coupon-approvals" class="button reject">❌ Review & Reject</a>
                    <a href="/admin/coupon-details/{safe_coupon_code}" class="button">📊 View Full Details</a>
                </div>
                
                <p><strong>EV Redemption Guidelines:</strong></p>
                <ul>
                    <li><strong>LFP Models:</strong> ₹15,000 redemption value</li>
                    <li><strong>Graphene Models:</strong> ₹7,500 redemption value</li>
                    <li><strong>Verification Required:</strong> Check user's eligibility and coupon status</li>
                    <li><strong>Documentation:</strong> Ensure all required documentation is provided</li>
                </ul>
                
                <p>Please process this request within 24 hours to maintain service quality standards.</p>
                
                <p>Best regards,<br>EV Reference Program System</p>
            </div>
            <div class="footer">
                <p>This is an automated admin notification from the Enhanced Coupon System.</p>
                <p>© 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - EV Redemption Request (Admin Notification)
    
    A user has submitted an EV redemption request that requires your approval.
    
    REQUEST DETAILS:
    ===============
    User: {safe_user_name} ({safe_user_id})
    Email: {safe_user_email}
    Coupon Code: {safe_coupon_code}
    Original Value: ₹{safe_coupon_value:,.0f}
    EV Model Selected: {model_info['name']}
    Model Description: {model_info['description']}
    Redemption Amount: ₹{safe_redemption_amount:,.0f}
    Current Status: {safe_status}
    Admin Claim Status: {safe_admin_status}
    EV Expiry Date: {safe_ev_expiry}
    
    ADMIN ACTION REQUIRED:
    =====================
    This EV redemption request requires your immediate review and approval.
    
    Review Tasks:
    * Review the user's eligibility and coupon validity
    * Verify the selected EV model and redemption amount
    * Check coupon expiry dates and usage status
    * Approve or reject with detailed admin notes
    
    EV REDEMPTION GUIDELINES:
    ========================
    * LFP Models: ₹15,000 redemption value
    * Graphene Models: ₹7,500 redemption value
    * Verification Required: Check user's eligibility and coupon status
    * Documentation: Ensure all required documentation is provided
    
    Please process this request within 24 hours to maintain service quality standards.
    
    Best regards,
    EV Reference Program System
    
    ---
    This is an automated admin notification from the Enhanced Coupon System.
    """
    
        # Safe subject construction
        safe_subject = f"EV Redemption Request - {safe_user_name} ({safe_user_id}) - Code: {safe_coupon_code}"
        
        # Send email with protected content
        result = send_email(
            to=safe_admin_email,
            subject=safe_subject,
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send EV redemption request email to {safe_admin_email}: {str(e)}")
        return False


def send_training_redemption_request_email(admin_email: str, coupon, user, course_details: str, course_fee: float) -> bool:
    """
    Send admin notification for Training redemption request
    
    Args:
        admin_email: Admin's email address
        coupon: EnhancedCoupon object
        user: User object who made the request
        course_details: Details of selected training course
        course_fee: Total course fee for 20% calculation
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_admin_email = admin_email or "admin@evprogram.com"
        safe_coupon_code = getattr(coupon, 'coupon_code', None) or "UNKNOWN"
        safe_coupon_value = float(getattr(coupon, 'coupon_value', None) or 0)
        safe_redeemed_amount = float(getattr(coupon, 'redeemed_amount', None) or 0)
        safe_status = (getattr(coupon, 'status', None) or 'pending').title()
        safe_admin_status = (getattr(coupon, 'admin_claim_status', None) or 'pending').title()
        
        # Safe user field access
        safe_user_name = getattr(user, 'name', None) or "Unknown User"
        safe_user_id = getattr(user, 'id', None) or "UNKNOWN"
        safe_user_email = getattr(user, 'email', None) or "unknown@email.com"
        
        # Safe course details and fee
        safe_course_details = str(course_details or "Training Course")
        safe_course_fee = float(course_fee or 0)
        
        # SAFE 20% CALCULATION WITH DEFENSIVE PROGRAMMING
        safe_cashback_amount = safe_course_fee * 0.20
        safe_remaining_value = safe_coupon_value - safe_redeemed_amount
        safe_effective_usage = min(safe_cashback_amount, safe_remaining_value) if safe_remaining_value > 0 else 0
        
        # Safe date formatting
        training_expiry_obj = getattr(coupon, 'training_expiry_date', None)
        safe_training_expiry = training_expiry_obj.strftime('%B %d, %Y') if training_expiry_obj and hasattr(training_expiry_obj, 'strftime') else 'Not set'
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Training Redemption Request - Admin Notification</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .request-box {{ background: #e8f4fd; border: 2px solid #007bff; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-code {{ font-size: 24px; font-weight: bold; color: #0056b3; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .calculation {{ background: #d1ecf1; border: 1px solid #bee5eb; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .urgent {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; color: #721c24; }}
            .action-buttons {{ text-align: center; margin: 20px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 0 10px; }}
            .approve {{ background: #28a745; }}
            .reject {{ background: #dc3545; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Training Redemption Request</h1>
                <h2>Admin Action Required</h2>
            </div>
            <div class="content">
                <p>A user has submitted a Training redemption request that requires your approval.</p>
                
                <div class="request-box">
                    <h3 style="margin-top: 0; color: #0056b3;">📚 New Training Redemption Request</h3>
                    <div class="coupon-code">{safe_coupon_code}</div>
                    <p style="margin: 5px 0; color: #0056b3; font-size: 16px;">20% Cashback on ₹{safe_course_fee:,.0f} Course</p>
                    <span class="badge">PENDING APPROVAL</span>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Request Details</th>
                        <th>Information</th>
                    </tr>
                    <tr>
                        <td>User</td>
                        <td><strong>{safe_user_name} ({safe_user_id})</strong></td>
                    </tr>
                    <tr>
                        <td>Email</td>
                        <td><strong>{safe_user_email}</strong></td>
                    </tr>
                    <tr>
                        <td>Coupon Code</td>
                        <td><strong>{safe_coupon_code}</strong></td>
                    </tr>
                    <tr>
                        <td>Original Coupon Value</td>
                        <td><strong>₹{safe_coupon_value:,.0f}</strong></td>
                    </tr>
                    <tr>
                        <td>Already Redeemed</td>
                        <td><strong>₹{safe_redeemed_amount:,.0f}</strong></td>
                    </tr>
                    <tr>
                        <td>Remaining Value</td>
                        <td><strong>₹{safe_remaining_value:,.0f}</strong></td>
                    </tr>
                    <tr>
                        <td>Course Details</td>
                        <td><strong>{safe_course_details}</strong></td>
                    </tr>
                    <tr>
                        <td>Total Course Fee</td>
                        <td><strong>₹{safe_course_fee:,.0f}</strong></td>
                    </tr>
                    <tr>
                        <td>Current Status</td>
                        <td><strong>{safe_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Admin Claim Status</td>
                        <td><strong>{safe_admin_status}</strong></td>
                    </tr>
                    <tr>
                        <td>Training Expiry Date</td>
                        <td><strong>{safe_training_expiry}</strong></td>
                    </tr>
                </table>
                
                <div class="calculation">
                    <h4 style="margin-top: 0; color: #0c5460;">💰 Training Redemption Calculation</h4>
                    <p><strong>Course Fee:</strong> ₹{safe_course_fee:,.0f}</p>
                    <p><strong>20% Cashback:</strong> ₹{safe_cashback_amount:,.0f}</p>
                    <p><strong>Available from Coupon:</strong> ₹{safe_remaining_value:,.0f}</p>
                    <p><strong>Effective Usage:</strong> ₹{safe_effective_usage:,.0f} (minimum of cashback and available value)</p>
                    <p><strong>Value After Redemption:</strong> ₹{max(0, safe_remaining_value - safe_effective_usage):,.0f}</p>
                </div>
                
                <div class="urgent">
                    <h4 style="margin-top: 0;">🚨 Admin Action Required</h4>
                    <p><strong>This Training redemption request requires your immediate review and approval.</strong></p>
                    <ul>
                        <li>Verify course details and training provider</li>
                        <li>Confirm 20% cashback calculation accuracy</li>
                        <li>Check remaining coupon value and validity</li>
                        <li>Ensure user eligibility for training redemption</li>
                        <li>Approve or reject with detailed admin notes</li>
                    </ul>
                </div>
                
                <div class="action-buttons">
                    <a href="/admin/coupon-approvals" class="button approve">✅ Review & Approve</a>
                    <a href="/admin/coupon-approvals" class="button reject">❌ Review & Reject</a>
                    <a href="/admin/coupon-details/{safe_coupon_code}" class="button">📊 View Full Details</a>
                </div>
                
                <p><strong>Training Redemption Guidelines:</strong></p>
                <ul>
                    <li><strong>Cashback Rate:</strong> 20% of course fees</li>
                    <li><strong>Value Preservation:</strong> Remaining coupon value stays available</li>
                    <li><strong>Multiple Usage:</strong> Can be used for multiple courses until value depleted</li>
                    <li><strong>Course Verification:</strong> Ensure courses are from approved training providers</li>
                </ul>
                
                <p>Please process this request within 24 hours to maintain service quality standards.</p>
                
                <p>Best regards,<br>EV Reference Program System</p>
            </div>
            <div class="footer">
                <p>This is an automated admin notification from the Enhanced Coupon System.</p>
                <p>© 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - Training Redemption Request (Admin Notification)
    
    A user has submitted a Training redemption request that requires your approval.
    
    REQUEST DETAILS:
    ===============
    User: {safe_user_name} ({safe_user_id})
    Email: {safe_user_email}
    Coupon Code: {safe_coupon_code}
    Original Coupon Value: ₹{safe_coupon_value:,.0f}
    Already Redeemed: ₹{safe_redeemed_amount:,.0f}
    Remaining Value: ₹{safe_remaining_value:,.0f}
    Course Details: {safe_course_details}
    Total Course Fee: ₹{safe_course_fee:,.0f}
    Current Status: {safe_status}
    Admin Claim Status: {safe_admin_status}
    Training Expiry Date: {safe_training_expiry}
    
    TRAINING REDEMPTION CALCULATION:
    ===============================
    Course Fee: ₹{safe_course_fee:,.0f}
    20% Cashback: ₹{safe_cashback_amount:,.0f}
    Available from Coupon: ₹{safe_remaining_value:,.0f}
    Effective Usage: ₹{safe_effective_usage:,.0f} (minimum of cashback and available value)
    Value After Redemption: ₹{max(0, safe_remaining_value - safe_effective_usage):,.0f}
    
    ADMIN ACTION REQUIRED:
    =====================
    This Training redemption request requires your immediate review and approval.
    
    Review Tasks:
    * Verify course details and training provider
    * Confirm 20% cashback calculation accuracy
    * Check remaining coupon value and validity
    * Ensure user eligibility for training redemption
    * Approve or reject with detailed admin notes
    
    TRAINING REDEMPTION GUIDELINES:
    ==============================
    * Cashback Rate: 20% of course fees
    * Value Preservation: Remaining coupon value stays available
    * Multiple Usage: Can be used for multiple courses until value depleted
    * Course Verification: Ensure courses are from approved training providers
    
    Please process this request within 24 hours to maintain service quality standards.
    
    Best regards,
    EV Reference Program System
    
    ---
    This is an automated admin notification from the Enhanced Coupon System.
    """
    
        # Safe subject construction
        safe_subject = f"Training Redemption Request - {safe_user_name} ({safe_user_id}) - Code: {safe_coupon_code}"
        
        # Send email with protected content
        result = send_email(
            to=safe_admin_email,
            subject=safe_subject,
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send training redemption request email to {safe_admin_email}: {str(e)}")
        return False


def send_redemption_approved_email(email: str, coupon, user_name: str, redemption_type: str, redemption_details: dict, approved_by: str) -> bool:
    """
    Send approval notification when redemption is approved
    
    Args:
        email: User's email address
        coupon: EnhancedCoupon object
        user_name: User's name
        redemption_type: 'EV' or 'Training'
        redemption_details: Dict with redemption-specific details
        approved_by: Name of admin who approved
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_email = email or "user@unknown.com"
        safe_coupon_code = getattr(coupon, 'coupon_code', None) or "UNKNOWN"
        safe_user_name = str(user_name or "Valued Customer")
        safe_redemption_type = str(redemption_type or "Unknown").title()
        safe_approved_by = str(approved_by or "Admin Team")
        
        # Safe dictionary access for redemption details
        safe_details = redemption_details or {}
        
        # Safe date formatting for approval date
        approval_date_obj = getattr(coupon, 'approval_date', None)
        safe_approval_date = approval_date_obj.strftime('%B %d, %Y at %I:%M %p') if approval_date_obj and hasattr(approval_date_obj, 'strftime') else 'Today'
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        # Content varies by redemption type - safe type checking
        if safe_redemption_type.upper() == 'EV':
            type_icon = "🚗"
            type_title = "EV Purchase Redemption Approved!"
            safe_model_name = str(safe_details.get('model_name', 'selected model'))
            safe_amount = float(safe_details.get('amount', 0))
            type_message = f"Great news! Your EV redemption request has been approved for {safe_model_name} worth ₹{safe_amount:,.0f}."
            next_steps = [
                "Contact your preferred EV dealer and mention your approved coupon",
                f"Present your coupon code: {safe_coupon_code}",
                "Show this approval email to complete the redemption process",
                "Vehicle purchase must be completed within 30 days of approval",
                "Follow up with our team after successful vehicle purchase"
            ]
            specific_details = f"""
        <tr><td>EV Model</td><td><strong>{safe_model_name}</strong></td></tr>
        <tr><td>Redemption Amount</td><td><strong>₹{safe_amount:,.0f}</strong></td></tr>
        <tr><td>Vehicle Type</td><td><strong>{str(safe_details.get('description', 'Electric Vehicle'))}</strong></td></tr>
        """
        else:
            type_icon = "🎓"
            type_title = "Training Redemption Approved!"
            safe_course_name = str(safe_details.get('course_name', 'selected course'))
            type_message = f"Excellent! Your training redemption request has been approved for {safe_course_name} with 20% cashback."
            next_steps = [
                "Enroll in your approved training course",
                "Pay the course fee and obtain payment receipt",
                "Submit receipt through your dashboard for cashback processing",
                "Cashback will be credited to your coupon within 7 days",
                "You can use remaining coupon value for future courses"
            ]
            safe_course_fee = float(safe_details.get('course_fee', 0))
            safe_cashback_amount = float(safe_details.get('cashback_amount', 0))
            safe_provider = str(safe_details.get('provider', 'Approved Provider'))
            specific_details = f"""
        <tr><td>Course Name</td><td><strong>{safe_course_name}</strong></td></tr>
        <tr><td>Course Fee</td><td><strong>₹{safe_course_fee:,.0f}</strong></td></tr>
        <tr><td>20% Cashback</td><td><strong>₹{safe_cashback_amount:,.0f}</strong></td></tr>
        <tr><td>Training Provider</td><td><strong>{safe_provider}</strong></td></tr>
        """
    
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{safe_redemption_type} Redemption Approved - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .approval-box {{ background: #d4edda; border: 2px solid #28a745; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-code {{ font-size: 24px; font-weight: bold; color: #155724; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .next-steps {{ background: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{type_icon} {type_title}</h1>
                <h2>Your Request Has Been Approved</h2>
            </div>
            <div class="content">
                <p>Dear {safe_user_name},</p>
                <p>{type_message}</p>
                
                <div class="approval-box">
                    <h3 style="margin-top: 0; color: #155724;">✅ APPROVED</h3>
                    <div class="coupon-code">{safe_coupon_code}</div>
                    <p style="margin: 5px 0; color: #155724; font-size: 16px;">Approved by: <strong>{safe_approved_by}</strong></p>
                    <span class="badge">REDEMPTION APPROVED</span>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Approval Details</th>
                        <th>Information</th>
                    </tr>
                    <tr>
                        <td>Coupon Code</td>
                        <td><strong>{safe_coupon_code}</strong></td>
                    </tr>
                    <tr>
                        <td>Redemption Type</td>
                        <td><strong>{safe_redemption_type}</strong></td>
                    </tr>
                    {specific_details}
                    <tr>
                        <td>Approved By</td>
                        <td><strong>{safe_approved_by}</strong></td>
                    </tr>
                    <tr>
                        <td>Approval Date</td>
                        <td><strong>{safe_approval_date}</strong></td>
                    </tr>
                </table>
                
                <div class="next-steps">
                    <h3 style="margin-top: 0; color: #495057;">🚀 Next Steps:</h3>
                    <ol>
                        {"".join(f"<li>{step}</li>" for step in next_steps)}
                    </ol>
                    <p style="text-align: center;"><a href="/dashboard" class="button">📱 Go to Dashboard</a></p>
                </div>
                
                <p><strong>Important Notes:</strong></p>
                <ul>
                    <li>This approval is valid for 30 days from the approval date</li>
                    <li>Keep this email as proof of approved redemption</li>
                    <li>Contact support if you need assistance with the redemption process</li>
                    <li>Follow all terms and conditions for successful redemption</li>
                </ul>
                
                <p>Congratulations on your approved redemption! We're here to support you through the process.</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This redemption was approved by {safe_approved_by} from our admin team.</p>
                <p>© 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - {safe_redemption_type} Redemption Approved
    
    Dear {safe_user_name},
    
    {type_message}
    
    APPROVAL DETAILS:
    ================
    Coupon Code: {safe_coupon_code}
    Redemption Type: {safe_redemption_type}
    Approved By: {safe_approved_by}
    Approval Date: {safe_approval_date}
    
    NEXT STEPS:
    ==========
    {chr(10).join(f"{i+1}. {step}" for i, step in enumerate(next_steps))}
    
    IMPORTANT NOTES:
    ===============
    * This approval is valid for 30 days from the approval date
    * Keep this email as proof of approved redemption
    * Contact support if you need assistance with the redemption process
    * Follow all terms and conditions for successful redemption
    
    Congratulations on your approved redemption! We're here to support you through the process.
    
    Best regards,
    EV Reference Program Team
    
    ---
    This redemption was approved by {safe_approved_by} from our admin team.
    """
    
        # Safe subject construction
        safe_subject = f"{safe_redemption_type} Redemption Approved - Code: {safe_coupon_code}"
        
        # Send email with protected content
        result = send_email(
            to=safe_email,
            subject=safe_subject,
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send redemption approved email to {safe_email}: {str(e)}")
        return False


def send_redemption_rejected_email(email: str, coupon, user_name: str, redemption_type: str, rejection_reason: str, admin_notes: str, rejected_by: str) -> bool:
    """
    Send rejection notification when redemption is rejected
    
    Args:
        email: User's email address
        coupon: EnhancedCoupon object
        user_name: User's name
        redemption_type: 'EV' or 'Training'
        rejection_reason: Reason for rejection
        admin_notes: Detailed admin notes
        rejected_by: Name of admin who rejected
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # DEFENSIVE PROGRAMMING - Safe field access with None guards
        safe_email = email or "user@unknown.com"
        safe_coupon_code = getattr(coupon, 'coupon_code', None) or "UNKNOWN"
        safe_user_name = str(user_name or "Valued Customer")
        safe_redemption_type = str(redemption_type or "Unknown").title()
        safe_rejection_reason = str(rejection_reason or "Requires additional review")
        safe_admin_notes = str(admin_notes or "Please resubmit with updated information as needed.")
        safe_rejected_by = str(rejected_by or "Admin Team")
        
        # Content varies by redemption type - safe type checking
        type_icon = "🚗" if safe_redemption_type.upper() == 'EV' else "🎓"
        
        # ALL TEMPLATE CONSTRUCTION INSIDE TRY/EXCEPT
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{safe_redemption_type} Redemption Status - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .rejection-box {{ background: #f8d7da; border: 2px solid #dc3545; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-code {{ font-size: 24px; font-weight: bold; color: #721c24; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .notes-box {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .next-steps {{ background: #d1ecf1; border: 1px solid #bee5eb; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{type_icon} {safe_redemption_type} Redemption Update</h1>
                <h2>Request Requires Attention</h2>
            </div>
            <div class="content">
                <p>Dear {safe_user_name},</p>
                <p>We've reviewed your {safe_redemption_type.lower()} redemption request for coupon {safe_coupon_code}. Unfortunately, we need to address some concerns before we can proceed with approval.</p>
                
                <div class="rejection-box">
                    <h3 style="margin-top: 0; color: #721c24;">⚠️ REQUIRES REVISION</h3>
                    <div class="coupon-code">{safe_coupon_code}</div>
                    <p style="margin: 5px 0; color: #721c24; font-size: 16px;">Reviewed by: <strong>{safe_rejected_by}</strong></p>
                    <span class="badge">NEEDS REVISION</span>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Review Details</th>
                        <th>Information</th>
                    </tr>
                    <tr>
                        <td>Coupon Code</td>
                        <td><strong>{safe_coupon_code}</strong></td>
                    </tr>
                    <tr>
                        <td>Redemption Type</td>
                        <td><strong>{safe_redemption_type}</strong></td>
                    </tr>
                    <tr>
                        <td>Review Reason</td>
                        <td><strong>{safe_rejection_reason}</strong></td>
                    </tr>
                    <tr>
                        <td>Reviewed By</td>
                        <td><strong>{safe_rejected_by}</strong></td>
                    </tr>
                    <tr>
                        <td>Review Date</td>
                        <td><strong>Today</strong></td>
                    </tr>
                </table>
                
                <div class="notes-box">
                    <h4 style="margin-top: 0; color: #856404;">📝 Admin Notes & Guidance:</h4>
                    <p>{safe_admin_notes}</p>
                </div>
                
                <div class="next-steps">
                    <h3 style="margin-top: 0; color: #0c5460;">🔄 What You Can Do:</h3>
                    <ol>
                        <li><strong>Review the feedback:</strong> Carefully read the admin notes above</li>
                        <li><strong>Gather required information:</strong> Address the specific concerns mentioned</li>
                        <li><strong>Resubmit your request:</strong> Update your redemption request with the necessary corrections</li>
                        <li><strong>Contact support:</strong> If you need clarification, reach out to our support team</li>
                        <li><strong>Alternative options:</strong> Consider other redemption types if applicable</li>
                    </ol>
                    <p style="text-align: center;"><a href="/dashboard/redemption-request" class="button">🔄 Resubmit Request</a></p>
                </div>
                
                <p><strong>Don't worry!</strong> This isn't a final rejection - it's just a request for additional information or corrections. Many requests are approved after resubmission with the requested details.</p>
                
                <p><strong>Alternative Options:</strong></p>
                <ul>
                    <li>If this was an EV redemption, you could consider training redemption instead</li>
                    <li>If this was training redemption, you might explore different course options</li>
                    <li>Your coupon remains valid and can be used for other approved redemptions</li>
                    <li>Contact our support team for personalized guidance</li>
                </ul>
                
                <p>We appreciate your patience and look forward to helping you successfully redeem your coupon.</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This request was reviewed by {safe_rejected_by} from our admin team.</p>
                <p>© 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        # Safe text content construction with protected field access
        text_content = f"""
    EV Reference Program - {safe_redemption_type} Redemption Update
    
    Dear {safe_user_name},
    
    We've reviewed your {safe_redemption_type.lower()} redemption request for coupon {safe_coupon_code}. Unfortunately, we need to address some concerns before we can proceed with approval.
    
    REVIEW DETAILS:
    ==============
    Coupon Code: {safe_coupon_code}
    Redemption Type: {safe_redemption_type}
    Review Reason: {safe_rejection_reason}
    Reviewed By: {safe_rejected_by}
    Review Date: Today
    
    ADMIN NOTES & GUIDANCE:
    ======================
    {safe_admin_notes}
    
    WHAT YOU CAN DO:
    ===============
    1. Review the feedback: Carefully read the admin notes above
    2. Gather required information: Address the specific concerns mentioned
    3. Resubmit your request: Update your redemption request with the necessary corrections
    4. Contact support: If you need clarification, reach out to our support team
    5. Alternative options: Consider other redemption types if applicable
    
    Don't worry! This isn't a final rejection - it's just a request for additional information or corrections. Many requests are approved after resubmission with the requested details.
    
    ALTERNATIVE OPTIONS:
    ===================
    * If this was an EV redemption, you could consider training redemption instead
    * If this was training redemption, you might explore different course options
    * Your coupon remains valid and can be used for other approved redemptions
    * Contact our support team for personalized guidance
    
    We appreciate your patience and look forward to helping you successfully redeem your coupon.
    
    Best regards,
    EV Reference Program Team
    
    ---
    This request was reviewed by {safe_rejected_by} from our admin team.
    """
    
        # Safe subject construction
        safe_subject = f"{safe_redemption_type} Redemption Requires Revision - Code: {safe_coupon_code}"
        
        # Send email with protected content
        result = send_email(
            to=safe_email,
            subject=safe_subject,
            html=html_content,
            text=text_content
        )
        return True
    
    except Exception as e:
        print(f"Failed to send redemption rejected email to {safe_email}: {str(e)}")
        return False


def test_email_service() -> dict:
    """
    Test email service authentication and functionality
    
    Returns:
        dict: Test results with authentication status and error details if any
    """
    test_results = {
        'auth_token_available': False,
        'auth_token_format': 'unknown',
        'email_service_accessible': False,
        'test_successful': False,
        'error_message': None,
        'response_data': None
    }
    
    try:
        # Test authentication token
        auth_token = get_auth_token()
        test_results['auth_token_available'] = True
        
        if auth_token.startswith('Bearer ') and 'repl' in auth_token.lower():
            test_results['auth_token_format'] = 'bearer_repl_identity'
        elif auth_token.startswith('Bearer ') and 'depl' in auth_token.lower():
            test_results['auth_token_format'] = 'bearer_web_repl_renewal'
        elif auth_token.startswith('Bearer '):
            test_results['auth_token_format'] = 'bearer_token'
        else:
            test_results['auth_token_format'] = 'unknown_format'
        
        # Test email service with a simple test email (to a test address)
        # Using a non-existent test email to avoid sending real emails
        test_email_data = {
            "to": "test@example.com",
            "subject": "EV Reference Program - Email Service Test",
            "text": "This is a test email to verify the email service authentication is working correctly.",
            "html": """
            <html>
            <body>
                <h2>Email Service Test</h2>
                <p>This is a test email to verify the email service authentication is working correctly.</p>
                <p><strong>Test timestamp:</strong> {}</p>
            </body>
            </html>
            """.format(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
        }
        
        # Make test request (but don't actually send to avoid spam)
        # We'll use a dry-run approach - check if we can authenticate but not send
        response = requests.post(
            "https://connectors.replit.com/api/v2/mailer/send",
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_token,
            },
            json=test_email_data,
            timeout=30
        )
        
        test_results['email_service_accessible'] = True
        test_results['response_data'] = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
        }
        
        if response.ok:
            test_results['test_successful'] = True
            try:
                test_results['response_data']['body'] = response.json()
            except:
                test_results['response_data']['body'] = response.text[:200]
        else:
            # Even if the email fails (e.g., invalid recipient), if we get a proper error response
            # it means authentication worked
            if response.status_code in [400, 422]:  # Bad request or validation error
                test_results['test_successful'] = True  # Auth worked, just invalid email
                test_results['error_message'] = f"Authentication successful, but request invalid (expected for test): HTTP {response.status_code}"
            else:
                test_results['error_message'] = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No response body'}"
        
    except ValueError as e:
        if "No authentication token found" in str(e):
            test_results['error_message'] = str(e)
        else:
            test_results['error_message'] = f"Authentication error: {str(e)}"
    except requests.RequestException as e:
        test_results['error_message'] = f"Request error: {str(e)}"
    except Exception as e:
        test_results['error_message'] = f"Unexpected error: {str(e)}"
    
    return test_results


def print_email_test_results():
    """
    Run email service test and print formatted results
    """
    print("🧪 Testing Email Service Authentication and Connectivity...")
    print("=" * 60)
    
    results = test_email_service()
    
    # Print authentication status
    print(f"🔐 Authentication Token: {'✅ Available' if results['auth_token_available'] else '❌ Missing'}")
    if results['auth_token_available']:
        print(f"   Token Format: {results['auth_token_format']}")
    
    # Print service accessibility
    print(f"🌐 Email Service Access: {'✅ Reachable' if results['email_service_accessible'] else '❌ Unreachable'}")
    
    # Print test results
    print(f"✅ Overall Test Status: {'✅ PASSED' if results['test_successful'] else '❌ FAILED'}")
    
    if results['error_message']:
        print(f"⚠️  Error Details: {results['error_message']}")
    
    if results['response_data']:
        print(f"📊 Response Status: {results['response_data']['status_code']}")
        if results['response_data'].get('body'):
            print(f"📄 Response Body: {str(results['response_data']['body'])[:200]}")
    
    print("=" * 60)
    
    if results['test_successful']:
        print("🎉 Email service authentication is working correctly!")
        print("   Ready to send coupon receipt emails.")
    else:
        print("🚨 Email service needs attention before it can send emails.")
    
    return results


def send_coupon_expiry_notification(email: str, coupon, user_name: str, notification_type: str) -> bool:
    """
    Send coupon expiry notification for conversion/expiry warnings
    
    Args:
        email: User's email address
        coupon: EVPurchaseCoupon object
        user_name: User's name
        notification_type: '30_days', '7_days', 'expired', 'conversion_warning'
        
    Returns:
        True if email sent successfully, False otherwise
    """
    
    # Determine notification content based on type
    if notification_type == '30_days':
        subject_prefix = "⚠️ 30 Days Notice"
        alert_title = "🕐 30 Days Until Expiry"
        alert_message = "Your EV Purchase Coupon will expire in 30 days."
        urgency_class = "warning"
        urgency_color = "#856404"
        action_message = "You still have a full month to use your coupon for EV purchases."
    elif notification_type == '7_days':
        subject_prefix = "🚨 7 Days Notice"
        alert_title = "⏰ 7 Days Until Expiry"
        alert_message = "URGENT: Your EV Purchase Coupon expires in just 7 days!"
        urgency_class = "danger"
        urgency_color = "#721c24"
        action_message = "This is your final week to use this coupon for EV purchases."
    elif notification_type == 'expired':
        subject_prefix = "🔴 Expired"
        alert_title = "⛔ Coupon Has Expired"
        alert_message = "Your EV Purchase Coupon has expired and is no longer valid for EV purchases."
        urgency_class = "expired"
        urgency_color = "#6c757d"
        action_message = "This coupon can no longer be used for EV purchases."
    else:  # conversion_warning
        subject_prefix = "🔄 Conversion Notice"
        alert_title = "🔄 Auto-Conversion to Training Coupon"
        alert_message = "Your EV Purchase Coupon will automatically convert to a Training Coupon soon."
        urgency_class = "info"
        urgency_color = "#0c5460"
        action_message = f"After {coupon.auto_convert_after_months} months, unused EV coupons convert to training coupons."
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Coupon Expiry Notice - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .alert-box {{ padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .warning {{ background: #fff3cd; border: 2px solid #ffc107; color: #856404; }}
            .danger {{ background: #f8d7da; border: 2px solid #dc3545; color: #721c24; }}
            .expired {{ background: #f8f9fa; border: 2px solid #6c757d; color: #6c757d; }}
            .info {{ background: #d1ecf1; border: 2px solid #17a2b8; color: #0c5460; }}
            .coupon-pin {{ font-size: 24px; font-weight: bold; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .action-steps {{ background: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            .alternatives {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #17a2b8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{alert_title}</h1>
                <h2>Coupon PIN: {coupon.coupon_pin}</h2>
            </div>
            <div class="content">
                <p>Dear {user_name},</p>
                <p>This is an important notification about your EV Purchase Coupon.</p>
                
                <div class="alert-box {urgency_class}">
                    <h3 style="margin-top: 0; color: {urgency_color};">{alert_message}</h3>
                    <div class="coupon-pin" style="color: {urgency_color};">{coupon.coupon_pin}</div>
                    <p style="margin: 5px 0; font-size: 16px;">₹{coupon.coupon_value:,.2f} Value</p>
                    <p style="margin: 10px 0; font-size: 14px;">{action_message}</p>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Coupon Information</th>
                        <th>Details</th>
                    </tr>
                    <tr>
                        <td>Coupon PIN</td>
                        <td><strong>{coupon.coupon_pin}</strong></td>
                    </tr>
                    <tr>
                        <td>Coupon Value</td>
                        <td><strong>₹{coupon.coupon_value:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>Current Status</td>
                        <td><strong>{coupon.status}</strong></td>
                    </tr>
                    <tr>
                        <td>Generated Date</td>
                        <td><strong>{coupon.generated_date.strftime('%B %d, %Y')}</strong></td>
                    </tr>
                    <tr>
                        <td>EV Validity Expires</td>
                        <td><strong>{coupon.get_ev_expiry_date().strftime('%B %d, %Y') if coupon.get_ev_expiry_date() else 'N/A'}</strong></td>
                    </tr>
                    <tr>
                        <td>Auto-Convert Date</td>
                        <td><strong>{coupon.get_conversion_date().strftime('%B %d, %Y') if coupon.get_conversion_date() else 'N/A'}</strong></td>
                    </tr>
                </table>
                
                {f'''
                <div class="action-steps">
                    <h3 style="margin-top: 0; color: #495057;">🚗 Immediate Action Required:</h3>
                    <ol>
                        <li><strong>Contact EV Dealers:</strong> Reach out to authorized electric vehicle dealers</li>
                        <li><strong>Schedule Test Drives:</strong> Test drive your preferred EV models</li>
                        <li><strong>Prepare Documentation:</strong> Gather required documents for purchase</li>
                        <li><strong>Use Your PIN:</strong> Present {coupon.coupon_pin} during purchase</li>
                        <li><strong>Enjoy Discount:</strong> Get {coupon.discount_percentage}% discount on eligible EVs</li>
                    </ol>
                    <p style="text-align: center;"><a href="#" class="button">🏪 Find EV Dealers</a></p>
                </div>
                ''' if notification_type in ['30_days', '7_days'] else ''}
                
                {f'''
                <div class="alternatives">
                    <h3 style="margin-top: 0; color: #495057;">🎓 Alternative Options:</h3>
                    <p>Even though your EV coupon has expired, you still have options:</p>
                    <ul>
                        <li><strong>Training Conversion:</strong> Your coupon will automatically convert to a training coupon</li>
                        <li><strong>Skill Development:</strong> Use for professional courses and certifications</li>
                        <li><strong>Cashback Benefit:</strong> Enjoy {coupon.training_cashback_percentage}% cashback on training programs</li>
                        <li><strong>Extended Validity:</strong> Training coupons have {coupon.training_validity_months} months validity</li>
                    </ul>
                </div>
                ''' if notification_type == 'expired' else ''}
                
                <p>If you have any questions about your coupon status or need assistance with redemption, please contact our support team.</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>This is an automated notification. Monitor your dashboard for real-time coupon status.</p>
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    EV Reference Program - Coupon Expiry Notice
    
    Dear {user_name},
    
    {alert_message}
    
    COUPON DETAILS:
    ===============
    Coupon PIN: {coupon.coupon_pin}
    Coupon Value: ₹{coupon.coupon_value:,.2f}
    Current Status: {coupon.status}
    Generated Date: {coupon.generated_date.strftime('%B %d, %Y')}
    EV Validity Expires: {coupon.get_ev_expiry_date().strftime('%B %d, %Y') if coupon.get_ev_expiry_date() else 'N/A'}
    Auto-Convert Date: {coupon.get_conversion_date().strftime('%B %d, %Y') if coupon.get_conversion_date() else 'N/A'}
    
    {action_message}
    
    {'IMMEDIATE ACTION REQUIRED:' if notification_type in ['30_days', '7_days'] else ''}
    {'Contact EV dealers, schedule test drives, and use your PIN ' + coupon.coupon_pin + ' for purchase.' if notification_type in ['30_days', '7_days'] else ''}
    
    {'ALTERNATIVE OPTIONS:' if notification_type == 'expired' else ''}
    {'Your coupon will convert to a training coupon with ' + str(coupon.training_cashback_percentage) + '% cashback benefit.' if notification_type == 'expired' else ''}
    
    If you have any questions about your coupon status or need assistance with redemption, please contact our support team.
    
    Best regards,
    EV Reference Program Team
    
    ---
    This is an automated notification. Monitor your dashboard for real-time coupon status.
    """
    
    try:
        result = send_email(
            to=email,
            subject=f"{subject_prefix}: EV Coupon {coupon.coupon_pin} - ₹{coupon.coupon_value:,.0f}",
            html=html_content,
            text=text_content
        )
        return True
    except Exception as e:
        print(f"Failed to send coupon expiry notification to {email}: {str(e)}")
        return False


def send_coupon_conversion_notification(email: str, coupon, user_name: str) -> bool:
    """
    Send notification for automatic EV-to-training conversion
    
    Args:
        email: User's email address
        coupon: EVPurchaseCoupon object (now converted to training)
        user_name: User's name
        
    Returns:
        True if email sent successfully, False otherwise
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Coupon Converted to Training - EV Reference Program</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: white; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }}
            .conversion-box {{ background: #d1ecf1; border: 2px solid #17a2b8; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
            .coupon-pin {{ font-size: 28px; font-weight: bold; color: #17a2b8; letter-spacing: 2px; margin: 10px 0; font-family: monospace; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
            .info-table th, .info-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .info-table th {{ background: #f8f9fa; font-weight: bold; color: #495057; }}
            .benefits {{ background: #e8f4fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .courses {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .button {{ display: inline-block; background: #17a2b8; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; background: #17a2b8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔄 Coupon Automatically Converted!</h1>
                <h2>Now Valid for Training Programs</h2>
            </div>
            <div class="content">
                <p>Dear {user_name},</p>
                <p>Your EV Purchase Coupon has been automatically converted to a Training Coupon as per our program guidelines. You can now use it for professional training and skill development programs.</p>
                
                <div class="conversion-box">
                    <h3 style="margin-top: 0; color: #0c5460;">✅ Successfully Converted to Training Coupon</h3>
                    <div class="coupon-pin">{coupon.coupon_pin}</div>
                    <p style="margin: 5px 0; color: #0c5460; font-size: 16px;">₹{coupon.coupon_value:,.2f} Value • <span class="badge">TRAINING COUPON</span></p>
                    <p style="margin: 10px 0; color: #0c5460; font-size: 14px;">Converted on: {coupon.converted_date.strftime('%B %d, %Y') if coupon.converted_date else 'Today'}</p>
                </div>
                
                <table class="info-table">
                    <tr>
                        <th>Updated Coupon Details</th>
                        <th>Information</th>
                    </tr>
                    <tr>
                        <td>Coupon PIN</td>
                        <td><strong>{coupon.coupon_pin}</strong></td>
                    </tr>
                    <tr>
                        <td>Current Type</td>
                        <td><strong>Training Coupon</strong></td>
                    </tr>
                    <tr>
                        <td>Coupon Value</td>
                        <td><strong>₹{coupon.coupon_value:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>Training Validity</td>
                        <td><strong>{coupon.training_validity_months} months from conversion</strong></td>
                    </tr>
                    <tr>
                        <td>Cashback Percentage</td>
                        <td><strong>{coupon.training_cashback_percentage}% on course fees</strong></td>
                    </tr>
                    <tr>
                        <td>Original EV Expiry</td>
                        <td><strong>{coupon.get_ev_expiry_date().strftime('%B %d, %Y') if coupon.get_ev_expiry_date() else 'Expired'}</strong></td>
                    </tr>
                </table>
                
                <div class="benefits">
                    <h3 style="margin-top: 0; color: #495057;">🎓 Training Coupon Benefits:</h3>
                    <ul>
                        <li><strong>Full Value Applicable:</strong> Use the complete ₹{coupon.coupon_value:,.2f} value for training</li>
                        <li><strong>Cashback Rewards:</strong> Get {coupon.training_cashback_percentage}% cashback on course fees</li>
                        <li><strong>Extended Validity:</strong> {coupon.training_validity_months} months to use from conversion date</li>
                        <li><strong>Wide Selection:</strong> Choose from hundreds of professional courses</li>
                        <li><strong>Certification Value:</strong> Earn industry-recognized certifications</li>
                        <li><strong>Career Advancement:</strong> Boost your professional skills and opportunities</li>
                    </ul>
                </div>
                
                <div class="courses">
                    <h3 style="margin-top: 0; color: #495057;">📚 Available Training Categories:</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0;">
                        <div>• Digital Marketing</div>
                        <div>• Web Development</div>
                        <div>• Data Science</div>
                        <div>• Artificial Intelligence</div>
                        <div>• Project Management</div>
                        <div>• Financial Planning</div>
                        <div>• Business Analytics</div>
                        <div>• Graphic Design</div>
                        <div>• Content Writing</div>
                        <div>• Leadership Skills</div>
                        <div>• Sales & Marketing</div>
                        <div>• And Many More...</div>
                    </div>
                    <p style="text-align: center; margin-top: 20px;"><a href="#" class="button">🎓 Browse Training Courses</a></p>
                </div>
                
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4 style="margin-top: 0;">⏰ Important Deadline:</h4>
                    <p>Your training coupon will expire {coupon.training_validity_months} months from the conversion date. Please use it before the deadline to maximize your benefits.</p>
                </div>
                
                <p>This conversion happened automatically as part of our program benefits. You can now use your coupon for valuable skill development and career advancement.</p>
                
                <p>If you have any questions about using your training coupon or need course recommendations, our support team is here to help.</p>
                
                <p>Best regards,<br>EV Reference Program Team</p>
            </div>
            <div class="footer">
                <p>Your coupon remains valid and valuable - now for training and skill development!</p>
                <p>&copy; 2025 EV Reference Program. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    EV Reference Program - Coupon Converted to Training
    
    Dear {user_name},
    
    Your EV Purchase Coupon has been automatically converted to a Training Coupon as per our program guidelines.
    
    UPDATED COUPON DETAILS:
    ======================
    Coupon PIN: {coupon.coupon_pin}
    Current Type: Training Coupon
    Coupon Value: ₹{coupon.coupon_value:,.2f}
    Training Validity: {coupon.training_validity_months} months from conversion
    Cashback Percentage: {coupon.training_cashback_percentage}% on course fees
    Original EV Expiry: {coupon.get_ev_expiry_date().strftime('%B %d, %Y') if coupon.get_ev_expiry_date() else 'Expired'}
    Converted on: {coupon.converted_date.strftime('%B %d, %Y') if coupon.converted_date else 'Today'}
    
    TRAINING COUPON BENEFITS:
    ========================
    * Full Value Applicable: Use the complete ₹{coupon.coupon_value:,.2f} value for training
    * Cashback Rewards: Get {coupon.training_cashback_percentage}% cashback on course fees
    * Extended Validity: {coupon.training_validity_months} months to use from conversion date
    * Wide Selection: Choose from hundreds of professional courses
    * Certification Value: Earn industry-recognized certifications
    * Career Advancement: Boost your professional skills and opportunities
    
    AVAILABLE TRAINING CATEGORIES:
    =============================
    Digital Marketing, Web Development, Data Science, Artificial Intelligence,
    Project Management, Financial Planning, Business Analytics, Graphic Design,
    Content Writing, Leadership Skills, Sales & Marketing, and many more...
    
    IMPORTANT DEADLINE:
    ==================
    Your training coupon will expire {coupon.training_validity_months} months from the conversion date.
    Please use it before the deadline to maximize your benefits.
    
    This conversion happened automatically as part of our program benefits. You can now use your coupon for valuable skill development and career advancement.
    
    If you have any questions about using your training coupon or need course recommendations, our support team is here to help.
    
    Best regards,
    EV Reference Program Team
    
    ---
    Your coupon remains valid and valuable - now for training and skill development!
    """
    
    try:
        result = send_email(
            to=email,
            subject=f"🎓 Coupon Converted to Training - PIN: {coupon.coupon_pin} (₹{coupon.coupon_value:,.0f})",
            html=html_content,
            text=text_content
        )
        return True
    except Exception as e:
        print(f"Failed to send coupon conversion notification to {email}: {str(e)}")
        return False


def send_ticket_email(email: str, ticket, action_type: str) -> bool:
    """
    Send ticket notification emails using Replit Mail service
    
    Args:
        email: Recipient email address
        ticket: ServiceTicket object
        action_type: Type of ticket action (created, assigned, status_updated, etc.)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    
    # Define email content based on action type
    if action_type == 'created':
        subject = f"Support Ticket Created - {ticket.ticket_id}"
        action_title = "🎫 New Support Ticket Created"
        action_message = f"Your support ticket has been successfully created and assigned ID <strong>{ticket.ticket_id}</strong>."
        next_steps = "Our support team has been notified and will review your ticket within 24 hours."
    
    elif action_type == 'assigned':
        subject = f"Ticket Assigned - {ticket.ticket_id}"
        action_title = "👨‍💼 Ticket Assigned"
        action_message = f"Your ticket has been assigned to <strong>{ticket.assigned_admin.name}</strong> for resolution."
        next_steps = "The assigned team member will work on your issue and provide updates."
    
    elif action_type == 'status_updated':
        subject = f"Ticket Status Updated - {ticket.ticket_id}"
        action_title = "📝 Ticket Status Updated"
        action_message = f"Your ticket status has been updated to <strong>{ticket.status}</strong>."
        next_steps = "You will receive further updates as progress is made on your ticket."
    
    elif action_type == 'response_added':
        subject = f"Admin Response - {ticket.ticket_id}"
        action_title = "💬 Admin Response Added"
        action_message = "Our support team has added a response to your ticket."
        next_steps = "Please review the response and let us know if you need further assistance."
    
    elif action_type == 'resolved':
        subject = f"Ticket Resolved - {ticket.ticket_id}"
        action_title = "✅ Ticket Resolved"
        action_message = "Your support ticket has been marked as resolved."
        next_steps = "If you're satisfied with the resolution, no further action is needed. If you need additional help, please contact support."
    
    elif action_type == 'escalated':
        subject = f"Ticket Escalated - {ticket.ticket_id}"
        action_title = "⚠️ Ticket Escalated"
        action_message = "Your ticket has been escalated to our Super Admin team due to SLA requirements."
        next_steps = "A senior team member will prioritize your issue and provide an update soon."
    
    else:
        subject = f"Ticket Update - {ticket.ticket_id}"
        action_title = "📋 Ticket Update"
        action_message = "There has been an update to your support ticket."
        next_steps = "Please check your ticket details for more information."
    
    # Status badge color
    status_colors = {
        'Open': '#ffc107',
        'In Progress': '#007bff', 
        'Resolved': '#28a745',
        'Closed': '#6c757d'
    }
    status_color = status_colors.get(ticket.status, '#6c757d')
    
    # Priority badge color
    priority_colors = {
        'Low': '#28a745',
        'Medium': '#ffc107',
        'High': '#fd7e14',
        'Critical': '#dc3545'
    }
    priority_color = priority_colors.get(ticket.priority, '#6c757d')
    
    # SLA status color
    sla_colors = {
        'Within SLA': '#28a745',
        'SLA Breached': '#dc3545',
        'Escalated': '#fd7e14'
    }
    sla_color = sla_colors.get(ticket.sla_status, '#6c757d')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Support Ticket Update</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f8f9fa; padding: 30px; border: 1px solid #dee2e6; border-top: none; }}
            .ticket-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007bff; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; }}
            .admin-response {{ background: #e3f2fd; border: 1px solid #2196f3; border-radius: 5px; padding: 15px; margin: 20px 0; }}
            .issue-description {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
            .next-steps {{ background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 20px 0; }}
            .footer {{ background: #343a40; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            td {{ padding: 8px 0; }}
            .label {{ color: #6c757d; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{action_title}</h1>
            </div>
            
            <div class="content">
                <h2 style="color: #007bff; margin-top: 0;">Ticket: {ticket.ticket_id}</h2>
                <p>{action_message}</p>
                
                <div class="ticket-details">
                    <h3 style="margin-top: 0; color: #495057;">Ticket Details</h3>
                    <table>
                        <tr>
                            <td class="label">Category:</td>
                            <td>{ticket.issue_category}</td>
                        </tr>
                        <tr>
                            <td class="label">Priority:</td>
                            <td><span class="badge" style="background: {priority_color};">{ticket.priority}</span></td>
                        </tr>
                        <tr>
                            <td class="label">Status:</td>
                            <td><span class="badge" style="background: {status_color};">{ticket.status}</span></td>
                        </tr>
                        <tr>
                            <td class="label">SLA Status:</td>
                            <td><span class="badge" style="background: {sla_color};">{ticket.sla_status}</span></td>
                        </tr>
                        <tr>
                            <td class="label">Created:</td>
                            <td>{ticket.created_date.strftime('%Y-%m-%d %H:%M UTC')}</td>
                        </tr>
                        {"<tr><td class='label'>Assigned To:</td><td>" + ticket.assigned_admin.name + "</td></tr>" if ticket.assigned_admin else ""}
                    </table>
                </div>
                
                {"<div class='admin-response'><h4 style='margin-top: 0; color: #1976d2;'>Latest Admin Response:</h4><p style='margin-bottom: 0; color: #424242;'>" + ticket.admin_response + "</p></div>" if ticket.admin_response else ""}
                
                <div class="issue-description">
                    <h4 style="margin-top: 0; color: #495057;">Issue Description:</h4>
                    <p style="margin-bottom: 0; color: #6c757d;">{ticket.issue_description[:200]}{'...' if len(ticket.issue_description) > 200 else ''}</p>
                </div>
                
                <div class="next-steps">
                    <p style="margin: 0; color: #0c5460;"><strong>📋 Next Steps:</strong> {next_steps}</p>
                </div>
            </div>
            
            <div class="footer">
                <p style="margin: 0; font-size: 14px;">EV Reference Program - Support Team</p>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #adb5bd;">Need help? Contact our support team for assistance.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Fallback plain text version
    text_content = f"""
    Support Ticket Update - {ticket.ticket_id}
    
    {action_message}
    
    Ticket Details:
    - Category: {ticket.issue_category}
    - Priority: {ticket.priority}
    - Status: {ticket.status}
    - SLA Status: {ticket.sla_status}
    - Created: {ticket.created_date.strftime('%Y-%m-%d %H:%M UTC')}
    {"- Assigned To: " + ticket.assigned_admin.name if ticket.assigned_admin else ""}
    
    {"Admin Response: " + ticket.admin_response if ticket.admin_response else ""}
    
    Issue Description:
    {ticket.issue_description}
    
    Next Steps: {next_steps}
    
    EV Reference Program - Support Team
    Need help? Contact our support team for assistance.
    """
    
    try:
        result = send_email(
            to=email,
            subject=subject,
            html=html_content,
            text=text_content
        )
        return True
    except Exception as e:
        print(f"Failed to send ticket email to {email}: {str(e)}")
        return False