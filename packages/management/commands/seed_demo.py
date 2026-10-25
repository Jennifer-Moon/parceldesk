"""
Loads sample data for demonstrations.

Run with:  python manage.py seed_demo

Safe to run more than once: it clears the demo data it created
and rebuilds it, so the package ages are always correct relative
to today.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from packages.models import (
    Property, Resident, StaffProfile, Package, CustodyLog,
)

DEMO_PASSWORD = "ParcelDeskDemo2026"

RESIDENTS = [
    # first, last, username, building, unit
    ("Dana", "Whitfield", "dwhitfield", "B2", "214"),
    ("Marcus", "Reed", "mreed", "A1", "103"),
    ("Priya", "Raman", "praman", "B2", "207"),
]

# carrier, tracking, description, resident username, days ago it arrived
PACKAGES = [
    ("UPS", "1Z999AA10123456784", "Large box", "dwhitfield", 12),
    ("USPS", "9400110200793123456789", "Padded envelope", "mreed", 9),
    ("Amazon", "TBA305492117654", "Small box", "praman", 4),
    ("FedEx", "7712 4455 9087", "Small box", "mreed", 2),
    ("Amazon", "TBA305492119988", "Envelope", "dwhitfield", 1),
]


class Command(BaseCommand):
    help = "Load sample properties, residents, staff, and packages for demos."

    def handle(self, *args, **options):
        # Remove anything a previous run created, dependencies first.
        # A queryset delete does not call CustodyLog.delete(), so the
        # append-only guard on individual entries stays intact while
        # still allowing the demo data to be rebuilt.
        CustodyLog.objects.all().delete()
        Package.objects.all().delete()
        Resident.objects.all().delete()
        StaffProfile.objects.all().delete()
        Property.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        prop = Property.objects.create(
            name="Maple Grove Apartments",
            address="1400 Maple Grove Dr, Mount Pleasant, MI",
        )
        self.stdout.write(f"Created property: {prop.name}")

        staff_user = User.objects.create_user(
            username="jmoon", password=DEMO_PASSWORD,
            first_name="Jennifer", last_name="Moon",
            email="jmoon@example.com", is_staff=True,
        )
        StaffProfile.objects.create(user=staff_user, property=prop)
        self.stdout.write("Created staff login: jmoon")

        residents = {}
        for first, last, username, building, unit in RESIDENTS:
            user = User.objects.create_user(
                username=username, password=DEMO_PASSWORD,
                first_name=first, last_name=last,
                email=f"{username}@example.com",
            )
            residents[username] = Resident.objects.create(
                user=user, property=prop, building=building, unit=unit,
                move_in=timezone.now().date() - timedelta(days=400),
            )
            self.stdout.write(f"Created resident login: {username}")

        for carrier, tracking, desc, username, days_ago in PACKAGES:
            arrived = timezone.now() - timedelta(days=days_ago)
            pkg = Package.objects.create(
                resident=residents[username],
                carrier=carrier,
                tracking_number=tracking,
                description=desc,
                logged_at=arrived,
                logged_by=staff_user,
            )
            CustodyLog.objects.create(
                package=pkg,
                event=CustodyLog.EVENT_LOGGED,
                actor=staff_user,
                occurred_at=arrived,
                new_status=Package.STATUS_HELD,
            )

        aged = sum(1 for p in Package.objects.all() if p.is_aged())
        self.stdout.write(self.style.SUCCESS(
            f"\nLoaded {Package.objects.count()} packages "
            f"({aged} held more than 7 days)."
        ))
        self.stdout.write(f"All demo passwords: {DEMO_PASSWORD}")
