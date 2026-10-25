from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Property(models.Model):
    """A single apartment property that uses ParcelDesk."""
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name_plural = "properties"

    def __str__(self):
        return self.name


class Resident(models.Model):
    """A resident who receives packages. Linked to a Django login."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE,
                                 related_name="residents")
    building = models.CharField(max_length=20)
    unit = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    move_in = models.DateField(null=True, blank=True)
    move_out = models.DateField(null=True, blank=True)

    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    def __str__(self):
        return f"{self.full_name()} ({self.building}/{self.unit})"


class StaffProfile(models.Model):
    """A leasing office employee. Linked to a Django login."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE,
                                 related_name="staff")
    is_active = models.BooleanField(default=True)

    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    def __str__(self):
        return f"{self.full_name()} — {self.property.name}"


class Package(models.Model):
    """A package being held at the leasing office."""

    STATUS_HELD = "HELD"
    STATUS_PICKED_UP = "PICKED_UP"
    STATUS_CHOICES = [
        (STATUS_HELD, "Awaiting pickup"),
        (STATUS_PICKED_UP, "Picked up"),
    ]

    resident = models.ForeignKey(Resident, on_delete=models.PROTECT,
                                 related_name="packages")
    carrier = models.CharField(max_length=40)
    tracking_number = models.CharField(max_length=60)
    description = models.CharField(max_length=120, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES,
                              default=STATUS_HELD)
    logged_at = models.DateTimeField(default=timezone.now)
    logged_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                  related_name="packages_logged")
    picked_up_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                    null=True, blank=True,
                                    related_name="packages_released")

    class Meta:
        ordering = ["logged_at"]

    def days_held(self):
        """Days since the package was logged. Calculated on request, not stored."""
        end = self.picked_up_at or timezone.now()
        return (end - self.logged_at).days

    def is_aged(self, threshold=7):
        """True when the package has been held past the threshold."""
        return self.status == self.STATUS_HELD and self.days_held() >= threshold

    def __str__(self):
        return f"{self.carrier} {self.tracking_number} for {self.resident}"


class CustodyLog(models.Model):
    """
    Append-only record of every custody event for a package.

    Rows in this table are never updated or deleted. A correction is
    recorded as a new row, the way a ledger records a correcting entry.
    """

    EVENT_LOGGED = "LOGGED"
    EVENT_PICKED_UP = "PICKED_UP"
    EVENT_CORRECTION = "CORRECTION"
    EVENT_CHOICES = [
        (EVENT_LOGGED, "Logged at intake"),
        (EVENT_PICKED_UP, "Released to resident"),
        (EVENT_CORRECTION, "Correction"),
    ]

    package = models.ForeignKey(Package, on_delete=models.PROTECT,
                                related_name="custody_log")
    event = models.CharField(max_length=12, choices=EVENT_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.PROTECT,
                              related_name="custody_events")
    occurred_at = models.DateTimeField(default=timezone.now)
    previous_status = models.CharField(max_length=12, blank=True)
    new_status = models.CharField(max_length=12, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["occurred_at"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError(
                "CustodyLog entries are append-only and cannot be edited. "
                "Record a CORRECTION entry instead."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("CustodyLog entries are append-only and cannot be deleted.")

    def __str__(self):
        return f"{self.get_event_display()} — {self.occurred_at:%Y-%m-%d %H:%M}"


class Notification(models.Model):
    """Record of an email sent to a resident about a package."""

    TYPE_ARRIVED = "ARRIVED"
    TYPE_REMINDER = "REMINDER"
    TYPE_CHOICES = [
        (TYPE_ARRIVED, "Package arrived"),
        (TYPE_REMINDER, "Still waiting"),
    ]

    resident = models.ForeignKey(Resident, on_delete=models.CASCADE,
                                 related_name="notifications")
    package = models.ForeignKey(Package, on_delete=models.CASCADE,
                                related_name="notifications")
    message_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    sent_at = models.DateTimeField(default=timezone.now)
    delivered = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_message_type_display()} to {self.resident}"
