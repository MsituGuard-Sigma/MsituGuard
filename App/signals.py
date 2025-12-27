from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .models import Report, Notification, Profile
from django.core.mail import EmailMultiAlternatives

@receiver(pre_save, sender=Report)
def track_report_status_change(sender, instance, **kwargs):
    """Track status changes to send notifications"""
    if instance.pk:  # Only for existing reports
        try:
            old_report = Report.objects.get(pk=instance.pk)
            instance._old_status = old_report.status
        except Report.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create Profile when User is created"""
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'account_type': 'community',
                'phoneNumber': '',
                'location': '',
                'bio': 'Bio information not provided',
                'email': instance.email or 'example@example.com',
                'first_name': instance.first_name or '',
                'last_name': instance.last_name or '',
                'is_verified': False
            }
        )