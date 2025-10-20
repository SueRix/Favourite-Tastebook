from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from favourite_tastebook import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include('authentication.urls')),
    path('', include('recipe_manager.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
