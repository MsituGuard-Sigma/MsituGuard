from django.core.management.base import BaseCommand
from App.models import Species, County
import json

class Command(BaseCommand):
    help = 'Load species data into database'

    def handle(self, *args, **options):
        # Clear existing species data
        Species.objects.all().delete()
        
        # Species data with proper defaults
        species_data = [
            {
                'name': 'Eucalyptus',
                'soil': 'Well-drained',
                'rainfall': '600-1200mm',
                'temperature': '15-25°C',
                'care_level': 'Medium',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'Moderate',
                'planting_guide': [
                    'Plant in well-drained soil',
                    'Space trees 3-4 meters apart',
                    'Water regularly for first 6 months'
                ],
                'care_instructions': [
                    'Prune lower branches',
                    'Monitor for pests',
                    'Apply fertilizer annually'
                ]
            },
            {
                'name': 'Pine',
                'soil': 'Acidic, well-drained',
                'rainfall': '800-1500mm',
                'temperature': '10-22°C',
                'care_level': 'Low',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'Low to moderate',
                'planting_guide': [
                    'Choose high altitude areas',
                    'Test soil pH before planting',
                    'Plant in deep soil'
                ],
                'care_instructions': [
                    'Minimal watering needed',
                    'Monitor for fungal diseases',
                    'Thin overcrowded areas'
                ]
            },
            {
                'name': 'Acacia',
                'soil': 'Sandy to loam',
                'rainfall': '400-800mm',
                'temperature': '20-35°C',
                'care_level': 'Low',
                'best_season': 'Short rains',
                'planting_method': 'Seedling',
                'water': 'Low',
                'planting_guide': [
                    'Suitable for arid areas',
                    'Plant in full sun',
                    'Use drought-resistant varieties'
                ],
                'care_instructions': [
                    'Drought tolerant',
                    'Minimal care required',
                    'Natural nitrogen fixer'
                ]
            },
            {
                'name': 'Cypress',
                'soil': 'Well-drained loam',
                'rainfall': '700-1200mm',
                'temperature': '12-22°C',
                'care_level': 'Medium',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'Moderate',
                'planting_guide': [
                    'Plant in cooler areas',
                    'Provide wind protection',
                    'Maintain soil moisture'
                ],
                'care_instructions': [
                    'Regular pruning',
                    'Monitor for cypress aphids',
                    'Mulch base of tree'
                ]
            },
            {
                'name': 'Grevillea',
                'soil': 'Well-drained',
                'rainfall': '600-1000mm',
                'temperature': '15-28°C',
                'care_level': 'Low',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'Low to moderate',
                'planting_guide': [
                    'Fast-growing species',
                    'Plant in open areas',
                    'Good for agroforestry'
                ],
                'care_instructions': [
                    'Minimal maintenance',
                    'Harvest regularly',
                    'Control spread if needed'
                ]
            },
            {
                'name': 'Neem',
                'soil': 'Sandy to clay',
                'rainfall': '400-1200mm',
                'temperature': '20-35°C',
                'care_level': 'Low',
                'best_season': 'Short rains',
                'planting_method': 'Seedling',
                'water': 'Low',
                'planting_guide': [
                    'Drought tolerant',
                    'Medicinal properties',
                    'Plant in warm areas'
                ],
                'care_instructions': [
                    'Very drought resistant',
                    'Pest resistant',
                    'Prune for shape'
                ]
            },
            {
                'name': 'Wattle',
                'soil': 'Acidic soils',
                'rainfall': '800-1500mm',
                'temperature': '15-25°C',
                'care_level': 'Medium',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'Moderate',
                'planting_guide': [
                    'Nitrogen fixing tree',
                    'Good for timber',
                    'Plant in highlands'
                ],
                'care_instructions': [
                    'Fast growing',
                    'Regular pruning',
                    'Monitor for pests'
                ]
            },
            {
                'name': 'Cedar',
                'soil': 'Deep, well-drained',
                'rainfall': '1000-2000mm',
                'temperature': '12-20°C',
                'care_level': 'Medium',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'High',
                'planting_guide': [
                    'High value timber',
                    'Plant in high rainfall areas',
                    'Long-term investment'
                ],
                'care_instructions': [
                    'Regular watering',
                    'Protect from fire',
                    'Monitor for diseases'
                ]
            },
            {
                'name': 'Bamboo',
                'soil': 'Well-drained loam',
                'rainfall': '800-2000mm',
                'temperature': '15-30°C',
                'care_level': 'Medium',
                'best_season': 'Long rains',
                'planting_method': 'Rhizome',
                'water': 'High',
                'planting_guide': [
                    'Fast growing',
                    'Multiple uses',
                    'Plant in clumps'
                ],
                'care_instructions': [
                    'Contain spread',
                    'Harvest regularly',
                    'Divide clumps periodically'
                ]
            },
            {
                'name': 'Casuarina',
                'soil': 'Sandy, coastal',
                'rainfall': '400-1000mm',
                'temperature': '20-35°C',
                'care_level': 'Low',
                'best_season': 'Short rains',
                'planting_method': 'Seedling',
                'water': 'Low',
                'planting_guide': [
                    'Coastal areas',
                    'Wind protection',
                    'Soil stabilization'
                ],
                'care_instructions': [
                    'Salt tolerant',
                    'Drought resistant',
                    'Minimal care'
                ]
            },
            {
                'name': 'Jacaranda',
                'soil': 'Well-drained',
                'rainfall': '600-1200mm',
                'temperature': '15-28°C',
                'care_level': 'Medium',
                'best_season': 'Long rains',
                'planting_method': 'Seedling',
                'water': 'Moderate',
                'planting_guide': [
                    'Ornamental tree',
                    'Beautiful flowers',
                    'Shade provider'
                ],
                'care_instructions': [
                    'Prune for shape',
                    'Clean fallen flowers',
                    'Monitor for pests'
                ]
            },
            {
                'name': 'Indigenous Mix',
                'soil': 'Various',
                'rainfall': '600-1200mm',
                'temperature': '15-30°C',
                'care_level': 'Low',
                'best_season': 'Both seasons',
                'planting_method': 'Mixed',
                'water': 'Low to moderate',
                'planting_guide': [
                    'Native species',
                    'Biodiversity support',
                    'Local ecosystem'
                ],
                'care_instructions': [
                    'Minimal intervention',
                    'Natural growth',
                    'Wildlife support'
                ]
            }
        ]
        
        # Create species
        created_count = 0
        for species_info in species_data:
            species, created = Species.objects.get_or_create(
                name=species_info['name'],
                defaults=species_info
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created species: {species.name}")
            else:
                self.stdout.write(f"Species already exists: {species.name}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {created_count} new species')
        )
