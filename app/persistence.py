"""Versioned complete backups; merge-only restore with atomic conflict checks."""
import copy
from contextlib import closing
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from core import require, validate_plan, diagnostic_score, evaluate_trace, content_hash, DEFAULT_UNIT


def backup(store):
    from server import LOCK
    with LOCK, store.connect() as db:
        result = {"backup_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
                  "students": [json.loads(r[0]) for r in db.execute("SELECT data FROM students")],
                  "packages": [json.loads(r[0]) for r in db.execute("SELECT data FROM packages")],
                  "traces": [dict(r) for r in db.execute("SELECT * FROM traces")],
                  "trace_history": [dict(r) for r in db.execute("SELECT * FROM trace_history")]}
    for p in result["packages"]:
        p.pop("student_token", None)
    result["checksum"] = content_hash(result)
    return result


def restore(store, body):
    from server import LOCK
    require(body.get("confirmed") is True, "Confirm the backup merge")
    source = copy.deepcopy(body.get("backup"))
    require(isinstance(source, dict) and source.get("backup_version") == "1.0", "Unsupported backup")
    checksum = source.pop("checksum", None)
    require(checksum == content_hash(source), "Backup checksum mismatch")
    students, packages = source.get("students"), source.get("packages")
    require(isinstance(students, list) and isinstance(packages, list), "Invalid backup records")
    require(len({s['id'] for s in students}) == len(students), "Duplicate student")
    require(len({p['id'] for p in packages}) == len(packages), "Duplicate package")
    learners = {s['id']: s for s in students}
    packets = {p['id']: p for p in packages}
    for s in students:
        require(isinstance(s.get('label'), str) and isinstance(s.get('grade'), str), "Invalid learner")
        diagnostic_score(s.get('diagnostic', {}), s.get('unit_id', DEFAULT_UNIT))
    for p in packages:
        require(p['student_id'] in learners, "Missing student reference")
        require(p['status'] in ('draft','issued','evaluated'), "Invalid package status")
        validate_plan(p['plan'])
        require(content_hash(p['plan']) == p['plan_hash'], "Package plan hash mismatch")
    for table in ('traces', 'trace_history'):
        rows = source.get(table)
        require(isinstance(rows, list), "Missing trace history")
        for row in rows:
            require(row['package_id'] in packets and type(row['revision']) is int and row['revision'] > 0, "Invalid trace reference")
            trace = json.loads(row['data'])
            require(evaluate_trace(packets[row['package_id']], trace) == json.loads(row['evaluation']), "Trace evaluation mismatch")
    with LOCK, store.connect() as db:
        # Validate every collision before any mutation. Existing data is never overwritten.
        incoming = []
        for table, records in [('students', students), ('packages', packages)]:
            for record in records:
                old = db.execute(f'SELECT data FROM {table} WHERE id=?', (record['id'],)).fetchone()
                if old:
                    obj = json.loads(old[0]);obj.pop('student_token', None)
                    require(obj == record, 'Backup conflicts with existing record: ' + record['id'])
                else:
                    incoming.append((table, record))
        for table in ('traces','trace_history'):
            for row in source[table]:
                where = 'package_id=?' + (' AND revision=?' if table == 'trace_history' else '')
                args = (row['package_id'],row['revision']) if table == 'trace_history' else (row['package_id'],)
                old = db.execute(f'SELECT * FROM {table} WHERE {where}',args).fetchone()
                require(not old or dict(old) == row, 'Backup conflicts with existing trace')
        # Keep a local recovery snapshot before a successful merge.
        directory = store.path.parent / 'backups';directory.mkdir(exist_ok=True)
        destination = directory / ('before-restore-' + secrets.token_hex(6) + '.sqlite3')
        with closing(sqlite3.connect(str(destination))) as target:
            db.backup(target)
        for table, record in incoming:
            if table == 'students':
                db.execute('INSERT INTO students VALUES (?,?)',(record['id'],json.dumps(record)))
            else:
                record['student_token'] = secrets.token_urlsafe(24)
                db.execute('INSERT INTO packages VALUES (?,?,?)',(record['id'],record['student_id'],json.dumps(record)))
        for table in ('traces','trace_history'):
            for row in source[table]:
                db.execute(f'INSERT OR IGNORE INTO {table} VALUES (?,?,?,?)',tuple(row[k] for k in ('package_id','revision','data','evaluation')))
    return {'merged': len(incoming), 'snapshot': destination.name}
