# StayNest frontend (templates + static assets)

Owner: Rishi Singh (frontend / UI-UX). Stack: Django templates, HTML, CSS, vanilla JavaScript only.
Extract this ZIP into the **project root** (the folder containing `manage.py`) so that `templates/` and `static/` merge with the project.

## Folder structure

```
templates/
  base.html                      shared layout (nav, messages, footer)
  home.html
  accounts/login.html, register.html
  properties/property_list.html, property_detail.html, property_form.html, my_properties.html
  bookings/student_dashboard.html, owner_dashboard.html, my_requests.html
  partials/_field.html           one form field with label + errors
            _status_badge.html   status pill (pending/accepted/...)
            _property_card.html  property card used on home and list
            _booking_item.html   student's booking request row
            _owner_request_item.html  owner's booking request row (accept/reject)
static/css/style.css             all styling (no frameworks, no external fonts)
static/js/main.js                nav toggle, dismissible messages, confirm prompts,
                                 double-submit guard, gallery, image preview, filter collapse
```

## settings.py requirements (project lead)

```python
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
# context_processors must include request, auth and messages (Django defaults do)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"; MEDIA_ROOT = BASE_DIR / "media"   # property images
# urls.py (DEBUG only): + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
LOGIN_URL = "login"
```

## Route names and arguments

| Name | Arguments | Used for |
|---|---|---|
| home, register, login, logout | none | logout is a **POST** form (Django 5 LogoutView) |
| property_list | none | GET filters, see below |
| property_detail | `pk` (Property) | |
| property_create | none | |
| property_edit | `pk` (Property) | |
| student_dashboard, owner_dashboard, my_properties, my_requests | none | |
| booking_create | `pk` (**Property** pk) | POST `move_in_date`, `message` |
| booking_cancel | `pk` (**Booking** pk) | POST, no fields |
| booking_respond | `pk` (**Booking** pk) | POST `action` = `accept` or `reject` |

Login links append `?next=<current path>`; the login view should honour `next`.

## Assumptions about the user model

- `user.role` is `"student"` or `"owner"` (nav, dashboards and detail page branch on it).
- `user.email` exists. `user.get_full_name` is optional; the templates fall back to the email.

## Model fields and values the templates read

**Property**: `pk, name, property_type (+ get_property_type_display), description, city, locality, address, postal_code, monthly_rent, is_available (bool), status ('pending' | 'approved' | 'rejected', + get_status_display), owner, amenities (M2M, each has .name), images (related manager of images, each has .image), primary_image` (a property/method returning one image object or None; `img.image.url` is used).
**Booking**: `pk, property, student, status ('pending' | 'accepted' | 'rejected' | 'cancelled', + get_status_display), move_in_date (nullable date), message, created_at`.
Status values are used as CSS classes (`badge-pending`, `badge-accepted`, `badge-approved`, ...). Keep them lowercase.

## Context variables per template

| Template | Variables |
|---|---|
| home.html | `featured_properties` (approved, recent; may be empty), optional `property_type_choices` (list of `(value, label)`; falls back to hostel/pg) |
| property_list.html | `properties` (list or `page_obj`), optional `page_obj`, `query_string` (current GET params without `page`, urlencoded), `amenities` (all Amenity objects), `selected_amenities` (list of **strings** of chosen amenity ids), optional `property_type_choices` |
| property_detail.html | `property`; optional `existing_booking` (the logged-in student's active request for this property), optional `booking_form` (to re-show errors) |
| property_form.html | `form` (ModelForm), `property` (only when editing) |
| my_properties.html | `properties` (owner's own, any status) |
| student_dashboard.html | `bookings` (this student's requests, newest first) |
| my_requests.html | `bookings` (this student's requests, newest first) |
| owner_dashboard.html | `properties` (owner's), `booking_requests` (requests for owner's properties, newest first) |
| login.html / register.html | `form`; `next` (LoginView provides it) |

## Query parameters on property_list

`city, locality, property_type, min_rent, max_rent, amenities` (repeat the key; ids), `include_unavailable=1` (default: hide unavailable), `sort` = `newest` (default) | `rent_asc` | `rent_desc`, `page`.

## Form field names

- **register**: rendered by looping `form.visible_fields`, so any field names work. Needs fields for full name, email, password, password confirmation, and a role choice (Student/Owner only, never admin).
- **login**: same loop; needs email + password fields (e.g. a custom AuthenticationForm labelled "Email").
- **property_form**: `name, property_type, description, city, locality, address, postal_code, monthly_rent, is_available, amenities`. `amenities` must use `CheckboxSelectMultiple`.
  Images are a raw `<input type="file" name="images" multiple>`: read them with `request.FILES.getlist("images")`. Errors are shown from `form.images.errors` if you add that field. The form already has `enctype="multipart/form-data"`.
  Optional: checkboxes named `delete_images` (values = image pk) are sent on edit to remove existing photos. Ignore them if you do not support that.
  The UI says "the first photo is used as the cover"; make the first uploaded image the primary one, or change that sentence.
- **booking_create** POST: `move_in_date` (date, optional), `message` (optional, max 500).

## Backend work implied by the UI

1. `property_list` view needs the filter/sort params above and should pass the context listed.
2. Editing a rejected listing should reset it to `pending` (UI text says "save to submit it again"); change the text if you do not do this.
3. Cancel/respond views must enforce ownership and pending-only status on the server; the buttons only appear for pending requests.
4. Owners see requester name and email on their own requests only. Do not pass other users' data.
5. Use `messages.success/error` in views; `base.html` renders them.

## Notes

- No fake data, statistics or payment screens. Accepted requests are described as "not a paid or guaranteed reservation".
- Currency is shown as rupees (₹). Change the `&#8377;` entity in templates if needed.
- The JavaScript is optional: filters, forms, cancel/accept/reject all work as plain server-rendered pages.
- Validation of templates was done by static checks (tag balance, route names, includes, static paths, CSRF tokens). Django was not available in the build environment, so run the pages once against real views.
