"""Test-only self-contained materials, generated without external AI calls."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from server import Store,generate
from test_workbook import proposal,config
from learning_packages import export_package

with tempfile.TemporaryDirectory() as directory:
    store=Store(Path(directory)/'fixture.db')
    store.save('students',{'id':'S','label':'Fixture','grade':'Secondary','diagnostic':{}})
    p=proposal()
    p['title']='Reading with evidence'
    p['reason']='Read a short passage and distinguish observations from conclusions.'
    p['learning_summary']='Situation: no confirmed learning records.\nMeasures: start with group 1 and follow the printed feedback.'
    p['lesson']=[{'heading':'Read, compare, explain','text':'A good conclusion uses what the passage actually says. Separate an observation from an assumption. Read the question carefully, then choose the answer with direct support.','example':'The passage says that the library opens at nine. We can conclude that it is open at ten; we cannot infer that it opens every holiday.'}]
    for i,q in enumerate(p['questions']):
        q.update(prompt='Which statement is directly supported by the passage? ('+str(i+1)+')',skill='Evidence',options=[{'id':a,'text':t} for a,t in zip('ABCD',['The library opens at nine.','The library opens on every holiday.','Everyone visits the library.','The library never closes.'])],hints=['Look for a statement in the passage.','Compare the opening time with each option.'],explanation='The opening time is given explicitly; the other choices add information.',design_reason='Distinguish explicit evidence from assumptions.')
    for b in p['batch_feedback']:
        b.pop('rules')
        b.update(title='Group '+str(b['batch']),focus='Check evidence-based reading.',guidance='| Condition | Situation | Next step |\n| --- | --- | --- |\n| All answers correct | The first answers are consistent with the passage. | END |\n| Otherwise | Recheck the supporting sentence. | Review this group once, then END |')
    c=config();c['language']='en'
    with patch('server.ai_plan',return_value=(p,{'model':'fixture','attempts':[{}],'elapsed_seconds':0})):
        packet=generate(store,'S','live',c)
    print(json.dumps(export_package(packet)))
