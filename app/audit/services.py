import json
from datetime import datetime, timezone
from flask import request
from flask_login import current_user
from app.extensions import db
from app.models import AuditLog


def log_action(action, resource_type=None, resource_id=None, details=None,
               user_id=None, username=None):
    if user_id is None and current_user and hasattr(current_user, 'id') and current_user.is_authenticated:
        user_id = current_user.id
    if username is None and current_user and hasattr(current_user, 'username') and current_user.is_authenticated:
        username = current_user.username

    ip_address = None
    user_agent = None
    try:
        ip_address = request.remote_addr
        user_agent = str(request.user_agent)[:255] if request.user_agent else None
    except RuntimeError:
        pass

    details_str = json.dumps(details) if details and not isinstance(details, str) else details

    # Get previous hash for chain
    last_entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    previous_hash = last_entry.entry_hash if last_entry else None

    now = datetime.now(timezone.utc)
    timestamp_str = now.isoformat()

    entry = AuditLog(
        timestamp=now,
        timestamp_str=timestamp_str,
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details_str,
        ip_address=ip_address,
        user_agent=user_agent,
        previous_hash=previous_hash,
    )
    entry.entry_hash = entry.compute_hash()

    db.session.add(entry)
    db.session.commit()
    return entry


def verify_audit_chain():
    entries = AuditLog.query.order_by(AuditLog.id.asc()).all()
    if not entries:
        return True, 0, []

    errors = []
    for i, entry in enumerate(entries):
        # Verify hash chain linkage
        if i == 0:
            if entry.previous_hash is not None:
                errors.append({
                    'id': entry.id,
                    'error': 'First entry should have no previous hash',
                })
        else:
            if entry.previous_hash != entries[i - 1].entry_hash:
                errors.append({
                    'id': entry.id,
                    'error': f'Chain break: previous_hash does not match entry {entries[i-1].id}',
                })

        # Verify entry hash integrity
        computed = entry.compute_hash()
        if computed != entry.entry_hash:
            errors.append({
                'id': entry.id,
                'error': 'Entry hash mismatch - possible tampering',
            })

    is_valid = len(errors) == 0
    return is_valid, len(entries), errors
