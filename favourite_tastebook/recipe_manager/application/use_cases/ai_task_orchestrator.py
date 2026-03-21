from recipe_manager.infrastructure.task_queue.celery_adapter import CeleryAIAnalyzerAdapter

class AITaskOrchestratorUseCase:
    @classmethod
    def trigger_analysis(cls, image_base64):
        task_id = CeleryAIAnalyzerAdapter.trigger_analysis(image_base64=image_base64)
        return {'task_id': task_id}

    @classmethod
    def process_task_status(cls, task_id):
        result = CeleryAIAnalyzerAdapter.get_task_result(task_id)

        if result['status'] == 'ongoing':
            return {'status': 'ongoing', 'context': {'task_id': task_id}}

        if result['status'] == 'success':
            return {
                'status': 'success',
                'context': {'matched_ingredients': result['data'].get('matched_ingredients', [])}
            }

        return {
            'status': 'error',
            'context': {
                'error_message': 'AI service is currently busy or limits exceeded. Please try again in a minute.'}
        }