# app/utils/email_utils.py

import base64
import datetime
import os
import logging
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")

def send_email(to_email: str, subject: str, html_content: str):
    """
    Sends a generic email using SendGrid.
    """
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        logger.error("SendGrid credentials are not configured.")
        return

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Generic email sent to {to_email} | Subject: '{subject}' | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send generic email to {to_email}: {e}")

def send_contact_confirmation_email(to_email: str, company_name: str):
    subject = "FleetDocs — Contact Request Received"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #0044cc; padding: 20px; border-radius: 10px 10px 0 0; color: white;">
                <h2>FleetDocs</h2>
            </div>
            <div style="padding: 20px;">
                <p>Hi <strong>{company_name}</strong>,</p>
                <p>Thank you for contacting <strong>FleetDocs</strong>. We have received your request and our team will reach out to you shortly.</p>
                <p>Best regards,<br>FleetDocs Team</p>
            </div>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Contact confirmation email sent to {to_email} | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"SendGrid Error: {str(e)}")


def send_reset_email(to_email: str, token: str, identifier: str, role: str):
    reset_link = f"http://10.122.235.47:5000/reset-password?token={token}&identifier={identifier}"

    subject = "FleetDocs — Password Reset Request"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #0044cc; padding: 20px; border-radius: 10px 10px 0 0; color: white;">
                <h2>FleetDocs</h2>
            </div>
            <div style="padding: 20px;">
                <p>Hello,</p>
                <p>We received a request to reset your password for your <strong>FleetDocs</strong> account.</p>
                <p>Please click the button below to reset your password:</p>
                <p style="text-align: center;">
                    <a href="{reset_link}" style="display: inline-block; background-color: #0044cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p>If you didn’t request this, you can safely ignore this email.</p>
                <p>Thanks,<br>FleetDocs Team</p>
            </div>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Password reset email sent to {to_email} | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"SendGrid Error: {str(e)}")


def send_payment_instructions_email(to_email: str, payment_url: str, amount_due: str, due_date: str):
    subject = "FleetDocs — Payment Instructions"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #0044cc; padding: 20px; border-radius: 10px 10px 0 0; color: white;">
                <h2>FleetDocs Payment Instructions</h2>
            </div>
            <div style="padding: 20px;">
                <p>Dear Customer,</p>
                <p>Your payment of <strong>{amount_due}</strong> is due by <strong>{due_date}</strong>.</p>
                <p>Please click the button below to complete your payment securely:</p>
                <p style="text-align: center;">
                    <a href="{payment_url}" style="display: inline-block; background-color: #0044cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Pay Now
                    </a>
                </p>
                <p>Thank you for your prompt attention.</p>
                <p>Best regards,<br>FleetDocs Billing Team</p>
            </div>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Payment instructions email sent to {to_email} | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"SendGrid Error: {str(e)}")


def send_credential_email(to_email: str, username: str, temporary_password: str = None, reset_link: str = None):
    subject = "FleetDocs — Your Account Credentials"

    password_section = f"""
    <p>Your temporary password is: <strong>{temporary_password}</strong></p>
    <p>Please log in and change your password immediately.</p>
    """ if temporary_password else ""

    reset_section = f"""
    <p>If you need to reset your password, click the link below:</p>
    <p style="text-align: center;">
        <a href="{reset_link}" style="display: inline-block; background-color: #0044cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Reset Password
        </a>
    </p>
    """ if reset_link else ""

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #0044cc; padding: 20px; border-radius: 10px 10px 0 0; color: white;">
                <h2>FleetDocs Account Credentials</h2>
            </div>
            <div style="padding: 20px;">
                <p>Hello <strong>{username}</strong>,</p>
                {password_section}
                {reset_section}
                <p>If you have any questions, please contact support.</p>
                <p>Best regards,<br>FleetDocs Team</p>
            </div>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Credential email sent to {to_email} | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"SendGrid Error: {str(e)}")

