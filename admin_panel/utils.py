from .models import StaffActivityLog


def log_staff_action(performed_by, action_type, description, target_user=None):
    """Record a staff action in the activity log."""
    try:
        StaffActivityLog.objects.create(
            performed_by=performed_by,
            action_type=action_type,
            description=description,
            target_user=target_user,
        )
    except Exception:
        pass  # Never let logging crash a user-facing action


def staff_only(view_func):
    """Decorator: redirect unauthenticated users to login; raise 403 for logged-in non-staff."""
    from functools import wraps
    from django.contrib.auth.views import redirect_to_login
    from django.core.exceptions import PermissionDenied

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
