"""
User serializers for VocoEng Django Frontend

Serializers for user authentication, profile management, and API access.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User, UserSession, APIUsage


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'avatar', 'timezone', 'language',
            'notification_preferences', 'total_conversations',
            'total_messages', 'last_activity', 'subscription_plan',
            'subscription_status', 'created_at'
        ]
        read_only_fields = [
            'id', 'username', 'total_conversations', 'total_messages',
            'last_activity', 'subscription_plan', 'subscription_status',
            'created_at'
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'avatar',
            'timezone', 'language', 'notification_preferences'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API key management"""
    
    class Meta:
        model = User
        fields = ['api_key', 'api_usage_count', 'api_last_used']
        read_only_fields = ['api_usage_count', 'api_last_used']


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions"""
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'session_key', 'ip_address', 'user_agent',
            'created_at', 'last_activity', 'is_active'
        ]
        read_only_fields = ['session_key']


class APIUsageSerializer(serializers.ModelSerializer):
    """Serializer for API usage tracking"""
    
    class Meta:
        model = APIUsage
        fields = [
            'id', 'endpoint', 'method', 'status_code',
            'response_time_ms', 'request_size_bytes',
            'response_size_bytes', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    
    total_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    api_usage_count = serializers.IntegerField()
    last_activity = serializers.DateTimeField()
    subscription_plan = serializers.CharField()
    subscription_status = serializers.CharField()
    is_premium = serializers.BooleanField()
    is_subscription_active = serializers.BooleanField()
