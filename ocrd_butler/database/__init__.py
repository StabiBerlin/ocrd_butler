from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def reset_database():
    """ Renew the database. """
    db.drop_all()
    db.create_all()