def send_password_change_notification(to_email: str, company_name: str):
    """
    Sends an email notification after a password has been successfully changed.
    """
    subject = f"Security Alert: Your FleetDocs Password has been Changed"
    change_time = datetime.datetime.now().strftime("%d %B %Y at %I:%M %p")
    recovery_link = "fleetdocs://recover-account"

    html_content = f"""
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px;">
            <h2 style="color: #1A1A2E;">Password Changed Successfully</h2>
            <p>Hello {company_name},</p>
            <p>This is to confirm that the password for your FleetDocs account was successfully changed on <strong>{change_time}</strong>.</p>
            <p>If you made this change, you can safely disregard this email.</p>
            <hr>
            <p style="color: #E53935; font-weight: bold;">If you did NOT make this change, your account may be compromised.</p>
            <p>Please secure your account immediately by clicking the link below:</p>
            <p style="text-align: center;">
                <a href="{recovery_link}" style="display: inline-block; background-color: #E53935; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px;">
                    Secure Your Account Now
                </a>
            </p>
            <p>Thank you for using FleetDocs.</p>
        </div>
    </body>
    </html>
    """

    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Password change notification sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending password change notification: {str(e)}")


def send_account_recovery_credentials(to_email: str, company_name: str, username: str, new_password: str):
    """
    Sends new, temporary credentials after a successful account recovery.
    """
    subject = "Your FleetDocs Account Recovery Credentials"
    html_content = f"""
     <html>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px;">
            <h2 style="color: #1A1A2E;">Account Recovery Successful</h2>
            <p>Hello {company_name},</p>
            <p>Your account has been successfully recovered. We have generated a new temporary password for you to regain access.</p>
            <p>Please use the following credentials to log in:</p>
            <ul style="list-style-type: none; padding: 0;">
                <li><strong>Username:</strong> {username}</li>
                <li><strong>New Temporary Password:</strong> <strong style="color: #0044cc;">{new_password}</strong></li>
            </ul>
            <p style="font-weight: bold; color: #E53935;">For your security, you will be required to set a new password immediately after logging in.</p>
            <p>Thank you,<br>The FleetDocs Team</p>
        </div>
    </body>
    </html>
    """
    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Account recovery credentials sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending recovery credentials: {str(e)}")

def send_truck_added_email(to_email: str, company_name: str, truck: dict):
    """
    Sends a detailed confirmation email after a new truck is successfully added.
    """
    subject = f"Confirmation: New Truck '{truck['truck_number']}' Added to FleetDocs"
    added_time = datetime.datetime.now().strftime("%d %B %Y at %I:%M %p")

    def build_details_html(details_dict):
        rows = ""
        for key, value in details_dict.items():
            label = key.replace('_', ' ').title()
            rows += f'<tr><td style="padding: 4px; color: #bbb;">{label}</td><td style="padding: 4px; color: #fff; font-weight: 600;">{value or "N/A"}</td></tr>'
        return rows

    docs_html = ""
    for doc_name, doc_data in truck['documents'].items():
        docs_html += f'''
            <div style="background-color: #1A1A2E; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                <h4 style="margin: 0 0 10px 0; color: #FFCA28; border-bottom: 1px solid #444; padding-bottom: 5px;">{doc_name.upper()}</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    {build_details_html(doc_data)}
                </table>
            </div>
        '''

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #ddd; background-color: #2D2D44; color: #fff; border-radius: 10px;">
            <div style="background-color: #1A1A2E; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                <h2 style="color: #FFCA28; margin: 0;">Truck Added Successfully</h2>
            </div>
            <div style="padding: 25px;">
                <p style="color: #ccc;">Hello {company_name},</p>
                <p style="color: #ccc;">This email confirms that a new truck, <strong>{truck['truck_number']}</strong>, was successfully added to your FleetDocs account on {added_time}.</p>
                <img src="{truck['truck_photo_url']}" alt="Truck Photo" style="width: 100%; max-width: 400px; border-radius: 8px; margin: 15px auto; display: block;">
                
                <h3 style="color: #FFCA28; border-top: 1px solid #444; padding-top: 20px;">Vehicle Details</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                    {build_details_html({
                        'Model Number': truck['model_number'],
                        'Engine Number': truck['engine_number'],
                        'Chassis Number': truck['chassis_number'],
                        'Registration Date': truck['registration_date'],
                        'Tire Count': truck['tire_count']
                    })}
                </table>

                <h3 style="color: #FFCA28;">Document Summary</h3>
                {docs_html}
            </div>
            <div style="background-color: #1A1A2E; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)

    attachments = []
    for doc_name, doc_data in truck['documents'].items():
        try:
            response = requests.get(doc_data['s3_url'])
            if response.status_code == 200:
                encoded_file = base64.b64encode(response.content).decode()
                attachments.append(
                    Attachment(
                        FileContent(encoded_file),
                        FileName(f"{truck['truck_number']}_{doc_name.upper()}.pdf"),
                        FileType('application/pdf'),
                        Disposition('attachment')
                    )
                )
        except Exception as e:
            logger.error(f"Failed to fetch and attach {doc_name} from S3: {e}")
    message.attachment = attachments

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Truck added confirmation sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending truck added email: {str(e)}")


