from flask_testing import TestCase
from ocrd_butler.api.processors import Processors

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.database import models


task_data = dict(
    uid="001",
    src="src",
    workflow_id="1",
    description="desc",
)

workflow_data = dict(
    uid="123",
    name="name",
    description="desc",
    processors = [{
        "name": "foo"
    }]
)

workflow_data_no_uid = dict(
    name="name2",
    description="desc2",
    processors = [{
        "name": "bar"
    }]
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

    def test_get_all_tasks(self):
        for i in range(3):
            models.Task.add(**task_data)
        tasks = models.Task.get_all()
        assert models.Task.count() == len(tasks)
        assert type(tasks[0]) == models.Task

    def test_delete_task(self):
        task = models.Task.create(**task_data).save()
        assert models.Task.count() > 0
        assert models.Task.delete(task.id) is True
        assert models.Task.delete(task.id) is False

    def test_workflow(self):
        workflow = models.Workflow.create(**workflow_data).save()
        assert models.Workflow.count() == 1
        workflows = models.Workflow.get_all()
        assert type(workflows[0]) == models.Workflow
        workflow = models.Workflow.create(**workflow_data_no_uid).save()
        assert workflow is not None
