# Testing plan

## Automated tests (written, not yet run by the author)

Run: `python manage.py test` (or `python manage.py test bookings`).

| File | What it checks |
|---|---|
| `accounts/tests.py` | registration roles; admin role/flags cannot be posted; duplicate and weak passwords; email login; safe `next`; POST-only logout; user manager; dashboard role protection and empty states |
| `properties/tests.py` | unapproved listings hidden (list and detail); search by city/locality; type, rent, availability, amenity filters; sorting; owner-only create/edit; cannot self-approve or change owner; reapproval rules; image type/size/fake-image validation; primary image handling |
| `bookings/tests.py` | login required; students only; approved and available only; one pending per property; re-request after cancel; message length; cancel/respond permissions; final statuses cannot change; accept keeps availability; multiple accepts; unsafe redirect ignored; list pages show own data only |

`accounts/support_for_tests.py` swaps real templates for stand-ins, so these tests check
backend behaviour only. It builds a `Property` using the field names in
`DATABASE_CONTRACT.md`.

## Manual tests
Use section C of `INTEGRATION_CHECKLIST.md`.

## Not covered (known gaps)
* Two simultaneous requests from one student (race condition). SQLite makes this
  very unlikely in a demo; a database constraint on (student, property, pending)
  would fully prevent it (database developer's decision).
* Real template rendering, CSS and JavaScript (frontend developer's tests).
* Performance with large data.
