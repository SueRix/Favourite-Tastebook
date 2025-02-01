from django.urls import path
from .views import IndexView, OurProductView, HomeView

urlpatterns = [
    path('welcome/', IndexView.as_view(), name='welcome'),
    path('our_product/', OurProductView.as_view(), name='our_product'),
    path('home/', HomeView.as_view(), name='home'),
]
