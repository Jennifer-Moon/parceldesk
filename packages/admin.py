from django.contrib import admin

from .models import (
    Property, Resident, StaffProfile, Package, CustodyLog, Notification,
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "address")


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "property", "building", "unit", "is_active")
    list_filter = ("property", "is_active")
    search_fields = ("user__first_name", "user__last_name", "unit")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "property", "is_active")
    list_filter = ("property", "is_active")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("tracking_number", "carrier", "resident",
                    "status", "days_held", "logged_at")
    list_filter = ("status", "carrier")
    search_fields = ("tracking_number", "resident__user__last_name")


@admin.register(CustodyLog)
class CustodyLogAdmin(admin.ModelAdmin):
    """
    Read-only in the admin. The custody record is append-only, so it
    cannot be edited here by anyone, including an administrator.
    """
    list_display = ("package", "event", "actor", "occurred_at")
    list_filter = ("event",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("resident", "package", "message_type", "sent_at", "delivered")
    list_filter = ("message_type", "delivered")
