"""
URL configuration for vocoeng_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def health_check(request):
    """Health check endpoint for Cloud Run"""
    return JsonResponse({
        "status": "healthy",
        "service": "vocoeng-django-frontend",
        "version": "1.0.0"
    })


urlpatterns = [
    # Health check endpoint
    path('health/', health_check, name='health_check'),
    
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/conversations/', include('apps.conversations.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.urls')),
    
    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
