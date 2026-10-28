"""
Root URL configuration for StayNest.

URL layout:
    /admin/        Django Admin (listing moderation)
    /accounts/...  register, login, logout, dashboards   (accounts app)
    /bookings/...  booking requests                      (bookings app)
    /              home, property list/detail/manage     (properties app)
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("bookings/", include("bookings.urls")),
    # The properties app owns the home page, so it is included last at "".
    path("", include("properties.urls")),
]

# Uploaded images.
if settings.DEBUG:
    # Local development.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Demo-level hosting (e.g. Render free plan): Django serves MEDIA_ROOT itself.
    # For a real production site, serve media from object storage or a web
    # server instead. Files here are lost on hosts with temporary disks.
    urlpatterns += [
        re_path(
            r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"),
            serve_media,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
