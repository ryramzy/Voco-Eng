"""
Analytics models for VocoEng Django Frontend

Models for tracking platform usage, performance metrics, and business analytics.
"""

from django.db import models
from django.utils import timezone


class PlatformMetrics(models.Model):
    """Platform-wide metrics for analytics dashboard"""
    
    date = models.DateField(unique=True)
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    
    # Conversation metrics
    total_conversations = models.PositiveIntegerField(default=0)
    new_conversations = models.PositiveIntegerField(default=0)
    active_conversations = models.PositiveIntegerField(default=0)
    
    # Message metrics
    total_messages = models.PositiveIntegerField(default=0)
    messages_sent = models.PositiveIntegerField(default=0)
    messages_received = models.PositiveIntegerField(default=0)
    
    # API usage metrics
    api_requests = models.PositiveIntegerField(default=0)
    api_errors = models.PositiveIntegerField(default=0)
    avg_response_time_ms = models.FloatField(default=0)
    
    # Revenue metrics
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subscription_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'platform_metrics'
        verbose_name = 'Platform Metrics'
        verbose_name_plural = 'Platform Metrics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Metrics for {self.date}"


class ConversationAnalytics(models.Model):
    """Analytics for individual conversations"""
    
    conversation_id = models.CharField(max_length=100, unique=True)
    user_id = models.CharField(max_length=100)
    
    # Conversation details
    source = models.CharField(max_length=50)  # whatsapp, api, telegram
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    
    # Message counts
    user_messages = models.PositiveIntegerField(default=0)
    ai_messages = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    
    # Quality metrics
    avg_response_time_ms = models.FloatField(default=0)
    satisfaction_score = models.FloatField(null=True, blank=True)
    
    # AI model usage
    ai_model = models.CharField(max_length=100, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversation_analytics'
        verbose_name = 'Conversation Analytics'
        verbose_name_plural = 'Conversation Analytics'
        indexes = [
            models.Index(fields=['user_id', 'start_time']),
            models.Index(fields=['source', 'start_time']),
        ]
    
    def __str__(self):
        return f"Conversation {self.conversation_id} - {self.user_id}"


class UserBehavior(models.Model):
    """Track user behavior patterns"""
    
    user_id = models.CharField(max_length=100)
    date = models.DateField()
    
    # Session metrics
    sessions_count = models.PositiveIntegerField(default=0)
    total_session_time_seconds = models.PositiveIntegerField(default=0)
    avg_session_duration_seconds = models.FloatField(default=0)
    
    # Interaction metrics
    conversations_started = models.PositiveIntegerField(default=0)
    messages_sent = models.PositiveIntegerField(default=0)
    api_calls_made = models.PositiveIntegerField(default=0)
    
    # Feature usage
    features_used = models.JSONField(default=list)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_behavior'
        verbose_name = 'User Behavior'
        verbose_name_plural = 'User Behavior'
        unique_together = ['user_id', 'date']
        indexes = [
            models.Index(fields=['user_id', 'date']),
        ]
    
    def __str__(self):
        return f"Behavior {self.user_id} - {self.date}"


class SystemPerformance(models.Model):
    """System performance metrics"""
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Service metrics
    webhook_listener_requests = models.PositiveIntegerField(default=0)
    webhook_listener_errors = models.PositiveIntegerField(default=0)
    worker_processing_time_ms = models.FloatField(default=0)
    worker_errors = models.PositiveIntegerField(default=0)
    django_response_time_ms = models.FloatField(default=0)
    django_errors = models.PositiveIntegerField(default=0)
    
    # Resource metrics
    cpu_usage_percent = models.FloatField(default=0)
    memory_usage_percent = models.FloatField(default=0)
    disk_usage_percent = models.FloatField(default=0)
    
    # Database metrics
    db_connection_count = models.PositiveIntegerField(default=0)
    db_query_time_ms = models.FloatField(default=0)
    firestore_operations = models.PositiveIntegerField(default=0)
    firestore_latency_ms = models.FloatField(default=0)
    
    class Meta:
        db_table = 'system_performance'
        verbose_name = 'System Performance'
        verbose_name_plural = 'System Performance'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Performance at {self.timestamp}"
