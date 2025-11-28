"""URL configuration for finance_planner project.

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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


@csrf_exempt
def simple_login_view(request):
    """Простой login view для Swagger UI."""
    return HttpResponse(
        """
    <html>
    <head><title>Login</title></head>
    <body>
        <h1>Login</h1>
        <p>Для использования API используйте кнопку "Authorize" в Swagger UI</p>
        <p><a href="/docs/">Вернуться к документации</a></p>
    </body>
    </html>
    """
    )


schema_view = get_schema_view(
    openapi.Info(
        title="Finance Planner API",
        default_version="v1",
        description="API для управления финансами",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@yourapi.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("", include("django_prometheus.urls")),
    path("admin/", admin.site.urls),  # Вот это добавляет /admin
    # Django admin login для Swagger UI
    path("accounts/login/", simple_login_view, name="django_login"),
    path("api/", include("auth.urls")),
    path("api/users/", include("users.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/scenarios/", include("scenarios.urls")),
    path("api/regular-operations/", include("regular_operations.urls")),
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
]
