import requests
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)

class LocationService:
    """Multi-source location detection service for accurate Kenya-wide coverage"""
    
    def __init__(self):
        # Use only free APIs - no payment required
        pass
        
    def get_accurate_location(self, latitude: float, longitude: float) -> Dict:
        """
        Get most accurate location using multiple geocoding sources
        Returns: {
            'county': str,
            'region': str, 
            'country': str,
            'confidence': float,
            'source': str
        }
        """
        results = []
        
        # Try OpenStreetMap Nominatim (primary - completely free)
        osm_result = self._nominatim_geocode(latitude, longitude)
        if osm_result:
            results.append(osm_result)
            
        # Try LocationIQ (additional validation)
        locationiq_result = self._locationiq_geocode(latitude, longitude)
        if locationiq_result:
            results.append(locationiq_result)
        
        # Select best result
        if results:
            best_result = self._select_best_result(results)
            # Validate against Kenya counties
            return self._validate_kenya_location(best_result, latitude, longitude)
        
        # Fallback to coordinate-based estimation
        return self._coordinate_fallback(latitude, longitude)
    

    
    def _nominatim_geocode(self, lat: float, lng: float) -> Optional[Dict]:
        """OpenStreetMap Nominatim geocoding"""
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'en'
            }
            headers = {'User-Agent': 'MsituGuard/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if 'address' in data:
                address = data['address']
                county = self._extract_county_osm(address)
                
                return {
                    'county': county,
                    'region': address.get('state', ''),
                    'country': address.get('country', 'Kenya'),
                    'confidence': 0.7,
                    'source': 'OpenStreetMap',
                    'raw': data
                }
        except Exception as e:
            logger.error(f"Nominatim geocoding error: {e}")
            
        return None
    
    def _locationiq_geocode(self, lat: float, lng: float) -> Optional[Dict]:
        """LocationIQ geocoding (free tier)"""
        try:
            locationiq_key = getattr(settings, 'LOCATIONIQ_API_KEY', None)
            if not locationiq_key:
                return None
                
            url = "https://us1.locationiq.com/v1/reverse.php"
            params = {
                'key': locationiq_key,
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'address' in data:
                address = data['address']
                county = self._extract_county_locationiq(address)
                
                return {
                    'county': county,
                    'region': address.get('state', ''),
                    'country': address.get('country', 'Kenya'),
                    'confidence': 0.6,
                    'source': 'LocationIQ',
                    'raw': data
                }
        except Exception as e:
            logger.error(f"LocationIQ geocoding error: {e}")
            
        return None
    
    def _extract_county_google(self, result: Dict) -> str:
        """Extract county from Google Maps result"""
        for component in result.get('address_components', []):
            types = component.get('types', [])
            if 'administrative_area_level_1' in types:
                name = component['long_name']
                # Clean up county name
                if 'County' not in name and name != 'Nairobi':
                    name += ' County'
                return name
        return ''
    
    def _extract_region_google(self, result: Dict) -> str:
        """Extract region from Google Maps result"""
        for component in result.get('address_components', []):
            types = component.get('types', [])
            if 'administrative_area_level_2' in types:
                return component['long_name']
        return ''
    
    def _extract_county_osm(self, address: Dict) -> str:
        """Extract county from OSM address"""
        # Try different address levels
        county = (address.get('county') or 
                 address.get('state_district') or 
                 address.get('state') or '')
        
        if county and 'County' not in county and county != 'Nairobi':
            county += ' County'
        return county
    
    def _extract_county_locationiq(self, address: Dict) -> str:
        """Extract county from LocationIQ address"""
        county = (address.get('county') or 
                 address.get('state') or '')
        
        if county and 'County' not in county and county != 'Nairobi':
            county += ' County'
        return county
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """Select the most reliable result based on confidence and validation"""
        # Sort by confidence score
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Prefer results that have valid Kenya counties
        for result in results:
            if self._is_valid_kenya_county(result['county']):
                return result
        
        # Return highest confidence if no valid county found
        return results[0] if results else {}
    
    def _is_valid_kenya_county(self, county: str) -> bool:
        """Check if county name is a valid Kenya county"""
        kenya_counties = {
            'Baringo County', 'Bomet County', 'Bungoma County', 'Busia County',
            'Elgeyo-Marakwet County', 'Embu County', 'Garissa County', 'Homa Bay County',
            'Isiolo County', 'Kajiado County', 'Kakamega County', 'Kericho County',
            'Kiambu County', 'Kilifi County', 'Kirinyaga County', 'Kisii County',
            'Kisumu County', 'Kitui County', 'Kwale County', 'Laikipia County',
            'Lamu County', 'Machakos County', 'Makueni County', 'Mandera County',
            'Marsabit County', 'Meru County', 'Migori County', 'Mombasa County',
            'Murang\'a County', 'Nairobi', 'Nakuru County', 'Nandi County',
            'Narok County', 'Nyamira County', 'Nyandarua County', 'Nyeri County',
            'Samburu County', 'Siaya County', 'Taita-Taveta County', 'Tana River County',
            'Tharaka-Nithi County', 'Trans Nzoia County', 'Turkana County', 'Uasin Gishu County',
            'Vihiga County', 'Wajir County', 'West Pokot County'
        }
        return county in kenya_counties
    
    def _validate_kenya_location(self, result: Dict, lat: float, lng: float) -> Dict:
        """Validate and enhance location result for Kenya"""
        # Kenya bounding box validation
        if not (-5.0 <= lat <= 5.5 and 33.5 <= lng <= 42.0):
            result['confidence'] *= 0.5  # Reduce confidence if outside Kenya
        
        # Enhance with coordinate-based validation
        county_from_coords = self._get_county_from_coordinates(lat, lng)
        if county_from_coords and county_from_coords != result.get('county'):
            # Cross-validate with coordinate-based detection
            if self._is_valid_kenya_county(county_from_coords):
                result['county'] = county_from_coords
                result['confidence'] = min(result['confidence'] + 0.1, 1.0)
        
        return result
    
    def _get_county_from_coordinates(self, lat: float, lng: float) -> Optional[str]:
        """Get county based on coordinate ranges (simplified)"""
        # Accurate coordinate-based county detection for major counties
        county_bounds = {
            'Meru County': (-0.1, 0.3, 37.4, 38.0),  # Meru University area
            'Nyeri County': (-0.8, -0.2, 36.5, 37.2),
            'Nairobi': (-1.4, -1.1, 36.6, 37.1),
            'Kiambu County': (-1.3, -0.8, 36.5, 37.2),
            'Nakuru County': (-1.2, 0.2, 35.5, 36.8),
            'Mombasa County': (-4.2, -3.8, 39.4, 39.8),
        }
        
        for county, (min_lat, max_lat, min_lng, max_lng) in county_bounds.items():
            if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
                return county
        
        return None
    
    def _coordinate_fallback(self, lat: float, lng: float) -> Dict:
        """Fallback method using coordinate-based estimation"""
        county = self._get_county_from_coordinates(lat, lng)
        
        return {
            'county': county or 'Unknown County',
            'region': '',
            'country': 'Kenya',
            'confidence': 0.3,
            'source': 'Coordinate Estimation'
        }

# Global instance
location_service = LocationService()