from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('features.authentication.urls')),

    # Security to home page if user do not authenticated
    path('home/', login_required(TemplateView.as_view(template_name='home.html')), name='home_page'),
]
