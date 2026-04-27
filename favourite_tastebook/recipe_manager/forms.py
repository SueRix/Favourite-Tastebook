from .models import Ingredient
import base64
from django import forms


class RecipeSearchForm(forms.Form):
    q = forms.CharField(required=False, strip=True)
    category = forms.CharField(required=False)

    strict = forms.CharField(required=False)

    auto_show = forms.CharField(required=False)
    ai_mode_active = forms.CharField(required=False)

    recipe = forms.IntegerField(required=False)

    ingredient = forms.ModelMultipleChoiceField(
        queryset=Ingredient._default_manager,
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        if self.data and 'ai_selected' in self.data:
            cleaned_data['ai_selected'] = self.data.getlist('ai_selected')

        return cleaned_data


class ImageAIAnalysisForm(forms.Form):
    image = forms.ImageField(
        required=True,
        error_messages={'required': 'An image of the ingredients is required.'}
    )

    def get_base64_image(self) -> str:
        image_file = self.cleaned_data.get('image')
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode('utf-8')