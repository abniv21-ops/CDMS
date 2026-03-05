"""Add 30 more mixed audit log entries with proper hash chaining."""
import os
import json as _json
from datetime import datetime, timezone, timedelta

os.environ['FLASK_CONFIG'] = 'production'
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'seed-key')

from wsgi import app
from app.extensions import db
from app.models import AuditLog, User, Document

with app.app_context():
    all_users = {u.username: u for u in User.query.all()}
    all_docs = Document.query.order_by(Document.id).all()

    ips = [
        "10.0.1.15", "10.0.1.22", "10.0.2.8", "10.0.1.45",
        "10.0.3.12", "192.168.1.100", "10.0.4.55", "10.0.2.30",
        "192.168.2.10", "10.0.5.77",
    ]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/124.0",
    ]

    # Start from March 1 2026 08:00 UTC (after the existing Feb 25 entries)
    base_time = datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)

    def uid(name):
        u = all_users.get(name)
        return u.id if u else None

    def did(idx):
        return all_docs[idx].id if len(all_docs) > idx else idx + 1

    audit_entries = [
        # 1 - gharris early morning login
        (timedelta(hours=0), "gharris", "login_success",
         None, None, None,
         ips[0], agents[0]),

        # 2 - gharris views a SECRET satellite imagery doc
        (timedelta(hours=0, minutes=8), "gharris", "document_view",
         "document", did(16), None,
         ips[0], agents[0]),

        # 3 - new user registration
        (timedelta(hours=0, minutes=15), None, "register",
         "user", uid("fross"), {"username": "fross", "role": "viewer"},
         ips[5], agents[2]),

        # 4 - hpatel failed login (wrong password)
        (timedelta(hours=0, minutes=22), "hpatel", "login_failed",
         None, None, {"reason": "bad password", "attempts": 1},
         ips[8], agents[3]),

        # 5 - hpatel failed login again
        (timedelta(hours=0, minutes=23), "hpatel", "login_failed",
         None, None, {"reason": "bad password", "attempts": 2},
         ips[8], agents[3]),

        # 6 - hpatel account locked
        (timedelta(hours=0, minutes=24), "hpatel", "account_locked",
         "user", uid("hpatel"), {"reason": "3 consecutive failed attempts"},
         ips[8], agents[3]),

        # 7 - admin login
        (timedelta(hours=1), "admin", "login_success",
         None, None, None,
         ips[1], agents[0]),

        # 8 - admin activates fross
        (timedelta(hours=1, minutes=5), "admin", "user_activate",
         "user", uid("fross"), {"reason": "account review completed"},
         ips[1], agents[0]),

        # 9 - admin grants compartment TK to enguyen
        (timedelta(hours=1, minutes=10), "admin", "compartment_grant",
         "user", uid("enguyen"), {"compartment": "TK"},
         ips[1], agents[0]),

        # 10 - jsmith login
        (timedelta(hours=2), "jsmith", "login_success",
         None, None, None,
         ips[2], agents[1]),

        # 11 - jsmith creates a new document
        (timedelta(hours=2, minutes=15), "jsmith", "document_create",
         "document", did(13), {"title": "SIGINT Weekly Digest", "classification": "SECRET"},
         ips[2], agents[1]),

        # 12 - jsmith edits a document
        (timedelta(hours=2, minutes=30), "jsmith", "document_edit",
         "document", did(13), {"field": "description", "version": 2},
         ips[2], agents[1]),

        # 13 - bcooper login
        (timedelta(hours=3), "bcooper", "login_success",
         None, None, None,
         ips[3], agents[2]),

        # 14 - bcooper views TOP SECRET HUMINT doc
        (timedelta(hours=3, minutes=10), "bcooper", "document_view",
         "document", did(23), None,
         ips[3], agents[2]),

        # 15 - bcooper downloads TOP SECRET doc
        (timedelta(hours=3, minutes=12), "bcooper", "document_download",
         "document", did(23), None,
         ips[3], agents[2]),

        # 16 - cmartinez login
        (timedelta(hours=4), "cmartinez", "login_success",
         None, None, None,
         ips[4], agents[3]),

        # 17 - cmartinez access denied (missing compartment)
        (timedelta(hours=4, minutes=5), "cmartinez", "document_access_denied",
         "document", did(20), {"reason": "missing compartment: SCI"},
         ips[4], agents[3]),

        # 18 - admin grants document access to cmartinez
        (timedelta(hours=4, minutes=20), "admin", "document_access_granted",
         "document", did(7), {"granted_to_user_id": uid("cmartinez")},
         ips[1], agents[0]),

        # 19 - enguyen login
        (timedelta(hours=5), "enguyen", "login_success",
         None, None, None,
         ips[6], agents[1]),

        # 20 - enguyen views CONFIDENTIAL incident response doc
        (timedelta(hours=5, minutes=10), "enguyen", "document_view",
         "document", did(12), None,
         ips[6], agents[1]),

        # 21 - enguyen downloads document
        (timedelta(hours=5, minutes=12), "enguyen", "document_download",
         "document", did(12), None,
         ips[6], agents[1]),

        # 22 - admin edits user clearance for dkim
        (timedelta(hours=6), "admin", "user_edit",
         "user", uid("dkim"), {"field": "clearance_level", "old": 2, "new": 3},
         ips[1], agents[0]),

        # 23 - admin revokes compartment from hpatel
        (timedelta(hours=6, minutes=10), "admin", "compartment_revoke",
         "user", uid("hpatel"), {"compartment": "ORCON"},
         ips[1], agents[0]),

        # 24 - ijones login
        (timedelta(hours=7), "ijones", "login_success",
         None, None, None,
         ips[9], agents[0]),

        # 25 - ijones deletes a document (soft delete)
        (timedelta(hours=7, minutes=15), "ijones", "document_delete",
         "document", did(4), {"title": "Open Source Intelligence Report - Climate"},
         ips[9], agents[0]),

        # 26 - ijones restores the deleted document
        (timedelta(hours=7, minutes=30), "ijones", "document_restore",
         "document", did(4), {"title": "Open Source Intelligence Report - Climate"},
         ips[9], agents[0]),

        # 27 - admin revokes document access
        (timedelta(hours=8), "admin", "document_access_revoked",
         "document", did(7), {"revoked_from_user_id": uid("cmartinez")},
         ips[1], agents[0]),

        # 28 - admin runs integrity check
        (timedelta(hours=9), "admin", "integrity_check",
         None, None, {"result": "valid", "entries_checked": 57},
         ips[1], agents[0]),

        # 29 - awalker login
        (timedelta(hours=10), "awalker", "login_success",
         None, None, None,
         ips[7], agents[1]),

        # 30 - admin logout
        (timedelta(hours=10, minutes=30), "admin", "logout",
         None, None, None,
         ips[1], agents[0]),
    ]

    # Get the last entry for hash chaining
    last_entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    previous_hash = last_entry.entry_hash if last_entry else None

    for i, (offset, uname, action, res_type, res_id, details, ip, ua) in enumerate(audit_entries):
        ts = base_time + offset
        ts_str = ts.isoformat()
        details_str = _json.dumps(details) if details else None

        user_obj = all_users.get(uname) if uname else None
        entry = AuditLog(
            timestamp=ts,
            timestamp_str=ts_str,
            user_id=user_obj.id if user_obj else None,
            username=uname,
            action=action,
            resource_type=res_type,
            resource_id=res_id,
            details=details_str,
            ip_address=ip,
            user_agent=ua,
            previous_hash=previous_hash,
        )
        entry.entry_hash = entry.compute_hash()
        previous_hash = entry.entry_hash

        db.session.add(entry)
        print(f"  [{i+1:2d}] {ts_str[11:16]} | {uname or '???':<12} | {action}")

    db.session.commit()

    total = AuditLog.query.count()
    print(f"\n  Added 30 audit log entries (total now: {total}).")
    print("  Hash chain intact.")
