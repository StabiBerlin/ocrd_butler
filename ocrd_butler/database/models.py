# -*- coding: utf-8 -*-
"""OCRD Butler database models."""

from typing import List
import uuid

from ocrd_butler.database import db
from ocrd_butler.util import (
    logger,
    to_json,
)



class Task(db.Model):
    """ Database model for our tasks. """
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64))
    src = db.Column(db.String(255))
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'))
    description = db.Column(db.String(1024))
    parameters = db.Column(db.JSON)
    default_file_grp = db.Column(db.String(64))
    worker_task_id = db.Column(db.String(64))
    status = db.Column(db.String(64))
    # Change this "results" to postres specific JSON, if we switch.
    results = db.Column(db.JSON)

    workflow = db.relationship(
        "Workflow",
        backref=db.backref("workflows", lazy="dynamic")
    )

    def __init__(
        self, src, workflow_id, uid=None, parameters={}, description="",
        default_file_grp="DEFAULT", worker_task_id=None,
        status="CREATED", results={}
    ):
        if uid is None:
            uid = uuid.uuid4().__str__()
        self.uid = uid
        self.src = src
        self.workflow_id = workflow_id
        self.parameters = parameters
        self.description = description
        self.default_file_grp = default_file_grp
        self.worker_task_id = worker_task_id
        self.status = status
        self.results = results

    def to_json(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "src": self.src,
            "workflow": self.workflow.to_json(),
            "parameters": to_json(self.parameters),
            "description": self.description,
            "default_file_grp": self.default_file_grp,
            "worker_task_id": self.worker_task_id,
            "status": self.status,
            "results": self.results,
        }

    def __repr__(self):
        desc = self.description and ", description: {}".format(
            self.description) or ""
        return "Task {0} - source {1}, workflow {2}{3}".format(
            self.uid, self.src, self.workflow, desc
        )
        # TODO: test_frontend/test_task_delete fail with
        # self.uid, self.src, self.workflow.name, desc)


class Workflow(db.Model):
    """ Database model for our workflow.

    Example usage::

        [
            {
                "name": "ocrd-example",
                "parameters": {
                    "model": "/data/example/models"
                }
            },
        ]
    """
    __tablename__ = "workflows"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64))
    name = db.Column(db.String(64))
    description = db.Column(db.String(1024))
    processors = db.Column(db.JSON)

    def __init__(self, name, description, processors, uid=None):
        if uid is None:
            uid = uuid.uuid4().__str__()
        self.uid = uid
        self.name = name
        self.description = description
        self.processors = processors

    def to_json(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "name": self.name,
            "description": self.description,
            "processors": self.processors
        }

    def __repr__(self):
        return "Workflow {0} ({1})".format(self.name, self.description)


def delete(model: type, id: str) -> bool:
    """ delete the db model instance identified by ID if it exists,
    return ``False`` otherwise.
    """
    matches = model.query.filter_by(id=id)
    if matches.count() > 0:
        matches.delete()
        db.session.commit()
        return True
    else:
        logger.info(f"Can't delete {model.__name__} `{id}`: not found!")
        return False


def save(obj: db.Model) -> db.Model:
    """ save a db model instance to session and commit this change.
    """
    db.session.add(obj)
    db.session.commit()
    return obj


def get(model: type, **kwargs) -> db.Model:
    """ look up a db model instance by ID.
    """
    return model.query.filter_by(**kwargs).first()


def get_all(model: type) -> List[db.Model]:
    """ returns all instances of db model.
    """
    return model.query.all()


def create(model: type, **data) -> db.Model:
    """ create a new instance of the specified db model, without saving it.
    """
    return model(**data)


def add(model: type, **data) -> db.Model:
    """ create a new instance of the specified db model, and save it to
    session.
    """
    return create(model, **data).save()


def count(model: type) -> int:
    """ count number of db model instances.
    """
    return model.query.count()


def _add_model_operations():
    """ equip both db model classes with convenience functions for creation,
    deletion, item count, and so on.
    """
    for model in [Task, Workflow]:
        model.save = save
        for func in [
            get, create, add, count, delete, get_all
        ]:
            setattr(
                model, func.__name__, classmethod(func)
            )


_add_model_operations()
