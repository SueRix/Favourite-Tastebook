from .models import Ingredient
import json
import base64
from django import forms
from django.core.exceptions import ValidationError


class RecipeSearchForm(forms.Form):
    q = forms.CharField(required=False, strip=True)
    category = forms.CharField(required=False)
    strict = forms.BooleanField(required=False)

    recipe = forms.IntegerField(required=False)

    ingredient = forms.ModelMultipleChoiceField(
        queryset=Ingredient._default_manager,
        required=False,
    )


class ImageAIAnalysisForm(forms.Form):
    image = forms.ImageField(
        required=True,
        error_messages={'required': 'An image of the ingredients is required.'}
    )

    def get_base64_image(self) -> str:
        image_file = self.cleaned_data.get('image')
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode('utf-8')
