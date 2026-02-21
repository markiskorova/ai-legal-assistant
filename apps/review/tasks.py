from celery import shared_task

from apps.review.services import process_review_run


@shared_task
def process_review_run_task(run_id: str) -> None:
    process_review_run(run_id)
