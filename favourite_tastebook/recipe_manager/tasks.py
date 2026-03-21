import logging
from celery import shared_task
from recipe_manager.application.use_cases.analyze_image_use_case import AnalyzeImageIngredientsUseCase

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=0)
def analyze_image_task(self, image_base64):
    try:
        return AnalyzeImageIngredientsUseCase.execute(image_base64=image_base64)
    except Exception as exc:
        logger.error(f"AI Analysis failed: {str(exc)}")
        raise