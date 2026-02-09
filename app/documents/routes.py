import os
from flask import (Blueprint, render_template, redirect, url_for, flash, request,
                   abort, send_file, current_app)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (Document, DocumentVersion, DocumentDisseminationControl,
                        DocumentAccessList, Compartment, User)
from app.documents.forms import DocumentUploadForm, DocumentEditForm, DocumentSearchForm
from app.documents.services import get_accessible_documents, search_documents, check_document_access
from app.decorators import role_required
from app.utils import save_uploaded_file, compute_file_hash, get_safe_filename
from app.audit.services import log_action
from app.constants import AuditAction, DISSEMINATION_CONTROLS

documents_bp = Blueprint('documents', __name__, template_folder='../templates/documents')


@documents_bp.route('/')
@login_required
def index():
    documents = get_accessible_documents(current_user)
    return render_template('documents/index.html', documents=documents)


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('analyst', 'admin')
def upload():
    form = DocumentUploadForm()
    compartments = Compartment.query.all()
    form.compartments.choices = [(c.id, c.name) for c in compartments]

    if form.validate_on_submit():
        file = form.file.data
        safe_name = get_safe_filename(file.filename)

        file_path, file_hash, file_size, stored_name = save_uploaded_file(
            file, form.classification_level.data
        )

        doc = Document(
            title=form.title.data,
            description=form.description.data,
            classification_level=form.classification_level.data,
            file_path=file_path,
            file_name=safe_name,
            file_size=file_size,
            file_hash=file_hash,
            mime_type=file.content_type,
            author_id=current_user.id,
            current_version=1,
        )

        # Add compartments
        if form.compartments.data:
            selected_comps = Compartment.query.filter(Compartment.id.in_(form.compartments.data)).all()
            doc.compartments = selected_comps

        db.session.add(doc)
        db.session.flush()

        # Add dissemination controls
        if form.dissemination_controls.data:
            for control in form.dissemination_controls.data:
                db.session.add(DocumentDisseminationControl(
                    document_id=doc.id, control=control
                ))

        doc.build_classification_string()

        # Create version 1 record
        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            file_path=file_path,
            file_hash=file_hash,
            classification_level=doc.classification_level,
            classification_string=doc.classification_string,
            change_summary='Initial upload',
            created_by=current_user.id,
        )
        db.session.add(version)
        db.session.commit()

        log_action(AuditAction.DOCUMENT_CREATE,
                   resource_type='document', resource_id=doc.id,
                   details={'title': doc.title, 'classification': doc.classification_display})

        flash('Document uploaded successfully.', 'success')
        return redirect(url_for('documents.detail', doc_id=doc.id))

    return render_template('documents/upload.html', form=form)


@documents_bp.route('/<int:doc_id>')
@login_required
def detail(doc_id):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)

    if not allowed:
        if reason in ('clearance', 'compartment', 'need_to_know'):
            log_action(AuditAction.DOCUMENT_ACCESS_DENIED,
                       resource_type='document', resource_id=doc_id,
                       details={'reason': reason})
        abort(404)

    log_action(AuditAction.DOCUMENT_VIEW,
               resource_type='document', resource_id=doc.id)

    return render_template('documents/detail.html', document=doc)


@documents_bp.route('/<int:doc_id>/download')
@login_required
def download(doc_id):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)

    if not allowed:
        abort(404)

    # Verify file integrity
    if doc.file_hash:
        current_hash = compute_file_hash(doc.file_path)
        if current_hash != doc.file_hash:
            flash('File integrity check failed! The file may have been tampered with.', 'danger')
            log_action(AuditAction.DOCUMENT_DOWNLOAD,
                       resource_type='document', resource_id=doc.id,
                       details={'status': 'integrity_failure'})
            return redirect(url_for('documents.detail', doc_id=doc.id))

    log_action(AuditAction.DOCUMENT_DOWNLOAD,
               resource_type='document', resource_id=doc.id,
               details={'file_name': doc.file_name})

    return send_file(doc.file_path,
                     download_name=doc.file_name,
                     as_attachment=True)


@documents_bp.route('/<int:doc_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('analyst', 'admin')
def edit(doc_id):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)
    if not allowed:
        abort(404)

    # Only author or admin can edit
    if doc.author_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = DocumentEditForm(obj=doc)
    compartments = Compartment.query.all()
    form.compartments.choices = [(c.id, c.name) for c in compartments]
    form.dissemination_controls.choices = DISSEMINATION_CONTROLS

    if request.method == 'GET':
        form.compartments.data = [c.id for c in doc.compartments]
        form.dissemination_controls.data = [dc.control for dc in doc.dissemination_controls]

    if form.validate_on_submit():
        old_classification = doc.classification_display

        doc.title = form.title.data
        doc.description = form.description.data
        doc.classification_level = form.classification_level.data

        # Update compartments
        if form.compartments.data:
            selected_comps = Compartment.query.filter(Compartment.id.in_(form.compartments.data)).all()
            doc.compartments = selected_comps
        else:
            doc.compartments = []

        # Update dissemination controls
        DocumentDisseminationControl.query.filter_by(document_id=doc.id).delete()
        if form.dissemination_controls.data:
            for control in form.dissemination_controls.data:
                db.session.add(DocumentDisseminationControl(
                    document_id=doc.id, control=control
                ))

        # Handle file replacement
        if form.file.data:
            file = form.file.data
            safe_name = get_safe_filename(file.filename)
            file_path, file_hash, file_size, stored_name = save_uploaded_file(
                file, doc.classification_level
            )
            doc.file_path = file_path
            doc.file_name = safe_name
            doc.file_size = file_size
            doc.file_hash = file_hash
            doc.mime_type = file.content_type
            doc.current_version += 1

            # Create new version record
            doc.build_classification_string()
            version = DocumentVersion(
                document_id=doc.id,
                version_number=doc.current_version,
                file_path=file_path,
                file_hash=file_hash,
                classification_level=doc.classification_level,
                classification_string=doc.classification_string,
                change_summary=form.change_summary.data or 'File updated',
                created_by=current_user.id,
            )
            db.session.add(version)
        else:
            doc.build_classification_string()

        db.session.commit()

        log_action(AuditAction.DOCUMENT_EDIT,
                   resource_type='document', resource_id=doc.id,
                   details={'title': doc.title,
                            'old_classification': old_classification,
                            'new_classification': doc.classification_display,
                            'change_summary': form.change_summary.data})

        flash('Document updated successfully.', 'success')
        return redirect(url_for('documents.detail', doc_id=doc.id))

    return render_template('documents/edit.html', form=form, document=doc)


