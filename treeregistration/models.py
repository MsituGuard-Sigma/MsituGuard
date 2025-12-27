from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import hashlib


# -----------------------------
# User Profile Model
# -----------------------------
class UserProfile(models.Model):
    INDIVIDUAL = "individual"
    ORGANISATION = "organisation"

    USER_TYPES = [
        (INDIVIDUAL, "Individual"),
        (ORGANISATION, "Organisation"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='treeregistration_profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default=INDIVIDUAL)
    tree_count = models.PositiveIntegerField(default=0)
    badge = models.CharField(max_length=20, default="None")

    def update_badge(self):
        """Update badge based on user_type and tree_count."""
        old_badge = self.badge
        
        if self.user_type == self.INDIVIDUAL:
            if self.tree_count >= 1000:  # 500 + 500 for diamond
                self.badge = "Diamond"
            elif self.tree_count >= 500:
                self.badge = "Gold"
            elif self.tree_count >= 300:
                self.badge = "Silver"
            elif self.tree_count >= 100:
                self.badge = "Bronze"
            else:
                self.badge = "None"

        elif self.user_type == self.ORGANISATION:
            if self.tree_count >= 10000:  # 5000 + 5000 for diamond
                self.badge = "Diamond"
            elif self.tree_count >= 5000:
                self.badge = "Gold"
            elif self.tree_count >= 3000:
                self.badge = "Silver"
            elif self.tree_count >= 1000:
                self.badge = "Bronze"
            else:
                self.badge = "None"
        
        # Only save if badge changed
        if old_badge != self.badge:
            print(f"Badge updated from {old_badge} to {self.badge} for {self.user.username}")
        
        return self.badge != old_badge  # Return True if badge changed


# -----------------------------
# Helper: generate hash for photo
# -----------------------------
def generate_photo_hash(image_file) -> str:
    """Generates MD5 hash of uploaded image to prevent duplicates."""
    hasher = hashlib.md5()
    for chunk in image_file.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()


# -----------------------------
# Tree Model
# -----------------------------
class Tree(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='treeregistration_trees')
    photo = models.ImageField(upload_to="tree_photos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    photo_hash = models.CharField(max_length=64)
    latitude = models.FloatField(null=True, blank=True, help_text="GPS latitude coordinate")
    longitude = models.FloatField(null=True, blank=True, help_text="GPS longitude coordinate")
    location_name = models.CharField(max_length=255, null=True, blank=True, help_text="Location name")
    detected_county = models.CharField(max_length=100, null=True, blank=True, help_text="Detected county from location service")

    def save(self, *args, **kwargs):
        # Generate hash if not already set
        if not self.photo_hash and self.photo:
            self.photo_hash = generate_photo_hash(self.photo)

        super().save(*args, **kwargs)

        # Increment user's tree count and update badge
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        profile.tree_count += 1
        badge_changed = profile.update_badge()
        profile.save()
        
        if badge_changed:
            print(f"Congratulations! {self.user.username} earned a new badge: {profile.badge}!")

    def __str__(self):
        return f"Tree {self.id} by {self.user.username}"
