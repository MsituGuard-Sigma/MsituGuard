from django.core.management.base import BaseCommand
import pandas as pd
from App.models import LocationClimateData

class Command(BaseCommand):
    help = 'Import climate data from training dataset'
    
    def handle(self, *args, **options):
        # Load training data
        df = pd.read_csv('Tree_Prediction/training/cleaned_tree_data_FINAL.csv')
        
        # Group by county and get averages
        county_data = df.groupby('county').agg({
            'region': 'first',
            'rainfall_mm': 'mean',
            'temperature_c': 'mean', 
            'altitude_m': 'mean',
            'soil_ph': 'mean',
            'soil_type': 'first'
        }).reset_index()
        
        # Import into database
        for _, row in county_data.iterrows():
            LocationClimateData.objects.get_or_create(
                county_name=row['county'],
                defaults={
                    'region': row['region'],
                    'rainfall_mm': row['rainfall_mm'],
                    'temperature_c': row['temperature_c'],
                    'altitude_m': row['altitude_m'],
                    'soil_ph': row['soil_ph'],
                    'soil_type': row['soil_type']
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Climate data imported successfully!'))