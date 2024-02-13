# tasks.py
import os
from celery import Celery

# Get the RabbitMQ user and password from the environment
broker_user = os.environ.get('RABBITMQ_DEFAULT_USER')
broker_password = os.environ.get('RABBITMQ_DEFAULT_PASS')
broker_host = os.environ.get('RABBITMQ_HOST')

celery_app = Celery('document_ingestion', broker=f'amqp://{broker_user}:{broker_password}@{broker_host}')

@celery_app.task(bind=True)
def process_document_task(self, file_path):
    # Document processing logic here
    return 'Document processed'