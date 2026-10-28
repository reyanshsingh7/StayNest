# Integration checklist

Nothing in this project has been executed by the author of this code (no Django
was available when it was written). Treat the first run as the first test.

## A. Put the files together
- [ ] Create the project folder, the virtual environment and install `requirements.txt`.
- [ ] Copy these backend files in (they are already in the right folders).
- [ ] Database developer adds: `properties/models.py`, `properties/admin.py`,
      `bookings/models.py`, `bookings/admin.py` (and the `__init__.py` files if missing).
- [ ] Frontend developer adds `templates/` and `static/`.
- [ ] Compare the models with `docs/DATABASE_CONTRACT.md` (field names, status values,
      amenity fields). Differences are fixed in `properties/services.py` or
      `bookings/services.py`.
- [ ] Copy `.env.example` to `.env`.

## B. First run
```bash
python manage.py check
python manage.py makemigrations accounts properties bookings
python manage.py migrate
python manage.py createsuperuser
python manage.py test
python manage.py runserver
```
- [ ] `check` shows no errors. Typical first errors and meanings:
  * `ImportError ... properties.models` -> models file missing or misnamed.
  * `FieldError / KeyError 'has_wifi'` -> amenity field names differ.
  * `TemplateDoesNotExist` -> template name differs from `FRONTEND_CONTEXT.md`.
- [ ] `python manage.py test` passes (the tests use stand-in templates).
- [ ] Delete `db.sqlite3` and all `migrations/0*.py` files if you ever ran `migrate`
      before `AUTH_USER_MODEL` existed, then repeat the commands above.

## C. Manual walk-through (do this before the demo)
1. [ ] Register a student and an owner (two browsers or one private window).
2. [ ] Owner creates a property with 2 images. It must show as pending.
3. [ ] The home page and list do NOT show it. Its URL gives 404 when logged out.
4. [ ] In `/admin/` approve it. It now appears publicly.
5. [ ] Search, filter and sort on the list page.
6. [ ] Logged-out visitor sees a "log in" prompt on the detail page.
7. [ ] Student sends a request. A second request to the same property is refused.
8. [ ] Owner opens incoming requests, accepts. The property stays available.
9. [ ] Another student requests and is also accepted (multiple accepts are allowed).
10. [ ] Student cancels a pending request, then can send a new one.
11. [ ] Owner edits rent on the approved property -> status returns to pending.
12. [ ] Owner changes only availability -> stays approved.
13. [ ] Owner marks it unavailable -> students cannot request.
14. [ ] Student URL-hacks `/properties/<id>/edit/` -> 404. Student opens owner pages -> redirected.
15. [ ] Upload a `.txt` or a huge file -> clear error.
16. [ ] Log out works (POST button).

## D. Before deployment
- [ ] `DJANGO_DEBUG=False`, a real `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` set.
- [ ] `python manage.py check --deploy`
- [ ] Web server serves `media/` and `staticfiles/` (run `collectstatic`).
- [ ] `.env`, `db.sqlite3`, `media/` are not in Git.
