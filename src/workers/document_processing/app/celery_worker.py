from celery import Celery
import os


broker_user = os.environ.get("RABBITMQ_DEFAULT_USER")
broker_password = os.environ.get("RABBITMQ_DEFAULT_PASS")
broker_host = os.environ.get("RABBITMQ_HOST")

celery_app = Celery(
    "document_ingestion",
    broker=f"amqp://{broker_user}:{broker_password}@{broker_host}",
    backend='rpc://',
    include=["document_ingestion_tasks"],
)
