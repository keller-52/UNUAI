import copy,io,json,unittest
from pathlib import Path
from unittest.mock import patch
from server import ai_plan
from test_workbook import proposal,config
from workbook import feedback_scope_issues

class PromptIterationTests(unittest.TestCase):
 def test_scoped_feedback_repair_preserves_questions(self):
  original=proposal()
  for b in original['batch_feedback']:
   b.pop('rules');b['guidance']='| 选择情况 | 情况分析 | 跳转内容 |\n| --- | --- | --- |\n| 其他情况 | 待复查 | END |'
  original['batch_feedback'][0]['guidance']='| Q8 wrong | Review | Q7 |'
  repaired=copy.deepcopy(original['batch_feedback']);repaired[0]['guidance']='| Q2 wrong | Review | Q7 |\n| Otherwise | Ready | END |'
  payloads=[original,{'batch_feedback':repaired,'questions':[]}]
  envelopes=[io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(p)},'finish_reason':'stop'}]}).encode()) for p in payloads]
  provider={'protocol':'chat','base_url':'https://example.test/v1','api_key':'test','model':'test','json_mode':'off'}
  with patch('server.urllib.request.urlopen',side_effect=envelopes) as call:
   result,audit=ai_plan({'constraints':config(),'student_state':{'evidence':[]},'catalog':[]},provider)
  self.assertEqual(result['questions'],original['questions'])
  self.assertEqual(result['lesson'],original['lesson'])
  self.assertEqual(result['batch_feedback'],repaired)
  self.assertEqual(audit['attempts'][0]['repair_mode'],'feedback_only')
  self.assertEqual(call.call_count,2)
  self.assertIn('REPAIR RESPONSE OVERRIDE',json.loads(call.call_args.args[0].data)['messages'][0]['content'])
 def test_scope_allows_forward_destinations_and_free_policy(self):
  p={'batch_feedback':[{'batch':1,'guidance':'| Q2 wrong | Needs review | Q15 |\n| Otherwise | Ready | Group 3 |'}]}
  self.assertEqual(feedback_scope_issues(p,5),[])
  p['batch_feedback'][0]['guidance']='| Q6 wrong | Needs review | Q2 |'
  self.assertIn('Q6',feedback_scope_issues(p,5)[0])
 def test_two_reserved_showcase_spaces(self):
  slots=json.loads((Path(__file__).parents[1]/'showcase/manifest.json').read_text())['slots']
  self.assertEqual([s['id'] for s in slots],['humanities','science'])
  for slot in slots:
   self.assertEqual(set(slot['label']),{'en','zh'});self.assertEqual(slot['status'],'reserved')
   self.assertIsNone(slot['topic']);self.assertIsNone(slot['background']);self.assertEqual(slot['reference_questions'],[])

 def test_summary_only_repair_preserves_feedback(self):
  original=proposal();original['learning_summary']='Situation: confirmed_evaluations is empty. Measures: diagnose.'
  payloads=[original,{'learning_summary':'Situation: no confirmed answers. Measures: diagnose.'}]
  envelopes=[io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(p)},'finish_reason':'stop'}]}).encode()) for p in payloads]
  provider={'protocol':'chat','base_url':'https://example.test/v1','api_key':'test','model':'test','json_mode':'off'}
  with patch('server.urllib.request.urlopen',side_effect=envelopes):result,audit=ai_plan({'constraints':config(),'student_state':{'evidence':[]},'catalog':[]},provider)
  self.assertEqual(result['batch_feedback'],original['batch_feedback'])
  self.assertEqual(result['questions'],original['questions'])
  self.assertNotIn('confirmed_evaluations',result['learning_summary'])
  self.assertEqual(audit['attempts'][0]['repair_mode'],'fields_only')
