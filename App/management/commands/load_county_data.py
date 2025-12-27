from django.core.management.base import BaseCommand
from App.models import County, CountyEnvironment

class Command(BaseCommand):
    help = 'Load county data into database'

    def handle(self, *args, **options):
        # Clear existing county data
        County.objects.all().delete()
        CountyEnvironment.objects.all().delete()
        
        # Kenya counties with coordinates
        county_data = [
            {'name': 'Nairobi', 'latitude': -1.2921, 'longitude': 36.8219, 'region': 'Central'},
            {'name': 'Mombasa', 'latitude': -4.0435, 'longitude': 39.6682, 'region': 'Coastal'},
            {'name': 'Kisumu', 'latitude': -0.0917, 'longitude': 34.7680, 'region': 'Western'},
            {'name': 'Nakuru', 'latitude': -0.3031, 'longitude': 36.0800, 'region': 'Rift Valley'},
            {'name': 'Eldoret', 'latitude': 0.5143, 'longitude': 35.2694, 'region': 'Rift Valley'},
            {'name': 'Kitale', 'latitude': 1.0151, 'longitude': 35.0058,attice': 'Rift Valley'},
            {'name': 'Garissa', 'latitude': -0.4569, 'longitude': 39.6458, 'region': 'North Eastern'},
            {'name': 'Kakuma', 'latitude': 3.7167, 'longitude': 34.8833, 'region': 'North Eastern'},
            {'name': 'Lodwar', 'latitude': 3.1236, 'longitude': 35.5977, 'region': 'North Eastern'},
            {'name': 'Mandera', 'latitude': 3.9379, 'longitude': 41.8569, 'region': 'North Eastern'},
            {'name': 'Wajir', 'latitude': 1.7471, 'longitude': 40.0686, 'region': 'North Eastern'},
            {'name': 'Marsabit', 'latitude': 2.3286, 'longitude': 37.9892, 'region': 'North Eastern'},
            {'name': 'Isiolo', 'latitude': 0.3549, 'longitude': 37.5821, 'region': 'North Eastern'},
            {'name': 'Meru', 'latitude': 0.0476, 'longitude': 37.6498, 'region': 'Eastern'},
            {'name': 'Embu', 'latitude': -0.5312, 'longitude': 37.4506, 'region': 'Eastern'},
            {'name': 'Kitui', 'latitude': -1.3742, 'longitude': 38.0106, 'region': 'Eastern'},
            {'name': 'Machakos', 'latitude': -1.5174, 'longitude': 37.2625, 'region': 'Eastern'},
            {'name': 'Makueni', 'latitude': -1.7963, 'longitude': 37.6292, 'region': 'Eastern'},
            {'name': 'Tharaka', 'latitude': 0.3549, 'longitude': 37.5821, 'region': 'Eastern'},
            {'name': 'Nyeri', 'latitude': -0.4236, 'longitude': 36.9519, 'region': 'Central'},
            {'name': 'Kirinyaga', 'latitude': -0.4832, 'longitude': 37.1496, 'region': 'Central'},
            {'name': 'Muranga', 'latitude': -0.8563, 'longitude': 37.1545, 'region': 'Central'},
            {'name': 'Kiambu', 'latitude': -1.1833, 'longitude': 36.9333, 'region': 'Central'},
            {'name': 'Turkana', 'latitude': 2.9235, 'longitude': 35.1728, 'region': 'Rift Valley'},
            {'name': 'West Pokot', 'latitude': 1.2833, 'longitude': 35.1167, 'region': 'Rift Valley'},
            {'name': 'Samburu', 'latitude': 1.0167, 'longitude': 37.5833, 'region': 'Rift Valley'},
            {'name': 'Trans Nzoia', 'latitude': 1.0833, 'longitude': 35.0000, 'region': 'Rift Valley'},
            {'name': 'Uasin Gishu', 'latitude': 0.5167, 'longitude': 35.2833, 'region': 'Rift Valley'},
            {'name': 'Elgeyo Marakwet', 'latitude': 1.0000, 'longitude': 35.5000, 'region': 'Rift Valley'},
            {'name': 'Nandi', 'latitude': 0.2500, 'longitude': 35.0833, 'region': 'Rift Valley'},
            {'name': 'Baringo', 'latitude': 0.7500, 'longitude': 35.9333, 'region': 'Rift Valley'},
            {'name': 'Laikipia', 'latitude': 0.7500, 'longitude': 36.8333, 'region': 'Rift Valley'},
            {'name': 'Nakuru', 'latitude': -0.3031, 'longitude': 36.0800, 'region': 'Rift Valley'},
            {'name': 'Bomet', 'latitude': -0.7833, 'longitude': 35.3500, 'region': 'Rift Valley'},
            {'name': 'Kericho', 'latitude': -0.3667, 'longitude': 35.2833, 'region': 'Rift Valley'},
            {'name': 'Kajiado', 'latitude': -1.8333, 'longitude: 36.8333, 'region': 'Rift Valley'},
            {'name': 'Kwale', 'latitude': -4.1833, 'longitude': 39.4500, 'region': 'Coastal'},
            {'name': 'Kilifi', 'latitude': -3.6333, 'longitude': 39.8500, 'region': 'Coastal'},
            {'name': 'Tana River', 'latitude': -1.5000, 'longitude': 40.0000, 'region': 'Coastal'},
            {'name': 'Lamu', 'latitude': -2.2667, 'longitude: 40.9000, 'region': 'Coastal'},
            {'name': 'Taita Taveta', 'latitude': -3.3333, 'longitude': 38.3333, 'region': 'Coastal'},
            {'name': 'Garissa', 'latitude': -0.4569, 'longitude': 39.6458, 'region': 'North Eastern'},
            {'name': 'Wajir', 'latitude': 1.7471, 'longitude': 40.0686, 'region': 'North Eastern'},
            {'name': 'Mandera', 'latitude': 3.9379, 'longitude': 41.8569, 'region': 'North Eastern'},
            {'name': 'Marsabit', 'latitude': 2.3286, 'longitude': 37.9892, 'region': 'North Eastern'},
            {'name': 'Isiolo', 'latitude': 0.3549, 'longitude': 37.5821, 'region': 'North Eastern'},
            {'name': 'Meru', 'latitude': 0.0476, 'longitude': 37.6498, 'region': 'Eastern'},
            {'name': 'Tharaka', 'latitude': -0.0333, 'longitude': 37.6667, 'region': 'Eastern'},
            {'name': 'Embu', 'latitude': -0.5312, 'longitude': 37.4506, 'region': 'Eastern'},
            {'name': 'Kitui', 'latitude': -1.3742, 'longitude': 38.0106, 'region': 'Eastern'},
            {'name': 'Machakos', 'latitude': -1.5174, 'longitude': 37.2625, 'region': 'Eastern'},
            {'name': 'Makueni', 'latitude': -1.7963, 'longitude': 37.6292, 'region': 'Eastern'},
            {'name': 'Nyandarua', 'latitude': -0.2500, 'longitude': 36.7500, 'region': 'Central'},
            {'name': 'Nyeri', 'latitude': -0.4236, 'longitude': 36.9519, 'region': 'Central'},
            {'name': 'Kirinyaga', 'latitude': -0.4832, 'longitude': 37.1496, 'region': 'Central'},
            {'name': 'Muranga', 'latitude': -0.8563, 'longitude': 37.1545, 'region': 'Central'},
            {'name': 'Kiambu', 'latitude': -1.1833, 'longitude': 36.9333, 'region': 'Central'},
            {'name': 'Turkana', 'latitude': 2.9235, 'longitude': 35.1728, 'region': 'Rift Valley'},
            {'name': 'West Pokot', 'latitude': 1.2833, 'longitude': 35.1167, 'region': 'Rift Valley'},
            {'name': 'Samburu', 'latitude': 1.0167, 'longitude': 37.5833, 'region': 'Rift Valley'},
            {'name': 'Trans Nzoia', 'latitude': 1.0833, 'longitude': 35.0000, 'region': 'Rift Valley'},
            {'name': 'Uasin Gishu', 'latitude': 0.5167, 'longitude': 35.2833, 'region': 'Rift Valley'},
            {'name': 'Elgeyo Marakwet', 'latitude': 1.0000, 'longitude': 35.5000, 'region': 'Rift Valley'},
            {'name': 'Nandi', 'latitude': 0.2500, 'longitude': 35.0833, 'region': 'Rift Valley'},
            {'name': 'Baringo', 'latitude': 0.7500, 'longitude': 35.9333, 'region': 'Rift Valley'},
            {'name': 'Laikipia', 'latitude': 0.7500, 'longitude': 36.8333, 'region': 'Rift Valley'},
            {'name': 'Nakuru', 'latitude': -0.3031, 'longitude': 36.0800, 'region': 'Rift Valley'},
            {'name': 'Bomet', 'latitude': -0.7833, 'longitude': 35.3500, 'region': 'Rift Valley'},
            {'name': 'Kericho', 'latitude': -0.3667, 'longitude': 35.2833, 'region': 'Rift Valley'},
            {'name': 'Kajiado', 'latitude': -1.8333, 'longitude': 36.8333, 'region': 'Rift Valley'}
        ]
        
        # Create counties
        created_count = 0
        for county_info in county_data:
            county, created = County.objects.get_or_create(
                name=county_info['name'],
                defaults={
                    'latitude': county_info['latitude'],
                    'longitude': county_info['longitude']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created county: {county.name}")
            else:
                self.stdout.write(f"County already exists: {county.name}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {created_count} counties')
        )
