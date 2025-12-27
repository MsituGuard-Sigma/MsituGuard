from django.core.management.base import BaseCommand
from App.models import County

class Command(BaseCommand):
    help = "Update county coordinates for weather API calls"

    def handle(self, *args, **options):
        # Kenya county coordinates (approximate centers)
        county_coords = {
            "Meru": {"lat": -0.0469, "lon": 37.6556},
            "Nakuru": {"lat": -0.3031, "lon": 36.0800},
            "Machakos": {"lat": -1.5177, "lon": 37.2634},
            "Turkana": {"lat": 3.1167, "lon": 35.5833},
            "Garissa": {"lat": -0.4569, "lon": 39.6582},
            "Mombasa": {"lat": -4.0435, "lon": 39.6682},
            "Nyeri": {"lat": -0.4167, "lon": 36.9500},
            "Kiambu": {"lat": -1.1714, "lon": 36.8356},
            "Embu": {"lat": -0.5314, "lon": 37.4570},
            "Nairobi": {"lat": -1.2921, "lon": 36.8219},
            "Kisumu": {"lat": -0.1022, "lon": 34.7617},
            "Eldoret": {"lat": 0.5143, "lon": 35.2698},
        }

        updated_count = 0
        for county_name, coords in county_coords.items():
            try:
                county = County.objects.get(name=county_name)
                county.latitude = coords["lat"]
                county.longitude = coords["lon"]
                county.save()
                updated_count += 1
                self.stdout.write(f"Updated {county_name}: {coords['lat']}, {coords['lon']}")
            except County.DoesNotExist:
                self.stdout.write(f"County {county_name} not found, skipping")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated coordinates for {updated_count} counties")
        )