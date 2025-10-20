from auth import viewsets as views
from django.urls import path


urlpatterns = [
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/refresh/", views.refresh_token_view, name="refresh_token"),
    path("auth/csrf/", views.get_csrf_token, name="get_csrf_token"),
    path("auth/sign-up/", views.sign_up_view, name="sign_up_user"),
]