def send_truck_updated_email(to_email: str, company_name: str, truck: dict, updated_doc_type: str, new_doc_url: str):
    """
    Sends a confirmation email after a truck's document has been updated.
    """
    subject = f"Update: Document for Truck '{truck['truck_number']}' Changed"
    updated_time = datetime.datetime.now().strftime("%d %B %Y at %I:%M %p")

    docs_html = ""
    for doc_name, doc_data in truck['documents'].items():
        is_updated = doc_name == updated_doc_type
        style = 'background-color: #FFCA28; color: #1A1A2E; border: 2px solid #fff;' if is_updated else 'background-color: #1A1A2E;'
        
        doc_details_html = ""
        for key, value in doc_data.items():
            label = key.replace('_', ' ').title()
            doc_details_html += f'<tr><td style="padding: 4px; color: #bbb;">{label}</td><td style="padding: 4px; font-weight: 600;">{value or "N/A"}</td></tr>'

        docs_html += f'''
            <div style="{style} border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                <h4 style="margin: 0 0 10px 0; border-bottom: 1px solid #444; padding-bottom: 5px; {"color: #1A1A2E;" if is_updated else "color: #FFCA28;"}">{doc_name.upper()} {'(UPDATED)' if is_updated else ''}</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; {"color: #333;" if is_updated else "color: #fff;"}">
                    {doc_details_html}
                </table>
            </div>
        '''
    
    html_content = f"""
    <!-- Similar HTML structure as add_truck email, but with different text and the highlighted section -->
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #ddd; background-color: #2D2D44; color: #fff; border-radius: 10px;">
            <div style="background-color: #1A1A2E; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                <h2 style="color: #FFCA28; margin: 0;">Truck Document Updated</h2>
            </div>
            <div style="padding: 25px;">
                <p style="color: #ccc;">Hello {company_name},</p>
                <p style="color: #ccc;">This email confirms that the <strong>{updated_doc_type.upper()}</strong> document for truck <strong>{truck['truck_number']}</strong> was updated on {updated_time}.</p>
                
                <h3 style="color: #FFCA28; border-top: 1px solid #444; padding-top: 20px;">Document Summary</h3>
                {docs_html}
            </div>
             <div style="background-color: #1A1A2E; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)

    try:
        response = requests.get(new_doc_url)
        if response.status_code == 200:
            encoded_file = base64.b64encode(response.content).decode()
            attachment = Attachment(
                FileContent(encoded_file),
                FileName(f"{truck['truck_number']}_{updated_doc_type.upper()}_NEW.pdf"),
                FileType('application/pdf'),
                Disposition('attachment')
            )
            message.attachment = attachment
    except Exception as e:
        logger.error(f"Failed to fetch and attach updated document from S3: {e}")

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Truck updated confirmation sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending truck updated email: {str(e)}")


def send_truck_deleted_email(to_email: str, company_name: str, truck_number: str):
    """
    Sends a simple confirmation email after a truck has been deleted.
    """
    subject = f"Confirmation: Truck '{truck_number}' Deleted from FleetDocs"
    deleted_time = datetime.datetime.now().strftime("%d %B %Y at %I:%M %p")

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #ddd; background-color: #2D2D44; color: #fff; border-radius: 10px;">
            <div style="background-color: #1A1A2E; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                <h2 style="color: #FFCA28; margin: 0;">Truck Deleted</h2>
            </div>
            <div style="padding: 25px;">
                <p style="color: #ccc;">Hello {company_name},</p>
                <p style="color: #ccc;">This is to confirm that the truck with registration number <strong>{truck_number}</strong> was successfully deleted from your FleetDocs account on {deleted_time}.</p>
                <p style="color: #ccc;">This action cannot be undone.</p>
                <p style="color: #ccc;">If you did not authorize this action, please contact support immediately.</p>
            </div>
            <div style="background-color: #1A1A2E; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Truck deleted confirmation sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending truck deleted email: {str(e)}")

def send_driver_added_email(to_email: str, company_name: str, driver: dict):
    """
    Sends a confirmation email after a new driver is successfully added.
    """
    subject = f"Confirmation: New Driver '{driver['first_name']} {driver['last_name']}' Added"
    added_time = datetime.datetime.now().strftime("%d %B %Y at %I:%M %p")

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #ddd; background-color: #2D2D44; color: #fff; border-radius: 10px;">
            <div style="background-color: #1A1A2E; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                <h2 style="color: #FFCA28; margin: 0;">New Driver Added Successfully</h2>
            </div>
            <div style="padding: 25px;">
                <p style="color: #ccc;">Hello {company_name},</p>
                <p style="color: #ccc;">This email confirms that a new driver, <strong>{driver['first_name']} {driver['last_name']}</strong>, was added to your FleetDocs account on {added_time}.</p>
                <img src="{driver['driver_photo_url']}" alt="Driver Photo" style="width: 120px; height: 120px; border-radius: 60px; margin: 15px auto; display: block; border: 2px solid #FFCA28;">
                
                <h3 style="color: #FFCA28; border-top: 1px solid #444; padding-top: 20px;">Driver Details</h3>
                <p style="color: #fff;"><strong>Phone:</strong> {driver['phone_number']}</p>
                <p style="color: #fff;"><strong>Email:</strong> {driver.get('email') or 'N/A'}</p>
                
                <h3 style="color: #FFCA28;">License Details</h3>
                <p style="color: #fff;"><strong>Number:</strong> {driver['license']['license_number']}</p>
                <p style="color: #fff;"><strong>NT Validity:</strong> {driver['license']['validity_nt']}</p>
                <p style="color: #fff;"><strong>TR Validity:</strong> {driver['license']['validity_tr']}</p>
            </div>
            <div style="background-color: #1A1A2E; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Driver added confirmation sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending driver added email: {str(e)}")


def send_driver_updated_email(to_email: str, company_name: str, driver: dict, update_type: str):
    """
    Sends a notification email after a driver's details have been updated.
    """
    subject = f"Update: Details for Driver '{driver['first_name']} {driver['last_name']}' Changed"
    updated_time = datetime.datetime.now().strftime("%d %B %Y at %I:%M %p")

    html_content = f"""
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px;">
            <h2 style="color: #1A1A2E;">Driver Details Updated</h2>
            <p>Hello {company_name},</p>
            <p>This is to confirm that the <strong>{update_type}</strong> for driver <strong>{driver['first_name']} {driver['last_name']}</strong> was updated on {updated_time}.</p>
            <p><strong>New Phone Number:</strong> {driver['phone_number']}</p>
            <p><strong>New License Number:</strong> {driver['license']['license_number']}</p>
            <p>Please review these changes in your FleetDocs dashboard.</p>
        </div>
    </body>
    </html>
    """
    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Driver updated confirmation sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending driver updated email: {str(e)}")


def send_profile_update_email(to_email: str, company_name: str, updated_details: dict):
    """
    Sends a confirmation email after a company's profile has been updated.
    """
    subject = "Confirmation: Your FleetDocs Profile Has Been Updated"
    
    # Dynamically create HTML rows from the updated_details dictionary
    details_html = ""
    for key, value in updated_details.items():
        details_html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">{key}</td><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>{value}</strong></td></tr>'

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #1A1A2E; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                <h2 style="color: #FFCA28; margin: 0;">Profile Updated Successfully</h2>
            </div>
            <div style="padding: 25px;">
                <p>Hello {company_name},</p>
                <p>This is to confirm that your company profile details have been successfully updated on FleetDocs. Your new details are listed below:</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #f9f9f9;">
                    {details_html}
                </table>
                <p style="margin-top: 20px;">If you did not authorize this change, please contact our support team immediately.</p>
            </div>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #888;">
                © {datetime.datetime.now().year} FleetDocs. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    message = Mail(from_email=SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Profile update confirmation sent to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid Error sending profile update email: {str(e)}")
