from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

def send_verification_email(request, user):
    """Send email verification link to the user."""
    current_site = get_current_site(request)
    mail_subject = _('Activate your account')
    
    # Create verification token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build verification URL
    verification_url = f"http://{current_site.domain}/users/verify-email/{uid}/{token}/"
    
    # Render email template
    message = render_to_string('users/emails/verification_email.html', {
        'user': user,
        'verification_url': verification_url,
        'site_name': current_site.name,
    })
    
    # Send email
    send_mail(
        subject=mail_subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=message,
        fail_silently=False,
    )

def send_password_reset_email(request, user):
    """Send password reset link to the user."""
    current_site = get_current_site(request)
    mail_subject = _('Reset your password')
    
    # Create password reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build reset URL
    reset_url = f"http://{current_site.domain}/users/reset-password/{uid}/{token}/"
    
    # Render email template
    message = render_to_string('users/emails/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
        'site_name': current_site.name,
    })
    
    # Send email
    send_mail(
        subject=mail_subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=message,
        fail_silently=False,
    )

def verify_email(uidb64, token):
    """Verify user's email using the token."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return True
        return False
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return False
