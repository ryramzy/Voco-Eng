"""
Admin configuration for users app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserSession, APIUsage


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""
    
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'subscription_plan', 'subscription_status', 'is_active',
        'total_conversations', 'total_messages', 'last_activity'
    ]
    
    list_filter = [
        'subscription_plan', 'subscription_status', 'is_active',
        'is_staff', 'is_superuser', 'created_at'
    ]
    
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('phone_number', 'avatar', 'timezone', 'language')
        }),
        ('Analytics', {
            'fields': ('total_conversations', 'total_messages', 'last_activity', 'registration_source')
        }),
        ('API Access', {
            'fields': ('api_key', 'api_usage_count', 'api_last_used')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_status', 'subscription_expires')
        }),
        ('Preferences', {
            'fields': ('notification_preferences',)
        }),
    )
    
    readonly_fields = ['total_conversations', 'total_messages', 'api_usage_count', 'created_at', 'updated_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """User session admin"""
    
    list_display = ['user', 'ip_address', 'created_at', 'last_activity', 'is_active']
    list_filter = ['is_active', 'created_at', 'last_activity']
    search_fields = ['user__username', 'user__email', 'ip_address']
    readonly_fields = ['session_key', 'created_at', 'last_activity']


@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    """API usage admin"""
    
    list_display = [
        'user', 'endpoint', 'method', 'status_code',
        'response_time_ms', 'created_at'
    ]
    
    list_filter = ['method', 'status_code', 'created_at']
    search_fields = ['user__username', 'endpoint']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
