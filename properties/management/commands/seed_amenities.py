from django.core.management.base import BaseCommand
from django.db.models import Q

from properties.models import DEFAULT_AMENITIES, Amenity


class Command(BaseCommand):
    help = "Create the predefined StayNest amenities. Safe to run repeatedly."

    def handle(self, *args, **options):
        created = 0
        for name, slug in DEFAULT_AMENITIES:
            if Amenity.objects.filter(Q(slug=slug) | Q(name=name)).exists():
                continue
            Amenity.objects.create(name=name, slug=slug)
            created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Amenities ready: {created} created, "
                f"{len(DEFAULT_AMENITIES) - created} already present."
            )
        )
