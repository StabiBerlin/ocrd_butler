from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.database import models


task_data = dict(
    uid="001",
    src="src",
    chain_id="1",
    description="desc",
)


class DatabaseModelTests(TestCase):

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def test_create_task(self):
        count = models.Task.count()
        assert count == 0
        task = models.Task.add(**task_data)
        assert type(task) == models.Task
        assert models.Task.get(id=task.id) == task
        assert models.Task.count() == count + 1
        models.Task.delete(task.id)
        assert models.Task.count() == count

    def test_delete_task(self):
        task = models.Task.create(**task_data).save()
        assert models.Task.count() > 0
        assert models.Task.delete(task.id) is True
        assert models.Task.delete(task.id) is False
