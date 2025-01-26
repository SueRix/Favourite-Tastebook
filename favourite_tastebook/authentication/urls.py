from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import RegisterView, EmptyView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('empty/', EmptyView.as_view(), name='empty'),
]
