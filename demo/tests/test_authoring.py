import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_core import profile, good_trace
from core import (state_for, demo_proposal, validate_proposal, compile_plan, validate_plan,
                  public_package, validate_generated_question, ValidationError, validate_config)
from server import Store, generate
from persistence import backup,restore


def question():
    return {'id':'N1','skill':'inverse_operations','level':'foundation','equation':{'a':2,'b':-6,'c':16},
            'prompt_template':'解方程：{equation}。','options':[{'id':'A','text':'x = 5'},{'id':'B','text':'x = 11'},
            {'id':'C','text':'x = 10'},{'id':'D','text':'其他答案 / 不确定'}],'correct_option':'B',
            'misconception_options':{'A':'sign_change'},'hints':['保持等式两边相等。','两边加 6，再除以 2。'],
            'explanation':'两边加 6，得 2x=22，除以 2 得 x=11。检验 2×11-6=16。','design_reason':'检验负常数移项与系数处理。'}


class AuthoringTests(unittest.TestCase):
    def proposal(self):
        state=state_for(profile(),[]);p=demo_proposal(state,[])
        p['schema_version']='2.0';p['question_ids'][0]='N1';p['generated_questions']=[question()]
        return state,p

    def test_mixed_plan_and_student_projection(self):
        state,p=self.proposal();validate_proposal(p,state)
        plan=compile_plan(p,{'language':'zh'})
        self.assertEqual(plan['nodes'][0]['origin'],'ai_generated')
        self.assertIn('2x - 6 = 16',plan['nodes'][0]['prompt'])
        self.assertEqual(plan['nodes'][2]['origin'],'bank')
        package={'id':'P','student_id':'S','round':1,'version':1,'status':'issued','sheet_code':'ABC123','mode':'live','created_at':'now','config':{},'plan':plan}
        public=public_package(package)
        for key in ('equation','correct_option','design_reason','prompt_template','explanation'):
            self.assertNotIn(key,public['plan']['nodes'][0])
        plan['nodes'][0]['prompt']='Solve a different equation'
        with self.assertRaises(ValidationError):validate_plan(plan)

    def test_numeric_option_contract(self):
        raw=question()
        for option in raw['options'][:3]:option['value']=int(option.pop('text').split('=')[1])
        validated=validate_generated_question(raw)
        self.assertEqual(validated['options'][1]['text'],'x = 11')
        self.assertEqual(validate_generated_question(validated),validated)
        validated['options'][1]['text']='x = 12'
        with self.assertRaises(ValidationError):validate_generated_question(validated)

    def test_wrong_math_and_bad_contract_rejected(self):
        for change in ({'correct_option':'A'},{'equation':{'a':0,'b':1,'c':2}},
                       {'equation':{'a':3,'b':1,'c':2}}, {'prompt_template':'No equation'},
                       {'misconception_options':{'C':'sign_change'}}, {'hints':['one only']}):
            q=question();q.update(change)
            with self.assertRaises(ValidationError):validate_generated_question(q)
        q=question();q['options'][0]['text']='x = 11'
        with self.assertRaises(ValidationError):validate_generated_question(q)

    def test_all_generated_and_unused_rejected(self):
        state,p=self.proposal();p['generated_questions']=[];p['question_ids']=[]
        for i in range(1,4):
            q=question();q['id']=f'N{i}';q['equation']['c']+=i*2
            for o in q['options'][:3]:o['text']='x = '+str(int(o['text'].split('=')[1])+i)
            p['generated_questions'].append(q);p['question_ids'].append(q['id'])
        validate_proposal(p,state);compile_plan(p)
        p['question_ids'][0]='F01'
        with self.assertRaises(ValidationError):validate_proposal(p,state)

    def test_generated_backup_and_history_context(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'a.sqlite3');student=profile();student.update(label='Test',grade='Secondary');store.save('students',student)
            state,p=self.proposal()
            with patch('server.ai_plan',return_value=(p,{'model':'mock'})):
                first=generate(store,student['id'],'live',validate_config({'language':'zh'}))
            restored=Store(Path(folder)/'b.sqlite3');restore(restored,{'confirmed':True,'backup':backup(store)})
            self.assertEqual(restored.get('packages',first['id'])['plan'],first['plan'])
            with patch('server.ai_plan',return_value=(p,{'model':'mock'})) as call:
                generate(store,student['id'],'live',validate_config({}))
            request=call.call_args.args[0]
            self.assertEqual(request['historical_questions'][0]['questions'][0]['equation'],question()['equation'])
            self.assertNotIn('N1',request['used_question_ids'])

if __name__=='__main__':unittest.main()
