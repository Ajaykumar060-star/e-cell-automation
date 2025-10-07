import os
from flask import Flask

from .extensions import init_mongo
from .blueprints.students import bp as students_v2_bp


def create_app() -> Flask:
    app = Flask(__name__)
    # Basic config (kept minimal; real config lives in app.py or config.py)
    app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    app.config['MONGO_DB_NAME'] = os.getenv('MONGO_DB_NAME', os.getenv('DB_NAME', 'exam_management'))
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')

    # Init Mongo
    init_mongo(app)

    # Register blueprints
    init_blueprints(app)

    return app


def init_blueprints(app: Flask) -> None:
    app.register_blueprint(students_v2_bp)

