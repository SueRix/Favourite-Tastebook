from django.urls import path
from .views import IndexView, ProductFeaturesView, HomeView, FilterRecipesView

urlpatterns = [
    path('', IndexView.as_view(), name='welcome'),
    path('product_features/', ProductFeaturesView.as_view(), name='product_features'),
    path('home/', HomeView.as_view(), name='home'),
    path('api/filter_recipes/', FilterRecipesView.as_view(), name='filter_recipes'),

]
