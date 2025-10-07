from typing import Optional
from flask import Flask
from pymongo import MongoClient, ASCENDING

mongo_client: Optional[MongoClient] = None
mongo_db = None


def init_mongo(app: Flask) -> None:
    global mongo_client, mongo_db
    uri = app.config.get('MONGO_URI', 'mongodb://localhost:27017')
    db_name = app.config.get('MONGO_DB_NAME', 'exam_management')
    mongo_client = MongoClient(uri)
    mongo_db = mongo_client[db_name]
    # Common indexes
    try:
        mongo_db.students.create_index([('reg_no', ASCENDING)], name='idx_students_regno', unique=False)
        mongo_db.subjects.create_index([('code', ASCENDING)], name='idx_subjects_code', unique=False)
        mongo_db.exam_slots.create_index([('date', ASCENDING), ('session', ASCENDING), ('subject_id', ASCENDING)], name='idx_slots_date_sess_sub')
    except Exception:
        pass
    # Attach to app for convenience
    app.extensions = getattr(app, 'extensions', {})
    app.extensions['mongo_client'] = mongo_client
    app.extensions['mongo_db'] = mongo_db
