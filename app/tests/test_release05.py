import copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from core import ValidationError,validate_plan,evaluate_trace
from providers import PRESETS,build_request,response_content,parse_json_content
from workbook import validate_workbook,compile_workbook
from test_workbook import proposal,config
import pdf_export

class Release05Tests(unittest.TestCase):
 def test_provider_contracts(self):
  messages=[{'role':'system','content':'JSON instructions'},{'role':'user','content':'question'},{'role':'assistant','content':'bad JSON'},{'role':'user','content':'repair'}]
  fixtures={
   'chat':({'choices':[{'message':{'content':'{}'},'finish_reason':'stop'}]},'/chat/completions','Authorization'),
   'responses':({'output':[{'type':'message','content':[{'type':'output_text','text':'{}'}]}],'status':'completed'},'/responses','Authorization'),
   'azure_responses':({'output':[{'type':'message','content':[{'type':'output_text','text':'{}'}]}]},'/responses','api-key'),
   'anthropic':({'content':[{'type':'thinking','thinking':'private'},{'type':'text','text':'{}'}]},'/messages','x-api-key'),
   'gemini':({'candidates':[{'content':{'parts':[{'text':'ignored','thought':True},{'text':'{}'}]}}]},':generateContent','x-goog-api-key'),
   'dashscope':({'output':{'choices':[{'message':{'content':'{}'}}]}},'/services/aigc/text-generation/generation','Authorization')}
  for name,preset in PRESETS.items():
   with self.subTest(provider=name):
    p=dict(preset,provider=name,api_key='test-key',model='model-id',json_mode='auto')
    url,headers,payload=build_request(p,messages,16000);fixture,suffix,key=fixtures[p['protocol']]
    self.assertTrue(url.endswith(suffix));self.assertIn(key,headers);self.assertNotIn('test-key',url+json.dumps(payload))
    self.assertEqual(response_content(fixture,p)[0],'{}')
    if p['protocol']=='gemini':self.assertEqual(payload['contents'][1]['role'],'model')
    if p['protocol']=='anthropic':self.assertEqual(headers['anthropic-version'],'2023-06-01');self.assertEqual(payload['system'],'JSON instructions')
    if p['protocol']=='dashscope':self.assertEqual(payload['parameters']['result_format'],'message')
 def test_optional_json_mode_and_wrappers(self):
  p=dict(PRESETS['custom'],api_key='test',model='m',json_mode='off')
  self.assertNotIn('response_format',build_request(p,[],6000)[2])
  p['json_mode']='on';self.assertIn('response_format',build_request(p,[],6000)[2])
  for text in ['```json\n{"a":1}\n```','Here is the JSON: {"a":1}','{"a":1}']:
   self.assertEqual(parse_json_content(text),{'a':1})
  with self.assertRaises((ValueError,ValidationError)):parse_json_content('{"a":')
 def test_free_guidance_and_unknown_records(self):
  p=proposal()
  for b in p['batch_feedback']:b.pop('rules');b['guidance']='## 建议\n按自己的理解完成 Q1；需要时回看本组。最终 END。'
  validate_workbook(p,{'evidence':[]},12,6);plan=compile_workbook(p,config());validate_plan(plan)
  self.assertEqual(plan['routing_version'],'free-guidance-1')
  packet={'id':'P','version':1,'config':config(),'plan':plan}
  rows=[{'task_id':n['id'],'first_answer':'A' if n['id']=='Q1' else None,'hint_level':None,'retry_answer':None} for n in plan['nodes']]
  trace={'package_id':'P','package_version':1,'confirmed':True,'source':'synthetic','rows':rows}
  e=evaluate_trace(packet,trace);self.assertEqual(e['first_total'],1);self.assertFalse(e['route_complete']);self.assertEqual(e['results'][6]['completion'],'unanswered_or_skipped')
  trace['skipped_batches']=[2];self.assertEqual(evaluate_trace(packet,trace)['results'][6]['completion'],'not_assigned_confirmed')
  trace['skipped_batches']=[1]
  with self.assertRaises(ValidationError):evaluate_trace(packet,trace)
  p['batch_feedback'][0]['guidance']='Go to Q999'
  with self.assertRaises(ValidationError):validate_workbook(p,{'evidence':[]},12,6)
 def test_legacy_evaluation_shape_preserved(self):
  plan=compile_workbook(proposal(),config());packet={'id':'P','version':1,'config':config(),'plan':plan}
  rows=[{'task_id':n['id'],'first_answer':'A' if n['id']!='END' else None,'hint_level':None,'retry_answer':None} for n in plan['nodes']]
  e=evaluate_trace(packet,{'package_id':'P','package_version':1,'confirmed':True,'source':'synthetic','rows':rows})
  self.assertNotIn('routing_mode',e);self.assertNotIn('skipped_batches',e)
 def test_pdf_validates_render_acknowledgement(self):
  def run(command,**kwargs):
   out=next(x.split('=',1)[1] for x in command if x.startswith('--print-to-pdf='))
   Path(out).write_bytes(b'%PDF-'+b'0'*600)
   pdf_export.acknowledge(next(iter(pdf_export.JOBS)),True)
   return type('Done',(),{'returncode':0})()
  with patch('pdf_export.browser_path',return_value='/mock/browser'),patch('pdf_export.subprocess.run',side_effect=run):
   self.assertTrue(pdf_export.export_pdf(8765,['P'],'booklet').startswith(b'%PDF-'))
  self.assertEqual(pdf_export.JOBS,{})
  with patch('pdf_export.browser_path',return_value=None):
   with self.assertRaisesRegex(ValidationError,'PDF_BROWSER_MISSING'):pdf_export.export_pdf(8765,['P'],'booklet')
  def failed(command,**kwargs):
   pdf_export.acknowledge(next(iter(pdf_export.JOBS)),False,'Page budget exceeded');return type('Done',(),{'returncode':0})()
  with patch('pdf_export.browser_path',return_value='/mock/browser'),patch('pdf_export.subprocess.run',side_effect=failed):
   with self.assertRaisesRegex(ValidationError,'Page budget exceeded'):pdf_export.export_pdf(8765,['P'],'booklet')
if __name__=='__main__':unittest.main()
