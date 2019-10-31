from datetime import datetime

from ocrd_butler.database import db


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.String(63))
    mets_url = db.Column(db.String(255))
    file_grp = db.Column(db.String(63))
    worker_id = db.Column(db.String(63))
    parameter = db.Column(db.String(4095))

    chain_id = db.Column(db.Integer, db.ForeignKey('chains.id'))
    chain = db.relationship("Chain", backref=db.backref("chains", lazy="dynamic"))

    def __init__(self, work_id, mets_url, file_grp, worker_id, chain_id, parameter):
        self.work_id = work_id
        self.mets_url = mets_url
        self.file_grp = file_grp
        self.worker_id = worker_id
        self.chain_id = chain_id
        self.parameter = parameter

    def __repr__(self):
        return "<Task %r for %r>" % (self.id, self.work_id)

class Chain(db.Model):
    __tablename__ = "chains"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(1023))
    processors = db.Column(db.String(1023))

    def __init__(self, name, description, processors):
        self.name = name
        self.description = description
        self.processors = processors

    def __repr__(self):
        return "<Chain %r>" % self.name
