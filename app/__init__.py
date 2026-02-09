import os
from flask import Flask
from config import config
from app.extensions import db, login_manager, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance folders exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'instance/uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.documents.routes import documents_bp
    app.register_blueprint(documents_bp, url_prefix='/documents')

    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.audit.routes import audit_bp
    app.register_blueprint(audit_bp, url_prefix='/audit')

    from app.errors.handlers import errors_bp
    app.register_blueprint(errors_bp)

    # User loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Context processor for templates
    from app.constants import ClassificationLevel

    @app.context_processor
    def inject_globals():
        return {
            'ClassificationLevel': ClassificationLevel,
        }

    # Create tables and seed data on first request
    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    from app.models import User, Compartment
    from app.constants import DEFAULT_COMPARTMENTS

    # Seed compartments
    if Compartment.query.count() == 0:
        for name, display_name, description in DEFAULT_COMPARTMENTS:
            db.session.add(Compartment(
                name=name,
                display_name=display_name,
                description=description,
            ))
        db.session.commit()

    # Seed default admin user
    if User.query.filter_by(username='admin').first() is None:
        admin = User(
            username='admin',
            email='admin@cdms.local',
            role='admin',
            clearance_level=3,
            is_active=True,
        )
        admin.set_password('ChangeMe123!')
        db.session.add(admin)
        db.session.commit()
