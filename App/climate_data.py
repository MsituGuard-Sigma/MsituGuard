"""
Climate and environmental data lookup for Kenyan locations
Uses pre-compiled datasets with enhanced location detection
"""

import math
from datetime import datetime
from .location_service import location_service

class KenyanClimateData:
    """Lookup climate and environmental data for Kenyan locations using real dataset"""
    
    # County-specific climate data extracted from training dataset (10,000+ records)
    COUNTY_CLIMATE_DATA = {
        'Eldoret': {
            'rainfall_mm': 629.3,
            'temperature_c': 21.8,
            'altitude_m': 1735.4,
            'soil_ph': 6.8
        },
        'Garissa': {
            'rainfall_mm': 628.3,
            'temperature_c': 22.2,
            'altitude_m': 1726.5,
            'soil_ph': 6.7
        },
        'Kakamega': {
            'rainfall_mm': 630.2,
            'temperature_c': 22.0,
            'altitude_m': 1792.4,
            'soil_ph': 6.8
        },
        'Kiambu': {
            'rainfall_mm': 628.6,
            'temperature_c': 21.9,
            'altitude_m': 1744.8,
            'soil_ph': 6.7
        },
        'Kisumu': {
            'rainfall_mm': 633.4,
            'temperature_c': 22.0,
            'altitude_m': 1766.7,
            'soil_ph': 6.7
        },
        'Kitui': {
            'rainfall_mm': 631.0,
            'temperature_c': 22.0,
            'altitude_m': 1736.8,
            'soil_ph': 6.7
        },
        'Machakos': {
            'rainfall_mm': 631.9,
            'temperature_c': 21.6,
            'altitude_m': 1759.0,
            'soil_ph': 6.8
        },
        'Marsabit': {
            'rainfall_mm': 629.0,
            'temperature_c': 21.8,
            'altitude_m': 1737.8,
            'soil_ph': 6.7
        },
        'Meru': {
            'rainfall_mm': 629.6,
            'temperature_c': 22.1,
            'altitude_m': 1751.1,
            'soil_ph': 6.7
        },
        'Mombasa': {
            'rainfall_mm': 630.4,
            'temperature_c': 22.1,
            'altitude_m': 1741.3,
            'soil_ph': 6.8
        },
        'Nairobi': {
            'rainfall_mm': 631.3,
            'temperature_c': 22.0,
            'altitude_m': 1761.8,
            'soil_ph': 6.8
        },
        'Nakuru': {
            'rainfall_mm': 633.2,
            'temperature_c': 22.3,
            'altitude_m': 1731.8,
            'soil_ph': 6.8
        },
        'Nyeri': {
            'rainfall_mm': 632.1,
            'temperature_c': 21.8,
            'altitude_m': 1784.5,
            'soil_ph': 6.7
        },
        'Turkana': {
            'rainfall_mm': 634.0,
            'temperature_c': 22.4,
            'altitude_m': 1749.3,
            'soil_ph': 6.8
        },
    }
    
    # Fallback regional data for counties not in training dataset
    REGIONAL_CLIMATE_DATA = {
        'Nairobi': {
            'region': 'Nairobi',
            'county': 'Nairobi',
            'rainfall_mm': 631.3,
            'temperature_c': 22.0,
            'base_altitude': 1761.8,
            'soil_type': 'Loam',
            'soil_ph': 6.8
        },
        'Central': {
            'region': 'Central',
            'county': 'Nyeri',
            'rainfall_mm': 632.1,
            'temperature_c': 21.8,
            'base_altitude': 1784.5,
            'soil_type': 'Clay',
            'soil_ph': 6.7
        },
        'Coast': {
            'region': 'Coast',
            'county': 'Mombasa',
            'rainfall_mm': 630.4,
            'temperature_c': 22.1,
            'base_altitude': 1741.3,
            'soil_type': 'Sandy',
            'soil_ph': 6.8
        },
        'RiftValley': {
            'region': 'Rift Valley',
            'county': 'Nakuru',
            'rainfall_mm': 633.2,
            'temperature_c': 22.3,
            'base_altitude': 1731.8,
            'soil_type': 'Volcanic',
            'soil_ph': 6.8
        },
        'Western': {
            'region': 'Western',
            'county': 'Kakamega',
            'rainfall_mm': 630.2,
            'temperature_c': 22.0,
            'base_altitude': 1792.4,
            'soil_type': 'Loam',
            'soil_ph': 6.8
        },
        'Eastern': {
            'region': 'Eastern',
            'county': 'Machakos',
            'rainfall_mm': 631.9,
            'temperature_c': 21.6,
            'base_altitude': 1759.0,
            'soil_type': 'Red Soil',
            'soil_ph': 6.8
        },
        'Northern': {
            'region': 'Northern',
            'county': 'Marsabit',
            'rainfall_mm': 629.0,
            'temperature_c': 21.8,
            'base_altitude': 1737.8,
            'soil_type': 'Rocky',
            'soil_ph': 6.7
        },
        'NorthEastern': {
            'region': 'North Eastern',
            'county': 'Garissa',
            'rainfall_mm': 628.3,
            'temperature_c': 22.2,
            'base_altitude': 1726.5,
            'soil_type': 'Sandy',
            'soil_ph': 6.7
        },
        'Nyanza': {
            'region': 'Nyanza',
            'county': 'Kisumu',
            'rainfall_mm': 633.4,
            'temperature_c': 22.0,
            'base_altitude': 1766.7,
            'soil_type': 'Clay',
            'soil_ph': 6.7
        }
    }
    
    # Coordinate boundaries for Kenyan regions (accurate GPS boundaries)
    REGION_BOUNDARIES = {
        'Nairobi': {'lat_min': -1.45, 'lat_max': -1.15, 'lon_min': 36.6, 'lon_max': 37.1},
        'Central': {'lat_min': -1.0, 'lat_max': 0.5, 'lon_min': 36.5, 'lon_max': 37.5},
        'Coast': {'lat_min': -4.7, 'lat_max': -1.6, 'lon_min': 39.0, 'lon_max': 41.9},
        'RiftValley': {'lat_min': -2.0, 'lat_max': 2.0, 'lon_min': 35.0, 'lon_max': 37.0},
        'Western': {'lat_min': -1.0, 'lat_max': 1.5, 'lon_min': 34.0, 'lon_max': 35.5},
        'Eastern': {'lat_min': -3.0, 'lat_max': 1.0, 'lon_min': 37.5, 'lon_max': 40.0},
        'Northern': {'lat_min': 1.0, 'lat_max': 5.0, 'lon_min': 35.0, 'lon_max': 42.0},
        'NorthEastern': {'lat_min': -1.0, 'lat_max': 4.0, 'lon_min': 38.0, 'lon_max': 42.0},
        'Nyanza': {'lat_min': -1.5, 'lat_max': 0.5, 'lon_min': 33.8, 'lon_max': 35.5}
    }
    
    @classmethod
    def get_location_data(cls, latitude, longitude, altitude=None, detected_county=None, detected_region=None):
        """Get comprehensive location data from GPS coordinates with real API detection"""
        
        # First try to get county-specific data from training dataset
        if detected_county:
            county_name = cls._normalize_county_name(detected_county)
            if county_name in cls.COUNTY_CLIMATE_DATA:
                county_data = cls.COUNTY_CLIMATE_DATA[county_name].copy()
                climate_data = {
                    'county': detected_county,
                    'region': detected_region or cls._get_region_for_county(county_name),
                    'rainfall_mm': county_data['rainfall_mm'],
                    'temperature_c': county_data['temperature_c'],
                    'altitude_m': county_data['altitude_m'],
                    'soil_ph': county_data['soil_ph'],
                    'soil_type': 'Loam'  # Default soil type
                }
            else:
                # Fallback to regional data
                region_key = cls._map_county_to_region(detected_county)
                climate_data = cls.REGIONAL_CLIMATE_DATA[region_key].copy()
                climate_data['county'] = detected_county
                climate_data['region'] = detected_region or climate_data['region']
        else:
            # Fallback to coordinate-based detection
            region_key = cls._find_region(latitude, longitude)
            climate_data = cls.REGIONAL_CLIMATE_DATA[region_key].copy()
        
        # Use GPS altitude if available, otherwise use dataset altitude
        if altitude and altitude > 0:
            climate_data['altitude_m'] = int(altitude)
        elif 'base_altitude' in climate_data:
            climate_data['altitude_m'] = climate_data['base_altitude']
        
        # Auto-detect planting season based on current date
        climate_data['planting_season'] = cls._get_planting_season()
        
        return climate_data
    
    @classmethod
    def _find_region(cls, lat, lon):
        """Find Kenyan region based on coordinates"""
        for region, bounds in cls.REGION_BOUNDARIES.items():
            if (bounds['lat_min'] <= lat <= bounds['lat_max'] and 
                bounds['lon_min'] <= lon <= bounds['lon_max']):
                return region
        
        # Default to Central if coordinates don't match
        return 'Central'
    
    @classmethod
    def _map_county_to_region(cls, county_name):
        """Map county name to region key for climate data lookup"""
        county_to_region = {
            'Nairobi': 'Nairobi',
            'Meru County': 'Eastern',  # Meru is in Eastern region
            'Nyeri County': 'Central', 
            'Kiambu County': 'Central',
            'Murang\'a County': 'Central',
            'Kirinyaga County': 'Central',
            'Nyandarua County': 'Central',
            'Embu County': 'Central',
            'Tharaka-Nithi County': 'Central',
            'Mombasa County': 'Coast',
            'Kilifi County': 'Coast',
            'Kwale County': 'Coast',
            'Lamu County': 'Coast',
            'Taita-Taveta County': 'Coast',
            'Tana River County': 'Coast',
            'Nakuru County': 'RiftValley',
            'Kajiado County': 'RiftValley',
            'Laikipia County': 'RiftValley',
            'Nandi County': 'RiftValley',
            'Uasin Gishu County': 'RiftValley',
            'Elgeyo-Marakwet County': 'RiftValley',
            'West Pokot County': 'RiftValley',
            'Baringo County': 'RiftValley',
            'Bomet County': 'RiftValley',
            'Kericho County': 'RiftValley',
            'Narok County': 'RiftValley',
            'Samburu County': 'RiftValley',
            'Kakamega County': 'Western',
            'Bungoma County': 'Western',
            'Busia County': 'Western',
            'Vihiga County': 'Western',
            'Trans Nzoia County': 'Western',
            'Machakos County': 'Eastern',
            'Kitui County': 'Eastern',
            'Makueni County': 'Eastern',
            'Marsabit County': 'Northern',
            'Isiolo County': 'Northern',
            'Turkana County': 'Northern',
            'Garissa County': 'NorthEastern',
            'Wajir County': 'NorthEastern',
            'Mandera County': 'NorthEastern',
            'Kisumu County': 'Nyanza',
            'Siaya County': 'Nyanza',
            'Kisii County': 'Nyanza',
            'Nyamira County': 'Nyanza',
            'Homa Bay County': 'Nyanza',
            'Migori County': 'Nyanza'
        }
        
        return county_to_region.get(county_name, 'Central')  # Default to Central
    
    @classmethod
    def _normalize_county_name(cls, county_name):
        """Normalize county name to match training dataset format"""
        # Remove 'County' suffix and normalize
        normalized = county_name.replace(' County', '').strip()
        
        # Handle special cases
        name_mapping = {
            'Uasin Gishu': 'Eldoret',  # Eldoret is the main town in Uasin Gishu
            'Garissa County': 'Garissa',
            'Meru County': 'Meru'
        }
        
        return name_mapping.get(normalized, normalized)
    
    @classmethod
    def _get_region_for_county(cls, county_name):
        """Get region name for a county"""
        county_to_region_name = {
            'Nairobi': 'Nairobi',
            'Eldoret': 'Rift Valley',
            'Garissa': 'North Eastern',
            'Kakamega': 'Western',
            'Kiambu': 'Central',
            'Kisumu': 'Nyanza',
            'Kitui': 'Eastern',
            'Machakos': 'Eastern',
            'Marsabit': 'Northern',
            'Meru': 'Eastern',
            'Mombasa': 'Coast',
            'Nakuru': 'Rift Valley',
            'Nyeri': 'Central',
            'Turkana': 'Northern'
        }
        return county_to_region_name.get(county_name, 'Central')
    
    @classmethod
    def _get_planting_season(cls):
        """Auto-detect planting season based on current month"""
        current_month = datetime.now().month
        
        # Kenya's planting seasons:
        # Wet Season: March-May (long rains), October-December (short rains)
        # Dry Season: June-September, January-February
        
        if current_month in [3, 4, 5, 10, 11, 12]:
            return 'Wet'
        elif current_month in [6, 7, 8, 9, 1, 2]:
            return 'Dry'
        else:
            return 'Transition'