import hashlib
import os
import uuid
from flask import current_app


def compute_file_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_uploaded_file(file_storage, classification_level):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    level_folder = os.path.join(upload_folder, str(classification_level))
    os.makedirs(level_folder, exist_ok=True)

    ext = os.path.splitext(file_storage.filename)[1] if file_storage.filename else ''
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(level_folder, unique_name)

    file_storage.save(file_path)
    file_hash = compute_file_hash(file_path)
    file_size = os.path.getsize(file_path)

    return file_path, file_hash, file_size, unique_name


def delete_file(file_path):
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def get_safe_filename(filename):
    if not filename:
        return 'unnamed_file'
    # Keep only the basename, strip path components
    name = os.path.basename(filename)
    # Remove any null bytes or path separators
    name = name.replace('\x00', '').replace('/', '').replace('\\', '')
    return name if name else 'unnamed_file'
