from django.urls import path, reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from .views import RegisterView, AccountDeleteView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),

    path(
        'password-change/',
        PasswordChangeView.as_view(
            template_name='profile/password_change.html',
            success_url=reverse_lazy('profile_edit')
        ),
        name='password_change'
    ),

    # account delete view
    path('delete/', AccountDeleteView.as_view(), name='account_delete'),
]
