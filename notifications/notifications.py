import logging
from django.db import models as db_models

logger = logging.getLogger(__name__)


def notify_user(recipient, title, message, notification_type='info', link=None, created_by=None):
    """Send a notification to a single user."""
    from .models import Notification
    try:
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            created_by=created_by,
        )
    except Exception as e:
        logger.error('notify_user: failed for user %s — %s', getattr(recipient, 'pk', '?'), e)


def notify_group(user_queryset, title, message, notification_type='info', link=None, created_by=None):
    """Send a notification to every user in a queryset."""
    from .models import Notification
    try:
        notifications = [
            Notification(
                recipient=user,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link,
                created_by=created_by,
            )
            for user in user_queryset
        ]
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)
    except Exception as e:
        logger.error('notify_group: failed — %s', e)


def notify_all(title, message, notification_type='broadcast', link=None, created_by=None):
    """Broadcast a notification to ALL users by saving one record with recipient=None."""
    from .models import Notification
    try:
        Notification.objects.create(
            recipient=None,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            created_by=created_by,
        )
    except Exception as e:
        logger.error('notify_all: failed — %s', e)


def get_unread_count(user):
    """Return the count of unread notifications for a user including broadcasts."""
    from .models import Notification
    return Notification.objects.filter(
        db_models.Q(recipient=user) | db_models.Q(recipient__isnull=True),
        is_read=False,
    ).count()


def get_notifications_for_user(user, limit=20):
    """Return the most recent notifications for a user including broadcasts."""
    from .models import Notification
    return Notification.objects.filter(
        db_models.Q(recipient=user) | db_models.Q(recipient__isnull=True)
    ).order_by('-created_at')[:limit]
