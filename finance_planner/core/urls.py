"""
URL configuration for finance_planner project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from auth import viewsets as views

schema_view = get_schema_view(
    openapi.Info(
        title="Your API",
        default_version='v1',
        description="API description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@yourapi.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    path('api/auth/login/', views.login_view, name='login'),
    path('api/auth/logout/', views.logout_view, name='logout'),
    path('api/auth/refresh/', views.refresh_token_view, name='refresh_token'),
    path('api/auth/csrf/', views.get_csrf_token, name='get_csrf_token'),
    path('api/auth/sign-up/', views.sign_up_view, name='sign_up_user'),

    path('api/users/', include('users.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/scenarios/', include('scenarios.urls')),
]
