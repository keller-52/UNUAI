"""Replay recorded synthetic failures; opt-in one live targeted repair per input."""
import argparse,copy,io,json,sys,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from workbook import compile_workbook
from prompt_stability import review

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--output',required=True);ap.add_argument('files',nargs='+');a=ap.parse_args()
 if not a.run:raise SystemExit('Use --run for paid repair calls on synthetic records only.')
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True);report=[]
 for index,name in enumerate(a.files):
  original=json.loads(Path(name).read_text());live=server.urllib.request.urlopen;calls=0;started=time.monotonic()
  def replay(request,**kwargs):
   nonlocal calls
   calls+=1
   if calls==1:return io.BytesIO(json.dumps({'model':'recorded-synthetic-output','choices':[{'message':{'content':json.dumps(original['proposal'])},'finish_reason':'stop'}]}).encode())
   return live(request,**kwargs)
  row={'input':Path(name).name,'kind':'recorded failure + live targeted repair'}
  try:
   with patch('server.urllib.request.urlopen',side_effect=replay):proposal,audit=server.ai_plan(original['request'],dict(server.PROVIDER))
   packet=copy.deepcopy(original);packet.update(proposal=proposal,plan=compile_workbook(proposal,original['config']),learning_summary=proposal['learning_summary'])
   same=proposal['questions']==original['proposal']['questions'] and proposal['lesson']==original['proposal']['lesson']
   issues=review(packet);row.update(result='PASS' if same and not issues else 'REVIEW',preserved_questions_and_lesson=same,issues=issues,repair_mode=audit['attempts'][0].get('repair_mode'))
   (out/f'repaired-{index+1}.json').write_text(json.dumps({'learning_summary':proposal['learning_summary'],'batch_feedback':proposal['batch_feedback']},ensure_ascii=False,indent=2),encoding='utf-8')
  except Exception as e:row.update(result='FAIL',error=str(e))
  row.update(live_calls=max(0,calls-1),seconds=round(time.monotonic()-started,2));report.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
