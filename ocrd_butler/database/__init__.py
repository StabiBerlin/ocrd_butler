from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def reset_database():
    """ Renew the database. """
    from ocrd_butler.database.models import Task, Chain
    db.drop_all()
    db.create_all()
