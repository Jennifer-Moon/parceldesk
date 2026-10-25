"""
Role-based session timeout.

Milestone 3 set different inactivity timeouts for the two roles:
staff time out after 15 minutes because they work from a shared
terminal in a semi-public office; residents time out after 60
minutes because they use personal devices.

Django's SESSION_COOKIE_AGE is global, so the per-role value is
applied here when the user logs in.
"""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

STAFF_TIMEOUT_SECONDS = 15 * 60
RESIDENT_TIMEOUT_SECONDS = 60 * 60


@receiver(user_logged_in)
def set_session_timeout(sender, request, user, **kwargs):
    is_staff_member = user.is_staff or hasattr(user, "staffprofile")
    seconds = STAFF_TIMEOUT_SECONDS if is_staff_member else RESIDENT_TIMEOUT_SECONDS
    request.session.set_expiry(seconds)
