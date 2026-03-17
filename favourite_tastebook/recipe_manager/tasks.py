import logging
from celery import shared_task
from recipe_manager.application.use_cases.analyze_image_use_case import AnalyzeImageIngredientsUseCase

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def analyze_image_task(self, image_base64: str) -> dict:
    try:
        result = AnalyzeImageIngredientsUseCase.execute(
            image_base64=image_base64
        )
        return result

    except Exception as exc:
        logger.error(f"Image analysis task failed on attempt {self.request.retries}: {str(exc)}")
        raise self.retry(exc=exc, countdown=5 ** self.request.retries)