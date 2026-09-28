"""Opt-in repeated paid tests on synthetic topics, with content checks, never real student data."""
import argparse,json,sys,time,re,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store,generate
from core import validate_config
CASES=[
 ('science','zh',10,'Ideal resistor circuits','Synthetic exercise: ideal DC sources and positive ohmic resistors only. V=IR. In series current is equal and resistances add. In parallel voltage is equal and reciprocals of resistance add. P=VI. Use exact arithmetic; no diagrams needed. Do not include capacitance, alternating current or temperature dependence.'),
 ('humanities','en',5,'Evidence and inference in a short passage','Fictional passage: At dawn Lin reached the locked community garden. A notice said it opened at eight. She waited on a bench with a seed packet. At eight a caretaker unlocked the gate. Lin thanked him and went inside. Teach explicit evidence versus plausible inference. Do not invent motives, backstory or events. Include any necessary passage within the printable material.'),
 ('policy','zh',10,'Fictional library rules','Fictional rules: at most 3 borrowed books. Returning frees a slot. A reservation occupies no slot until collection. Loans last 14 days. One renewal adds 7 days unless another reader reserved that book. Sunday is closed; a Sunday due date moves to Monday. Other days open. State weekday facts needed by each question; no real library claims.')]
def review(p):
 issues=[];size=p['plan']['batch_size'];zh=p['config']['language']=='zh'
 for b in p['plan']['batch_feedback']:
  g=b.get('guidance','');rows=[line.strip().strip('|').split('|') for line in g.splitlines() if '|' in line]
  if not any(len(c)==3 for c in rows):issues.append(f"group {b['batch']}: missing three-column feedback")
  for cells in rows:
   if len(cells)<3:continue
   future=[int(v) for v in re.findall(r'\bQ(\d+)',cells[0]) if int(v)>b['batch']*size]
   if future:issues.append(f"group {b['batch']}: future condition Q{future}")
  if not re.search(r'其他|otherwise|all other|remaining',g,re.I):issues.append(f"group {b['batch']}: no explicit fallback wording")
 summary=p['learning_summary']
 if not all(x in summary for x in (['情况','措施'] if zh else ['Situation','Measures'])):issues.append('summary: missing situation/measures labels')
 if re.search(r'confirmed_evaluations|student_state|independent_correct',summary):issues.append('summary: internal field names')
 return issues

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--rounds',type=int,default=1);ap.add_argument('--output',required=True);args=ap.parse_args()
 if not args.run:raise SystemExit('Use --run to authorise real paid API calls (up to two attempts per packet).')
 if not 1<=args.rounds<=3:raise SystemExit('rounds must be 1..3')
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True);reports=[]
 for repeat in range(args.rounds):
  for case,lang,size,topic,background in CASES:
   started=time.monotonic();row={'case':case,'repeat':repeat+1,'language':lang,'requested_questions':size*3}
   try:
    with tempfile.TemporaryDirectory() as d:
     s=Store(Path(d)/'test.sqlite3');s.save('students',{'id':'S-PROMPT','label':'Synthetic stability test','grade':'Secondary','diagnostic':{},'synthetic':True})
     c=validate_config({'custom_topic':True,'topic':topic,'background':background,'goal':'Explain clearly, then diagnose using varied questions and concise offline feedback.','language':lang,'batch_size':size,'batch_count':3,'max_pages':60})
     packet=generate(s,'S-PROMPT','live',c)
    issues=review(packet);row.update(structure='PASS',content_checks='PASS' if not issues else 'REVIEW',issues=issues,attempts=len(packet['audit']['attempts']),model=packet['audit']['model'],prompt=packet['audit']['prompt_version'],repairs=[a['validation'] for a in packet['audit']['attempts'][:-1]])
    # Only synthetic packet data; provider credentials are never included.
    (out/f'{repeat+1}-{case}.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
   except Exception as e:row.update(structure='FAIL',error=str(e))
   row['seconds']=round(time.monotonic()-started,2);reports.append(row)
   (out/'report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
