# What the backend code expects from the database developer

My code (views, forms, services, tests) is written against this contract. It has
**not been run against your real models**. Compare your models with this page.
If something differs, change it in **one place** (listed in the last column) or
tell me.

## General

* All user foreign keys use `settings.AUTH_USER_MODEL`.
* Status fields store the **upper-case strings** below.
* `created_at` uses `auto_now_add=True`; `updated_at` uses `auto_now=True`.

## `properties.models.Property`

| Field | Type / values | Needed by |
|---|---|---|
| `owner` | FK to user | `properties/forms.py`, views |
| `name` | CharField | form |
| `property_type` | CharField with `choices` `HOSTEL`, `PG` | `PropertyFilterForm` reads `Property._meta.get_field("property_type").choices` |
| `description` | TextField | form |
| `city`, `locality` | CharField | search |
| `address` | CharField or TextField | form |
| `postal_code` | CharField (max 6+) | form checks it is 6 digits |
| `monthly_rent` | DecimalField or PositiveIntegerField | form checks `> 0` and `<= 500000` |
| `approval_status` | CharField, values `PENDING`, `APPROVED`, `REJECTED`, default `PENDING` | `properties/services.py` |
| `is_available` | BooleanField, default `True` | filters, booking rule |
| `rejection_reason` | TextField/CharField, `blank=True` (null allowed) | cleared with `""` on resubmission |
| `created_at`, `updated_at` | DateTimeField | sorting |
| **Amenities** | one `BooleanField(default=False)` each: `has_wifi`, `has_meals`, `has_laundry`, `has_ac`, `has_power_backup`, `has_parking`, `has_cctv`, `has_housekeeping` | `AMENITY_FIELDS` in `properties/services.py` |

Amenity design is my assumption. If you use another design (for example a
many-to-many table), tell me, because forms and filters must change.

## `properties.models.PropertyImage`

| Field | Notes |
|---|---|
| `property` | FK to Property (field name must be `property`) |
| `image` | ImageField (`upload_to` of your choice) |
| `is_primary` | BooleanField, default `False` |
| `display_order` | PositiveIntegerField, default `0` |

Ordering used by my code: `display_order`, then `id`. Exactly one primary image
per property is maintained by `PropertyForm`.

## `bookings.models.BookingRequest`

| Field | Notes |
|---|---|
| `student` | FK to user |
| `property` | FK to Property |
| `status` | CharField, values `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED`, default `PENDING` (`bookings/services.py`) |
| `message` | TextField, `blank=True` (my form limits it to 300 characters) |
| `created_at`, `updated_at` | auto timestamps |
| `responded_at` | DateTimeField, `null=True, blank=True` |

## Admin (your files)

* `properties/admin.py` must let an administrator set `approval_status` and
  `rejection_reason`. Approve/Reject bulk actions are recommended.
* Include `owner`, `approval_status`, `city` in `list_display` and `list_filter`
  so moderation is easy.
* `bookings/admin.py`: register `BookingRequest` (read-only status is wise).

## Migrations

Because `AUTH_USER_MODEL = "accounts.User"`, create migrations for all apps
together **before the first `migrate`**:

```bash
python manage.py makemigrations accounts properties bookings
python manage.py migrate
```
