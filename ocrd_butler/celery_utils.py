# -*- coding: utf-8 -*-

"""Taskrunner definition."""

# def init_celery(celery, app):

#     celery.conf.update(app.config)
#     celery.conf.update(
#         task_serializer='json',
#         accept_content=['json'],  # Ignore other content
#         result_serializer='json',
#         timezone='Europe/Berlin',
#         enable_utc=True
#     )

#     TaskBase = celery.Task
#     class ContextTask(TaskBase):
#         abstract = True
#         def __call__(self, *args, **kwargs):
#             with app.app_context():
#                 return TaskBase.__call__(self, *args, **kwargs)
#     celery.Task = ContextTask


from celery import Celery

def create_celery_app(app):
    """
    Creates a celery application.

    Args:
        app (Object): Flask application object
    Returns:
        celery object
    """

    celery = Celery(app.import_name,
                    backend=app.config['CELERY_RESULT_BACKEND_URL'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],  # Ignore other content
        result_serializer='json',
        timezone='Europe/Berlin',
        enable_utc=True
    )

    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask

    return celery
