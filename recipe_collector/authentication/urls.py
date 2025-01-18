from django.urls import path
from .views import login_view, register_view, logout_view, success_of_auth_view #,ProtectedView

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('success/', success_of_auth_view, name='success'),
]
