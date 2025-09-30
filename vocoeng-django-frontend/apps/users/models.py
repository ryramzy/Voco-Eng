"""
User models for VocoEng Django Frontend

Custom user model with additional fields for analytics and user management.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    
    Adds fields for analytics, user preferences, and API access tracking.
    """
    
    # Basic profile information
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # User preferences
    language = models.CharField(max_length=10, default='en')
    notification_preferences = models.JSONField(default=dict, blank=True)
    
    # Analytics fields
    total_conversations = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    registration_source = models.CharField(max_length=50, default='web')
    
    # API access tracking
    api_key = models.CharField(max_length=64, blank=True, null=True, unique=True)
    api_usage_count = models.PositiveIntegerField(default=0)
    api_last_used = models.DateTimeField(blank=True, null=True)
    
    # Subscription and billing
    subscription_plan = models.CharField(max_length=50, default='free')
    subscription_status = models.CharField(max_length=20, default='active')
    subscription_expires = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def is_premium(self):
        """Check if user has premium subscription"""
        return self.subscription_plan in ['premium', 'enterprise']
    
    @property
    def is_subscription_active(self):
        """Check if subscription is currently active"""
        if not self.subscription_expires:
            return self.subscription_status == 'active'
        return (
            self.subscription_status == 'active' and 
            self.subscription_expires > timezone.now()
        )


class UserSession(models.Model):
    """
    Track user sessions for analytics
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at}"


class APIUsage(models.Model):
    """
    Track API usage for billing and analytics
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_usage')
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    response_time_ms = models.PositiveIntegerField()
    request_size_bytes = models.PositiveIntegerField(default=0)
    response_size_bytes = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_usage'
        verbose_name = 'API Usage'
        verbose_name_plural = 'API Usage Records'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['endpoint', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.endpoint} - {self.created_at}"
