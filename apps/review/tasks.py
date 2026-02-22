from celery import shared_task

from apps.review.services import process_review_run


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def process_review_run_task(self, run_id: str) -> None:
    process_review_run(run_id)
