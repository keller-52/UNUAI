import copy
import json
import tempfile
from pathlib import Path
import sys
import unittest
import sqlite3
import threading
import urllib.request
import urllib.error
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import validate_config, evaluate_trace, ValidationError, UNITS, content_hash
from server import Store, generate, make_server
from persistence import backup, restore
from test_core import good_trace


class ProductTests(unittest.TestCase):
    def test_restore_snapshot_closes_and_conflicts_are_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Store(Path(folder)/'source.sqlite3')
            source.save('students',{'id':'S','label':'Original','grade':'Secondary','diagnostic':{}})
            snapshot=backup(source)
            target=Store(Path(folder)/'target.sqlite3')
            connections=[]
            connect=sqlite3.connect
            def tracked(*args,**kwargs):
                db=connect(*args,**kwargs)
                if 'before-restore-' in str(args[0]):connections.append(db)
                return db
            with patch('persistence.sqlite3.connect',side_effect=tracked):
                restore(target,{'confirmed':True,'backup':snapshot})
            self.assertEqual(len(connections),1)
            with self.assertRaises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')
            conflicting=copy.deepcopy(snapshot)
            conflicting['students'].insert(0,{'id':'NEW','label':'New','grade':'Secondary','diagnostic':{}})
            conflicting['students'][1]['label']='Conflicting'
            conflicting.pop('checksum');conflicting['checksum']=content_hash(conflicting)
            with self.assertRaises(ValidationError):restore(target,{'confirmed':True,'backup':conflicting})
            self.assertEqual([s['id'] for s in backup(target)['students']],['S'])
            self.assertEqual(target.get('students','S')['label'],'Original')
            conflicting['checksum']='invalid'
            with self.assertRaises(ValidationError):restore(target,{'confirmed':True,'backup':conflicting})

    def test_restart_marks_running_jobs_interrupted(self):
        with tempfile.TemporaryDirectory() as folder:
            filename=Path(folder)/'jobs.sqlite3';store=Store(filename)
            with store.connect() as db:
                for status in ('running','complete','failed'):
                    db.execute('INSERT INTO generation_jobs VALUES (?,?)',(status,json.dumps({'id':status,'status':status})))
            server=make_server(0,filename, allow_test_fixtures=True)
            try:
                with server.store.connect() as db:
                    jobs={row['id']:json.loads(row['data'])['status'] for row in db.execute('SELECT * FROM generation_jobs')}
                self.assertEqual(jobs,{'running':'interrupted','complete':'complete','failed':'failed'})
            finally:server.server_close()

    def test_running_job_duplicate_and_completed_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            server=make_server(0,Path(folder)/'jobs.sqlite3', allow_test_fixtures=True)
            server.store.save('students',{'id':'S','label':'Synthetic','grade':'Secondary','diagnostic':{}})
            serving=threading.Thread(target=server.serve_forever);serving.start()
            entered=threading.Event();release=threading.Event();results=[]
            def request(endpoint,body=None):
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+endpoint,
                    data=None if body is None else json.dumps(body).encode(),headers={'X-PaperAI':'local-teacher','Content-Type':'application/json'})
                try:
                    with urllib.request.urlopen(req,timeout=10) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as response:
                    with response:return response.code,json.load(response)
            body={'student_id':'S','mode':'demo','config':{},'request_id':'unique-test-job'}
            def delayed(*args):
                entered.set()
                if not release.wait(5):raise TimeoutError('Test did not release generation')
                return generate(*args)
            try:
                with patch('server.generate',side_effect=delayed):
                    client=threading.Thread(target=lambda:results.append(request('/api/generate',body)));client.start()
                    self.assertTrue(entered.wait(5))
                    self.assertEqual(request('/api/jobs')[1]['jobs'][0]['status'],'running')
                    self.assertEqual(request('/api/generate',body)[0],409)
                    release.set();client.join(10);self.assertFalse(client.is_alive())
                self.assertEqual(results[0][0],201)
                replay=request('/api/generate',body)
                self.assertEqual(replay[1]['id'],results[0][1]['id'])
                self.assertEqual(len(server.store.packages()),1)
                self.assertEqual(request('/api/jobs')[1]['jobs'][0]['status'],'complete')
            finally:
                release.set();server.shutdown();server.server_close();serving.join()

    def test_languages_counts_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            original=Store(Path(folder)/'original.sqlite3')
            original.save('students',{'id':'S-BILINGUAL','label':'Sample','grade':'Secondary','diagnostic':{}})
            for language in ('en','zh'):
                for count in (2,3,4):
                    package=generate(original,'S-BILINGUAL','demo',validate_config({'language':language,'question_count':count}))
                    self.assertEqual(len(package['plan']['nodes']),count*2)
                    self.assertEqual(len(package['proposal']['question_ids']),count)
                    self.assertEqual(len(package['schedule']),count)
                    self.assertEqual(package['plan']['language'],language)
                    self.assertIn('解方程' if language=='zh' else 'Solve',package['plan']['nodes'][0]['prompt'])
            snapshot=backup(original)
            restored=Store(Path(folder)/'restored.sqlite3')
            self.assertEqual(restore(restored,{'confirmed':True,'backup':snapshot})['merged'],7)
            self.assertEqual(restore(restored,{'confirmed':True,'backup':snapshot})['merged'],0)
            self.assertEqual(len(restored.packages()),6)
            self.assertNotEqual(restored.packages()[0]['student_token'],original.packages()[0]['student_token'])
            changed=restored.get('students','S-BILINGUAL');changed['label']='Changed';restored.save('students',changed)
            with self.assertRaises(ValidationError):restore(restored,{'confirmed':True,'backup':snapshot})
            self.assertEqual(restored.get('students','S-BILINGUAL')['label'],'Changed')

    def test_backup_retains_trace_revisions(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'source.sqlite3');store.save('students',{'id':'S','label':'S','grade':'Secondary','diagnostic':{}})
            p=generate(store,'S','demo',validate_config({}));p['status']='evaluated';store.save('packages',p)
            trace=good_trace(p);result=evaluate_trace(p,trace)
            with store.connect() as db:
                values=(p['id'],1,json.dumps(trace),json.dumps(result))
                db.execute('INSERT INTO traces VALUES (?,?,?,?)',values);db.execute('INSERT INTO trace_history VALUES (?,?,?,?)',values)
            restored=Store(Path(folder)/'target.sqlite3');restore(restored,{'confirmed':True,'backup':backup(store)})
            self.assertEqual(restored.evaluations('S'),[result])

    def test_unit_and_language_constraints(self):
        self.assertEqual(len(UNITS),1)
        for bad in ({'unit_id':'unregistered'},{'language':'fr'},{'question_count':5},{'question_count':4,'max_pages':3}):
            with self.assertRaises(ValidationError):validate_config(bad)


if __name__=='__main__':unittest.main()
