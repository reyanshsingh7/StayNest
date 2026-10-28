# StayNest

A Django hostel/PG discovery and booking-request platform. Property owners list their PGs and hostels; students browse, filter, and send booking requests. An administrator approves listings before they go public.

**Tech stack:** Python 3.11+, Django 5.2, SQLite, server-rendered HTML/CSS/vanilla JS. No React, Tailwind, or Bootstrap.

---

## Prerequisites

- Windows 10/11 (or any OS with Python 3.11+)
- Python 3.11 or 3.12 (64-bit) installed from [python.org](https://python.org) – tick **"Add Python to PATH"**
- Internet access for first-time package installation

---

## Windows setup (PowerShell)

```powershell
# 1. Clone / unzip the project, then enter its directory
cd StayNest_unified

# 2. Create a virtual environment
py -3.12 -m venv .venv

# 3. Activate it
.\.venv\Scripts\Activate.ps1

# 4. Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 5. Copy the example env file and edit it
Copy-Item .env.example .env
```

Open `.env` and set at minimum (`.env.example` documents every supported variable):

```dotenv
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=replace-this-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Generate a secret key with:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Database and initial data

```powershell
# Apply the migrations that ship with the project
python manage.py migrate

# Load the predefined amenity list (Wi-Fi, Laundry, …)
python manage.py seed_amenities
```

---

## Verification

```powershell
# Django system check (should report 0 issues)
python manage.py check

# Run all tests
python manage.py test

# Confirm no pending migrations
python manage.py makemigrations --check
```

---

## Create a superuser (administrator)

```powershell
python manage.py createsuperuser
```

The admin can approve listings at `http://127.0.0.1:8000/admin/` → **Properties → Properties → select → Action: Approve selected**.

---

## Run the development server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

---

## User roles

| Role | How to create | What they can do |
|------|--------------|-----------------|
| Student | Public `/accounts/register/` | Browse properties, send booking requests, cancel pending requests |
| Owner | Public `/accounts/register/` | Create/edit listings, respond to booking requests |
| Administrator | `python manage.py createsuperuser` | Approve / reject pending listings via Django Admin |

---

## End-to-end workflow

1. **Register** as an owner → add a property → it goes to *Pending* status
2. **Log in as admin** at `/admin/` → approve the listing
3. **Register** as a student → browse properties → open a listing → send a booking request
4. **Log in as owner** → *Dashboard* → see incoming requests → Accept or Reject
5. **Log in as student** → *My requests* → Cancel a pending request

---

## Project layout

```
StayNest_unified/
├── accounts/          # Custom email-login user model (Student / Owner roles)
├── bookings/          # BookingRequest model, forms, views
├── config/            # Django project settings, root URL config
├── properties/        # Property, Amenity, PropertyImage models; public and owner views
│   └── management/commands/seed_amenities.py
├── static/            # CSS and JS source files
├── templates/         # All server-rendered templates
├── docs/              # Development-time integration notes
├── .env.example       # Environment variable template
├── .gitignore
├── manage.py
└── requirements.txt
```

---

## Key design decisions

- **No payments.** An accepted booking request is a message of intent only, not a reservation.
- **Approval workflow.** New and edited listings go to *pending*; an admin approves or rejects them.
- **Amenities as M2M.** `Property.amenities` is a `ManyToManyField` to `Amenity`; no boolean convenience fields.
- **Lowercase status values.** Both `Property.ApprovalStatus` and `BookingRequest.Status` use lowercase choices (`draft`, `pending`, `approved`, `rejected`, `accepted`, `cancelled`).
- **Image ordering by `sort_order`.** `PropertyImage` uses `sort_order` (not `display_order`).
- **No `move_in_date` or `responded_at`.** `BookingRequest` only tracks `message`, `status`, `created_at`, `updated_at`.

---

## Deploying on Render (free plan, demo)

1. Push the repository to GitHub, then create a **New Web Service** on [Render](https://render.com) from it.
2. Settings: Language **Python 3**, Build Command `./build.sh`, Start Command `gunicorn config.wsgi:application`, Instance type **Free**.
3. Environment variables (Render dashboard):

| Variable | Value |
|----------|-------|
| `DJANGO_SECRET_KEY` | a new long random value |
| `DJANGO_DEBUG` | `False` |
| `PYTHON_VERSION` | a full 3.12 version, e.g. `3.12.3` |
| `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_FULL_NAME`, `DJANGO_SUPERUSER_PASSWORD` | optional: creates an admin during each build |

Render sets `RENDER_EXTERNAL_HOSTNAME` automatically, and the settings add it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

**Limitation:** this project uses SQLite and local `media/` storage. On the free plan, data created while the site is running (registrations, listings, bookings, uploaded photos) is expected to be lost when the service restarts or redeploys. Accounts created by `build.sh` survive because they are part of the build. For persistent data, use Render PostgreSQL and external media storage (not set up here). Free services also sleep when idle, so the first request can be slow.

## Git and security notes

- `.env`, `db.sqlite3`, `media/` (uploaded images), `.venv/` and `staticfiles/` are git-ignored and must never be committed. Each developer creates their own local copies.
- Without `DJANGO_DEBUG=True`, the app refuses to start unless `DJANGO_SECRET_KEY` is set, and enables HTTPS-only cookies and redirects. Keep `DJANGO_DEBUG=True` for local development only.
- Before any real deployment, set a new secret key, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, and serve over HTTPS. This project has not been deployment-hardened.
- The `docs/` folder holds development-time integration notes written while the team merged their parts; some details there (e.g. upper-case status values, partial file names) are out of date. This README is the current reference.

## Contributors

- Rishi Singh: frontend / UI-UX (templates and static assets), per `docs/FRONTEND_README.md`.

Other contributors and roles are not recorded in the project files; add them here.

## License

No license has been selected yet. Add a `LICENSE` file if you want others to be able to reuse the code.

---

## Feature: Gender-Specific Accommodation

### What it does

Owners can specify who their property is intended for:

| Choice | Value | Display |
|--------|-------|---------|
| Girls Only | `girls` | Girls Only |
| Boys Only | `boys` | Boys Only |
| Co-ed / All Genders | `all` | Co-ed / All Genders (default) |

This is owner-provided information displayed as-is. StayNest does not independently verify accommodation policies.

### Where it appears

| Location | What you see |
|----------|-------------|
| **Home page** | Three quick-filter shortcuts in the hero section (Girls' Hostels & PGs, Boys' Hostels & PGs, Co-ed / All Genders) |
| **Property listing** | "Accommodation for" dropdown filter in the left sidebar; accommodation badge on every property card |
| **Property detail page** | "Accommodation policy" section below Amenities |
| **Property create / edit form** | "Who can stay here?" dropdown between Property type and Monthly rent |
| **Django Admin** | `accommodation_for` column in the property list and in the list filter sidebar |

### Browsing without filtering

Students do **not** need to state their own gender. The filter is optional — all accommodation types are shown when no filter is selected.

### Migration

If setting up from scratch, the existing migration covers this field:

```powershell
python manage.py migrate
```

If upgrading an existing database that already has `properties 0001_initial` applied:

```powershell
python manage.py migrate properties 0002_add_accommodation_for
```

Existing records default to `all` (Co-ed / All Genders).

### Modified files (Gender-Specific Accommodation feature)

| File | Change |
|------|--------|
| `properties/models.py` | Added `AccommodationFor` TextChoices inner class; added `accommodation_for` field |
| `properties/migrations/0002_add_accommodation_for.py` | Migration for the new field |
| `properties/forms.py` | Added `accommodation_for` to `PropertyForm.Meta.fields`; added `accommodation_for` filter to `PropertyFilterForm` |
| `properties/services.py` | Added `accommodation_for` to `SIGNIFICANT_FIELDS` |
| `properties/admin.py` | Added `accommodation_for` to `list_display`, `list_filter`, and fieldsets |
| `properties/tests.py` | Full test suite for the feature (16 new tests) |
| `accounts/support_for_tests.py` | Added `accommodation_for` to `valid_property_data` helper |
| `templates/home.html` | Added Girls/Boys/Co-ed shortcut links in hero section |
| `templates/properties/property_list.html` | Added "Accommodation for" filter dropdown |
| `templates/properties/property_form.html` | Added "Who can stay here?" field to Basic details fieldset |
| `templates/properties/property_detail.html` | Added "Accommodation policy" section |
| `templates/partials/property_card.html` | Added accommodation badge; fixed empty-queryset template error |
| `templates/partials/owner_property_card.html` | Fixed empty-queryset template error |
| `static/css/style.css` | Added badge styles for `badge--accom-*` and `accom-shortcut` components |
