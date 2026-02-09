from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from app.auth.forms import LoginForm, RegistrationForm
from app.audit.services import log_action
from app.constants import AuditAction

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('documents.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None:
            log_action(AuditAction.LOGIN_FAILED, details={'username': form.username.data, 'reason': 'unknown user'})
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html', form=form)

        # Check lockout
        if user.is_locked:
            log_action(AuditAction.LOGIN_FAILED, user_id=user.id, username=user.username,
                       details={'reason': 'account locked'})
            flash('Account is locked due to too many failed attempts. Try again later.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.check_password(form.password.data):
            user.failed_login_attempts += 1
            max_attempts = current_app.config.get('MAX_FAILED_LOGINS', 5)
            if user.failed_login_attempts >= max_attempts:
                lockout_mins = current_app.config.get('LOCKOUT_DURATION_MINUTES', 15)
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_mins)
                log_action(AuditAction.ACCOUNT_LOCKED, user_id=user.id, username=user.username,
                           details={'attempts': user.failed_login_attempts})
            db.session.commit()
            log_action(AuditAction.LOGIN_FAILED, user_id=user.id, username=user.username,
                       details={'reason': 'bad password', 'attempts': user.failed_login_attempts})
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.is_active:
            flash('Your account has been deactivated. Contact an administrator.', 'danger')
            return render_template('auth/login.html', form=form)

        # Successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        login_user(user, remember=form.remember_me.data)
        log_action(AuditAction.LOGIN_SUCCESS)

        next_page = request.args.get('next')
        if next_page and not next_page.startswith('/'):
            next_page = None
        return redirect(next_page or url_for('documents.index'))

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log_action(AuditAction.LOGOUT)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('documents.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='viewer',
            clearance_level=0,
            is_active=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        log_action(AuditAction.REGISTER, user_id=user.id, username=user.username,
                   resource_type='user', resource_id=user.id)
        flash('Registration successful! You can now log in. Note: You have UNCLASSIFIED clearance by default.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)
