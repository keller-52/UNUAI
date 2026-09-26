import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
import io
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import (BANK, ValidationError, compile_plan, demo_proposal, state_for,
                  validate_plan, validate_proposal, evaluate_trace, public_package)
from server import make_server, PROVIDER, ai_plan, Store


class StoreConnectionTests(unittest.TestCase):
    def test_connection_commits_rolls_back_and_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'connections.db')
            with store.connect() as db:
                db.execute("INSERT INTO students VALUES (?, ?)", ('saved', '{}'))
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute('SELECT 1')
            with self.assertRaisesRegex(RuntimeError, 'rollback'):
                with store.connect() as failed:
                    failed.execute("INSERT INTO students VALUES (?, ?)", ('discarded', '{}'))
                    raise RuntimeError('rollback')
            with self.assertRaises(sqlite3.ProgrammingError):
                failed.execute('SELECT 1')
            with store.connect() as check:
                self.assertEqual([row[0] for row in check.execute('SELECT id FROM students')], ['saved'])


def profile(ready=False):
    return {"id": "S-TEST", "diagnostic": {k: BANK[k]["correct_option"] if ready else next(iter(BANK[k]["misconception_options"]))
                                           for k in ("D01", "D02", "D03")}}


def sample_package():
    state = state_for(profile(), [])
    return {"id": "P1", "version": 1, "plan": compile_plan(demo_proposal(state, []))}


def good_trace(p):
    nodes = {n["id"]: n for n in p["plan"]["nodes"]}
    rows = [{"task_id": n["id"], "order": None, "first_answer": None, "hint_level": None, "retry_answer": None}
            for n in nodes.values()]
    key = p["plan"]["entry_node"]
    order = 1
    while key:
        n = nodes[key]
        row = next(r for r in rows if r["task_id"] == key)
        row["order"] = order
        order += 1
        if n["type"] == "choice_question":
            row["first_answer"] = n["correct_option"]
            row["hint_level"] = 0
            key = next(r["next"] for r in n["routes"] if r["answer"] == n["correct_option"])
        else:
            key = n.get("next")
    return {"package_id": p["id"], "package_version": 1, "confirmed": True, "source": "synthetic", "rows": rows}


