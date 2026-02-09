import hashlib
import json
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# Association tables
user_compartments = db.Table(
    'user_compartments',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('compartment_id', db.Integer, db.ForeignKey('compartments.id'), primary_key=True),
    db.Column('granted_at', db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.Column('granted_by', db.Integer, db.ForeignKey('users.id'), nullable=True),
)

document_compartments = db.Table(
    'document_compartments',
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('compartment_id', db.Integer, db.ForeignKey('compartments.id'), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    clearance_level = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    compartments = db.relationship('Compartment', secondary=user_compartments,
                                   backref=db.backref('users', lazy='dynamic'),
                                   lazy='dynamic',
                                   primaryjoin='User.id == user_compartments.c.user_id')
    documents = db.relationship('Document', backref='author', lazy='dynamic',
                                foreign_keys='Document.author_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked(self):
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def clearance_display(self):
        from app.constants import ClassificationLevel
        return ClassificationLevel(self.clearance_level).display_name

    def has_compartment(self, compartment_name):
        return self.compartments.filter(
            Compartment.name == compartment_name
        ).first() is not None

    def has_all_compartments(self, compartment_list):
        if not compartment_list:
            return True
        user_comp_names = {c.name for c in self.compartments.all()}
        required = {c.name if hasattr(c, 'name') else c for c in compartment_list}
        return required.issubset(user_comp_names)

    def can_access_document(self, document):
        if self.clearance_level < document.classification_level:
            return False
        doc_comps = document.compartments
        if doc_comps and not self.has_all_compartments(doc_comps):
            return False
        if document.access_list_entries:
            if not self.is_admin:
                user_ids = [a.user_id for a in document.access_list_entries]
                if self.id not in user_ids:
                    return False
        return True

    def __repr__(self):
        return f'<User {self.username}>'


class Compartment(db.Model):
    __tablename__ = 'compartments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Compartment {self.name}>'


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    classification_level = db.Column(db.Integer, nullable=False, default=0)
    classification_string = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(512), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    file_hash = db.Column(db.String(64), nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_version = db.Column(db.Integer, default=1)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    compartments = db.relationship('Compartment', secondary=document_compartments,
                                   backref=db.backref('documents', lazy='dynamic'),
                                   lazy='select')
    access_list_entries = db.relationship('DocumentAccessList', backref='document',
                                         lazy='select', cascade='all, delete-orphan')
    dissemination_controls = db.relationship('DocumentDisseminationControl',
                                             backref='document', lazy='select',
                                             cascade='all, delete-orphan')
    versions = db.relationship('DocumentVersion', backref='document', lazy='dynamic',
                               order_by='DocumentVersion.version_number.desc()')

    @property
    def classification_display(self):
        from app.constants import ClassificationLevel
        return ClassificationLevel(self.classification_level).display_name

    @property
    def classification_css(self):
        from app.constants import ClassificationLevel
        return ClassificationLevel(self.classification_level).css_class

    def build_classification_string(self):
        from app.constants import ClassificationLevel
        parts = [ClassificationLevel(self.classification_level).display_name]
        comp_names = sorted([c.name for c in self.compartments])
        if comp_names:
            parts.append('//' + '/'.join(comp_names))
        controls = [dc.control for dc in self.dissemination_controls]
        if controls:
            parts.append('//' + '/'.join(sorted(controls)))
        self.classification_string = ''.join(parts)
        return self.classification_string

    def __repr__(self):
        return f'<Document {self.title}>'


class DocumentDisseminationControl(db.Model):
    __tablename__ = 'document_dissemination_controls'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    control = db.Column(db.String(50), nullable=False)


class DocumentAccessList(db.Model):
    __tablename__ = 'document_access_list'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], backref='access_grants')
    granter = db.relationship('User', foreign_keys=[granted_by])


class DocumentVersion(db.Model):
    __tablename__ = 'document_versions'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_hash = db.Column(db.String(64), nullable=True)
    classification_level = db.Column(db.Integer, nullable=False)
    classification_string = db.Column(db.String(255), nullable=True)
    change_summary = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    creator = db.relationship('User', foreign_keys=[created_by])


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    timestamp_str = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    previous_hash = db.Column(db.String(64), nullable=True)
    entry_hash = db.Column(db.String(64), nullable=False)

    user = db.relationship('User', backref=db.backref('audit_entries', lazy='dynamic'))

    @property
    def details_dict(self):
        if self.details:
            try:
                return json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def compute_hash(self):
        ts = self.timestamp_str or (self.timestamp.isoformat() if self.timestamp else '')
        data = (
            f"{ts}"
            f"{self.user_id}"
            f"{self.username}"
            f"{self.action}"
            f"{self.resource_type}"
            f"{self.resource_id}"
            f"{self.details}"
            f"{self.ip_address}"
            f"{self.previous_hash or ''}"
        )
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def __repr__(self):
        return f'<AuditLog {self.id}: {self.action}>'
