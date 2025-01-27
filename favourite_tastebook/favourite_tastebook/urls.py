from django.contrib import admin
from django.urls import path, include
from authentication.views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('authentication.urls')),

    path('home/', HomeView.as_view(), name='home'),
]
