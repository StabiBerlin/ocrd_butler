# -*- coding: utf-8 -*-
"""OCRD Butler database models."""

from ocrd_butler.database import db
# from sqlalchemy.dialects.postgresql import JSON


class Task(db.Model):
    """ Database model for our tasks. """
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64))
    src = db.Column(db.String(255))
    chain_id = db.Column(db.Integer, db.ForeignKey('chains.id'))
    description = db.Column(db.String(1024))
    parameters = db.Column(db.String(4096))
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
            "chain": self.chain.name,
            "parameters": self.parameters,
            "description": self.description,
            "default_file_grp": self.default_file_grp,
            "worker_task_id": self.worker_task_id,
            "status": self.status,
            "results": self.results,
        }

    def __repr__(self):
        desc = self.description and ", description: {}".format(
            self.description) or ""
        return "<Task {0} - source {1}, chain {2}{3}>".format(
            self.uid, self.src, self.chain.name, desc)


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
        return "<self {0} ({1})>".format(self.name, self.description)