class CoreTests(unittest.TestCase):
    def test_catalog_arithmetic(self):
        for q in BANK.values():
            a,b,c = (q["equation"][k] for k in ("a","b","c"))
            answer = next(o for o in q["options"] if o["id"] == q["correct_option"])
            self.assertEqual(a * int(answer["text"].split("=")[1]) + b, c)

    def test_personalized_demo_and_second_round(self):
        low = state_for(profile(), [])
        high = state_for(profile(True), [])
        self.assertNotEqual(demo_proposal(low, [])["question_ids"], demo_proposal(high, [])["question_ids"])
        p = sample_package()
        e = evaluate_trace(p, good_trace(p))
        new = state_for(profile(), [e])
        self.assertEqual(new["status"], "ready_for_transfer_check")
        self.assertTrue(all(q.startswith("T") for q in demo_proposal(new, [])["question_ids"]))

    def test_unknown_baseline_not_mastered(self):
        self.assertEqual(state_for({"diagnostic": {}}, [])["status"], "unknown")

    def test_wrong_answer_route_preserved(self):
        p = sample_package(); t = good_trace(p)
        n = p["plan"]["nodes"][0]
        t["rows"][0]["first_answer"] = next(o["id"] for o in n["options"] if o["id"] != n["correct_option"])
        e = evaluate_trace(p, t)
        self.assertTrue(e["warnings"])
        self.assertEqual(e["first_correct"], 2)

    def test_unknown_answer_not_marked_incorrect(self):
        p = sample_package(); t = good_trace(p); t["rows"][0]["first_answer"] = None
        e = evaluate_trace(p, t)
        self.assertEqual(e["first_total"], 2)
        self.assertIsNone(e["results"][0]["first_correct"])

    def test_unknown_hints_not_counted_independent(self):
        p=sample_package();t=good_trace(p);t["rows"][0]["hint_level"]=None
        self.assertEqual(evaluate_trace(p,t)["independent_total"],2)

    def test_incomplete_path_does_not_trigger_progression(self):
        p=sample_package();t=good_trace(p);t["rows"][0]["first_answer"]=None
        self.assertEqual(state_for(profile(),[evaluate_trace(p,t)])["status"],"needs_support_check")

    def test_duplicate_visit_rejected(self):
        p=sample_package();t=good_trace(p);t["rows"][-1]["order"]=1
        with self.assertRaises(ValidationError):evaluate_trace(p,t)

    def test_wrong_version_rejected(self):
        p=sample_package();t=good_trace(p);t["package_version"]=2
        with self.assertRaises(ValidationError):evaluate_trace(p,t)

    def test_unconfirmed_rejected(self):
        p=sample_package();t=good_trace(p);t["confirmed"]=False
        with self.assertRaises(ValidationError):evaluate_trace(p,t)

    def test_answers_on_unvisited_rejected(self):
        p=sample_package();t=good_trace(p);t["rows"][0]["order"]=None
        with self.assertRaises(ValidationError):evaluate_trace(p,t)

    def test_invalid_graph_and_answer_rejected(self):
        for mutation in (lambda p:p["nodes"][0]["routes"][0].update(next="ABSENT"),
                         lambda p:p["nodes"][0]["routes"][0].update(next="Q1"),
                         lambda p:p["nodes"][0].update(correct_option="D")):
            p=sample_package()["plan"];mutation(p)
            with self.assertRaises(ValidationError):validate_plan(p)

    def test_bad_ai_ids_and_evidence_rejected(self):
        s=state_for(profile(),[])
        for change in ({"question_ids":["FAKE","F01","F02"]},{"evidence_refs":["invented"]}):
            p=demo_proposal(s,[]);p.update(change)
            with self.assertRaises(ValidationError):validate_proposal(p,s)


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.server=make_server(0,Path(cls.tmp.name)/"test.db")
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()

    def request(self,path,body=None,header=True):
        req=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),
                                   headers={"Content-Type":"application/json",**({"X-PaperAI":"local-teacher"} if header else {})})
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)

    def test_full_round_revision_and_student_projection(self):
        status,s=self.request('/api/students',{'label':'Test learner','diagnostic':profile()['diagnostic']})
        self.assertEqual(status,201)
        status,p=self.request('/api/generate',{'student_id':s['id'],'mode':'demo','config':{}})
        self.assertEqual(status,201);self.assertIsNone(p['audit']['model'])
        self.assertEqual(self.request('/api/packages/'+p['id']+'/trace',{'trace':good_trace(p)})[0],400)
        self.assertEqual(self.request('/api/packages/'+p['id']+'/approve',{'plan_hash':p['plan_hash'],'reviewed':True})[0],200)
        trace=good_trace(p)
        status,res=self.request('/api/packages/'+p['id']+'/trace',{'trace':trace,'expected_revision':0})
        self.assertEqual(status,200);self.assertEqual(res['revision'],1)
        status,again=self.request('/api/packages/'+p['id']+'/trace',{'trace':trace,'expected_revision':0})
        self.assertTrue(again['duplicate']);self.assertEqual(again['revision'],1)
        changed=copy.deepcopy(trace);changed['rows'][0]['hint_level']=1
        self.assertEqual(self.request('/api/packages/'+p['id']+'/trace',{'trace':changed,'expected_revision':0})[0],400)
        self.assertEqual(self.request('/api/packages/'+p['id']+'/trace',{'trace':changed,'expected_revision':1})[1]['revision'],2)
        _,pub=self.request('/api/learn/'+p['id']+'?token='+p['student_token'])
        raw=json.dumps(pub);self.assertNotIn('correct_option',raw);self.assertNotIn('misconception_options',raw);self.assertNotIn('audit',pub)
        self.assertTrue(all('explanation' not in n for n in pub['plan']['nodes'] if n['type']=='choice_question'))
        self.assertEqual(self.request('/api/learn/'+p['id']+'?token=wrong')[0],400)
        _,p2=self.request('/api/generate',{'student_id':s['id'],'mode':'demo','config':{}})
        self.assertEqual(p2['round'],2)
        self.assertTrue(p2['request']['confirmed_evaluations'])
        self.assertNotEqual(p['proposal']['question_ids'],p2['proposal']['question_ids'])

    def test_missing_credentials_no_demo_fallback(self):
        saved=dict(PROVIDER)
        try:
            PROVIDER['api_key']='';PROVIDER['model']=''
            _,s=self.request('/api/students',{'label':'No key'})
            status,r=self.request('/api/generate',{'student_id':s['id'],'mode':'live','config':{}})
            self.assertEqual(status,400);self.assertIn('Configure',r['error'])
            _,bootstrap=self.request('/api/bootstrap')
            self.assertFalse(any(p['student_id']==s['id'] for p in bootstrap['packages']))
        finally:PROVIDER.update(saved)

    def test_csrf_header_required(self):
        self.assertEqual(self.request('/api/seed',{},header=False)[0],400)

    def test_page_budget_rejected(self):
        _,s=self.request('/api/students',{'label':'Page budget'})
        self.assertEqual(self.request('/api/generate',{'student_id':s['id'],'mode':'demo','config':{'max_pages':1}})[0],400)


class AIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.state=state_for(profile(),[])
        self.request={"student_state":self.state}
        self.provider={"base_url":"https://example.invalid/v1","model":"mock-model","api_key":"test-only-key"}

    def response(self,content):
        return io.BytesIO(json.dumps({"model":"mock-model","choices":[{"message":{"content":content}}],"usage":{"total_tokens":100}}).encode())

    def test_live_protocol_with_mock_transport(self):
        proposal=demo_proposal(self.state,[])
        with patch('urllib.request.urlopen',return_value=self.response(json.dumps(proposal))) as call:
            result,audit=ai_plan(self.request,self.provider)
        self.assertEqual(result,proposal)
        sent=json.loads(call.call_args.args[0].data)
        self.assertEqual(sent['response_format'],{'type':'json_object'})
        self.assertEqual(audit['model'],'mock-model')
        self.assertNotIn('test-only-key',json.dumps(audit))

    def test_invalid_json_repair_attempt(self):
        proposal=demo_proposal(self.state,[])
        with patch('urllib.request.urlopen',side_effect=[self.response('not json'),self.response(json.dumps(proposal))]):
            _,audit=ai_plan(self.request,self.provider)
        self.assertEqual(len(audit['attempts']),2)

    def test_two_invalid_responses_fail_without_fallback(self):
        with patch('urllib.request.urlopen',side_effect=[self.response('{}'),self.response('{}')]):
            with self.assertRaisesRegex(ValidationError,'failed validation twice'):
                ai_plan(self.request,self.provider)

    def test_http_failure_is_explicit(self):
        with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://example.invalid',401,'bad key',{},None)):
            with self.assertRaisesRegex(ValidationError,'No demo fallback'):
                ai_plan(self.request,self.provider)


if __name__=='__main__':unittest.main()
