import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import validate_config,validate_plan,public_package,evaluate_trace,ValidationError
from workbook import validate_workbook,compile_workbook
from server import Store,generate
from persistence import backup,restore


def proposal(count=12,size=6):
    return {'title':'测试主题','reason':'按背景讲解再检查。','learning_summary':'暂无记录，不能判断掌握情况。','evidence_refs':[],
        'lesson':[{'heading':'概念','text':'先理解教师提供的背景。','example':'一个完整示例。'}],
        'questions':[{'id':f'Q{i+1}','skill':'判断','prompt':f'第{i+1}个问题','origin':'ai_generated',
          'options':[{'id':x,'text':x+'选项'} for x in 'ABCD'],'correct_option':'A','hints':['提示一','提示二'],
          'explanation':'根据背景判断。','design_reason':'检查知识理解。'} for i in range(count)],
        'batch_feedback':[{'batch':i+1,'title':f'题组 {i+1}','focus':'检查本组知识点','rules':[{'min_correct':0,'max_correct':size//2,'action':'review_then_continue','target_batch':i+2 if i+1<count//size else 'END','feedback':'回看本批概念，重试错题。'},
            {'min_correct':size//2+1,'max_correct':size,'action':'continue','target_batch':i+3 if i+2<count//size else 'END','feedback':'按目标题组继续。'}]} for i in range(count//size)]}


def config():return validate_config({'custom_topic':True,'topic':'教师待测主题','background':'完整背景内容','batch_size':6,'batch_count':2})


class WorkbookTests(unittest.TestCase):
    def test_batch_rules(self):
        p=proposal();validate_workbook(p,{'evidence':[]},12,6)
        plan=compile_workbook(p,config());validate_plan(plan)
        for low in (3,5):
            bad=copy.deepcopy(p);bad['batch_feedback'][0]['rules'][1]['min_correct']=low
            with self.assertRaises(ValidationError):validate_workbook(bad,{'evidence':[]},12,6)
        bad=copy.deepcopy(p);bad['batch_feedback'][0]['rules'][0]['action']='unknown'
        with self.assertRaises(ValidationError):validate_workbook(bad,{'evidence':[]},12,6)

    def test_scope_scan_evaluation_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'a.sqlite3');store.save('students',{'id':'S','label':'Test','grade':'Secondary','diagnostic':{'D01':'A'}})
            with patch('server.ai_plan',return_value=(proposal(),{'model':'mock'})) as call:
                p=generate(store,'S','live',config())
            request=call.call_args.args[0]
            self.assertEqual(request['student_state']['evidence'],[]);self.assertEqual(request['catalog'],[])
            self.assertEqual(len(p['record_sheets']),2)
            self.assertEqual(sum(len(s['task_ids']) for s in p['record_sheets']),12)
            self.assertEqual(len({s['code'] for s in p['record_sheets']}),2)
            public=public_package(p);self.assertNotIn('batch_feedback',public['plan'])
            for n in public['plan']['nodes'][:-1]:
                for key in ['correct_option','hints','explanation']:self.assertNotIn(key,n)
            rows=[{'task_id':n['id'],'order':None,'first_answer':'A' if n['id']!='END' else None,'retry_answer':None,'hint_level':0 if n['id']!='END' else None} for n in p['plan']['nodes']]
            trace={'package_id':p['id'],'package_version':1,'confirmed':True,'source':'synthetic','rows':rows}
            e=evaluate_trace(p,trace);self.assertEqual(e['first_correct'],12);self.assertEqual(e['topic_id'],config()['topic_id'])
            p['status']='evaluated';store.save('packages',p)
            with store.connect() as db:db.execute('INSERT INTO traces VALUES (?,?,?,?)',(p['id'],1,json.dumps(trace),json.dumps(e)))
            target=Store(Path(folder)/'b.sqlite3');restore(target,{'confirmed':True,'backup':backup(store)})
            self.assertEqual(target.get('packages',p['id'])['record_sheets'],p['record_sheets'])
            next_p=proposal();next_p['evidence_refs']=[p['id']+':Q1']
            with patch('server.ai_plan',return_value=(next_p,{'model':'mock'})) as call:generate(store,'S','live',config())
            self.assertEqual(call.call_args.args[0]['confirmed_evaluations'][0]['first_correct'],12)

    def test_offline_branch_and_skipped_questions(self):
        c=validate_config(dict(config(),batch_count=3,batch_size=5));p=proposal(15,5)
        p['batch_feedback'][0]['rules'].insert(0,{'min_correct':0,'max_correct':5,'wrong_any':['Q2'],'action':'review_then_continue','feedback':'补强 Q2 对应概念','target_batch':2})
        validate_workbook(p,{'evidence':[]},15,5)
        packet={'id':'P','version':1,'config':c,'plan':compile_workbook(p,c)}
        rows=[{'task_id':n['id'],'first_answer':'A' if n['id'] not in ['Q6','Q7','Q8','Q9','Q10','END'] else None,'retry_answer':None,'hint_level':None} for n in packet['plan']['nodes']]
        trace={'package_id':'P','package_version':1,'confirmed':True,'source':'synthetic','rows':rows}
        e=evaluate_trace(packet,trace)
        self.assertEqual(e['prescribed_batch_path'],[1,3]);self.assertTrue(e['route_complete'])
        self.assertEqual(e['results'][5]['completion'],'not_assigned_by_route');self.assertEqual(e['warnings'],[])
        rows[1]['first_answer']='B'
        e=evaluate_trace(packet,trace)
        self.assertEqual(e['prescribed_batch_path'],[1,2]);self.assertFalse(e['route_complete'])
        self.assertEqual(e['results'][5]['completion'],'missing_or_unreadable')
        for target in (1,4,'Q99'):
            bad=copy.deepcopy(p);bad['batch_feedback'][0]['rules'][0]['target_batch']=target
            with self.assertRaises(ValidationError):validate_workbook(bad,{'evidence':[]},15,5)

    def test_custom_config_bounds(self):
        c=config();self.assertEqual(c['question_count'],12)
        for size in (4,11):
            with self.assertRaises(ValidationError):validate_config(dict(c,batch_size=size))

if __name__=='__main__':unittest.main()
