"""
Custom user model for StayNest.

* Login identifier: email address (not a username).
* Roles: STUDENT or OWNER.
* Administrators are ordinary users with is_staff / is_superuser = True.
  They are created ONLY with "createsuperuser" or inside Django Admin,
  never through public registration.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager that creates users with an email address instead of a username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set.")
        # Emails are stored in lowercase so "A@x.com" and "a@x.com" are one account.
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Django hashes the password
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a normal (non-admin) user."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create an administrator (used by "manage.py createsuperuser")."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        """Used by Django's login system. Case-insensitive email lookup."""
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        OWNER = "OWNER", "Property owner"

    email = models.EmailField("email address", unique=True)
    full_name = models.CharField("full name", max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    is_active = models.BooleanField(default=True)
    # is_staff = may log in to Django Admin. (is_superuser comes from PermissionsMixin.)
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Can log in to the admin site (administrators only).",
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]  # asked by "createsuperuser" besides email/password

    class Meta:
        ordering = ["email"]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER
