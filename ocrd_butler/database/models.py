# -*- coding: utf-8 -*-
"""OCRD Butler database models."""

from __future__ import annotations
from typing import List

from ocrd_butler.database import db
from ocrd_butler.util import (
    logger,
    to_json,
)
# from sqlalchemy.dialects.postgresql import JSON

log = logger(__name__)


class Task(db.Model):
    """ Database model for our tasks. """
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64))
    src = db.Column(db.String(255))
    chain_id = db.Column(db.Integer, db.ForeignKey('chains.id'))
    description = db.Column(db.String(1024))
    parameters = db.Column(db.JSON)
    default_file_grp = db.Column(db.String(64))
    worker_task_id = db.Column(db.String(64))
    status = db.Column(db.String(64))
    # Change this "results" to postres specific JSON, if we switch.
    results = db.Column(db.JSON)

    chain = db.relationship("Chain",
                            backref=db.backref("chains", lazy="dynamic"))

    def __init__(self, uid, src, chain_id, parameters={}, description="",
                 default_file_grp="DEFAULT", worker_task_id=None,
                 status="CREATED", results={}):
        self.uid = uid
        self.src = src
        self.chain_id = chain_id
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
            "chain": self.chain.to_json(),
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
        return "Task {0} - source {1}, chain {2}{3}".format(
            self.uid, self.src, self.chain, desc)
            # TODO: test_frontend/test_task_delete fail with
            # self.uid, self.src, self.chain.name, desc)


class Chain(db.Model):
    """ Database model for our chains. """
    __tablename__ = "chains"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(1024))
    processors = db.Column(db.JSON)
    parameters = db.Column(db.JSON)

    def __init__(self, name, description, processors, parameters=None):
        self.name = name
        self.description = description
        self.processors = processors
        self.parameters = parameters

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "processors": self.processors,
            "parameters": self.parameters,
        }

    def __repr__(self):
        return "Chain {0} ({1})".format(self.name, self.description)


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
        log.info(f"Can't delete {model.__name__} `{id}`: not found!")
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
    for model in [Task, Chain]:
        model.save = save
        for func in [
            get, create, add, count, delete, get_all
        ]:
            setattr(
                model, func.__name__, classmethod(func)
            )


_add_model_operations()
