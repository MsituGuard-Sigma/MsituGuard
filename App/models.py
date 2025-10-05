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
    
    # Environmental rewards and tokens
    tree_points = models.PositiveIntegerField(default=0, help_text='Points from verified tree plantings')
    environmental_badges = models.TextField(blank=True, help_text='Comma-separated list of earned badges')
    token_balance = models.PositiveIntegerField(default=0, help_text='Current token balance')
    total_tokens_earned = models.PositiveIntegerField(default=0, help_text='Total tokens earned all time')
    
    # Carbon credits system
    carbon_credits_balance = models.FloatField(default=0.0, help_text='Current carbon credits balance (tonnes CO2)')
    total_carbon_credits_earned = models.FloatField(default=0.0, help_text='Total carbon credits earned all time')
    estimated_carbon_value_kes = models.FloatField(default=0.0, help_text='Estimated value of carbon portfolio in KES')
    
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
    
    def add_tokens(self, amount, description="Token reward"):
        """Add tokens to user balance"""
        self.token_balance += amount
        self.total_tokens_earned += amount
        self.save()
    
    @property
    def total_tree_predictions(self):
        """Count of tree predictions made by this user"""
        return TreePrediction.objects.filter(user=self.user).count()
    
    def spend_tokens(self, amount):
        """Spend tokens from user balance"""
        if self.token_balance >= amount:
            self.token_balance -= amount
            self.save()
            return True
        return False
    
    @property
    def conservation_rank(self):
        """User rank based on total tokens earned"""
        if self.total_tokens_earned >= 100: return "🏆 Conservation Champion"
        elif self.total_tokens_earned >= 50: return "🥇 Environmental Leader"
        elif self.total_tokens_earned >= 25: return "🥈 Green Guardian"
        elif self.total_tokens_earned >= 10: return "🥉 Eco Warrior"
        elif self.total_tokens_earned >= 5: return "🌟 Nature Defender"
        return "🌱 Environmental Supporter"
    
    def add_carbon_credits(self, amount, description="Carbon credits earned"):
        """Add carbon credits to user balance"""
        self.carbon_credits_balance += amount
        self.total_carbon_credits_earned += amount
        # Update estimated value (300 KES per tonne CO2 - user rate)
        self.estimated_carbon_value_kes = self.carbon_credits_balance * 300
        self.save()
    
    @property
    def carbon_portfolio_summary(self):
        """Summary of user's carbon portfolio"""
        return {
            'balance': round(self.carbon_credits_balance, 3),
            'total_earned': round(self.total_carbon_credits_earned, 3),
            'estimated_value': round(self.estimated_carbon_value_kes, 2),
            'co2_impact_kg': round(self.carbon_credits_balance * 1000, 1)
        }

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
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
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
    
    # AI classification (keep existing ML functionality)
    predicted_category = models.CharField(max_length=50, blank=True, null=True)
    
    # Token reward (will be awarded when verified)
    tokens_awarded = models.BooleanField(default=False)
    
    def award_tokens(self):
        """Award tokens for verified environmental report"""
        if not self.tokens_awarded and self.status == 'verified' and self.image:
            Token.objects.create(
                user=self.reporter,
                action_type='report_photo',
                tokens_earned=1,
                description=f'Environmental report: {self.title}',
                report=self
            )
            self.reporter.profile.add_tokens(1, f'Environmental report: {self.title}')
            self.tokens_awarded = True
            self.save(update_fields=['tokens_awarded'])
            return True
        return False
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()}"

# Keep Alert model as alias for backward compatibility
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

