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
        error_messages={'required': 'An image of the fridge is required.'}
    )

    ingredients = forms.CharField(required=True)

    def clean_ingredients(self) -> list:
        raw_ingredients = self.cleaned_data.get('ingredients')
        try:
            parsed_list = json.loads(raw_ingredients)

            if not isinstance(parsed_list, list):
                raise ValidationError("Ingredients must be a JSON array.")

            names_list = []
            for item in parsed_list:
                if isinstance(item, str):
                    names_list.append(item)
                elif isinstance(item, dict) and "fields" in item and "name" in item["fields"]:
                    names_list.append(item["fields"]["name"])
                elif isinstance(item, dict) and "name" in item:
                    names_list.append(item["name"])
                else:
                    raise ValidationError("Array items must be strings or objects with a 'name' field.")

            return names_list

        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format for ingredients.")

    def get_base64_image(self) -> str:
        image_file = self.cleaned_data.get('image')
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode('utf-8')
