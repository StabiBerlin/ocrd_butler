from datetime import datetime

from ocrd_butler.app import db


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    description = db.Column(db.String(1023))
    work_id = db.Column(db.String)
    queue_id = db.Column(db.String, primary_key=True)

    chain_id = db.Column(db.Integer, db.ForeignKey('chains.id'))
    chain = db.relationship("Chain", backref=db.backref("chains", lazy="dynamic"))

    def __init__(self, title, description, work_id, queue_id, chain):
        self.title = title
        self.description = description
        self.work_id = work_id
        self.queue_id = queue_id
        self.chain = chain

    def __repr__(self):
        return "<Task %r>" % self.title


# class ProcessorTable(db.Model):
#     __tablename__ = "processors"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50))

#     def __init__(self, name):
#         self.name = name

#     def __repr__(self):
#         return "<Processor %s>" % self.name

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
