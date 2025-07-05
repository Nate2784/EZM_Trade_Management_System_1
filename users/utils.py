from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(user_email, otp_code):
    """
    Send OTP code to user's email for verification.
    """
    subject = 'Your OTP Code for EZM Trade Management System'
    message = f'''
    Hello,
    
    Your OTP code for account verification is: {otp_code}
    
    This code will expire in 10 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    EZM Trade Management System
    '''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
