"""Forms for registration and login."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User

# Only these two roles can be chosen at registration.
# There is deliberately NO administrator option.
REGISTRATION_ROLE_CHOICES = [
    (User.Role.STUDENT, "Student - I am looking for a hostel or PG"),
    (User.Role.OWNER, "Property owner - I want to list my property"),
]


class RegistrationForm(forms.ModelForm):
    """Sign-up form for students and property owners."""

    role = forms.ChoiceField(
        choices=REGISTRATION_ROLE_CHOICES,
        widget=forms.RadioSelect,
        label="I am a",
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        # Only these model fields can be set by the visitor.
        # is_staff / is_superuser are NOT here, so they can never be posted.
        fields = ["full_name", "email", "role"]
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_full_name(self):
        full_name = " ".join(self.cleaned_data["full_name"].split())
        if len(full_name) < 2:
            raise ValidationError("Please enter your full name.")
        return full_name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_role(self):
        # Defence in depth: ChoiceField already limits the value.
        role = self.cleaned_data["role"]
        if role not in (User.Role.STUDENT, User.Role.OWNER):
            raise ValidationError("Please choose Student or Property owner.")
        return role

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned_data

    def _post_clean(self):
        # Runs after the model instance is filled, so the similarity validator
        # can compare the password with the email and name.
        super()._post_clean()
        password = self.cleaned_data.get("password2")
        if password and not self.errors.get("password2"):
            try:
                validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password2", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        # Never allow administrator rights from public registration.
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """Login form that asks for an email address.

    Django's base form names the first field "username"; it holds the email.
    """

    error_messages = {
        "invalid_login": "Incorrect email or password. Please try again.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email address"
        self.fields["username"].widget = forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email"}
        )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
