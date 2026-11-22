"""
Tests for ParcelDesk.  Run with:  python manage.py test

Unit tests check one method on its own. Integration tests sign a user in
and make a real request, so the whole stack runs.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packages.models import (
    Property, Resident, StaffProfile, Package, CustodyLog,
)

PASSWORD = "ParcelDeskTesting2026"


def make_world():
    """
    Build a small property with one staff member and two residents.
    Most tests need this, so it lives in one place.
    """
    prop = Property.objects.create(name="Maple Grove", address="1400 Maple Grove Dr")

    staff_user = User.objects.create_user(
        username="staff1", password=PASSWORD,
        first_name="Jennifer", last_name="Moon",
    )
    StaffProfile.objects.create(user=staff_user, property=prop)

    marcus_user = User.objects.create_user(
        username="marcus", password=PASSWORD,
        first_name="Marcus", last_name="Reed", email="marcus@example.com",
    )
    marcus = Resident.objects.create(
        user=marcus_user, property=prop, building="A1", unit="103"
    )

    dana_user = User.objects.create_user(
        username="dana", password=PASSWORD,
        first_name="Dana", last_name="Whitfield", email="dana@example.com",
    )
    dana = Resident.objects.create(
        user=dana_user, property=prop, building="B2", unit="214"
    )

    return prop, staff_user, marcus, dana


def log_package(resident, staff_user, days_ago=0, carrier="UPS", tracking="1Z999"):
    """Create a package that arrived a given number of days ago."""
    return Package.objects.create(
        resident=resident,
        carrier=carrier,
        tracking_number=tracking,
        logged_at=timezone.now() - timedelta(days=days_ago),
        logged_by=staff_user,
    )


# =====================================================================
#  UNIT TESTS
# =====================================================================

class PackageAgingTests(TestCase):
    """Milestone 1 set the aging threshold at seven days."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()

    def test_days_held_counts_from_arrival(self):
        pkg = log_package(self.marcus, self.staff, days_ago=5)
        self.assertEqual(pkg.days_held(), 5)

    def test_days_held_on_a_package_logged_today_is_zero(self):
        pkg = log_package(self.marcus, self.staff, days_ago=0)
        self.assertEqual(pkg.days_held(), 0)

    def test_days_held_stops_counting_once_picked_up(self):
        """A package collected after 3 days stays at 3, not however long ago it arrived."""
        pkg = log_package(self.marcus, self.staff, days_ago=10)
        pkg.picked_up_at = pkg.logged_at + timedelta(days=3)
        pkg.status = Package.STATUS_PICKED_UP
        pkg.save()
        self.assertEqual(pkg.days_held(), 3)

    def test_package_under_the_threshold_is_not_aged(self):
        pkg = log_package(self.marcus, self.staff, days_ago=6)
        self.assertFalse(pkg.is_aged())

    def test_package_exactly_at_the_threshold_is_aged(self):
        """Seven days counts. This is the boundary the dashboard depends on."""
        pkg = log_package(self.marcus, self.staff, days_ago=7)
        self.assertTrue(pkg.is_aged())

    def test_package_well_past_the_threshold_is_aged(self):
        pkg = log_package(self.marcus, self.staff, days_ago=30)
        self.assertTrue(pkg.is_aged())

    def test_collected_package_is_never_aged(self):
        """An old package that has been picked up should not keep showing as a problem."""
        pkg = log_package(self.marcus, self.staff, days_ago=30)
        pkg.status = Package.STATUS_PICKED_UP
        pkg.picked_up_at = timezone.now()
        pkg.save()
        self.assertFalse(pkg.is_aged())

    def test_threshold_can_be_changed(self):
        pkg = log_package(self.marcus, self.staff, days_ago=4)
        self.assertFalse(pkg.is_aged(threshold=7))
        self.assertTrue(pkg.is_aged(threshold=3))


