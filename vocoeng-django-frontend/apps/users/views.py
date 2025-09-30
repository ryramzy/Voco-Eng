"""
User views for VocoEng Django Frontend

Views for user authentication, profile management, and API access.
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
import uuid

from .models import User, UserSession, APIUsage
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserUpdateSerializer, PasswordChangeSerializer, APIKeySerializer,
    UserSessionSerializer, APIUsageSerializer, UserStatsSerializer
)


class UserRegistrationView(APIView):
    """User registration endpoint"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """User login endpoint"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last activity
            user.last_activity = timezone.now()
            user.save(update_fields=['last_activity'])
            
            # Track session
            UserSession.objects.create(
                user=user,
                session_key=str(uuid.uuid4()),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """User profile management"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """Password change endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIKeyView(APIView):
    """API key management"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = APIKeySerializer(request.user)
        return Response(serializer.data)
    
    def post(self, request):
        # Generate new API key
        api_key = str(uuid.uuid4()).replace('-', '')
        request.user.api_key = api_key
        request.user.save(update_fields=['api_key'])
        
        serializer = APIKeySerializer(request.user)
        return Response(serializer.data)
    
    def delete(self, request):
        request.user.api_key = None
        request.user.save(update_fields=['api_key'])
        return Response({'message': 'API key revoked'})


class UserStatsView(APIView):
    """User statistics endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        stats = {
            'total_conversations': user.total_conversations,
            'total_messages': user.total_messages,
            'api_usage_count': user.api_usage_count,
            'last_activity': user.last_activity,
            'subscription_plan': user.subscription_plan,
            'subscription_status': user.subscription_status,
            'is_premium': user.is_premium,
            'is_subscription_active': user.is_subscription_active,
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)


class UserSessionsView(APIView):
    """User sessions management"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        sessions = UserSession.objects.filter(user=request.user, is_active=True)
        serializer = UserSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    def delete(self, request, session_id=None):
        if session_id:
            try:
                session = UserSession.objects.get(id=session_id, user=request.user)
                session.is_active = False
                session.save()
                return Response({'message': 'Session terminated'})
            except UserSession.DoesNotExist:
                return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Terminate all sessions except current
            UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
            return Response({'message': 'All sessions terminated'})


class APIUsageView(APIView):
    """API usage tracking"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        usage = APIUsage.objects.filter(user=request.user).order_by('-created_at')[:100]
        serializer = APIUsageSerializer(usage, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def track_api_usage(request):
    """Track API usage for analytics"""
    try:
        APIUsage.objects.create(
            user=request.user,
            endpoint=request.data.get('endpoint', ''),
            method=request.data.get('method', ''),
            status_code=request.data.get('status_code', 200),
            response_time_ms=request.data.get('response_time_ms', 0),
            request_size_bytes=request.data.get('request_size_bytes', 0),
            response_size_bytes=request.data.get('response_size_bytes', 0),
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        # Update user API usage count
        request.user.api_usage_count += 1
        request.user.api_last_used = timezone.now()
        request.user.save(update_fields=['api_usage_count', 'api_last_used'])
        
        return Response({'message': 'Usage tracked'})
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
