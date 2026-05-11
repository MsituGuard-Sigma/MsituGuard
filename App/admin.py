from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from .models import (
    Comment,
    County,
    CountyEnvironment,
    CountySpecies,
    ForumPost,
    Profile,
    Report,
    Species,
    TreePlanting,
)


@admin.action(description="Mark selected reports as verified")
def verify_reports(modeladmin, request, queryset):
    queryset.update(status="verified")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "reporter", "report_type", "status", "has_image")
    list_filter = ("report_type", "status")
    readonly_fields = ("image_preview", "ai_prediction", "risk_level")
    actions = [verify_reports]
    fieldsets = (
        (
            "Report Information",
            {
                "fields": (
                    "title",
                    "description",
                    "report_type",
                    "location_name",
                    "latitude",
                    "longitude",
                    "phoneNumber",
                    "reporter",
                )
            },
        ),
        ("Image", {"fields": ("image_preview",)}),
        ("AI Review", {"fields": ("ai_prediction", "risk_level")}),
        ("Admin Actions", {"fields": ("status",)}),
    )

    def has_image(self, obj):
        return bool(obj.image)

    has_image.boolean = True
    has_image.short_description = "Image"

    def ai_prediction(self, obj):
        if obj.predicted_category:
            return obj.predicted_category.replace("_", " ")
        return "No prediction"

    ai_prediction.short_description = "AI Prediction"

    def risk_level(self, obj):
        probability = self._extract_probability(obj.description or "")
        if probability is None:
            return "Not scored"
        if probability >= 70:
            return "High risk"
        if probability >= 40:
            return "Moderate risk"
        return "Low risk"

    risk_level.short_description = "Risk Assessment"

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f"""
                <div style="text-align: center;">
                    <img src="{obj.image.url}" style="max-height: 200px; max-width: 300px; border: 2px solid #ddd; border-radius: 8px;"/>
                    <br><small>Report image</small>
                </div>
                """
            )
        return mark_safe('<div style="text-align: center; color: #999;">No image uploaded</div>')

    image_preview.short_description = "Image Preview"

    @staticmethod
    def _extract_probability(description):
        import re

        match = re.search(r"\[ML_PROBABILITY:([0-9.]+)\]", description)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        "bio",
        "location",
        "email",
        "phoneNumber",
        "profile_picture",
        "first_name",
        "last_name",
        "account_type",
        "is_verified",
        "verification_requested",
    )


class UserAdmin(DefaultUserAdmin):
    inlines = [ProfileInline]
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "get_location",
        "get_phone_number",
    )

    def get_location(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.location if profile else ""

    get_location.short_description = "Location"

    def get_phone_number(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.phoneNumber if profile else ""

    get_phone_number.short_description = "Phone number"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "account_type", "is_verified", "verification_requested")
    list_filter = ("account_type", "is_verified", "verification_requested")
    search_fields = ("user__username", "user__email", "phoneNumber", "location")
    actions = ["verify_users"]

    @admin.action(description="Verify selected users")
    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True, verification_requested=False)
        self.message_user(request, f"{updated} users verified successfully.")


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)


admin.site.register(ForumPost)
admin.site.register(Comment)


@admin.register(TreePlanting)
class TreePlantingAdmin(admin.ModelAdmin):
    list_display = ("title", "planter_display_name", "number_of_trees", "status", "planted_date")
    list_filter = ("status", "tree_type")
    list_editable = ("status",)
    readonly_fields = ("planted_date",)
    ordering = ("-planted_date",)

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_obj = TreePlanting.objects.get(pk=obj.pk)
            old_status = old_obj.status

        super().save_model(request, obj, form, change)

        if obj.status == "verified" and old_status != "verified":
            obj.award_tree_points()


class CountySpeciesInline(admin.TabularInline):
    model = CountySpecies
    extra = 0
    autocomplete_fields = ["species"]


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    inlines = [CountySpeciesInline]


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "soil",
        "rainfall",
        "temperature",
        "care_level",
        "best_season",
        "planting_method",
        "water",
    ]
    search_fields = ["name"]
    readonly_fields = ["planting_guide", "care_instructions"]


@admin.register(CountyEnvironment)
class CountyEnvironmentAdmin(admin.ModelAdmin):
    list_display = [
        "county",
        "climate_zone",
        "best_season",
        "rainfall_mm_min",
        "rainfall_mm_max",
        "temperature_c_min",
        "temperature_c_max",
        "soil_type",
        "altitude_m_min",
        "altitude_m_max",
        "soil_ph_min",
        "soil_ph_max",
    ]
    search_fields = ["county__name"]


@admin.register(CountySpecies)
class CountySpeciesAdmin(admin.ModelAdmin):
    list_display = ["county", "species", "survival_rate", "species_rank"]
    list_filter = ["county"]
    autocomplete_fields = ["county", "species"]
