"""Opt-in single real custom-workbook generation; synthetic data only."""
import argparse,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store,generate
from core import validate_config

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--language',choices=['en','zh'],default='zh');p.add_argument('--size',type=int,default=10);p.add_argument('--output',default='test-results/live-05');args=p.parse_args()
 if not args.run:raise SystemExit('Pass --run for one paid generation (up to two model attempts).')
 with tempfile.TemporaryDirectory() as folder:
  s=Store(Path(folder)/'test.sqlite3');s.save('students',{'id':'S-LIVE-05','label':'Synthetic test','grade':'Secondary','diagnostic':{},'synthetic':True})
  config=validate_config({'custom_topic':True,'topic':'Synthetic library policy reasoning','background':'Fictional test rules only: maximum 3 borrowed books; loan duration 14 days. Returns free slots. Reservations do not use a slot until collected. Renewal adds 7 days unless another reader reserved the book. Sunday is closed; a Sunday due date moves to Monday. All other days are open. No real library policy claims.','goal':'Explain the rules, generate differentiated groups and freely design offline feedback using Markdown.','language':args.language,'batch_size':args.size,'batch_count':3,'max_pages':60})
  packet=generate(s,'S-LIVE-05','live',config)
  out=Path(args.output);out.mkdir(parents=True,exist_ok=True);(out/'synthetic-package.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
  report={'model':packet['audit']['model'],'seconds':packet['audit']['elapsed_seconds'],'attempts':len(packet['audit']['attempts']),'questions':len(packet['proposal']['questions']),'routing':packet['plan']['routing_version'],'language':args.language,'record_pages':len(packet['record_sheets'])}
  (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