class CustodyLogAppendOnlyTests(TestCase):
    """Milestone 3: no role may change a custody record, administrators included."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()
        self.pkg = log_package(self.marcus, self.staff, days_ago=2)
        self.entry = CustodyLog.objects.create(
            package=self.pkg, event=CustodyLog.EVENT_LOGGED,
            actor=self.staff, new_status=Package.STATUS_HELD,
        )

    def test_a_new_entry_can_be_created(self):
        self.assertEqual(CustodyLog.objects.count(), 1)

    def test_editing_an_entry_raises(self):
        self.entry.note = "changed after the fact"
        with self.assertRaises(ValueError):
            self.entry.save()

    def test_the_edit_is_not_written_to_the_database(self):
        """Confirm the refusal actually protected the row, not just raised."""
        self.entry.note = "changed after the fact"
        with self.assertRaises(ValueError):
            self.entry.save()
        self.assertEqual(CustodyLog.objects.get(pk=self.entry.pk).note, "")

    def test_deleting_an_entry_raises(self):
        with self.assertRaises(ValueError):
            self.entry.delete()

    def test_the_entry_survives_the_delete_attempt(self):
        with self.assertRaises(ValueError):
            self.entry.delete()
        self.assertTrue(CustodyLog.objects.filter(pk=self.entry.pk).exists())

    def test_a_correction_is_recorded_as_a_new_entry(self):
        """The way to fix a mistake is to add to the log, not change it."""
        CustodyLog.objects.create(
            package=self.pkg, event=CustodyLog.EVENT_CORRECTION,
            actor=self.staff, note="Logged to the wrong unit",
        )
        self.assertEqual(self.pkg.custody_log.count(), 2)
        self.assertEqual(self.pkg.custody_log.first().event, CustodyLog.EVENT_LOGGED)


class PasswordPolicyTests(TestCase):
    """Milestone 3: 15-character minimum, no composition rules (NIST SP 800-63B)."""

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_password("Short1!")

    def test_fourteen_characters_is_rejected(self):
        """One under the limit, to confirm the boundary is where we think it is."""
        with self.assertRaises(ValidationError):
            validate_password("abcdefghijklmn")

    def test_fifteen_characters_is_accepted(self):
        validate_password("abcdefghijklmno")

    def test_a_long_passphrase_with_no_symbols_is_accepted(self):
        """No composition rules means plain words are fine if they are long enough."""
        validate_password("correct horse battery staple")

    def test_a_long_common_password_is_still_rejected(self):
        """
        A known keyboard-walk password that is long enough to pass the
        length rule. The common-password check catches it.
        """
        with self.assertRaises(ValidationError):
            validate_password("1q2w3e4r5t6y7u8i9o0p")

    def test_common_password_check_rarely_fires_at_our_minimum(self):
        """
        Only 46 of Django's 19,646 common passwords are 15+ characters, so at
        our minimum the check adds very little. Recorded, not assumed away.
        """
        validate_password("passwordpassword")  # accepted, by design of the list


class ModelStringTests(TestCase):
    """Readable names matter in the admin, which is how staff see records."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()

    def test_resident_full_name(self):
        self.assertEqual(self.marcus.full_name(), "Marcus Reed")

    def test_resident_falls_back_to_username(self):
        user = User.objects.create_user(username="nameless", password=PASSWORD)
        resident = Resident.objects.create(
            user=user, property=self.prop, building="C3", unit="301"
        )
        self.assertEqual(resident.full_name(), "nameless")

    def test_resident_string_shows_the_unit(self):
        self.assertIn("A1/103", str(self.marcus))

    def test_package_string_names_the_carrier_and_resident(self):
        pkg = log_package(self.marcus, self.staff, carrier="FedEx")
        self.assertIn("FedEx", str(pkg))
        self.assertIn("Marcus Reed", str(pkg))


# =====================================================================
#  INTEGRATION TESTS
# =====================================================================

