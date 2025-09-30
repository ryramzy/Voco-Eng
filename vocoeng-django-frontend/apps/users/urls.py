"""
URL configuration for users app
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='user_register'),
    path('login/', views.UserLoginView.as_view(), name='user_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    
    # API key management
    path('api-key/', views.APIKeyView.as_view(), name='api_key'),
    
    # User statistics
    path('stats/', views.UserStatsView.as_view(), name='user_stats'),
    
    # Session management
    path('sessions/', views.UserSessionsView.as_view(), name='user_sessions'),
    path('sessions/<int:session_id>/', views.UserSessionsView.as_view(), name='user_session_detail'),
    
    # API usage tracking
    path('usage/', views.APIUsageView.as_view(), name='api_usage'),
    path('track-usage/', views.track_api_usage, name='track_api_usage'),
]
