from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import (
    MyPasswordChangeView, MyPasswordChangeDoneView,
    MyPasswordResetView, MyPasswordResetDoneView,
    MyPasswordResetConfirmView, MyPasswordResetCompleteView, RegisterView, ProfileUpdateView
)

urlpatterns = [
    path('login/',  auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileUpdateView.as_view(template_name='update_profile.html'), name='profile'),
    path('password-change/', MyPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', MyPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password-reset/', MyPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', MyPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', MyPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/complete/', MyPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