class LoginRoutingTests(TestCase):
    """Each role should land on the right page after signing in."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()

    def test_staff_lands_on_the_dashboard(self):
        self.client.login(username="staff1", password=PASSWORD)
        response = self.client.get(reverse("home"), follow=True)
        self.assertRedirects(response, reverse("staff_dashboard"))

    def test_resident_lands_on_their_packages(self):
        self.client.login(username="marcus", password=PASSWORD)
        response = self.client.get(reverse("home"), follow=True)
        self.assertRedirects(response, reverse("resident_packages"))

    def test_signed_out_visitor_sees_the_home_page(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_does_not_sign_anyone_in(self):
        self.assertFalse(self.client.login(username="marcus", password="wrong"))


class AuthorizationTests(TestCase):
    """Milestone 3 access matrix: a resident sees only their own records."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()
        log_package(self.marcus, self.staff, days_ago=2, carrier="FedEx", tracking="MARCUS-1")
        log_package(self.dana, self.staff, days_ago=9, carrier="UPS", tracking="DANA-1")

    def test_resident_sees_their_own_package(self):
        self.client.login(username="marcus", password=PASSWORD)
        body = self.client.get(reverse("resident_packages")).content.decode()
        self.assertIn("MARCUS-1", body)

    def test_resident_cannot_see_another_residents_package(self):
        self.client.login(username="marcus", password=PASSWORD)
        body = self.client.get(reverse("resident_packages")).content.decode()
        self.assertNotIn("DANA-1", body)

    def test_resident_page_requires_signing_in(self):
        response = self.client.get(reverse("resident_packages"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_requires_signing_in(self):
        response = self.client.get(reverse("staff_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_staff_can_open_the_package_list(self):
        self.client.login(username="staff1", password=PASSWORD)
        response = self.client.get(reverse("package_list"))
        self.assertEqual(response.status_code, 200)

    def test_resident_is_turned_away_from_the_staff_package_list(self):
        """A resident typing the URL should be redirected, not shown an error."""
        self.client.login(username="marcus", password=PASSWORD)
        response = self.client.get(reverse("package_list"))
        self.assertEqual(response.status_code, 302)

    def test_collected_packages_drop_off_the_resident_page(self):
        pkg = Package.objects.get(tracking_number="MARCUS-1")
        pkg.status = Package.STATUS_PICKED_UP
        pkg.picked_up_at = timezone.now()
        pkg.save()

        self.client.login(username="marcus", password=PASSWORD)
        body = self.client.get(reverse("resident_packages")).content.decode()
        self.assertNotIn("MARCUS-1", body)


class SessionTimeoutTests(TestCase):
    """Milestone 3: staff time out at 15 minutes, residents at 60."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()

    def test_staff_session_expires_after_fifteen_minutes(self):
        self.client.login(username="staff1", password=PASSWORD)
        self.assertEqual(self.client.session.get_expiry_age(), 15 * 60)

    def test_resident_session_expires_after_sixty_minutes(self):
        self.client.login(username="marcus", password=PASSWORD)
        self.assertEqual(self.client.session.get_expiry_age(), 60 * 60)

    def test_the_two_roles_do_not_get_the_same_timeout(self):
        self.client.login(username="staff1", password=PASSWORD)
        staff_age = self.client.session.get_expiry_age()
        self.client.logout()
        self.client.login(username="marcus", password=PASSWORD)
        self.assertNotEqual(staff_age, self.client.session.get_expiry_age())


class SeedDataTests(TestCase):
    """The demo depends on seed_demo producing the right data."""

    def test_seed_creates_packages_and_logins(self):
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Package.objects.count(), 5)
        self.assertTrue(User.objects.filter(username="jmoon").exists())
        self.assertTrue(User.objects.filter(username="mreed").exists())

    def test_seed_creates_two_aged_packages(self):
        """Milestone 1 measures packages held past seven days, so the demo needs some."""
        call_command("seed_demo", verbosity=0)
        aged = [p for p in Package.objects.all() if p.is_aged()]
        self.assertEqual(len(aged), 2)

    def test_every_seeded_package_has_a_custody_entry(self):
        call_command("seed_demo", verbosity=0)
        for pkg in Package.objects.all():
            self.assertGreaterEqual(pkg.custody_log.count(), 1)

    def test_running_seed_twice_does_not_duplicate_data(self):
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Package.objects.count(), 5)


class PackageLifecycleTests(TestCase):
    """A package logged at the desk, held, then collected."""

    def setUp(self):
        self.prop, self.staff, self.marcus, self.dana = make_world()

    def test_a_package_moves_from_held_to_collected(self):
        pkg = log_package(self.marcus, self.staff, days_ago=1)
        CustodyLog.objects.create(
            package=pkg, event=CustodyLog.EVENT_LOGGED,
            actor=self.staff, new_status=Package.STATUS_HELD,
        )
        self.assertEqual(pkg.status, Package.STATUS_HELD)

        previous = pkg.status
        pkg.status = Package.STATUS_PICKED_UP
        pkg.picked_up_at = timezone.now()
        pkg.released_by = self.staff
        pkg.save()
        CustodyLog.objects.create(
            package=pkg, event=CustodyLog.EVENT_PICKED_UP, actor=self.staff,
            previous_status=previous, new_status=pkg.status,
        )

        pkg.refresh_from_db()
        self.assertEqual(pkg.status, Package.STATUS_PICKED_UP)
        self.assertEqual(pkg.custody_log.count(), 2)

    def test_the_earlier_custody_entry_is_unchanged_after_pickup(self):
        """Adding the pickup entry must not rewrite the intake entry."""
        pkg = log_package(self.marcus, self.staff, days_ago=1)
        first = CustodyLog.objects.create(
            package=pkg, event=CustodyLog.EVENT_LOGGED,
            actor=self.staff, new_status=Package.STATUS_HELD,
        )
        original_time = first.occurred_at

        CustodyLog.objects.create(
            package=pkg, event=CustodyLog.EVENT_PICKED_UP, actor=self.staff,
            previous_status=Package.STATUS_HELD, new_status=Package.STATUS_PICKED_UP,
        )

        first.refresh_from_db()
        self.assertEqual(first.event, CustodyLog.EVENT_LOGGED)
        self.assertEqual(first.occurred_at, original_time)