class Token(models.Model):
    ACTION_TYPES = [
        ('report_photo', 'Environmental Report with Photo'),
        ('tree_planting', 'Tree Planting Activity'),
        ('forum_post', 'Community Forum Post'),
        ('resource_share', 'Resource Sharing'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    tokens_earned = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=200)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    # Link to related objects
    report = models.ForeignKey(Report, on_delete=models.CASCADE, null=True, blank=True)
    tree_planting = models.ForeignKey('TreePlanting', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} earned {self.tokens_earned} tokens for {self.get_action_type_display()}"

class Reward(models.Model):
    REWARD_TYPES = [
        ('data_bundle', 'Data Bundle'),
        ('tree_kit', 'Tree Planting Kit'),
        ('workshop', 'Workshop Access'),
        ('certificate', 'Certificate'),
    ]
    
    PROGRAM_TYPES = [
        ('environmental', 'Environmental Reporting'),
        ('trees', '15 Billion Trees Initiative'),
        ('both', 'Both Programs'),
    ]
    
    name = models.CharField(max_length=200)
    reward_type = models.CharField(max_length=50, choices=REWARD_TYPES)
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPES, default='both')
    token_cost = models.PositiveIntegerField()
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.token_cost} tokens)"

class UserReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('delivered', 'Delivered')], default='pending')
    certificate_url = models.URLField(blank=True, null=True, help_text='URL to generated certificate')
    
    def __str__(self):
        return f"{self.user.username} redeemed {self.reward.name}"

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
    
    # Carbon credits data
    tree_age_months = models.PositiveIntegerField(default=0, help_text='Age of trees in months')
    estimated_annual_co2_kg = models.FloatField(default=0.0, help_text='Estimated CO2 absorption per year (kg)')
    carbon_credits_potential = models.FloatField(default=0.0, help_text='Potential carbon credits (tonnes CO2/year)')
    
    # Token reward (will be awarded when verified)
    tokens_awarded = models.BooleanField(default=False)
    carbon_credits_calculated = models.BooleanField(default=False)
    
    def award_tokens(self):
        """Award tokens for verified tree planting"""
        print(f"Checking token award: tokens_awarded={self.tokens_awarded}, status={self.status}, planter={self.planter}")
        
        if not self.tokens_awarded and self.status == 'verified' and self.planter:
            # Award 2 tokens per tree planted
            tokens = self.number_of_trees * 2
            Token.objects.create(
                user=self.planter,
                action_type='tree_planting',
                tokens_earned=tokens,
                description=f'Tree planting: {self.number_of_trees} trees',
                tree_planting=self
            )
            self.planter.profile.add_tokens(tokens, f'Tree planting: {self.number_of_trees} trees')
            
            # Award special initiative badge for first-time planters
            user_tree_count = TreePlanting.objects.filter(planter=self.planter, status='verified').count()
            if user_tree_count == 1:  # First verified tree planting
                self.planter.profile.add_badge("🌍 15 Billion Trees Initiative Participant")
            
            # Mark tokens as awarded and save
            self.tokens_awarded = True
            self.save(update_fields=['tokens_awarded'])
            
            print(f"Tokens awarded: {tokens} to {self.planter.username} for {self.title}")
            return True
        else:
            print(f"Tokens not awarded - already awarded: {self.tokens_awarded}, status: {self.status}, has planter: {bool(self.planter)}")
            return False
    
    def calculate_carbon_potential(self):
        """Calculate carbon credits potential for this tree planting"""
        if not self.carbon_credits_calculated and self.status == 'verified':
            from .carbon_credits import carbon_calculator
            
            # Use tree type as species (map to our species list)
            species_mapping = {
                'indigenous': 'Indigenous Mix',
                'exotic': 'Grevillea',
                'fruit': 'Indigenous Mix',
                'bamboo': 'Bamboo',
                'other': 'Indigenous Mix'
            }
            
            species = species_mapping.get(self.tree_type, 'Indigenous Mix')
            
            # Calculate for each tree
            carbon_data = carbon_calculator.calculate_carbon_potential(
                species=species,
                age_months=self.tree_age_months,
                survival_rate=85,  # Assume 85% survival for verified trees
                location_data=None  # Could be enhanced with GPS data
            )
            
            # Store carbon data
            self.estimated_annual_co2_kg = carbon_data['annual_co2_kg'] * self.number_of_trees
            self.carbon_credits_potential = carbon_data['annual_co2_tonnes'] * self.number_of_trees
            self.carbon_credits_calculated = True
            
            # Award carbon credits to user (for mature trees)
            if self.tree_age_months >= 24 and self.planter:
                self.planter.profile.add_carbon_credits(
                    self.carbon_credits_potential,
                    f'Carbon credits from {self.number_of_trees} trees'
                )
            
            self.save(update_fields=['estimated_annual_co2_kg', 'carbon_credits_potential', 'carbon_credits_calculated'])
            return True
        return False
    
    class Meta:
        ordering = ['-planted_date']
    
    @property
    def planter_display_name(self):
        if self.planter:
            return f"{self.planter.first_name} {self.planter.last_name}".strip() or self.planter.username
        return f"{self.planter_name} (Unregistered)" if self.planter_name else "Unknown Planter"
    
    @property
    def carbon_summary(self):
        """Summary of carbon impact for this planting"""
        return {
            'annual_co2_kg': self.estimated_annual_co2_kg,
            'carbon_credits': self.carbon_credits_potential,
            'estimated_value_kes': self.carbon_credits_potential * 500,
            'trees_count': self.number_of_trees
        }
    
    def __str__(self):
        return f"{self.title} - {self.number_of_trees} trees by {self.planter_display_name}"

