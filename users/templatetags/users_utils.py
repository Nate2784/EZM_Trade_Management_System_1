# users/utils.py
import logging
import random
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

try:
    logger.info('Loading users_utils.py')
except Exception as e:
    logger.error(f'Error loading users_utils.py: {e}')

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(user):
    otp = generate_otp()
    user.otp_code = otp
    user.save()
    send_mail(
        'Your OTP for EZM BuildSync',
        f'Hello {user.username}, your OTP code is: {otp}',
        'no-reply@ezm-buildsync.com',
        [user.email],
        fail_silently=False,
    )

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, class_name):
    return field.as_widget(attrs={"class": class_name})

@register.filter
def attr(field, args):
    attrs = {}
    parts = args.split(',')
    for part in parts:
        key, value = part.split(':')
        attrs[key.strip()] = value.strip()
    return field.as_widget(attrs=attrs)
