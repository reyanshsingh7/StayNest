"""Registration, login, logout and the two role dashboards."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from bookings.models import BookingRequest
from bookings.services import STATUS_PENDING, count_by_status
from properties.models import Property
from properties.services import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    attach_display_data,
    count_by_approval,
)

from .forms import EmailAuthenticationForm, RegistrationForm
from .permissions import dashboard_url_name, owner_required, student_required


def register(request):
    """Create a STUDENT or OWNER account, log the user in, go to their dashboard."""
    if request.user.is_authenticated:
        return redirect(dashboard_url_name(request.user))

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to StayNest, {user.get_short_name()}! Your account is ready.")
            return redirect(dashboard_url_name(user))
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


class StayNestLoginView(LoginView):
    """Email + password login. Sends each role to its own dashboard."""

    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # "?next=" is honoured only when Django says it is a safe address.
        return self.get_redirect_url() or reverse(dashboard_url_name(self.request.user))

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().get_short_name()}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Login failed. Please check your email and password.")
        return super().form_invalid(form)


@require_POST
def logout_view(request):
    """Log out. POST only (so other sites cannot log users out with a link)."""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("home")


@student_required
def student_dashboard(request):
    """Summary for a student: request counts, latest requests, suggestions."""
    own_requests = BookingRequest.objects.filter(student=request.user)
    recent_requests = list(
        own_requests.select_related("property").order_by("-created_at", "-id")[:5]
    )
    attach_display_data([booking.property for booking in recent_requests])
    counts = count_by_status(own_requests)

    context = {
        "bookings": recent_requests,
        "total_count": counts["total"],
        "pending_count": counts["pending"],
        "accepted_count": counts["accepted"],
    }
    return render(request, "bookings/student_dashboard.html", context)


@owner_required
def owner_dashboard(request):
    """Summary for an owner: listing statuses and incoming requests."""
    own_properties = Property.objects.filter(owner=request.user)
    incoming = BookingRequest.objects.filter(property__owner=request.user)

    pending_requests = list(
        incoming.filter(status=STATUS_PENDING)
        .select_related("property", "student")
        .order_by("-created_at", "-id")[:5]
    )
    recent_properties = list(
        attach_display_data(own_properties.order_by("-created_at", "-id")[:4])
    )
    approval_counts = count_by_approval(own_properties)
    request_counts = count_by_status(incoming)

    context = {
        "booking_requests": pending_requests,
        "properties": recent_properties,
        "property_count": approval_counts["total"],
        "approved_count": approval_counts["approved"],
        "pending_approval_count": approval_counts["pending"],
        "pending_requests_count": request_counts["pending"],
    }
    return render(request, "bookings/owner_dashboard.html", context)