@documents_bp.route('/<int:doc_id>/delete', methods=['POST'])
@login_required
@role_required('analyst', 'admin')
def delete(doc_id):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)
    if not allowed:
        abort(404)

    if doc.author_id != current_user.id and not current_user.is_admin:
        abort(403)

    doc.is_deleted = True
    db.session.commit()

    log_action(AuditAction.DOCUMENT_DELETE,
               resource_type='document', resource_id=doc.id,
               details={'title': doc.title})

    flash('Document marked as deleted.', 'warning')
    return redirect(url_for('documents.index'))


@documents_bp.route('/<int:doc_id>/restore', methods=['POST'])
@login_required
@role_required('admin')
def restore(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        abort(404)

    doc.is_deleted = False
    db.session.commit()

    log_action(AuditAction.DOCUMENT_RESTORE,
               resource_type='document', resource_id=doc.id,
               details={'title': doc.title})

    flash('Document restored.', 'success')
    return redirect(url_for('documents.detail', doc_id=doc.id))


@documents_bp.route('/<int:doc_id>/versions')
@login_required
def versions(doc_id):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)
    if not allowed:
        abort(404)

    version_list = doc.versions.order_by(DocumentVersion.version_number.desc()).all()
    return render_template('documents/versions.html', document=doc, versions=version_list)


@documents_bp.route('/<int:doc_id>/versions/<int:version_num>/download')
@login_required
def version_download(doc_id, version_num):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)
    if not allowed:
        abort(404)

    version = DocumentVersion.query.filter_by(
        document_id=doc_id, version_number=version_num
    ).first_or_404()

    log_action(AuditAction.DOCUMENT_DOWNLOAD,
               resource_type='document', resource_id=doc.id,
               details={'version': version_num, 'file_name': doc.file_name})

    return send_file(version.file_path,
                     download_name=f"v{version_num}_{doc.file_name}",
                     as_attachment=True)


@documents_bp.route('/<int:doc_id>/access', methods=['GET', 'POST'])
@login_required
@role_required('analyst', 'admin')
def manage_access(doc_id):
    doc = db.session.get(Document, doc_id)
    allowed, reason = check_document_access(doc, current_user)
    if not allowed:
        abort(404)

    if doc.author_id != current_user.id and not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id', type=int)

        if action == 'grant' and user_id:
            target_user = db.session.get(User, user_id)
            if target_user:
                existing = DocumentAccessList.query.filter_by(
                    document_id=doc.id, user_id=user_id
                ).first()
                if not existing:
                    access = DocumentAccessList(
                        document_id=doc.id,
                        user_id=user_id,
                        granted_by=current_user.id,
                    )
                    db.session.add(access)
                    db.session.commit()
                    log_action(AuditAction.DOCUMENT_ACCESS_GRANTED,
                               resource_type='document', resource_id=doc.id,
                               details={'granted_to': target_user.username})
                    flash(f'Access granted to {target_user.username}.', 'success')

        elif action == 'revoke' and user_id:
            access = DocumentAccessList.query.filter_by(
                document_id=doc.id, user_id=user_id
            ).first()
            if access:
                target_user = db.session.get(User, user_id)
                db.session.delete(access)
                db.session.commit()
                log_action(AuditAction.DOCUMENT_ACCESS_REVOKED,
                           resource_type='document', resource_id=doc.id,
                           details={'revoked_from': target_user.username if target_user else user_id})
                flash('Access revoked.', 'warning')

        return redirect(url_for('documents.manage_access', doc_id=doc.id))

    access_list = DocumentAccessList.query.filter_by(document_id=doc.id).all()
    all_users = User.query.filter(User.is_active == True).order_by(User.username).all()

    return render_template('documents/manage_access.html',
                           document=doc,
                           access_list=access_list,
                           all_users=all_users)


@documents_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = DocumentSearchForm()
    documents = []

    if form.validate_on_submit() or request.args.get('query'):
        query_text = form.query.data or request.args.get('query', '')
        classification = form.classification.data or request.args.get('classification', '')
        documents = search_documents(current_user, query_text, classification)

    return render_template('documents/search.html', form=form, documents=documents)
