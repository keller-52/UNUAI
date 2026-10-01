import io,json,unittest
from unittest.mock import patch
from server import ai_plan
from workbook import validate_workbook
from core import ValidationError
from test_workbook import proposal

class Release06Tests(unittest.TestCase):
 def test_summary_has_no_question_generation_instruction(self):
  answer={'summary':'Situation: unknown. Measures: collect first answers.','strengths':[],'needs':['Unknown'],'next_steps':['Collect first answers'],'evidence_refs':[]}
  response={'choices':[{'message':{'content':json.dumps(answer)},'finish_reason':'stop'}]}
  provider={'protocol':'chat','base_url':'https://example.test/v1','api_key':'test','model':'test','json_mode':'off'}
  with patch('server.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
   result,audit=ai_plan({'operation':'summary','constraints':{'custom_topic':True,'question_count':30,'batch_size':10,'language':'zh'},'student_state':{'evidence':[]}},provider)
  system=json.loads(call.call_args.args[0].data)['messages'][0]['content']
  self.assertIn('Summarise existing evidence only',system)
  self.assertNotIn('Current packet:',system)
  self.assertEqual(result,answer)
  self.assertEqual(audit['prompt_version'],'paper-summary-2')
 def test_missing_hint_error_names_question_for_repair(self):
  p=proposal();p['questions'][2]['hints']=['Only one']
  with self.assertRaisesRegex(ValidationError,'Q3: hints must be an array of exactly two'):
   validate_workbook(p,{'evidence':[]},12,6)
