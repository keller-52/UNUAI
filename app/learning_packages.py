"""Portable, self-contained learning materials; no learner records or credentials."""
import copy
import re
import secrets

from core import ValidationError, content_hash, require, validate_config, validate_plan
from workbook import compile_workbook, validate_workbook

FORMAT = 'paper-ai-learning-package'
FORMAT_VERSION = '1.0'
FIELDS = ('id', 'version', 'sheet_code', 'record_sheets', 'config', 'proposal', 'plan',
          'plan_hash', 'compiler_version', 'template_version', 'pages', 'schedule')


def portable_materials(package):
    require(package.get('config', {}).get('custom_topic') is True,
            'Only topic learning packages can be imported or exported.')
    return {key: copy.deepcopy(package[key]) for key in FIELDS if key in package}


def export_package(package):
    result = {'format': FORMAT, 'format_version': FORMAT_VERSION,
              'package': portable_materials(package)}
    result['checksum'] = content_hash(result)
    return result


def checked_materials(source):
    require(isinstance(source, dict), 'Choose a learning package JSON file.')
    if 'format' in source:
        require(source.get('format') == FORMAT and source.get('format_version') == FORMAT_VERSION,
                'Unsupported learning package format.')
        source = copy.deepcopy(source)
        checksum = source.pop('checksum', None)
        require(checksum == content_hash(source), 'Learning package checksum mismatch.')
        source = source.get('package')
    require(isinstance(source, dict), 'Choose a learning package JSON file.')
    try:
        p = portable_materials(source)
        require(isinstance(p.get('id'), str) and re.fullmatch(r'PKG-[A-Z0-9-]{1,64}', p['id']),
                'Invalid learning package ID.')
        require(type(p.get('version')) is int and p['version'] >= 1, 'Invalid learning package version.')
        raw_config = p.get('config')
        require(isinstance(raw_config, dict) and not raw_config.get('include_reference_bank'),
                'Reference banks are unavailable')
        config = validate_config(raw_config)
        require(config == raw_config, 'Learning package settings are inconsistent.')
        proposal = p.get('proposal')
        require(isinstance(proposal, dict), 'Missing learning package content.')
        refs = proposal.get('evidence_refs')
        require(isinstance(refs, list) and all(isinstance(r, str) for r in refs), 'Invalid evidence references.')
        validate_workbook(proposal, {'evidence': [{'ref': r} for r in refs]},
                          config['question_count'], config['batch_size'])
        validate_plan(p['plan'])
        require(compile_workbook(proposal, config) == p['plan'], 'Learning package content does not match its plan.')
        require(content_hash(p['plan']) == p.get('plan_hash'), 'Learning package plan hash mismatch.')
        sheets = p.get('record_sheets')
        require(isinstance(sheets, list) and all(isinstance(s, dict) for s in sheets), 'Invalid record sheets.')
        task_ids = [n['id'] for n in p['plan']['nodes'] if n['type'] == 'choice_question']
        require([t for s in sheets for t in s.get('task_ids', [])] == task_ids, 'Record sheets must cover every question once.')
        require(all(type(s.get('page')) is int and s['page'] == i + 1 and
                    isinstance(s.get('task_ids'), list) and 1 <= len(s['task_ids']) <= 8
                    for i, s in enumerate(sheets)), 'Invalid record sheet pagination.')
        codes = [p.get('sheet_code')] + [s.get('code') for s in sheets]
        require(all(isinstance(c, str) and re.fullmatch(r'[0-9A-F]{6}', c) for c in codes)
                and len(set(codes)) == len(codes), 'Invalid or duplicate record sheet codes.')
        require(p.get('pages') == config['question_count'], 'Invalid learning package page metadata.')
        require(p.get('template_version') == 'OMR-1', 'Unsupported record sheet format.')
        require(isinstance(p.get('schedule'), list) and
                [s.get('task_id') for s in p['schedule']] == task_ids and
                all(type(s.get('day')) is int and 1 <= s['day'] <= config['offline_days'] for s in p['schedule']),
                'Invalid learning schedule.')
        return p
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValidationError('Incomplete or malformed learning package.') from exc


def import_package(store, body):
    from server import LOCK, now
    student = store.get('students', body.get('student_id'))
    materials = checked_materials(body.get('learning_package'))
    fingerprint = content_hash(materials)
    with LOCK, store.connect() as db:
        old = db.execute('SELECT data FROM packages WHERE id=?', (materials['id'],)).fetchone()
        if old:
            import json
            old = json.loads(old[0])
            require(old['student_id'] == student['id'] and
                    (old.get('import_fingerprint') == fingerprint or portable_materials(old) == materials),
                    'This package ID already exists with different content or another learner.')
            return {'package_id': old['id'], 'duplicate': True}
        codes = {materials['sheet_code']} | {s['code'] for s in materials['record_sheets']}
        existing = store.packages()
        occupied = {p['sheet_code'] for p in existing} | {s['code'] for p in existing for s in p.get('record_sheets', [])}
        require(not codes.intersection(occupied), 'Record sheet codes conflict with an existing package.')
        package = dict(materials, student_id=student['id'],
                       round=max((p['round'] for p in existing if p['student_id'] == student['id']), default=0) + 1,
                       status='draft', mode='imported', created_at=now(),
                       student_token=secrets.token_urlsafe(24), import_fingerprint=fingerprint,
                       unit_version='portable-1', reused_question_ids=[], request={},
                       audit={'provider': 'imported', 'model': None, 'attempts': [], 'elapsed_seconds': 0,
                              'notice': 'Imported materials; teacher review required.'},
                       learning_summary=materials['proposal']['learning_summary'],
                       summary_evidence_refs=[], summary_as_of=0)
        # Keep old evidence references in the content snapshot only. They do not become
        # observations for this learner; later AI requests use confirmed local traces.
        db.execute('INSERT INTO packages VALUES (?,?,?)',
                   (package['id'], student['id'], __import__('json').dumps(package)))
    return {'package_id': package['id'], 'duplicate': False}
