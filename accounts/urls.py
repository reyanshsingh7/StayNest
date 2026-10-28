from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.StayNestLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/owner/", views.owner_dashboard, name="owner_dashboard"),
]
