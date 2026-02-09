from enum import IntEnum


class ClassificationLevel(IntEnum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3

    @property
    def display_name(self):
        return {
            0: 'UNCLASSIFIED',
            1: 'CONFIDENTIAL',
            2: 'SECRET',
            3: 'TOP SECRET',
        }[self.value]

    @property
    def css_class(self):
        return {
            0: 'unclassified',
            1: 'confidential',
            2: 'secret',
            3: 'top-secret',
        }[self.value]

    @property
    def color(self):
        return {
            0: '#008000',
            1: '#0000FF',
            2: '#FF0000',
            3: '#FFA500',
        }[self.value]


CLASSIFICATION_CHOICES = [
    (0, 'UNCLASSIFIED'),
    (1, 'CONFIDENTIAL'),
    (2, 'SECRET'),
    (3, 'TOP SECRET'),
]


class UserRole:
    VIEWER = 'viewer'
    ANALYST = 'analyst'
    ADMIN = 'admin'

    CHOICES = [
        ('viewer', 'Viewer'),
        ('analyst', 'Analyst'),
        ('admin', 'Admin'),
    ]

    HIERARCHY = {
        'viewer': 0,
        'analyst': 1,
        'admin': 2,
    }


class AuditAction:
    # Auth
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILED = 'login_failed'
    LOGOUT = 'logout'
    REGISTER = 'register'
    ACCOUNT_LOCKED = 'account_locked'

    # Documents
    DOCUMENT_CREATE = 'document_create'
    DOCUMENT_VIEW = 'document_view'
    DOCUMENT_DOWNLOAD = 'document_download'
    DOCUMENT_EDIT = 'document_edit'
    DOCUMENT_DELETE = 'document_delete'
    DOCUMENT_RESTORE = 'document_restore'
    DOCUMENT_ACCESS_DENIED = 'document_access_denied'
    DOCUMENT_ACCESS_GRANTED = 'document_access_granted'
    DOCUMENT_ACCESS_REVOKED = 'document_access_revoked'

    # Admin
    USER_EDIT = 'user_edit'
    USER_DEACTIVATE = 'user_deactivate'
    USER_ACTIVATE = 'user_activate'
    COMPARTMENT_GRANT = 'compartment_grant'
    COMPARTMENT_REVOKE = 'compartment_revoke'

    # System
    INTEGRITY_CHECK = 'integrity_check'


DEFAULT_COMPARTMENTS = [
    ('SCI', 'Sensitive Compartmented Information', 'Access to SCI material'),
    ('SI', 'Special Intelligence', 'SIGINT-derived intelligence'),
    ('TK', 'Talent Keyhole', 'Satellite imagery intelligence'),
    ('HCS', 'HUMINT Control System', 'Human intelligence sources'),
    ('NOFORN', 'No Foreign Nationals', 'Not releasable to foreign nationals'),
    ('ORCON', 'Originator Controlled', 'Dissemination controlled by originator'),
]

DISSEMINATION_CONTROLS = [
    ('NOFORN', 'Not Releasable to Foreign Nationals'),
    ('ORCON', 'Originator Controlled'),
    ('REL TO', 'Releasable To (specified countries)'),
    ('FOUO', 'For Official Use Only'),
]
