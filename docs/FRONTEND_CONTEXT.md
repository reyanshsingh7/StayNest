# Template integration guide (for the frontend developer)

Templates live in the project-level `templates/` folder. Template file names the
views render:

| Template | Rendered by |
|---|---|
| `accounts/register.html` | `register` |
| `accounts/login.html` | `login` |
| `accounts/student_dashboard.html` | `student_dashboard` |
| `accounts/owner_dashboard.html` | `owner_dashboard` |
| `properties/home.html` | `home` |
| `properties/property_list.html` | `property_list` |
| `properties/property_detail.html` | `property_detail` |
| `properties/property_form.html` | `property_create` AND `property_edit` |
| `properties/my_properties.html` | `my_properties` |
| `bookings/my_requests.html` | `my_requests` |
| `bookings/owner_requests.html` | `owner_requests` (extra route) |

## Rules that apply everywhere

* **Every POST form needs `{% csrf_token %}`.**
* **Logout must be a POST form** (a plain link gives "405 Method Not Allowed"):
  `<form method="post" action="{% url 'logout' %}">{% csrf_token %}<button>Log out</button></form>`
* **Property forms with images need `enctype="multipart/form-data"`.**
* **Messages:** loop over `messages`; each has `message.tags`, one of
  `success`, `error`, `warning`, `info`.
* **Role-aware navigation:** use `user.is_authenticated`, `user.is_student`,
  `user.is_owner`, `user.is_staff`, `user.full_name`.
* Use `{% url %}` names only. URL names: `home`, `register`, `login`, `logout`,
  `property_list`, `property_detail` (arg `pk`), `property_create`,
  `property_edit` (arg `pk`), `student_dashboard`, `owner_dashboard`,
  `my_properties`, `my_requests`, `booking_create` (arg `property_id`),
  `booking_cancel` (arg `pk`), `booking_respond` (arg `pk`),
  **plus one extra: `owner_requests`** (the owner's incoming-requests page).
* Property cards: use `property.cover_image` (a `PropertyImage` or `None`; show
  a placeholder when `None`) and `property.amenity_labels` (list of strings).
  `cover_image.image.url` is the picture URL.
* Always loop over the list variables named below (`properties`,
  `booking_requests`), **not** over `page_obj`.
* Status values to style: properties `PENDING`/`APPROVED`/`REJECTED`;
  requests `PENDING`/`ACCEPTED`/`REJECTED`/`CANCELLED`.
* Wording: an accepted request must be described as "accepted by owner", never
  as "booked" or "reserved".

## Page contexts

### `register` and `login`
* `form`. Register fields: `form.full_name`, `form.email`, `form.role` (radio
  buttons), `form.password1`, `form.password2`.
* Login fields: `form.username` (**this holds the email address**) and
  `form.password`. `form.non_field_errors` holds login errors.
* Login can include `<input type="hidden" name="next" value="{{ next }}">`.

### `home`
* `featured_properties` (list of up to 6), `popular_cities` (list of strings),
  `total_properties` (int), `search_form` (use `search_form.city`,
  `search_form.locality`; submit with GET to `property_list`).

### `property_list` (search form uses GET)
* `properties` (list), `page_obj` (`has_previous`, `has_next`,
  `previous_page_number`, `next_page_number`, `number`),
  `paginator.num_pages`, `is_paginated`, `result_count`.
* `filter_form` with fields `city`, `locality`, `property_type`, `min_rent`,
  `max_rent`, `available_only`, `amenities` (checkbox list), `sort`.
* `query_string`: current filters without the page. Pagination links:
  `?{{ query_string }}&page={{ page_obj.next_page_number }}`.
* `has_filters` (bool, to show a "Clear filters" link and an empty-result hint).

### `property_detail`
* `property` (model), `owner_name`, `images` (list), `primary_image`,
  `amenity_labels`.
* `is_owner`, `is_publicly_visible` (False means owner/staff preview of a
  pending/rejected listing: show a status banner; if rejected show
  `property.rejection_reason`), `is_student`.
* Booking box:
  * `can_request_booking` True: show a form (POST to
    `{% url 'booking_create' property.pk %}`) with `booking_form.message`.
  * `booking_block_reason` (string or None): show it instead of the form
    (for example "You already have a pending request").
  * `pending_request`: the student's current pending request or None.
  * `show_login_prompt` True: show "Log in to send a booking request" linking
    to `login`.

### `property_form` (create and edit)
* `form`, `is_edit` (bool), `property` (None on create).
* `form` fields: `name`, `property_type`, `description`, `city`, `locality`,
  `address`, `postal_code`, `monthly_rent`, `is_available`, amenity checkboxes
  (`has_wifi`, `has_meals`, `has_laundry`, `has_ac`, `has_power_backup`,
  `has_parking`, `has_cctv`, `has_housekeeping`), and `new_images`
  (multi-file input).
* Edit only: `existing_images` (list of `PropertyImage`), plus
  `form.delete_images` (checkboxes) and `form.primary_image` (radio buttons)
  to remove images / choose the cover image. `was_approved` (bool): show a note
  that important changes send the listing for approval again.
* Limits for help text: `max_images`, `max_image_size_mb`,
  `allowed_image_extensions`.

### `my_properties`
* `properties` (list; each has `pending_request_count`, `cover_image`),
  `property_counts` (`total`, `approved`, `pending`, `rejected`),
  `status_filter` ("" or `PENDING`/`APPROVED`/`REJECTED`, via `?status=`),
  `has_properties` (empty state), `pending_requests_total`.

### `student_dashboard`
* `request_counts` (`total`, `pending`, `accepted`, `rejected`, `cancelled`),
  `recent_requests` (list of up to 5 requests; `booking.property.cover_image`
  is available), `has_requests`, `suggested_properties` (list of up to 3).

### `owner_dashboard`
* `property_counts` (`total`, `approved`, `pending`, `rejected`),
  `unavailable_count`, `request_counts`, `pending_requests` (up to 5, with
  `.student.full_name` and `.property.name`), `rejected_properties` (list with
  `rejection_reason`), `recent_properties` (list), `has_properties`.

### `my_requests` (student)
* `booking_requests` (list; each has `.property` with `cover_image`, `.status`,
  `.message`, `.created_at`), `status_counts`, `status_filter` (`?status=`),
  `has_requests`.
* Cancel button (only when `booking.status == "PENDING"`):
  `<form method="post" action="{% url 'booking_cancel' booking.pk %}">{% csrf_token %}...`

### `owner_requests` (owner)
* `booking_requests` (each has `.student.full_name`, `.student.email`,
  `.property`, `.status`, `.message`, `.created_at`, `.responded_at`),
  `status_counts`, `status_filter`, `property_filter` (id string or ""),
  `owner_properties` (for a filter dropdown, `?property=<id>`), `has_requests`.
* Buttons (only when `PENDING`):
  `<form method="post" action="{% url 'booking_respond' booking.pk %}">{% csrf_token %}<button name="action" value="accept">Accept</button><button name="action" value="reject">Reject</button></form>`
* Show the student's email only for `ACCEPTED` requests (privacy).
* Optional hidden field `next` (a path on this site) returns the owner to the
  page they came from after responding.

### Error pages
Create `templates/404.html` (and optionally `403.html`, `500.html`). Hidden or
foreign objects return a 404 on purpose.
