from flask_login import current_user
from app.extensions import db
from app.models import Document, DocumentAccessList


def get_accessible_documents(user, include_deleted=False):
    """Query documents that the user has clearance and compartment access for."""
    query = Document.query.filter(
        Document.classification_level <= user.clearance_level
    )

    if not include_deleted:
        query = query.filter(Document.is_deleted == False)

    documents = query.order_by(Document.updated_at.desc()).all()

    # Filter by compartment access and need-to-know in Python
    # (complex join logic simplified for clarity)
    accessible = []
    for doc in documents:
        if user.can_access_document(doc):
            accessible.append(doc)

    return accessible


def search_documents(user, query_text=None, classification=None):
    """Search documents with access filtering."""
    query = Document.query.filter(
        Document.classification_level <= user.clearance_level,
        Document.is_deleted == False,
    )

    if query_text:
        search = f'%{query_text}%'
        query = query.filter(
            db.or_(
                Document.title.ilike(search),
                Document.description.ilike(search),
                Document.file_name.ilike(search),
            )
        )

    if classification is not None and classification != '':
        query = query.filter(Document.classification_level == int(classification))

    documents = query.order_by(Document.updated_at.desc()).all()

    # Post-filter for compartment and need-to-know access
    return [doc for doc in documents if user.can_access_document(doc)]


def check_document_access(document, user):
    """Check if user can access a specific document. Returns (allowed, reason)."""
    if document is None:
        return False, 'not_found'

    if document.is_deleted and not user.is_admin:
        return False, 'deleted'

    if user.clearance_level < document.classification_level:
        return False, 'clearance'

    doc_comps = document.compartments
    if doc_comps and not user.has_all_compartments(doc_comps):
        return False, 'compartment'

    if document.access_list_entries and not user.is_admin:
        user_ids = [a.user_id for a in document.access_list_entries]
        if user.id not in user_ids:
            return False, 'need_to_know'

    return True, 'granted'
