from django.contrib import admin
from .models import UserProfile, Tree


# --------- User Profile Admin ---------
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'tree_count', 'badge')
    list_filter = ('user_type', 'badge')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user',)


# --------- Tree Admin ---------
class TreeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'uploaded_at', 'photo')
    list_filter = ('uploaded_at', 'user')
    search_fields = ('user__username',)
    readonly_fields = ('uploaded_at', 'photo_hash')


# Register models
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Tree, TreeAdmin)
