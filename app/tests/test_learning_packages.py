import copy
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from core import ValidationError, content_hash
from learning_packages import export_package, import_package
from server import Store, generate, make_server
from test_workbook import proposal, config


class LearningPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Store(Path(self.temp.name)/'source.db')
        self.target = Store(Path(self.temp.name)/'target.db')
        for store in (self.source, self.target):
            store.save('students', {'id':'S', 'label':'Learner', 'grade':'Secondary', 'diagnostic':{}})
        with patch('server.ai_plan', return_value=(proposal(), {'model':'mock'})):
            self.package = generate(self.source, 'S', 'live', config())
        self.portable = export_package(self.package)

    def load(self, source=None):
        return import_package(self.target, {'student_id':'S', 'learning_package':self.portable if source is None else source})

    def test_round_trip_frozen_content_codes_and_no_records(self):
        self.package.update(status='evaluated', trace={'secret':'answer'}, evaluation={'first_total':1},
                            ai_summary={'summary':'Old learner'}, request={'api_key':'secret'})
        p = export_package(self.package)
        self.assertNotIn('student_token', p['package'])
        self.assertNotIn('student_id', p['package'])
        self.assertNotIn('secret', json.dumps(p))
        self.assertFalse({'trace','evaluation','request','audit','ai_summary'} & set(p['package']))
        result=self.load(p)
        restored=self.target.get('packages', result['package_id'])
        self.assertEqual(restored['plan'], self.package['plan'])
        self.assertEqual(restored['record_sheets'], self.package['record_sheets'])
        self.assertEqual(restored['sheet_code'], self.package['sheet_code'])
        self.assertEqual(restored['status'], 'draft')
        self.assertEqual(restored['mode'], 'imported')
        self.assertEqual(restored['summary_evidence_refs'], [])
        self.assertEqual(self.target.evaluations('S'), [])
        self.assertNotEqual(restored['student_token'], self.package['student_token'])

    def test_duplicate_is_idempotent(self):
        first=self.load();second=self.load()
        self.assertEqual(first['package_id'],second['package_id'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(len(self.target.packages()),1)

    def test_old_round_json_is_supported(self):
        p=copy.deepcopy(self.package);p.update(trace={'rows':[]},trace_revision=8)
        self.load(p)
        restored=self.target.packages()[0]
        self.assertNotIn('trace',restored)
        self.assertNotIn('trace_revision',restored)

    def test_checksum_failure_does_not_write(self):
        p=copy.deepcopy(self.portable);p['package']['plan']['title']='Changed'
        with self.assertRaisesRegex(ValidationError,'checksum'):self.load(p)
        self.assertEqual(self.target.packages(),[])

    def test_recomputed_checksum_cannot_hide_inconsistent_content(self):
        for change in ('plan','codes','hint','config','schedule'):
            p=copy.deepcopy(self.portable)
            if change=='plan':p['package']['plan']['nodes'][0]['correct_option']='B'
            if change=='codes':p['package']['record_sheets'][0]['task_ids'].pop()
            if change=='hint':p['package']['proposal']['questions'][0]['hints']=[]
            if change=='config':p['package']['config']['question_count']=99
            if change=='schedule':p['package']['schedule'][0]['day']=99
            p.pop('checksum');p['checksum']=content_hash(p)
            with self.subTest(change=change),self.assertRaises(ValidationError):self.load(p)
        self.assertEqual(self.target.packages(),[])

    def test_collision_with_another_learner_is_rejected(self):
        self.load()
        self.target.save('students',{'id':'T','label':'Other','grade':'Secondary','diagnostic':{}})
        with self.assertRaisesRegex(ValidationError,'another learner'):
            import_package(self.target,{'student_id':'T','learning_package':self.portable})
        self.assertEqual(len(self.target.packages()),1)

    def test_sheet_collision_is_atomic(self):
        self.load();p=copy.deepcopy(self.package);p['id']='PKG-SECOND'
        with self.assertRaisesRegex(ValidationError,'codes conflict'):self.load(p)
        self.assertEqual(len(self.target.packages()),1)

    def test_import_requires_a_learner_and_complete_structure(self):
        for raw in ([],{}, {'format':'unknown'}, {'config':{'custom_topic':True}}):
            with self.subTest(raw=raw),self.assertRaises(ValidationError):self.load(raw)
        with self.assertRaises(ValidationError):import_package(self.target,{'student_id':'NOPE','learning_package':self.portable})

    def test_formal_api_rejects_presets_and_fixture_generation(self):
        server=make_server(0,Path(self.temp.name)/'formal.db')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        data=json.load(opener.open(base+'/api/bootstrap'))
        self.assertFalse({'diagnostic','units','showcase_slots'} & set(data))
        for path,body in [('/api/seed',{}),('/api/generate',{'mode':'demo','config':{}}),
                          ('/api/generate',{'mode':'live','config':{}}),
                          ('/api/generate',{'mode':'live','config':{'custom_topic':True,'include_reference_bank':True}})]:
            req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-PaperAI':'local-teacher'})
            with self.subTest(path=path,body=body),self.assertRaises(urllib.error.HTTPError) as caught:opener.open(req)
            self.assertEqual(caught.exception.code,400);caught.exception.close()

    def test_imported_draft_can_be_edited_without_source_request(self):
        server=make_server(0,Path(self.temp.name)/'edited.db')
        server.store.save('students',{'id':'S','label':'Learner','grade':'Secondary','diagnostic':{}})
        result=import_package(server.store,{'student_id':'S','learning_package':self.portable})
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        url=f'http://127.0.0.1:{server.server_port}/api/packages/{result["package_id"]}/edit'
        body={'plan_hash':self.package['plan_hash'],'title':'Reviewed learning package'}
        req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-PaperAI':'local-teacher'})
        with opener.open(req) as response:edited=json.load(response)
        self.assertEqual(edited['plan']['title'],'Reviewed learning package')
        self.assertEqual(edited['status'],'draft')
        self.assertEqual(edited['request'],{})
        self.assertEqual(server.store.evaluations('S'),[])
        self.assertNotEqual(edited['plan_hash'],self.package['plan_hash'])
        from learning_packages import checked_materials
        checked_materials(export_package(edited))


if __name__=='__main__':unittest.main()
