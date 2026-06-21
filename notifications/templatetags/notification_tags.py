from django import template
from django.db import models as db_models

register = template.Library()


@register.inclusion_tag('notifications/bell.html', takes_context=True)
def notification_bell(context):
    request = context.get('request')
    user = context.get('user')
    if not user or not user.is_authenticated:
        return {'unread_count': 0, 'notifications': [], 'user': user}
    from notifications.models import Notification
    notifications = list(
        Notification.objects.filter(
            db_models.Q(recipient=user) | db_models.Q(recipient__isnull=True)
        ).order_by('-created_at')[:10]
    )
    unread_count = sum(1 for n in notifications if not n.is_read)
    return {
        'unread_count': unread_count,
        'notifications': notifications,
        'user': user,
        'request': request,
    }
