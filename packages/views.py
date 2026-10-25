from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def home(request):
    """
    Entry point. Sends a signed-in user to the right place for their
    role, and everyone else to the login page.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, "staffprofile") or request.user.is_staff:
            return redirect("staff_dashboard")
        if hasattr(request.user, "resident"):
            return redirect("resident_packages")
    return render(request, "packages/home.html")


@login_required
def staff_dashboard(request):
    """Action menu for property staff. Views are built out in Sprint 2."""
    return render(request, "packages/staff_dashboard.html")


@login_required
def resident_packages(request):
    """
    A resident's own packages.

    The queryset is filtered by request.user, never by an identifier
    taken from the URL. This is the Milestone 3 authorization rule.
    """
    resident = getattr(request.user, "resident", None)
    packages = []
    if resident is not None:
        packages = resident.packages.filter(status="HELD").order_by("logged_at")
    return render(
        request,
        "packages/resident_packages.html",
        {"packages": packages, "resident": resident},
    )
