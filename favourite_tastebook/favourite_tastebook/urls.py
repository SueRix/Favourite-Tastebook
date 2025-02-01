from django.contrib import admin
from django.urls import path, include
from recipe_manager.views import IndexView, OurProductView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('authentication.urls')),
    path('welcome/', IndexView.as_view(), name='welcome'),
    path('our_product/', OurProductView.as_view(), name='our_product')
]
