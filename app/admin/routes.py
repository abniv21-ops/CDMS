from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Document, Compartment, AuditLog, user_compartments
from app.admin.forms import UserEditForm
from app.decorators import admin_required
from app.audit.services import log_action
from app.constants import AuditAction, ClassificationLevel

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_documents = Document.query.filter_by(is_deleted=False).count()
    total_audit_entries = AuditLog.query.count()

    # Documents by classification
    doc_by_class = {}
    for level in ClassificationLevel:
        count = Document.query.filter_by(
            classification_level=level.value, is_deleted=False
        ).count()
        doc_by_class[level.display_name] = count

    # Recent audit entries
    recent_audit = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           total_documents=total_documents,
                           total_audit_entries=total_audit_entries,
                           doc_by_class=doc_by_class,
                           recent_audit=recent_audit)


@admin_bp.route('/users')
@login_required
@admin_required
def users_list():
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        old_role = user.role
        old_clearance = user.clearance_level

        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.clearance_level = form.clearance_level.data

        if form.new_password.data:
            user.set_password(form.new_password.data)

        db.session.commit()

        log_action(AuditAction.USER_EDIT,
                   resource_type='user', resource_id=user.id,
                   details={
                       'username': user.username,
                       'old_role': old_role, 'new_role': user.role,
                       'old_clearance': old_clearance, 'new_clearance': user.clearance_level,
                       'password_changed': bool(form.new_password.data),
                   })

        flash(f'User {user.username} updated successfully.', 'success')
        return redirect(url_for('admin.users_list'))

    return render_template('admin/user_edit.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/compartments', methods=['GET', 'POST'])
@login_required
@admin_required
def user_compartments_view(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    all_compartments = Compartment.query.all()
    user_comps = {c.id for c in user.compartments.all()}

    if request.method == 'POST':
        action = request.form.get('action')
        comp_id = request.form.get('compartment_id', type=int)

        if comp_id:
            comp = db.session.get(Compartment, comp_id)
            if comp:
                if action == 'grant':
                    if comp.id not in user_comps:
                        stmt = user_compartments.insert().values(
                            user_id=user.id,
                            compartment_id=comp.id,
                            granted_by=current_user.id,
                        )
                        db.session.execute(stmt)
                        db.session.commit()
                        log_action(AuditAction.COMPARTMENT_GRANT,
                                   resource_type='user', resource_id=user.id,
                                   details={'compartment': comp.name, 'user': user.username})
                        flash(f'Granted {comp.name} access to {user.username}.', 'success')

                elif action == 'revoke':
                    if comp.id in user_comps:
                        stmt = user_compartments.delete().where(
                            (user_compartments.c.user_id == user.id) &
                            (user_compartments.c.compartment_id == comp.id)
                        )
                        db.session.execute(stmt)
                        db.session.commit()
                        log_action(AuditAction.COMPARTMENT_REVOKE,
                                   resource_type='user', resource_id=user.id,
                                   details={'compartment': comp.name, 'user': user.username})
                        flash(f'Revoked {comp.name} access from {user.username}.', 'warning')

        return redirect(url_for('admin.user_compartments_view', user_id=user.id))

    return render_template('admin/user_compartments.html',
                           user=user,
                           all_compartments=all_compartments,
                           user_comps=user_comps)


@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def user_deactivate(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users_list'))

    if user.is_active:
        user.is_active = False
        action = AuditAction.USER_DEACTIVATE
        flash(f'User {user.username} deactivated.', 'warning')
    else:
        user.is_active = True
        action = AuditAction.USER_ACTIVATE
        user.failed_login_attempts = 0
        user.locked_until = None
        flash(f'User {user.username} activated.', 'success')

    db.session.commit()
    log_action(action, resource_type='user', resource_id=user.id,
               details={'username': user.username})

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/statistics')
@login_required
@admin_required
def statistics():
    # User stats
    total_users = User.query.count()
    users_by_role = {}
    for role_val, role_label in [('viewer', 'Viewer'), ('analyst', 'Analyst'), ('admin', 'Admin')]:
        users_by_role[role_label] = User.query.filter_by(role=role_val).count()

    users_by_clearance = {}
    for level in ClassificationLevel:
        users_by_clearance[level.display_name] = User.query.filter_by(
            clearance_level=level.value
        ).count()

    # Document stats
    total_docs = Document.query.count()
    active_docs = Document.query.filter_by(is_deleted=False).count()
    deleted_docs = Document.query.filter_by(is_deleted=True).count()

    docs_by_class = {}
    for level in ClassificationLevel:
        docs_by_class[level.display_name] = Document.query.filter_by(
            classification_level=level.value, is_deleted=False
        ).count()

    # Audit stats
    total_audit = AuditLog.query.count()
    recent_logins = AuditLog.query.filter_by(action=AuditAction.LOGIN_SUCCESS).count()
    failed_logins = AuditLog.query.filter_by(action=AuditAction.LOGIN_FAILED).count()

    return render_template('admin/statistics.html',
                           total_users=total_users,
                           users_by_role=users_by_role,
                           users_by_clearance=users_by_clearance,
                           total_docs=total_docs,
                           active_docs=active_docs,
                           deleted_docs=deleted_docs,
                           docs_by_class=docs_by_class,
                           total_audit=total_audit,
                           recent_logins=recent_logins,
                           failed_logins=failed_logins)
