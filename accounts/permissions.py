"""
Server-side role checks shared by all apps.

Usage:
    @student_required
    def my_view(request): ...

An anonymous visitor is sent to the login page.
A logged-in user with the wrong role is sent to their own dashboard with an error message.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .models import User


def dashboard_url_name(user):
    """Return the URL name of the dashboard that suits this user."""
    if user.is_staff:
        return "admin:index"
    if user.role == User.Role.OWNER:
        return "owner_dashboard"
    return "student_dashboard"


def _role_required(role, label):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role != role:
                messages.error(request, f"That page is only available to {label} accounts.")
                return redirect(dashboard_url_name(request.user))
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


student_required = _role_required(User.Role.STUDENT, "student")
owner_required = _role_required(User.Role.OWNER, "property owner")
