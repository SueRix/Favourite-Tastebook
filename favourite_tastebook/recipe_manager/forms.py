from django import forms
from .models import Ingredient


class RecipeSearchForm(forms.Form):
    q = forms.CharField(required=False, strip=True)
    category = forms.CharField(required=False)
    strict = forms.BooleanField(required=False)

    recipe = forms.IntegerField(required=False)

    ingredient = forms.ModelMultipleChoiceField(
        queryset=Ingredient._default_manager,
        required=False,
    )
