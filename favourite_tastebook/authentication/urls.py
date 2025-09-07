from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (RegisterView, UpdateProfileView)

urlpatterns = [
    path('login/',  auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('update-profile/', UpdateProfileView.as_view(template_name='update_profile.html'), name='profile'),
]