class FireRiskPrediction(models.Model):
    RISK_LEVELS = [
        ('LOW', 'Low Risk'),
        ('MODERATE', 'Moderate Risk'),
        ('HIGH', 'High Risk'),
        ('EXTREME', 'Extreme Risk'),
    ]
    
    # Location info
    location_name = models.CharField(max_length=200, help_text='Area/forest name')
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Weather data
    temperature_c = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    wind_speed_ms = models.FloatField(null=True, blank=True)
    rainfall_mm_24h = models.FloatField(null=True, blank=True)
    
    # Environmental data
    ndvi = models.FloatField(null=True, blank=True, help_text='Vegetation index')
    recent_fires = models.IntegerField(default=0, help_text='Recent fires in area')
    
    # Risk assessment
    risk_score = models.FloatField(help_text='Risk score 0-1')
    risk_level = models.CharField(max_length=16, choices=RISK_LEVELS)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.location_name} - {self.risk_level} ({self.created_at.date()})"

class CitizenFireReport(models.Model):
    OBSERVATION_TYPES = [
        ('smoke', 'Smoke'),
        ('heat', 'Heat'),
        ('flames', 'Flames'),
        ('smell', 'Burning smell'),
        ('other', 'Other'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    reporter_name = models.CharField(max_length=200, blank=True, help_text='Name for anonymous reports')
    reporter_phone = models.CharField(max_length=50, blank=True, help_text='Phone for anonymous reports')
    location_name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    observation = models.CharField(max_length=64, choices=OBSERVATION_TYPES)
    notes = models.TextField(blank=True)
    image = models.ImageField(upload_to='fire_reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.observation} @ {self.location_name} ({self.created_at.date()})"

class TreePrediction(models.Model):
    SURVIVAL_LEVELS = [
        ('high', 'High Success Rate'),
        ('medium', 'Medium Success Rate'),
        ('low', 'Low Success Rate'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
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
    survival_probability = models.FloatField(help_text='Probability of survival (0-1)')
    survival_level = models.CharField(max_length=20, choices=SURVIVAL_LEVELS)
    recommended_species = models.TextField(blank=True, help_text='JSON list of recommended species')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        user_name = self.user.username if self.user else 'Anonymous'
        return f"{user_name} - {self.tree_species} ({self.survival_level}) - {self.created_at.date()}"

class CarbonTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('sell', 'Sell Credits'),
        ('fund', 'Fund Project'),
        ('trade', 'Trade Credits'),
        ('earn', 'Earn Credits'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.FloatField(help_text='Amount in tonnes CO2')
    value_kes = models.FloatField(default=0.0, help_text='Value in KES')
    description = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional fields for specific transaction types
    project_name = models.CharField(max_length=200, blank=True, help_text='For project funding')
    buyer_name = models.CharField(max_length=200, blank=True, help_text='For credit sales')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_transaction_type_display()} - {self.amount}t CO2"