from django.urls import path
from .views import IndexView, ProductFeaturesView, HomeView, FilterRecipesView, FavoriteIngredientView, \
    SearchIngredientsView

urlpatterns = [
    path('', IndexView.as_view(), name='welcome'),
    path('product_features/', ProductFeaturesView.as_view(), name='product_features'),
    path('home/', HomeView.as_view(), name='home'),
    path('api/filter_recipes/', FilterRecipesView.as_view(), name='filter_recipes'),
    path('api/favorite_ingredient/', FavoriteIngredientView.as_view(), name='favorite_ingredient'),
    path('api/search_ingredients/', SearchIngredientsView.as_view(), name='search_ingredients'),

]
