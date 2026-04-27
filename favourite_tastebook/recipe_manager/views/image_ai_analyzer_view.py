from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from recipe_manager.forms import ImageAIAnalysisForm
from recipe_manager.application.use_cases.ai_task_orchestrator import AITaskOrchestratorUseCase
from recipe_manager.models import Ingredient


#dev decorator
@method_decorator(csrf_exempt, name='dispatch')
class AIFormView(View):
    def get(self, request, *args, **kwargs):
        context = {'form': ImageAIAnalysisForm()}
        return render(request, 'partials/upload_image_for_ai.html', context)

#dev decorator
@method_decorator(csrf_exempt, name='dispatch')
class AIProcessView(View):
    def post(self, request, *args, **kwargs):
        form = ImageAIAnalysisForm(request.POST, request.FILES)

        if not form.is_valid():
            context = {'form': form, 'error_message': 'Invalid file or data.'}
            return render(request, 'partials/upload_image_for_ai.html', context)

        context = AITaskOrchestratorUseCase.trigger_analysis(
            image_base64=form.get_base64_image()
        )
        return render(request, 'partials/ai_spinner_polling.html', context)

#dev
@method_decorator(csrf_exempt, name='dispatch')
class AIStatusView(View):
    def get(self, request, task_id, *args, **kwargs):
        result = AITaskOrchestratorUseCase.process_task_status(task_id=task_id)

        if result['status'] == 'ongoing':
            return render(request, 'partials/ai_spinner_polling.html', result['context'])

        if result['status'] == 'success':
            matched_names = result['context'].get('matched_ingredients', [])

            # Direct database query for the specific partial
            ingredients_qs = Ingredient.objects.filter(name__in=matched_names).order_by("name")

            context = {
                'matched_ingredients': ingredients_qs,
                'match_count': ingredients_qs.count(),
                'status': 'success',
                'ai_success_message': f"Found {ingredients_qs.count()} ingredients!"
            }

            response = render(request, 'partials/ingredients_analyzer_result.html', context)
            response['HX-Trigger'] = 'updateRecipes'
            return response

        # Error state
        error_context = result['context']
        error_context['form'] = ImageAIAnalysisForm()
        return render(request, 'partials/upload_image_for_ai.html', error_context)