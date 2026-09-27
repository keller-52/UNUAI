"""Teacher-defined topics, batch worksheets and evidence summaries."""
import copy
from core import require,text,content_hash


def validate_workbook(p,state,count,batch_size=6):
    require(isinstance(p,dict),'Workbook must be a JSON object')
    for field,limit in [('title',90),('reason',700),('learning_summary',1200)]:text(p.get(field),field,limit)
    refs=p.get('evidence_refs')
    allowed={x['ref'] for x in state.get('evidence',[])}
    require(isinstance(refs,list) and all(isinstance(x,str) and x in allowed for x in refs),'Unknown evidence reference')
    require(not allowed or refs,'Reference existing evidence')
    lesson=p.get('lesson')
    require(isinstance(lesson,list) and 1<=len(lesson)<=5,'Provide 1–5 teaching sections')
    for section in lesson:
        require(isinstance(section,dict),'Invalid teaching section')
        for k,lim in [('heading',100),('text',1200),('example',800)]:text(section.get(k),k,lim)
    questions=p.get('questions')
    require(isinstance(questions,list) and len(questions)==count,f'Provide exactly {count} questions')
    for i,q in enumerate(questions,1):
        require(isinstance(q,dict) and q.get('id')==f'Q{i}',f'Question ID must be Q{i}')
        for k,lim in [('prompt',700),('skill',100),('explanation',900),('design_reason',400)]:text(q.get(k),k,lim)
        options=q.get('options')
        require(isinstance(options,list) and len(options)==4 and all(isinstance(o,dict) for o in options),'Four options required')
        require([o.get('id') for o in options]==list('ABCD'),'Options must be A B C D')
        for o in options:text(o.get('text'),'option',300)
        require(q.get('correct_option') in list('ABCD'),'Invalid answer')
        require(len(set(o['text'].strip() for o in options))==4,'Options must be distinct')
        hints=q.get('hints')
        require(isinstance(hints,list) and len(hints)==2,'Two hints required')
        for hint in hints:text(hint,'hint',350)
        require(q.get('origin') in ('ai_generated','bank_adapted'),'Invalid question origin')
        if q['origin']=='bank_adapted':text(q.get('reference_id'),'Reference ID',80)
    batches=p.get('batch_feedback')
    require(isinstance(batches,list) and len(batches)==count//batch_size,'One feedback block per batch required')
    reachable={1}
    for i,batch in enumerate(batches):
        number=i+1
        require(isinstance(batch,dict) and batch.get('batch')==number,'Invalid feedback batch')
        text(batch.get('title'),'Batch title',100)
        text(batch.get('focus'),'Batch focus',300)
        rules=batch.get('rules');require(isinstance(rules,list) and 1<=len(rules)<=batch_size+4,'Invalid feedback rules')
        coverage=[];fallback_started=False
        for rule in rules:
            require(isinstance(rule,dict),'Invalid feedback rule')
            low,high=rule.get('min_correct'),rule.get('max_correct')
            require(type(low) is int and type(high) is int and 0<=low<=high<=batch_size,'Invalid score range')
            require(rule.get('action') in ('review_then_continue','continue'),'Invalid feedback action')
            text(rule.get('feedback'),'Feedback',900)
            target=rule.get('target_batch')
            require(target=='END' or type(target) is int and number<target<=len(batches),'Target must be a later existing batch or END')
            if number in reachable and target!='END':reachable.add(target)
            wrong=rule.get('wrong_any',[])
            require(isinstance(wrong,list) and len(set(wrong))==len(wrong),'Invalid wrong-answer condition')
            valid_ids={f'Q{j}' for j in range(i*batch_size+1,(i+1)*batch_size+1)}
            require(all(isinstance(q,str) and q in valid_ids for q in wrong),'Wrong-answer condition must refer to this batch')
            if wrong:
                require(not fallback_started,'Targeted conditions must precede score fallback rules')
            else:
                fallback_started=True;coverage.extend(range(low,high+1))
        require(sorted(coverage)==list(range(batch_size+1)),'Fallback ranges must cover all scores exactly once')
    require(reachable==set(range(1,len(batches)+1)),'Every printed batch must be reachable')
    require(len({r['target_batch'] for r in batches[0]['rules']})>=2,'First batch needs at least two different destinations')
    return p


def compile_workbook(p,config):
    nodes=[]
    for i,q in enumerate(p['questions']):
        n=copy.deepcopy(q);n.update(type='choice_question',bank_id=q['id'],level='teacher_review',
            misconception_options={},routes=[{'answer':a,'next':f'Q{i+2}' if i+1<len(p['questions']) else 'END'} for a in 'ABCD'])
        nodes.append(n)
    nodes.append({'id':'END','type':'finish','text':'Return the record sheets.'})
    return {'layout':'batch-v1','title':p['title'],'unit_id':config['unit_id'],'language':config['language'],
            'topic_id':config['topic_id'],'entry_node':'Q1','lesson':copy.deepcopy(p['lesson']),'nodes':nodes,
            'routing_version':'offline-batch-1','batch_size':config['batch_size'],'batch_feedback':copy.deepcopy(p['batch_feedback']),
            'batches':[{k:b[k] for k in ('batch','title','focus')} for b in p['batch_feedback']],
            'verification':'structure_only_teacher_review_required'}


def validate_workbook_plan(plan):
    require(plan.get('verification')=='structure_only_teacher_review_required','Invalid workbook verification label')
    nodes=plan.get('nodes');require(isinstance(nodes,list) and 6<=len(nodes)<=31,'Invalid workbook size')
    questions=nodes[:-1];require(nodes[-1].get('id')=='END','Missing finish')
    fake={'title':plan['title'],'reason':'Restored packet','learning_summary':'Stored snapshot','evidence_refs':[],
          'lesson':plan['lesson'],'questions':questions,'batch_feedback':plan['batch_feedback']}
    validate_workbook(fake,{'evidence':[]},len(questions),plan['batch_size'])
    for i,n in enumerate(questions):
        expected=f'Q{i+2}' if i+1<len(questions) else 'END'
        require(n.get('routes')==[{'answer':a,'next':expected} for a in 'ABCD'],'Invalid batch sequence')
    return True


def evaluate_workbook(package,trace):
    require(isinstance(trace,dict) and trace.get('confirmed') is True,'Confirm the record')
    require(trace.get('package_id')==package['id'] and trace.get('package_version')==package['version'],'Package mismatch')
    require(trace.get('source') in ('manual','scan','synthetic'),'Invalid trace source')
    nodes=package['plan']['nodes'];rows=trace.get('rows')
    require(isinstance(rows,list) and len(rows)==len(nodes) and all(isinstance(r,dict) for r in rows),'Record every task row')
    lookup={r.get('task_id'):r for r in rows}
    require(set(lookup)=={n['id'] for n in nodes},'Task IDs mismatch')
    results=[]
    require(all(lookup['END'].get(k) is None for k in ('first_answer','retry_answer','hint_level')),'END has no answer fields')
    for n in nodes[:-1]:
        r=lookup[n['id']];first=r.get('first_answer');retry=r.get('retry_answer');hint=r.get('hint_level')
        require(first is None or first in list('ABCD'),'Invalid answer')
        require(retry is None or retry in list('ABCD'),'Invalid retry')
        require(hint is None or type(hint) is int and hint in (0,1,2),'Invalid hint')
        results.append({'task_id':n['id'],'bank_id':n['bank_id'],'first_answer':first,
            'first_correct':None if first is None else first==n['correct_option'],
            'retry_correct':None if retry is None else retry==n['correct_option'],'hint_level':hint,
            'completion':'completed' if first else 'missing_or_unreadable','misconception':None})
    require(any(r['first_answer'] for r in results),'Enter at least one answer')
    # Reconstruct the prescribed branch only from complete first-answer batches.
    # Blank rows are not automatically errors: a paper branch can skip a whole group.
    by_id={r['task_id']:r for r in results};batch_path=[];current=1;route_complete=False
    size=package['plan']['batch_size'];feedback=package['plan']['batch_feedback']
    while current!='END':
        batch_path.append(current)
        group=[by_id[f'Q{i}'] for i in range((current-1)*size+1,current*size+1)]
        if any(r['first_correct'] is None for r in group):break
        score=sum(r['first_correct'] for r in group)
        wrong={r['task_id'] for r in group if not r['first_correct']}
        rule=next(r for r in feedback[current-1]['rules'] if r['min_correct']<=score<=r['max_correct'] and (not r.get('wrong_any') or wrong.intersection(r['wrong_any'])))
        current=rule['target_batch']
    if current=='END':route_complete=True
    warnings=[]
    for index,r in enumerate(results):
        if index//size+1 not in batch_path:
            if r['first_answer']:warnings.append(r['task_id']+': answered outside the reconstructable prescribed route')
            elif route_complete:r['completion']='not_assigned_by_route'
    eligible=[r for r in results if r['first_correct'] is not None];independent=[r for r in eligible if r['hint_level']==0]
    return {'package_id':package['id'],'topic_id':package['config']['topic_id'],'source':trace['source'],
            'path':[r['task_id'] for r in results if r['first_answer']], 'results':results,'warnings':warnings,'prescribed_batch_path':batch_path,'route_complete':route_complete,
            'first_correct':sum(r['first_correct'] for r in eligible),'first_total':len(eligible),
            'independent_correct':sum(r['first_correct'] for r in independent),'independent_total':len(independent),
            'note':'Descriptive only. Topic answers require teacher review; prescribed route is reconstructed from first answers, not observed visit order.'}


def validate_summary(p,state):
    require(isinstance(p,dict),'Summary must be JSON')
    text(p.get('summary'),'summary',1600)
    for field in ('strengths','needs','next_steps'):
        require(isinstance(p.get(field),list) and len(p[field])<=5,'Invalid summary list')
        for item in p[field]:text(item,field,400)
    refs=p.get('evidence_refs');allowed={e['ref'] for e in state.get('evidence',[])}
    require(isinstance(refs,list) and all(isinstance(r,str) and r in allowed for r in refs),'Invalid summary evidence')
    require(not allowed or refs,'Cite summary evidence')


def topic_state(student,evaluations,config):
    from core import state_for
    learner=copy.deepcopy(student);learner['diagnostic']={}
    state=state_for(learner,evaluations)
    state.update(unit_id=config['topic_id'],topic=config['topic'],status='observations_available' if state['evidence'] else 'unknown',hypotheses=[],review_required=False,
                 note='Descriptive topic-specific evidence only; no fixed-subject readiness heuristic or established mastery.')
    return state
