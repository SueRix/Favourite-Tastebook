from recipe_manager.application.use_cases.home_dashboard import DashboardUseCase
from recipe_manager.infrastructure.task_queue.celery_adapter import CeleryAIAnalyzerAdapter


class AITaskOrchestratorUseCase:
    """
    Application layer: Orchestrates the task queue adapter and UI context generation.
    Completely decoupled from Celery.
    """

    @classmethod
    def trigger_analysis(cls, image_base64: str) -> dict:
        task_id = CeleryAIAnalyzerAdapter.trigger_analysis(
            image_base64=image_base64
        )

        return {'task_id': task_id}

    @classmethod
    def process_task_status(cls, task_id: str, query_params) -> dict:
        result = CeleryAIAnalyzerAdapter.get_task_result(task_id)

        if result['status'] == 'ongoing':
            return {
                'status': 'ongoing',
                'context': {'task_id': task_id}
            }

        if result['status'] == 'success':
            matched_ingredients = result['data'].get('matched_ingredients', [])

            filters = query_params.copy()
            filters.setlist('ai_selected', matched_ingredients)

            context = DashboardUseCase.build_ingredients_partial(filters)
            context['ai_success_message'] = f"Found {len(matched_ingredients)} ingredients!"
            context['status'] = 'success'
            context['match_count'] = len(matched_ingredients)
            context['matched_ingredients'] = matched_ingredients

            return {
                'status': 'success',
                'context': context
            }

        return {
            'status': 'error',
            'context': {'error_message': 'AI analysis failed. Please try again.'}
        }
