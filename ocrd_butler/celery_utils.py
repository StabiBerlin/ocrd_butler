# -*- coding: utf-8 -*-

"""Utils for celery."""


def init_celery(celery, app):

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
