from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from django.views.static import serve
urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("authentication.urls")),

    path("profile/", include("profile_manager.urls")),

    path("home/", include("recipe_manager.urls")),

    # Server-to-server tool surface for the n8n cooking agent. Kept off the
    # browser-facing prefixes so it can be firewalled as a single path.
    path("api/agent/", include("recipe_manager.agent_urls")),

    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)