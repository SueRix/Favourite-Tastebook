from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from authentication.views import HomeView
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('authentication.urls')),
    path('accounts/', include('profile_manager.urls')),
    path('home/', HomeView.as_view(), name='home'),
    path("", include("recipe_manager.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
