from celery.result import AsyncResult
from recipe_manager.tasks import analyze_image_task


class CeleryAIAnalyzerAdapter:
    """
    Infrastructure layer: Encapsulates Celery task execution and state checking.
    Keeps the Application layer clean of framework-specific imports.
    """

    @staticmethod
    def trigger_analysis(image_base64: str) -> str:
        """
        Dispatches the Celery task and returns the task ID.
        """
        task = analyze_image_task.delay(image_base64)
        return task.id

    @staticmethod
    def get_task_result(task_id: str) -> dict:
        """
        Retrieves the task status and payload without exposing AsyncResult.
        """
        task_result = AsyncResult(task_id)

        if task_result.state in ['PENDING', 'STARTED']:
            return {'status': 'ongoing'}

        if task_result.state == 'SUCCESS':
            return {
                'status': 'success',
                'data': task_result.result
            }

        return {
            'status': 'error',
            'error_message': 'AI task failed or was revoked.'
        }