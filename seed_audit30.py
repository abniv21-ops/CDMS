"""Seed 30 additional mixed audit log entries across all 11 users."""
import os
import json as _json
from datetime import datetime, timezone, timedelta

os.environ['FLASK_CONFIG'] = 'production'
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'seed-key')

from wsgi import app
from app.extensions import db
from app.models import User, Document, AuditLog

with app.app_context():
    all_users = {u.username: u for u in User.query.all()}
    all_docs = Document.query.order_by(Document.id).all()

    ips = [
        "10.0.1.15", "10.0.1.22", "10.0.2.8", "10.0.1.45",
        "10.0.3.12", "192.168.1.100", "10.0.2.30", "10.0.4.5",
        "172.16.0.20", "10.0.1.88",
    ]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0",
    ]

    # Start from Feb 26 08:00 UTC (day after existing entries)
    base_time = datetime(2026, 2, 26, 8, 0, 0, tzinfo=timezone.utc)

    def uid(name):
        u = all_users.get(name)
        return u.id if u else None

    def did(idx):
        return all_docs[idx].id if idx < len(all_docs) else idx + 1

    audit_entries = [
        # 1 - hpatel login
        (timedelta(hours=0), "hpatel", "login_success",
         None, None, None, ips[3], agents[0]),
        # 2 - hpatel views UNCLASSIFIED doc
        (timedelta(hours=0, minutes=8), "hpatel", "document_view",
         "document", did(5), None, ips[3], agents[0]),
        # 3 - hpatel access denied on SECRET doc
        (timedelta(hours=0, minutes=15), "hpatel", "document_access_denied",
         "document", did(16), {"reason": "insufficient clearance"}, ips[3], agents[0]),
        # 4 - ijones login
        (timedelta(hours=0, minutes=30), "ijones", "login_success",
         None, None, None, ips[4], agents[1]),
        # 5 - ijones views TOP SECRET doc
        (timedelta(hours=0, minutes=40), "ijones", "document_view",
         "document", did(26), None, ips[4], agents[1]),
        # 6 - ijones downloads TOP SECRET doc
        (timedelta(hours=0, minutes=42), "ijones", "document_download",
         "document", did(26), None, ips[4], agents[1]),
        # 7 - admin login
        (timedelta(hours=1), "admin", "login_success",
         None, None, None, ips[0], agents[0]),
        # 8 - admin creates user account
        (timedelta(hours=1, minutes=10), "admin", "user_create",
         "user", uid("dkim"), {"username": "dkim", "role": "viewer"}, ips[0], agents[0]),
        # 9 - enguyen login
        (timedelta(hours=1, minutes=30), "enguyen", "login_success",
         None, None, None, ips[5], agents[2]),
        # 10 - enguyen uploads document
        (timedelta(hours=1, minutes=45), "enguyen", "document_create",
         "document", did(12), {"title": "Incident Response Plan - Cyber", "classification": "CONFIDENTIAL"},
         ips[5], agents[2]),
        # 11 - failed login attempt (brute force)
        (timedelta(hours=2), None, "login_failed",
         None, None, {"username": "root", "reason": "unknown user"}, ips[8], agents[2]),
        # 12 - another failed login
        (timedelta(hours=2, minutes=1), None, "login_failed",
         None, None, {"username": "administrator", "reason": "unknown user"}, ips[8], agents[2]),
        # 13 - gharris login
        (timedelta(hours=2, minutes=30), "gharris", "login_success",
         None, None, None, ips[6], agents[0]),
        # 14 - gharris views SECRET doc
        (timedelta(hours=2, minutes=40), "gharris", "document_view",
         "document", did(21), None, ips[6], agents[0]),
        # 15 - gharris edits document classification
        (timedelta(hours=2, minutes=50), "gharris", "document_edit",
         "document", did(21), {"field": "classification_level", "old": "SECRET", "new": "SECRET"},
         ips[6], agents[0]),
        # 16 - bcooper login
        (timedelta(hours=3), "bcooper", "login_success",
         None, None, None, ips[2], agents[2]),
        # 17 - bcooper views TOP SECRET doc
        (timedelta(hours=3, minutes=15), "bcooper", "document_view",
         "document", did(24), None, ips[2], agents[2]),
        # 18 - bcooper downloads TOP SECRET doc
        (timedelta(hours=3, minutes=17), "bcooper", "document_download",
         "document", did(24), None, ips[2], agents[2]),
        # 19 - admin grants document access
        (timedelta(hours=4), "admin", "document_access_granted",
         "document", did(22), {"granted_to_user_id": uid("awalker")}, ips[0], agents[0]),
        # 20 - awalker login
        (timedelta(hours=4, minutes=30), "awalker", "login_success",
         None, None, None, ips[7], agents[1]),
        # 21 - awalker views SECRET doc (newly granted access)
        (timedelta(hours=4, minutes=40), "awalker", "document_view",
         "document", did(22), None, ips[7], agents[1]),
        # 22 - jsmith login
        (timedelta(hours=5), "jsmith", "login_success",
         None, None, None, ips[1], agents[1]),
        # 23 - jsmith views and downloads SIGINT report
        (timedelta(hours=5, minutes=10), "jsmith", "document_view",
         "document", did(14), None, ips[1], agents[1]),
        # 24 - jsmith downloads SIGINT report
        (timedelta(hours=5, minutes=12), "jsmith", "document_download",
         "document", did(14), None, ips[1], agents[1]),
        # 25 - admin runs integrity check
        (timedelta(hours=6), "admin", "integrity_check",
         None, None, {"result": "valid", "entries_checked": 50}, ips[0], agents[0]),
        # 26 - cmartinez login
        (timedelta(hours=7), "cmartinez", "login_success",
         None, None, None, ips[9], agents[0]),
        # 27 - cmartinez views UNCLASSIFIED doc
        (timedelta(hours=7, minutes=10), "cmartinez", "document_view",
         "document", did(2), None, ips[9], agents[0]),
        # 28 - dkim login
        (timedelta(hours=8), "dkim", "login_success",
         None, None, None, ips[4], agents[2]),
        # 29 - dkim access denied (missing compartment TK)
        (timedelta(hours=8, minutes=5), "dkim", "document_access_denied",
         "document", did(16), {"reason": "missing compartment: TK"}, ips[4], agents[2]),
        # 30 - fross login failed (deactivated account)
        (timedelta(hours=9), "fross", "login_failed",
         None, None, {"reason": "account deactivated"}, ips[5], agents[2]),
    ]

    last_entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    previous_hash = last_entry.entry_hash if last_entry else None

    for i, (offset, uname, action, res_type, res_id, details, ip, ua) in enumerate(audit_entries):
        ts = base_time + offset
        ts_str = ts.isoformat()
        details_str = _json.dumps(details) if details else None

        entry = AuditLog(
            timestamp=ts,
            timestamp_str=ts_str,
            user_id=uid(uname) if uname else None,
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
    print(f"\n  Seeded 30 additional audit log entries with valid hash chain.")
    print(f"  Total audit entries: {AuditLog.query.count()}")
