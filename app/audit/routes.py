import csv
import io
from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required

from app.decorators import admin_required
from app.models import AuditLog
from app.audit.services import verify_audit_chain, log_action
from app.constants import AuditAction

audit_bp = Blueprint('audit', __name__, template_folder='../templates/audit')


@audit_bp.route('/')
@login_required
@admin_required
def log_viewer():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user', '')

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if user_filter:
        query = query.filter(AuditLog.username.ilike(f'%{user_filter}%'))

    pagination = query.paginate(page=page, per_page=50, error_out=False)

    actions = [r[0] for r in AuditLog.query.with_entities(AuditLog.action).distinct().all()]

    return render_template('admin/audit_log.html',
                           entries=pagination.items,
                           pagination=pagination,
                           actions=sorted(actions),
                           current_action=action_filter,
                           current_user_filter=user_filter)


@audit_bp.route('/document/<int:doc_id>')
@login_required
@admin_required
def document_trail(doc_id):
    entries = AuditLog.query.filter_by(
        resource_type='document', resource_id=doc_id
    ).order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/audit_log.html',
                           entries=entries,
                           pagination=None,
                           actions=[],
                           current_action='',
                           current_user_filter='',
                           trail_title=f'Document #{doc_id} Audit Trail')


@audit_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def user_trail(user_id):
    entries = AuditLog.query.filter_by(
        user_id=user_id
    ).order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/audit_log.html',
                           entries=entries,
                           pagination=None,
                           actions=[],
                           current_action='',
                           current_user_filter='',
                           trail_title=f'User #{user_id} Audit Trail')


@audit_bp.route('/verify')
@login_required
@admin_required
def verify():
    is_valid, total, errors = verify_audit_chain()

    log_action(
        AuditAction.INTEGRITY_CHECK,
        resource_type='audit_log',
        details={'result': 'pass' if is_valid else 'fail', 'total_entries': total, 'errors': len(errors)},
    )

    return render_template('admin/audit_verify.html',
                           is_valid=is_valid,
                           total=total,
                           errors=errors)


@audit_bp.route('/export')
@login_required
@admin_required
def export_csv():
    entries = AuditLog.query.order_by(AuditLog.timestamp.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Timestamp', 'User ID', 'Username', 'Action',
                     'Resource Type', 'Resource ID', 'Details', 'IP Address',
                     'Previous Hash', 'Entry Hash'])
    for e in entries:
        writer.writerow([e.id, e.timestamp.isoformat(), e.user_id, e.username,
                         e.action, e.resource_type, e.resource_id, e.details,
                         e.ip_address, e.previous_hash, e.entry_hash])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_log_export.csv'},
    )
