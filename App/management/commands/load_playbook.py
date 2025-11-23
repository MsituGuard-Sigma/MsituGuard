from django.core.management.base import BaseCommand
from App.models import County, Species, CountySpecies, CountyEnvironment

class Command(BaseCommand):
    help = "Load the enhanced tree planting playbook into the database"

    def handle(self, *args, **options):

        # REALISTIC SPECIES-COUNTY-SEASON COMPATIBILITY MAP
        county_species_compatibility = {
            "Meru": {
                "Indigenous Mix": {
                    "survival_rate": 85.0,
                    "rank": 1,
                    "match_score": 98,
                    "seasonal_bonus": {"March-May": 8, "Oct-Dec": 5, "June-Sept": -15},
                    "why_good": "Native highland species - perfectly adapted to Meru's climate and soil"
                },
                "Grevillea": {
                    "survival_rate": 78.0,
                    "rank": 2,
                    "match_score": 85,
                    "seasonal_bonus": {"Oct-Dec": 12, "March-May": 6, "June-Sept": -18},
                    "why_good": "Thrives in Meru's highland conditions, especially during short rains (Oct-Dec)"
                },
                "Pine": {
                    "survival_rate": 82.0,
                    "rank": 2,
                    "match_score": 88,
                    "seasonal_bonus": {"March-June": 10, "July-Sept": -8, "Oct-Dec": 3},
                    "why_good": "Excellent for Meru highlands - cool temperatures and good rainfall"
                },
                "Cypress": {
                    "survival_rate": 75.0,
                    "rank": 3,
                    "match_score": 80,
                    "seasonal_bonus": {"March-June": 8, "July-Sept": -12, "Oct-Dec": 2},
                    "why_good": "Good highland species but needs consistent moisture"
                }
            },
            
            "Nakuru": {
                "Pine": {
                    "survival_rate": 88.0,
                    "rank": 1,
                    "match_score": 96,
                    "seasonal_bonus": {"March-June": 7, "July-Sept": -5, "Oct-Dec": 4},
                    "why_good": "Perfect conditions - Nakuru's volcanic soil and cool climate ideal for Pine"
                },
                "Cypress": {
                    "survival_rate": 85.0,
                    "rank": 2,
                    "match_score": 92,
                    "seasonal_bonus": {"March-June": 6, "July-Sept": -8, "Oct-Dec": 3},
                    "why_good": "Excellent highland climate, volcanic soil perfect for Cypress"
                },
                "Indigenous Mix": {
                    "survival_rate": 83.0,
                    "rank": 3,
                    "match_score": 90,
                    "seasonal_bonus": {"March-May": 5, "Oct-Dec": 4, "June-Sept": -12},
                    "why_good": "Native highland species adapted to Nakuru's conditions"
                }
            },
            
            "Machakos": {
                "Indigenous Mix": {
                    "survival_rate": 80.0,
                    "rank": 1,
                    "match_score": 92,
                    "seasonal_bonus": {"March-May": 10, "June-Sept": -8, "Oct-Dec": 5},
                    "why_good": "Native dryland species - perfectly adapted to Machakos semi-arid conditions"
                },
                "Neem": {
                    "survival_rate": 76.0,
                    "rank": 2,
                    "match_score": 88,
                    "seasonal_bonus": {"March-May": 12, "June-Sept": -5, "Oct-Dec": 3},
                    "why_good": "Excellent drought tolerance - thrives in Machakos dry conditions"
                },
                "Grevillea": {
                    "survival_rate": 65.0,
                    "rank": 3,
                    "match_score": 70,
                    "seasonal_bonus": {"March-May": 15, "June-Sept": -20, "Oct-Dec": 5},
                    "why_good": "Challenging but possible with extra care during wet season only"
                }
            },
            
            "Turkana": {
                "Neem": {
                    "survival_rate": 82.0,
                    "rank": 1,
                    "match_score": 95,
                    "seasonal_bonus": {"March-April": 8, "Irrigated": 15, "June-Sept": -25},
                    "why_good": "Perfect for Turkana - exceptional drought and heat tolerance"
                },
                "Indigenous Mix": {
                    "survival_rate": 75.0,
                    "rank": 2,
                    "match_score": 85,
                    "seasonal_bonus": {"March-May": 10, "Irrigated": 12, "June-Sept": -20},
                    "why_good": "Native dryland acacias adapted to extreme arid conditions"
                },
                "Eucalyptus": {
                    "survival_rate": 55.0,
                    "rank": 3,
                    "match_score": 60,
                    "seasonal_bonus": {"March-May": 15, "Irrigated": 20, "June-Sept": -30},
                    "why_good": "High risk - only with irrigation and intensive care"
                }
            },
            
            "Garissa": {
                "Neem": {
                    "survival_rate": 76.0,
                    "rank": 1,
                    "match_score": 91,
                    "seasonal_bonus": {"March-May": 8, "Irrigated": 12, "Dry": -18},
                    "why_good": "Best species for arid conditions, minimal water needs"
                }
            },
            
            "Mombasa": {
                "Neem": {
                    "survival_rate": 78.0,
                    "rank": 1,
                    "match_score": 85,
                    "seasonal_bonus": {"April-June": 8, "July-Sept": 2, "Oct-Dec": 3},
                    "why_good": "Good heat tolerance for Mombasa's hot coastal climate"
                },
                "Indigenous Mix": {
                    "survival_rate": 72.0,
                    "rank": 2,
                    "match_score": 80,
                    "seasonal_bonus": {"April-June": 10, "July-Sept": -5, "Oct-Dec": 5},
                    "why_good": "Native coastal species adapted to Mombasa conditions"
                },
                "Grevillea": {
                    "survival_rate": 58.0,
                    "rank": 3,
                    "match_score": 65,
                    "seasonal_bonus": {"April-June": 15, "July-Sept": -15, "Oct-Dec": 5},
                    "why_good": "Challenging - needs intensive care and optimal timing"
                },
                "Pine": {
                    "survival_rate": 35.0,
                    "rank": 4,
                    "match_score": 40,
                    "seasonal_bonus": {"April-June": 10, "July-Sept": -20, "Oct-Dec": 5},
                    "why_good": "Very high risk - coastal heat unsuitable for highland Pine"
                }
            },
            
            "Nyeri": {
                "Pine": {
                    "survival_rate": 92.0,
                    "rank": 1,
                    "match_score": 98,
                    "seasonal_bonus": {"March-June": 5, "July-Sept": -3, "Oct-Dec": 4},
                    "why_good": "Absolute best conditions - Nyeri's cool highland climate perfect for Pine"
                },
                "Indigenous Mix": {
                    "survival_rate": 90.0,
                    "rank": 2,
                    "match_score": 96,
                    "seasonal_bonus": {"March-May": 6, "Oct-Dec": 5, "June-Sept": -8},
                    "why_good": "Native highland species - excellent adaptation to Nyeri conditions"
                },
                "Cypress": {
                    "survival_rate": 87.0,
                    "rank": 3,
                    "match_score": 92,
                    "seasonal_bonus": {"March-June": 4, "July-Sept": -6, "Oct-Dec": 3},
                    "why_good": "Excellent highland species for Nyeri's cool climate"
                },
                "Grevillea": {
                    "survival_rate": 84.0,
                    "rank": 4,
                    "match_score": 88,
                    "seasonal_bonus": {"March-May": 6, "Oct-Dec": 8, "June-Sept": -10},
                    "why_good": "Good highland adaptation, thrives in Nyeri's conditions"
                }
            },
            
            "Kiambu": {
                "Grevillea": {
                    "survival_rate": 87.0,
                    "rank": 1,
                    "match_score": 94,
                    "seasonal_bonus": {"March-May": 6, "Oct-Dec": 4, "June-Sept": -8},
                    "why_good": "Excellent highland adaptation, perfect for coffee agroforestry"
                },
                "Cypress": {
                    "survival_rate": 83.0,
                    "rank": 2,
                    "match_score": 90,
                    "seasonal_bonus": {"March-June": 3, "July-Sept": -8, "Oct-Dec": 1},
                    "why_good": "Good highland species, suitable climate and altitude"
                }
            },
            
            "Embu": {
                "Grevillea": {
                    "survival_rate": 81.0,
                    "rank": 1,
                    "match_score": 87,
                    "seasonal_bonus": {"March-May": 5, "Oct-Dec": 3, "June-Sept": -10},
                    "why_good": "Good highland adaptation, excellent for agroforestry"
                },
                "Cypress": {
                    "survival_rate": 81.0,
                    "rank": 2,
                    "match_score": 86,
                    "seasonal_bonus": {"March-June": 3, "July-Sept": -10, "Oct-Dec": 1},
                    "why_good": "Highland species, good timber potential"
                },
                "Indigenous Mix": {
                    "survival_rate": 87.0,
                    "rank": 1,
                    "match_score": 94,
                    "seasonal_bonus": {"March-May": 5, "Oct-Dec": 3, "June-Sept": -8},
                    "why_good": "Native species perfectly adapted to eastern highlands"
                }
            }
        }

        # COUNTY ENVIRONMENT PROFILES
        county_env = {
            "Meru": {
                "rainfall_mm_min": 600, "rainfall_mm_max": 1500,
                "temperature_c_min": 15, "temperature_c_max": 25,
                "soil_type": "Clay / Loam",
                "altitude_m_min": 1200, "altitude_m_max": 2000,
                "soil_ph_min": 6.0, "soil_ph_max": 7.5,
                "climate_zone": "Semi-Humid",
                "best_season": "March–May, Oct–Dec"
            },
            "Machakos": {
                "rainfall_mm_min": 500, "rainfall_mm_max": 1100,
                "temperature_c_min": 18, "temperature_c_max": 27,
                "soil_type": "Red Soil / Clay",
                "altitude_m_min": 1000, "altitude_m_max": 1600,
                "soil_ph_min": 6.0, "soil_ph_max": 7.4,
                "climate_zone": "Semi-Arid",
                "best_season": "March–May"
            },
            "Turkana": {
                "rainfall_mm_min": 100, "rainfall_mm_max": 300,
                "temperature_c_min": 28, "temperature_c_max": 36,
                "soil_type": "Rocky / Sandy",
                "altitude_m_min": 300, "altitude_m_max": 900,
                "soil_ph_min": 7.5, "soil_ph_max": 8.5,
                "climate_zone": "Extremely Arid",
                "best_season": "Any (if irrigated)"
            },
            "Garissa": {
                "rainfall_mm_min": 250, "rainfall_mm_max": 350,
                "temperature_c_min": 26, "temperature_c_max": 34,
                "soil_type": "Red Soil",
                "altitude_m_min": 150, "altitude_m_max": 400,
                "soil_ph_min": 6.0, "soil_ph_max": 7.0,
                "climate_zone": "Arid",
                "best_season": "March–May"
            },
            "Nakuru": {
                "rainfall_mm_min": 800, "rainfall_mm_max": 1400,
                "temperature_c_min": 12, "temperature_c_max": 22,
                "soil_type": "Volcanic / Loam",
                "altitude_m_min": 1600, "altitude_m_max": 2100,
                "soil_ph_min": 5.5, "soil_ph_max": 6.8,
                "climate_zone": "Sub-Humid",
                "best_season": "March–June, Oct–Dec"
            },
            "Mombasa": {
                "rainfall_mm_min": 1000, "rainfall_mm_max": 1200,
                "temperature_c_min": 24, "temperature_c_max": 32,
                "soil_type": "Sandy / Coral",
                "altitude_m_min": 0, "altitude_m_max": 50,
                "soil_ph_min": 6.5, "soil_ph_max": 7.8,
                "climate_zone": "Coastal Humid",
                "best_season": "April–June"
            },
            "Nyeri": {
                "rainfall_mm_min": 900, "rainfall_mm_max": 1600,
                "temperature_c_min": 12, "temperature_c_max": 20,
                "soil_type": "Volcanic / Clay",
                "altitude_m_min": 1700, "altitude_m_max": 2100,
                "soil_ph_min": 6.0, "soil_ph_max": 7.0,
                "climate_zone": "Sub-Humid",
                "best_season": "March–May, October–December"
            },
            "Kiambu": {
                "rainfall_mm_min": 800, "rainfall_mm_max": 1400,
                "temperature_c_min": 14, "temperature_c_max": 22,
                "soil_type": "Clay / Loam",
                "altitude_m_min": 1500, "altitude_m_max": 1900,
                "soil_ph_min": 6.2, "soil_ph_max": 7.2,
                "climate_zone": "Sub-Humid",
                "best_season": "March–May, October–December"
            },
            "Embu": {
                "rainfall_mm_min": 500, "rainfall_mm_max": 1500,
                "temperature_c_min": 18, "temperature_c_max": 28,
                "soil_type": "Red Soil / Clay",
                "altitude_m_min": 1200, "altitude_m_max": 1800,
                "soil_ph_min": 6.0, "soil_ph_max": 7.3,
                "climate_zone": "Semi-Humid",
                "best_season": "March–May, October–December"
            }
        }

        # SPECIES PROFILES
        species_profiles = {
            "Grevillea": {
                "soil": "Loam / Clay-loam",
                "rainfall": "600–1800mm",
                "temperature": "15–28°C",
                "care_level": "Low",
                "best_season": "March–May, October–December",
                "planting_method": "Seedling",
                "water": "Weekly watering for the first 4 weeks",
                "base_survival_rate": 75.0,
                "drought_tolerance": "Medium",
                "heat_tolerance": "Medium",
                "cold_tolerance": "High",
                "altitude_preference": "Any",
                "rainfall_optimal_min": 600,
                "rainfall_optimal_max": 1800,
                "planting_guide": [
                    "Dig a hole 2x2 ft",
                    "Mix soil with compost/manure",
                    "Place seedling upright",
                    "Mulch to retain moisture",
                    "Water immediately after planting"
                ],
                "care_instructions": [
                    "Mulch every 2–3 months",
                    "Protect from goats/livestock",
                    "Remove weeds monthly",
                    "Water during long dry periods"
                ]
            },
            "Cypress": {
                "soil": "Clay / Volcanic",
                "rainfall": "700–1500mm",
                "temperature": "12–22°C",
                "care_level": "Medium",
                "best_season": "March–June",
                "planting_method": "Cutting or Seedling",
                "water": "2x per week for first month",
                "base_survival_rate": 78.0,
                "drought_tolerance": "Low",
                "heat_tolerance": "Low",
                "cold_tolerance": "Excellent",
                "altitude_preference": "Highland",
                "rainfall_optimal_min": 700,
                "rainfall_optimal_max": 1500,
                "planting_guide": [
                    "Dig deep hole (3x3 ft)",
                    "Add compost and topsoil",
                    "Stake if area is windy",
                    "Water deeply after planting"
                ],
                "care_instructions": [
                    "Weed monthly",
                    "Apply manure annually",
                    "Prune to shape",
                    "Protect from frost in high areas"
                ]
            },
            "Pine": {
                "soil": "Red soil / Clay / Sandy-loam",
                "rainfall": "800–1800mm",
                "temperature": "10–22°C",
                "care_level": "Medium",
                "best_season": "March–June",
                "planting_method": "Seedling",
                "water": "Weekly for 2 months",
                "base_survival_rate": 80.0,
                "drought_tolerance": "Low",
                "heat_tolerance": "Low",
                "cold_tolerance": "Excellent",
                "altitude_preference": "Highland",
                "rainfall_optimal_min": 800,
                "rainfall_optimal_max": 1800,
                "planting_guide": [
                    "Prepare hole 2x2 ft",
                    "Apply compost",
                    "Water thoroughly",
                    "Ensure spacing of 1.5–3m"
                ],
                "care_instructions": [
                    "Remove weeds regularly",
                    "Mulch during dry season",
                    "Protect from livestock",
                    "Check for pests annually"
                ]
            },
            "Neem": {
                "soil": "Red soil / Sandy soil",
                "rainfall": "200–600mm",
                "temperature": "24–34°C",
                "care_level": "Low",
                "best_season": "March–April",
                "planting_method": "Seedling or Direct Seeding",
                "water": "Little water (can survive drought)",
                "base_survival_rate": 70.0,
                "drought_tolerance": "Excellent",
                "heat_tolerance": "Excellent",
                "cold_tolerance": "Poor",
                "altitude_preference": "Lowland",
                "rainfall_optimal_min": 200,
                "rainfall_optimal_max": 600,
                "planting_guide": [
                    "Dig 2x2 ft hole",
                    "Mix soil with little manure",
                    "Plant the seedling",
                    "Water lightly"
                ],
                "care_instructions": [
                    "Minimal care required",
                    "Keep area weed-free",
                    "Water once every 10–14 days during drought",
                    "Protect from termites"
                ]
            },
            "Eucalyptus": {
                "soil": "Sandy / Loam",
                "rainfall": "400–1200mm",
                "temperature": "18–32°C",
                "care_level": "Low",
                "best_season": "March–May",
                "planting_method": "Seedling",
                "water": "Weekly for 4 weeks",
                "base_survival_rate": 72.0,
                "drought_tolerance": "Medium",
                "heat_tolerance": "Medium",
                "cold_tolerance": "Medium",
                "altitude_preference": "Any",
                "rainfall_optimal_min": 400,
                "rainfall_optimal_max": 1200,
                "planting_guide": [
                    "Dig hole 2 ft deep",
                    "Fill with manure and topsoil",
                    "Plant straight and firm",
                    "Mulch lightly"
                ],
                "care_instructions": [
                    "Weed around base",
                    "Avoid planting near rivers (drinks a lot)",
                    "Prune after 1 year"
                ]
            },
            "Indigenous Mix": {
                "soil": "Loam / Clay / Volcanic",
                "rainfall": "600–1800mm",
                "temperature": "12–26°C",
                "care_level": "Medium",
                "best_season": "March–May",
                "planting_method": "Seedling",
                "water": "Weekly for 1 month",
                "base_survival_rate": 85.0,
                "drought_tolerance": "High",
                "heat_tolerance": "Medium",
                "cold_tolerance": "High",
                "altitude_preference": "Any",
                "rainfall_optimal_min": 600,
                "rainfall_optimal_max": 1800,
                "planting_guide": [
                    "Dig hole 2x2 ft",
                    "Fill with compost",
                    "Water well",
                    "Mulch"
                ],
                "care_instructions": [
                    "Weed regularly",
                    "Apply mulch",
                    "Protect from livestock",
                    "Prune lightly after 1 year"
                ]
            }
        }

        # Load counties and environments
        self.stdout.write("Loading counties and environments...")
        for county_name in county_species_compatibility.keys():
            county, created = County.objects.get_or_create(name=county_name)
            if created:
                self.stdout.write(f"  Created county: {county_name}")
            
            env = county_env.get(county_name)
            if env:
                CountyEnvironment.objects.update_or_create(county=county, defaults=env)
                self.stdout.write(f"  Updated environment for {county_name}")

        # Load all species
        self.stdout.write("\nLoading species profiles...")
        species_objects = {}
        for name, profile in species_profiles.items():
            sp, created = Species.objects.update_or_create(name=name, defaults=profile)
            species_objects[name] = sp
            if created:
                self.stdout.write(f"  Created species: {name}")
            else:
                self.stdout.write(f"  Updated species: {name}")

        # Link counties to species with compatibility data
        self.stdout.write("\nLinking counties to species with compatibility scores...")
        for county_name, species_dict in county_species_compatibility.items():
            county = County.objects.get(name=county_name)
            
            for species_name, compat_data in species_dict.items():
                species = species_objects.get(species_name)
                if species:
                    county_species, created = CountySpecies.objects.update_or_create(
                        county=county,
                        species=species,
                        defaults={
                            'survival_rate': compat_data['survival_rate'],
                            'species_rank': compat_data['rank'],
                            'environmental_match_score': compat_data['match_score'],
                            'seasonal_performance': compat_data['seasonal_bonus'],
                            'recommendation_reason': compat_data['why_good']
                        }
                    )
                    action = "Created" if created else "Updated"
                    self.stdout.write(f"  {action}: {county_name} -> {species_name} (Survival: {compat_data['survival_rate']}%)")

        self.stdout.write(self.style.SUCCESS("\nPlaybook loaded successfully!"))
        self.stdout.write(self.style.SUCCESS(f"   - {len(county_env)} counties"))
        self.stdout.write(self.style.SUCCESS(f"   - {len(species_profiles)} species"))
        self.stdout.write(self.style.SUCCESS(f"   - County-species compatibility data loaded"))