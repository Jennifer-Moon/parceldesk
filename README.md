# ParcelDesk

Package management for small multifamily properties.
MIS 4500 — Bryan Albert, Jennifer Moon, Nicholas Bernier.

Django 6.1 · PostgreSQL (Neon) · Bootstrap 5 · hosted on Render.

---

## Running it locally

```bash
pip install -r requirements.txt
cp .env.example .env          # then edit it
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

With no `DATABASE_URL` set, it uses a local SQLite file. Set
`DATABASE_URL` to the Neon connection string to use Postgres.

### Demo logins

`seed_demo` creates these. Password for all of them is
`ParcelDeskDemo2026`.

| Username | Role |
|---|---|
| jmoon | Staff |
| dwhitfield | Resident |
| mreed | Resident |
| praman | Resident |

Five packages are loaded, two held longer than seven days.
Re-running `seed_demo` rebuilds the data so package ages stay correct;
superuser accounts are left alone.

---

## What is built (Sprint 1)

- Data models: Property, Resident, StaffProfile, Package, CustodyLog, Notification
- Django admin for all of them
- Login and logout, with role-based routing from `/`
- Password rules: 15-character minimum, no composition rules (NIST SP 800-63B)
- Session timeouts by role: staff 15 minutes, residents 60 minutes
- Resident package view, filtered to the signed-in user
- Sample data command

### Sprint 2 and 3 to come

Staff package list with aged highlighting, intake form, mark-picked-up,
and the arrival email. The staff dashboard buttons are visibly disabled
until those views exist.

---

## Design decisions worth knowing

**The custody log is append-only.** `CustodyLog.save()` raises an error
on an existing row and `delete()` raises on any row. A correction is a
new `CORRECTION` entry, the way a ledger records a correcting entry.
The Django admin shows the log read-only for everyone, superusers
included — that is the Milestone 3 rule that no role may edit a custody
record.

A bulk queryset delete still bypasses the guard, which is how
`seed_demo` resets demo data. The protection is at the application
layer; enforcing it in the database would need a trigger.

**`days_held()` is calculated, not stored.** It reads `logged_at` when
called, which is why no background job is needed to age packages.

**Authorization is enforced in the queryset.** Views filter by
`request.user`, never by an identifier from the URL.

---

## Deploying to Render

1. Connect this repo to a new Render Web Service.
2. Build command `./build.sh`, start command
   `gunicorn parceldesk.wsgi:application`.
3. Set these environment variables in the Render dashboard:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | a fresh key, see below |
   | `DATABASE_URL` | the Neon connection string |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | the Render hostname, e.g. `parceldesk.onrender.com` |

Generate a new secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Rotate the secret key.** The original `startproject` key was committed
in the first push and is in the git history, so it must not be used in
production. The new key goes in Render's dashboard only.

`build.sh` runs migrations at deploy time. Run `seed_demo` once from
the Render shell after the first deploy if the demo needs data.

### Free tier limits

- The web service sleeps after 15 minutes idle and takes about a minute
  to wake. Load the page a few minutes before any demonstration.
- Neon's free database does not expire, but it is capped at 0.5 GB of
  storage and 100 compute-hours per month.
