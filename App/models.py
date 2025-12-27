from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser, Group, Permission
import os
import requests
from django.conf import settings


# Create your models here.
class Profile(models.Model):
    ACCOUNT_TYPES = [
        ('community', 'Community Member'),
        ('donor', 'Donor/Supporter'),
        ('organization', 'Local Organization'),
    ]
    
    DONOR_TIERS = [
        ('basic', 'Basic Supporter'),
        ('standard', 'Standard Donor'),
        ('premium', 'Premium Supporter'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phoneNumber = models.CharField(
        max_length=50,
        default=' ',
        validators=[RegexValidator(regex=r'^\d*$', message='Only numeric values are allowed')]
    )
    location = models.CharField(max_length=100, blank=True, default=' ')
    bio = models.TextField(default='Bio information not provided')
    email = models.EmailField(default='example@example.com')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    is_verified = models.BooleanField(default=False)
    verification_requested = models.BooleanField(default=False)
    
    # New fields for monetization
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES, default='community')
    donor_tier = models.CharField(max_length=50, choices=DONOR_TIERS, blank=True, null=True)
    monthly_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_donated = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    donor_since = models.DateTimeField(blank=True, null=True)
    
    # Environmental tracking
    tree_points = models.PositiveIntegerField(default=0, help_text='Points from verified tree plantings')
    environmental_badges = models.TextField(blank=True, help_text='Comma-separated list of earned badges')
    
    
    @property
    def badges_list(self):
        if self.environmental_badges:
            return [badge.strip() for badge in self.environmental_badges.split(',') if badge.strip()]
        return []
    
    def add_badge(self, badge_name):
        current_badges = self.badges_list
        if badge_name not in current_badges:
            current_badges.append(badge_name)
            self.environmental_badges = ', '.join(current_badges)
            self.save()
    
    @property
    def environmental_level(self):
        if self.tree_points >= 500: return "🌳 Forest Guardian"
        elif self.tree_points >= 200: return "🌲 Tree Champion"
        elif self.tree_points >= 100: return "🌿 Green Warrior"
        elif self.tree_points >= 50: return "🌱 Eco Defender"
        elif self.tree_points >= 10: return "🍃 Nature Friend"
        return "🌾 Environmental Supporter"
    
    @property
    def is_donor(self):
        return self.account_type == 'donor'
    
    @property
    def donor_badge(self):
        # Only show badge if they've actually contributed money
        if not self.is_donor or self.total_donated <= 0:
            return None
        badges = {
            'basic': '🥉 Basic Supporter',
            'standard': '🥈 Community Donor', 
            'premium': '🥇 Premium Supporter'
        }
        return badges.get(self.donor_tier, '💝 Supporter')
    
    @property
    def is_active_donor(self):
        """Check if user is a donor who has actually contributed"""
        return self.is_donor and self.total_donated > 0
    
    @property
    def total_verified_trees(self):
        """Count of verified trees planted by this user"""
        from django.db.models import Sum
        result = TreePlanting.objects.filter(planter=self.user, status='verified').aggregate(
            total=Sum('number_of_trees')
        )
        return result['total'] or 0
    

    
    @property
    def total_tree_predictions(self):
        """Count of tree predictions made by this user"""
        return TreePrediction.objects.filter(user=self.user).count()
    

    
    @property
    def conservation_rank(self):
        """User rank based on tree points"""
        if self.tree_points >= 100: return "🏆 Conservation Champion"
        elif self.tree_points >= 50: return "🥇 Environmental Leader"
        elif self.tree_points >= 25: return "🥈 Green Guardian"
        elif self.tree_points >= 10: return "🥉 Eco Warrior"
        elif self.tree_points >= 5: return "🌟 Nature Defender"
        return "🌱 Environmental Supporter"
    

    def __str__(self):
        return self.user.username 

class Report(models.Model):
    REPORT_TYPES = [
        ('fire', 'Fire/Wildfire'),
        ('illegal_logging', 'Illegal Logging'),
        ('pollution', 'Pollution'),
        ('deforestation', 'Deforestation'),
        ('wildlife_poaching', 'Wildlife Poaching'),
        ('water_contamination', 'Water Contamination'),
        ('air_pollution', 'Air Pollution'),
        ('waste_dumping', 'Illegal Waste Dumping'),
        ('other', 'Other Environmental Issue'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('verified', 'Verified'),
        ('resolved', 'Resolved'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=250)
    description = models.TextField()
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES, default='other')
    
    # Location fields
    location_name = models.CharField(max_length=200, help_text='Area/landmark name')
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Media and metadata
    image = models.ImageField(upload_to='report_images/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Contact info
    phoneNumber = models.CharField(
        max_length=50,
        default='',
        validators=[RegexValidator(regex=r'^\+?[0-9]{10,15}$', message='Enter valid phone number')]
    )
    
    #AI classification
    predicted_category = models.CharField(max_length=50, blank=True, null=True)
    

    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()}"

Alert = Report 

class Resource(models.Model):
    RESOURCE_TYPES = [
        ('Food', 'Food'),
        ('Water', 'Water'),
        ('Clothes', 'Clothes'),
        ('Shelter', 'Shelter'),
        ('Medical', 'Medical'),
        ('Transportation', 'Transportation'),
        ('Tools', 'Tools'),
        ('Other', 'Other'),
    ]
    contributor = models.ForeignKey(User, on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=100, choices=RESOURCE_TYPES)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField()
    phoneNumber = models.CharField(
        max_length=17,
        validators=[RegexValidator(regex=r'^\d+$', message='Only numeric values are allowed')]
    )
    location = models.CharField(max_length=200)
    is_approved = models.BooleanField(default=False)
    date_contributed = models.DateTimeField(auto_now_add=True)
    is_allocated = models.BooleanField(default=False)
    available = models.BooleanField(default=True)
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return self.resource_type

class EmergencyContact(models.Model):
    name = models.CharField(max_length=250)
    phone = models.CharField(max_length=50)
    email = models.EmailField(default='contact@example.com')
    organization = models.CharField(max_length=250)

    def __str__(self):
        return f"{self.name} ({self.organization})"

class ResourceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('matched', 'Matched'),
        ('fulfilled', 'Fulfilled'),
        ('rejected', 'Rejected'),
    ]

    HELP_TYPES = [
        ('Food', 'Food'),
        ('Water', 'Water'),
        ('Clothes', 'Clothes'),
        ('Shelter', 'Shelter'),
        ('Medical', 'Medical'),
        ('Transportation', 'Transportation'),
        ('Tools', 'Tools'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    help_type = models.CharField(max_length=100, choices=HELP_TYPES)
    description = models.TextField()
    quantity_requested = models.PositiveIntegerField(default=1)
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    matched_contribution = models.ForeignKey(Resource, null=True, blank=True, on_delete=models.SET_NULL)
    response_message = models.TextField(blank=True, null=True)
    is_fulfilled = models.BooleanField(default=False)

    phoneNumber = models.CharField(
        max_length=50,
        default='',
        validators=[RegexValidator(regex=r'^\d+$', message='Only numeric values are allowed')]
    )

    location = models.CharField(max_length=200, default='')

    def __str__(self):
        return f"User: {self.user.username}, Help Type: {self.help_type}"

class ForumPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title 

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('report_verified', 'Report Verified'),
        ('report_resolved', 'Report Resolved'),
        ('tree_verified', 'Tree Planting Verified'),
        ('general', 'General Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    report = models.ForeignKey(Report, on_delete=models.CASCADE, null=True, blank=True)
    tree_planting = models.ForeignKey('TreePlanting', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"



class TreePlanting(models.Model):
    PLANTING_STATUS = [
        ('planned', 'Planned'),
        ('planted', 'Planted'),
        ('verified', 'Verified'),
    ]
    
    TREE_TYPES = [
        ('indigenous', 'Indigenous Species'),
        ('exotic', 'Exotic Species'),
        ('fruit', 'Fruit Trees'),
        ('bamboo', 'Bamboo'),
        ('other', 'Other'),
    ]
    
    planter = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    planter_name = models.CharField(max_length=200, blank=True, help_text='Name of person who planted (for unregistered users)')
    title = models.CharField(max_length=250, default='Tree Planting Initiative')
    location_name = models.CharField(max_length=200, help_text='Area/location name')
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    tree_type = models.CharField(max_length=50, choices=TREE_TYPES, default='indigenous')
    number_of_trees = models.PositiveIntegerField(default=1)
    description = models.TextField(help_text='Describe the planting area and purpose')
    
    # Images
    before_image = models.ImageField(upload_to='tree_planting/before/', blank=True, null=True, help_text='Photo of area before planting')
    after_image = models.ImageField(upload_to='tree_planting/after/', blank=True, null=True, help_text='Photo after planting trees')
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=PLANTING_STATUS, default='planned')
    planted_date = models.DateTimeField(auto_now_add=True)
    
    # Contact info
    phoneNumber = models.CharField(
        max_length=50,
        default='',
        validators=[RegexValidator(regex=r'^\+?[0-9]{10,15}$', message='Enter valid phone number')]
    )
    
    # Future: ML prediction results will be stored here
    suitability_score = models.FloatField(null=True, blank=True, help_text='Tree survival prediction score')
    
    # Tree age tracking
    tree_age_months = models.PositiveIntegerField(default=0, help_text='Age of trees in months')
    
    def award_tree_points(self):
        """Award tree points for verified tree planting"""
        if self.status == 'verified' and self.planter:
            # Award tree points
            points = self.number_of_trees
            self.planter.profile.tree_points += points
            
            # Award special initiative badge for first-time planters
            user_tree_count = TreePlanting.objects.filter(planter=self.planter, status='verified').count()
            if user_tree_count == 1:  # First verified tree planting
                self.planter.profile.add_badge("🌍 15 Billion Trees Initiative Participant")
            
            self.planter.profile.save()
            return True
        return False
    
    
    class Meta:
        ordering = ['-planted_date']
    
    @property
    def planter_display_name(self):
        if self.planter:
            return f"{self.planter.first_name} {self.planter.last_name}".strip() or self.planter.username
        return f"{self.planter_name} (Unregistered)" if self.planter_name else "Unknown Planter"
    
    
    def __str__(self):
        return f"{self.title} - {self.number_of_trees} trees by {self.planter_display_name}"


class WeatherSnapshot(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    temperature_c = models.FloatField()
    humidity = models.IntegerField()
    rain_mm_hour = models.FloatField(default=0)
    wind_speed = models.FloatField()
    source = models.CharField(max_length=50, default="OpenWeather")
    cached = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Weather @ {self.created_at} ({self.latitude},{self.longitude})"

class TreePrediction(models.Model):
    SURVIVAL_LEVELS = [
        ('high', 'High Success Rate'),
        ('medium', 'Medium Success Rate'),
        ('low', 'Low Success Rate'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('very_high', 'Very High'),
        ('high', 'High'),
        ('moderate', 'Moderate'),
        ('low', 'Low'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    weather_snapshot = models.ForeignKey(WeatherSnapshot, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Input parameters
    tree_species = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    soil_type = models.CharField(max_length=100)
    rainfall_mm = models.FloatField()
    temperature_c = models.FloatField()
    altitude_m = models.FloatField()
    soil_ph = models.FloatField()
    planting_season = models.CharField(max_length=50)
    planting_method = models.CharField(max_length=100)
    care_level = models.CharField(max_length=50)
    water_source = models.CharField(max_length=100)
    tree_age_months = models.IntegerField()
    
    # Prediction results
    survival_probability = models.FloatField(help_text='Probability of survival (0-100)')
    survival_level = models.CharField(max_length=20, choices=SURVIVAL_LEVELS)
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVELS, default='moderate')
    model_version = models.CharField(max_length=20, default='v1.0.0')
    risk_factors = models.TextField(blank=True, help_text='JSON list of identified risks')
    explanation_reasons = models.TextField(blank=True, help_text='JSON list of explanation reasons')
    recommended_species = models.TextField(blank=True, help_text='JSON list of recommended species')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        user_name = self.user.username if self.user else 'Anonymous'
        return f"{user_name} - {self.tree_species} ({self.survival_level}) - {self.created_at.date()}"

class LocationClimateData(models.Model):
    county_name = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=50)
    rainfall_mm = models.FloatField()
    temperature_c = models.FloatField()
    altitude_m = models.FloatField()
    soil_ph = models.FloatField()
    soil_type = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.county_name} - {self.region}"

#county models

class County(models.Model):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=36.0)

    def __str__(self):
        return self.name


class CountyEnvironment(models.Model):
    county = models.OneToOneField(County, on_delete=models.CASCADE, related_name="environment")
    rainfall_mm_min = models.FloatField()
    rainfall_mm_max = models.FloatField()
    temperature_c_min = models.FloatField()
    temperature_c_max = models.FloatField()
    soil_type = models.CharField(max_length=100)
    altitude_m_min = models.FloatField()
    altitude_m_max = models.FloatField()
    soil_ph_min = models.FloatField()
    soil_ph_max = models.FloatField()
    climate_zone = models.CharField(max_length=50)
    best_season = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.county.name} Environment"

class Species(models.Model):
    name = models.CharField(max_length=100, unique=True)
    soil = models.CharField(max_length=100, default="Unknown")  # default added
    rainfall = models.CharField(max_length=50, default="Unknown")  # default added
    temperature = models.CharField(max_length=50, default="Unknown")  # default added
    care_level = models.CharField(max_length=50, default="Unknown")  # default added
    best_season = models.CharField(max_length=50, default="Unknown")  # already had default
    planting_method = models.CharField(max_length=50, default="Unknown")  # new default
    water = models.CharField(max_length=100, default="Unknown")  # default added
    planting_guide = models.JSONField(default=list)  # default is empty list
    care_instructions = models.JSONField(default=list)  # default is a callable

    def __str__(self):
        return self.name


class CountySpecies(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    
    # Enhanced playbook fields
    survival_rate = models.FloatField(default=70.0, help_text='Expected survival percentage for this species in this county')
    species_rank = models.IntegerField(default=1, help_text='Ranking of species for this county (1=best, 2=good, etc.)')
    environmental_match_score = models.FloatField(default=70.0, help_text='Environmental compatibility score (0-100)')
    seasonal_performance = models.JSONField(default=dict, help_text='Seasonal bonuses/penalties as JSON')
    recommendation_reason = models.TextField(default='Good species for this area', help_text='Why this species works well in this county')

    class Meta:
        unique_together = ('county', 'species')
        ordering = ['species_rank', 'species__name']

    def __str__(self):
        return f"{self.species.name} in {self.county.name} ({self.survival_rate}% survival)"

