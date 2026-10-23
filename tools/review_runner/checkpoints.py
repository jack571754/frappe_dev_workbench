"""Task-scoped OCR state, independent of attempts and ephemeral containers."""
import hashlib
import json
import re
from pathlib import Path


def checkpoint_directory(root, task, provider):
    identity = {key: task.get(key) for key in
                ('name', 'repository', 'head_sha', 'base_sha', 'review_mode', 'checkpoint_generation')}
    identity['provider'] = provider
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = Path(root) / 'checkpoints' / key
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    return directory


def session_id(raw):
    payload = json.loads(raw)
    if payload is None:
        return None
    rows = payload.get('sessions', []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError('Invalid OCR session list')
    if not rows:
        return None
    value = rows[0].get('id') or rows[0].get('session_id')
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value):
        raise ValueError('Invalid OCR session identifier')
    return value
