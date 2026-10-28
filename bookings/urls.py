from django.urls import path

from . import views

urlpatterns = [
    # Student pages
    path("requests/", views.my_requests, name="my_requests"),
    path("create/<int:property_id>/", views.booking_create, name="booking_create"),
    path("<int:pk>/cancel/", views.booking_cancel, name="booking_cancel"),
    # Owner pages
    path("incoming/", views.owner_requests, name="owner_requests"),
    path("<int:pk>/respond/", views.booking_respond, name="booking_respond"),
]
