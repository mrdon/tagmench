from datetime import datetime

from tagmench import db


class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(), server_default="now()")
    updated_at = db.Column(db.DateTime(), server_default="now()", onupdate=datetime.now)
