"""Teaching contracts, audited arithmetic bank, paper graph and trace evaluation.

Reference catalog is author-created. Live proposals may also contain AI-authored questions.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

VERSION = "0.5.0"
PROMPT_VERSION = "paper-author-2"
MAX_NODES = 8


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def text(value, label, maximum=500):
    require(isinstance(value, str) and 0 < len(value.strip()) <= maximum,
            f"{label}: expected 1–{maximum} characters")
    return value.strip()


def make_question(key, a, b, c, level):
    # Equation a*x + b = c; all selected catalog equations have integer solutions.
    require(a != 0 and (c - b) % a == 0, "Invalid catalog equation")
    answer = (c - b) // a
    wrong = (c + b) // a if (c + b) % a == 0 else answer + 2
    if wrong == answer:
        wrong = answer + 2
    other = answer - 1
    while other in (answer, wrong):
        other -= 1
    values = [answer, wrong, other]
    # Rotate correct choices to prevent a trivial 'always A' workbook.
    shift = sum(map(ord, key)) % 3
    values = values[shift:] + values[:shift]
    left = "x" if a == 1 else f"{a}x"
    left += f" + {b}" if b >= 0 else f" - {-b}"
    return {
        "id": key, "skill": "inverse_operations", "level": level,
        "equation": {"a": a, "b": b, "c": c},
        "prompt": f"Solve {left} = {c}.",
        "options": [{"id": chr(65+i), "text": f"x = {v}"} for i, v in enumerate(values)]
                   + [{"id": "D", "text": "Another answer / not sure"}],
        "correct_option": chr(65+values.index(answer)),
        "misconception_options": {chr(65+values.index(wrong)): "sign_change"},
        "hints": ["Keep the equation balanced: apply the same operation to both sides.",
                  f"Subtract ({b}) from both sides, then divide both sides by {a}."],
        "explanation": f"Subtract ({b}) from both sides: {a}x = {c-b}. "
                       f"Divide by {a}: x = {answer}. Check: {a} × ({answer}) + ({b}) = {c}.",
        "source": "PAPER AI author-created demonstration bank",
    }


def load_units():
    units = {}
    for path in sorted((Path(__file__).parent / "units").glob("*.json")):
        unit = json.loads(path.read_text(encoding="utf-8"))
        require(unit.get("schema_version") == "1.0", "Unsupported unit schema")
        require(unit.get("verification") == "linear_integer_equation", "Unit requires a registered verification adapter")
        require(unit["id"] not in units, "Duplicate unit ID")
        bank = {q["id"]: q for q in unit["questions"]}
        require(len(bank) == len(unit["questions"]), "Duplicate question ID")
        require(all(k in bank for k in unit["diagnostic_ids"]), "Invalid diagnostic IDs")
        for q in bank.values():
            equation = q["equation"]
            expected = make_question(q["id"], equation["a"], equation["b"], equation["c"], q["level"])
            for key in ("options", "correct_option", "misconception_options"):
                require(q[key] == expected[key], "Question verification failed")
            require(set(q.get("translations", {})) >= set(unit["languages"]) - {"en"}, "Missing question translation")
        unit["bank"] = bank
        units[unit["id"]] = unit
    return units


UNITS = load_units()
DEFAULT_UNIT = "linear-equations"
BANK = UNITS[DEFAULT_UNIT]["bank"]


def unit_bank(unit_id=DEFAULT_UNIT):
    require(unit_id in UNITS, "Unknown knowledge unit")
    return UNITS[unit_id]["bank"]


def localized_question(q, language="en"):
    result = copy.deepcopy(q)
    result.update(result.pop("translations", {}).get(language, {}))
    return result


def public_question(q):
    return {k: copy.deepcopy(q[k]) for k in ("id", "skill", "level", "prompt", "options", "hints")}


def diagnostic_score(answers, unit_id=DEFAULT_UNIT):
    bank = unit_bank(unit_id)
    diagnostic_ids = UNITS[unit_id]["diagnostic_ids"]
    require(isinstance(answers, dict), "diagnostic must be an object")
    require(not (set(answers) - set(diagnostic_ids)), "Unknown diagnostic task")
    observations = []
    for qid in diagnostic_ids:
        value = answers.get(qid)
        require(value is None or value in ("A", "B", "C", "D"), "Invalid diagnostic answer")
        if value is not None:
            observations.append({"task_id": qid, "answer": value,
                                 "correct": value == bank[qid]["correct_option"],
                                 "misconception": bank[qid]["misconception_options"].get(value)})
    return observations


def state_for(student, evaluations):
    unit_id = student.get("unit_id", DEFAULT_UNIT)
    diag = diagnostic_score(student.get("diagnostic", {}), unit_id)
    evidence = [{"ref": f"diagnostic:{r['task_id']}", **r} for r in diag]
    for evaluation in evaluations:
        for result in evaluation["results"]:
            if result["first_correct"] is not None:
                evidence.append({"ref": f"{evaluation['package_id']}:{result['task_id']}",
                                 "correct": result["first_correct"],
                                 "independent": None if result["hint_level"] is None else result["hint_level"] == 0,
                                 "misconception": result.get("misconception")})
    recent = evidence[-6:]
    correct = sum(r["correct"] for r in recent)
    total = len(recent)
    if evaluations:
        latest = evaluations[-1]
        eligible = [r for r in latest["results"] if r["first_correct"] is not None]
        ready = (len(eligible) == len(latest["results"]) >= 2 and not latest["warnings"]
                 and all(r["first_correct"] and r["hint_level"] == 0 for r in eligible))
    else:
        ready = len(diag) == len(UNITS[unit_id]["diagnostic_ids"]) and all(r["correct"] for r in diag)
    return {
        "unit_id": unit_id,
        "version": len(evaluations) + 1,
        "independent_correct": sum(r.get("independent") is True and r["correct"] for r in recent),
        "supported_correct": sum(r.get("independent") is False and r["correct"] for r in recent),
        "evidence_quality": "insufficient" if total < 3 else "observations_available",
        "review_required": bool(evaluations) and len(evaluations) % 3 == 0,
        "mastery": "not_established",
        "status": "ready_for_transfer_check" if ready else ("needs_support_check" if total else "unknown"),
        "recent_correct": correct, "recent_total": total,
        "recent_window_size": 6,
        "metric_scope": "recent_correct, recent_total, independent_correct and supported_correct use only the last six observed answers; confirmed_evaluations contains complete round totals",
        "hypotheses": ([{"label": "sign_change", "status": "needs_verification",
                         "evidence_refs": [r["ref"] for r in recent if r.get("misconception") == "sign_change"]}]
                       if any(r.get("misconception") == "sign_change" for r in recent) else []),
        "evidence": evidence,
        "note": "Demonstration heuristic, not a validated mastery score. Prompt use is self-reported.",
    }


def demo_proposal(state, used_ids, count=3, language="en"):
    bank = unit_bank(state.get("unit_id", DEFAULT_UNIT))
    level = "transfer" if state["status"] == "ready_for_transfer_check" else "foundation"
    choices = [q["id"] for q in bank.values() if q["level"] == level and not q["id"].startswith("D")]
    fresh = [q for q in choices if q not in used_ids]
    review = [q for q in choices if q in used_ids][-1:] if state.get("review_required") else []
    selected = (review + [q for q in fresh + choices if q not in review])
    selected = list(dict.fromkeys(selected))[:count]
    proposal = {
        "title": "Independent transfer check" if level == "transfer" else "Keeping equations balanced",
        "question_ids": selected,
        "reason": ("Recent answers support checking transfer with new coefficient equations."
                   if level == "transfer" else "Gather more independent evidence and practise inverse operations before progressing."),
        "coach_notes": ["Apply the same operation to both sides. Check your result in the original equation."] * (count-1),
        "evidence_refs": [r["ref"] for r in state["evidence"][-6:]],
    }

    if language == "zh":
        proposal.update(title="独立迁移检查" if level == "transfer" else "保持等式平衡",
                        reason="根据已有记录安排独立检查；需要时使用提示，并保留首次答案。",
                        coach_notes=["等式两边进行相同运算，再将结果代回原方程检验。"] * (count-1))
    return proposal


def validate_generated_question(raw):
    require(isinstance(raw, dict), "Generated question must be an object")
    q = copy.deepcopy(raw)
    require(isinstance(q.get("id"), str) and re.fullmatch(r"N[1-9][0-9]*", q["id"]), "Generated IDs must be N1, N2, ...")
    require(q.get("skill") == "inverse_operations", "Unsupported generated skill")
    require(q.get("level") in ("foundation", "transfer"), "Invalid generated level")
    eq = q.get("equation")
    require(isinstance(eq, dict) and set(eq) == {"a", "b", "c"}, "Equation must contain a,b,c")
    require(all(type(eq[k]) is int and abs(eq[k]) <= 1000 for k in eq), "Equation coefficients must be bounded integers")
    a,b,c = (eq[k] for k in ("a","b","c"))
    require(a != 0 and (c-b) % a == 0 and abs((c-b)//a) <= 1000, "Equation needs one bounded integer solution")
    template = text(q.get("prompt_template"), "prompt_template", 240)
    require(template.count("{equation}") == 1, "Include {equation} exactly once")
    left = "x" if a == 1 else f"{a}x"
    left += f" + {b}" if b >= 0 else f" - {-b}"
    q["prompt"] = template.replace("{equation}", f"{left} = {c}")
    options = q.get("options")
    require(isinstance(options,list) and len(options)==4 and all(isinstance(o,dict) for o in options), "Four generated options required")
    require([o.get("id") for o in options] == ["A","B","C","D"], "Options must be ordered A,B,C,D")
    values = {}
    for o in options[:3]:
        if "value" in o:
            require(type(o["value"]) is int and abs(o["value"]) <= 10000, f"{q['id']}:{o['id']} numeric value must be an integer")
            values[o["id"]] = o["value"]
            canonical = f"x = {o['value']}"
            require("text" not in o or o["text"] == canonical, "Option text/value mismatch")
            o["text"] = canonical
        else:
            value = text(o.get("text"), "Numeric option", 40)
            normalized=value.replace("−","-").replace("＝","=")
            match = re.fullmatch(r"x\s*=\s*([+-]?[0-9]+)", normalized)
            require(match is not None, f"{q['id']}:{o['id']} provide numeric value as an integer, not formatted prose")
            values[o["id"]] = int(match[1])
    text(options[3].get("text"), "D option", 100)
    require(len(set(values.values()))==3, "Numeric options must be distinct")
    correct = [key for key,value in values.items() if a*value+b==c]
    require(len(correct)==1 and q.get("correct_option")==correct[0], "Generated answer does not solve equation uniquely")
    mistakes = q.get("misconception_options", {})
    require(isinstance(mistakes,dict), "Invalid misconception map")
    for key,label in mistakes.items():
        require(key in values and key != correct[0] and label == "sign_change" and a*values[key]==c+b,
                f"Generated {q['id']} option {key}: sign_change requires a*option_value=c+b ({c+b}); remove this entry from misconception_options or fix the distractor. Use {{}} if uncertain.")
    hints=q.get("hints")
    require(isinstance(hints,list) and len(hints)==2, "Exactly two generated hints required")
    for hint in hints:text(hint,"Hint",240)
    text(q.get("explanation"),"Explanation",900)
    text(q.get("design_reason"),"Question design reason",400)
    q["misconception_options"]=mistakes
    q["origin"]="ai_generated"
    q["source"]="AI-authored; arithmetic verified; teaching prose requires teacher review"
    return {key:q[key] for key in ("id","skill","level","equation","prompt_template","prompt","options","correct_option","misconception_options","hints","explanation","design_reason","origin","source")}


def proposal_questions(proposal, unit_id=DEFAULT_UNIT, language="en"):
    bank=unit_bank(unit_id)
    raw=proposal.get("generated_questions",[])
    require(isinstance(raw,list) and len(raw)<=4, "generated_questions must be an array of at most four items")
    generated={}
    for item in raw:
        q=validate_generated_question(item)
        require(q["id"] not in generated and q["id"] not in bank, "Duplicate generated ID")
        generated[q["id"]]=q
    ids=proposal.get("question_ids",[])
    require(all(k in ids for k in generated), "Unused generated question")
    result=[]
    for key in ids:
        if key in generated:result.append(generated[key])
        else:
            require(key in bank and key not in UNITS[unit_id]["diagnostic_ids"], "Unknown or diagnostic-only question selected")
            q=localized_question(bank[key],language);q["origin"]="bank";result.append(q)
    require(len({tuple(q["equation"][k] for k in ("a","b","c")) for q in result})==len(result), "Duplicate equation in this packet")
    return result


def validate_proposal(proposal, state, count=3):
    bank = unit_bank(state.get("unit_id", DEFAULT_UNIT))
    require(isinstance(proposal, dict), "AI response must be a JSON object")
    text(proposal.get("title"), "title", 90)
    text(proposal.get("reason"), "reason", 700)
    ids = proposal.get("question_ids")
    require(isinstance(ids, list) and len(ids) == count and all(isinstance(x, str) for x in ids),
            f"question_ids must contain exactly {count} strings")
    require(len(set(ids)) == count, "Select distinct questions")
    proposal_questions(proposal, state.get("unit_id", DEFAULT_UNIT))
    notes = proposal.get("coach_notes")
    require(isinstance(notes, list) and len(notes) == count-1, f"{count-1} coach_notes required")
    for note in notes:
        text(note, "coach note", 450)
    refs = proposal.get("evidence_refs")
    allowed = {r["ref"] for r in state["evidence"]}
    require(isinstance(refs, list) and all(isinstance(x, str) and x in allowed for x in refs), "Unknown evidence reference")
    require(not allowed or len(refs) > 0, "Reference at least one observed item")
    return copy.deepcopy(proposal)


def compile_plan(proposal, config=None):
    config = config or {}
    language = config.get("language", "en")
    unit_id = config.get("unit_id", DEFAULT_UNIT)
    bank = unit_bank(unit_id)
    count = len(proposal["question_ids"])
    nodes = []
    for i, q in enumerate(proposal_questions(proposal, unit_id, language), 1):
        qid = q["id"]
        node = {**q, "id": f"Q{i}", "bank_id": qid, "type": "choice_question"}
        next_node = f"Q{i+1}" if i < count else "END"
        node["routes"] = [{"answer": o["id"], "next": next_node if o["id"] == q["correct_option"] or i == count else f"R{i}"}
                          for o in q["options"]]
        nodes.append(node)
        if i < count:
            nodes.append({"id": f"R{i}", "type": "explanation", "text": q["explanation"],
                          "coach_note": proposal["coach_notes"][i-1], "next": next_node})
    nodes.append({"id": "END", "type": "finish", "text": "检查记录纸并交给教师。" if language == "zh" else "Check your record sheet and return it to your teacher."})
    plan = {"unit_id": unit_id, "language": language, "title": proposal["title"], "entry_node": "Q1", "nodes": nodes}
    validate_plan(plan)
    return plan


def validate_plan(plan):
    if isinstance(plan,dict) and plan.get("layout")=="batch-v1":
        from workbook import validate_workbook_plan
        return validate_workbook_plan(plan)
    require(isinstance(plan, dict), "Plan must be an object")
    bank = unit_bank(plan.get("unit_id", DEFAULT_UNIT))
    nodes = plan.get("nodes")
    require(isinstance(nodes, list) and 1 <= len(nodes) <= MAX_NODES, "Invalid node count")
    require(all(isinstance(n, dict) and isinstance(n.get("id"), str) for n in nodes), "Invalid nodes")
    lookup = {n["id"]: n for n in nodes}
    require(len(lookup) == len(nodes), "Duplicate node id")
    require(plan.get("entry_node") in lookup, "Unknown entry node")
    edges = {}
    for n in nodes:
        kind = n.get("type")
        require(kind in ("choice_question", "explanation", "finish"), "Unsupported node type")
        if kind == "choice_question":
            if n.get("origin") == "ai_generated":
                raw=copy.deepcopy(n);raw["id"]=n.get("bank_id")
                original=validate_generated_question(raw)
            else:
                require(n.get("bank_id") in bank, "Unverified question source")
                original = localized_question(bank[n["bank_id"]], plan.get("language", "en"))
            for k in ("prompt", "options", "correct_option", "equation", "hints"):
                require(n.get(k) == original[k], f"Question content mismatch: {n['id']}.{k}")
            routes = n.get("routes", [])
            require(len(routes) == 4 and {r.get("answer") for r in routes} == {"A", "B", "C", "D"}, "Incomplete routes")
            edges[n["id"]] = [r.get("next") for r in routes]
        elif kind == "explanation":
            text(n.get("text"), "Explanation", 900)
            text(n.get("coach_note"), "Coach note", 450)
            edges[n["id"]] = [n.get("next")]
        else:
            require("next" not in n and "routes" not in n, "Finish cannot have successors")
            edges[n["id"]] = []
    seen, active = set(), set()
    def visit(key):
        require(key in lookup, f"Unknown route target: {key}")
        require(key not in active, "Teaching graph contains a cycle")
        if key in seen:
            return
        active.add(key)
        for target in edges[key]:
            visit(target)
        active.remove(key)
        seen.add(key)
    visit(plan["entry_node"])
    require(seen == set(lookup), "Unreachable node")
    require(any(n["type"] == "finish" for n in nodes), "Missing finish node")
    return True


def public_package(package):
    result = {k: copy.deepcopy(package[k]) for k in
              ("id", "student_id", "round", "version", "status", "sheet_code", "mode", "created_at", "config")}
    result["record_sheets"] = copy.deepcopy(package.get("record_sheets",[]))
    result["schedule"] = copy.deepcopy(package.get("schedule", []))
    result["plan"] = copy.deepcopy(package["plan"])
    for n in result["plan"]["nodes"]:
        for secret in ("correct_option", "misconception_options", "equation", "design_reason", "prompt_template"):
            n.pop(secret, None)
        if n["type"] == "choice_question":
            n.pop("explanation", None)
    if result["plan"].get("layout")=="batch-v1":
        for n in result["plan"]["nodes"]:n.pop("hints",None)
        result["plan"].pop("batch_feedback",None)
    # Remedial explanations intentionally reveal worked solutions, as teaching content.
    return result


def evaluate_trace(package, trace):
    if package["plan"].get("layout")=="batch-v1":
        from workbook import evaluate_workbook
        return evaluate_workbook(package,trace)
    require(isinstance(trace, dict), "Trace must be an object")
    require(trace.get("package_id") == package["id"] and trace.get("package_version") == package["version"],
            "Package/version mismatch")
    require(trace.get("confirmed") is True, "Teacher confirmation required")
    require(trace.get("source") in ("manual", "scan", "synthetic"), "Unknown trace source")
    rows = trace.get("rows")
    nodes = {n["id"]: n for n in package["plan"]["nodes"]}
    require(isinstance(rows, list) and len(rows) == len(nodes), "One row per printed node required")
    require(all(isinstance(r, dict) and isinstance(r.get("task_id"), str) for r in rows), "Invalid trace rows")
    require({r["task_id"] for r in rows} == set(nodes), "Trace node mismatch")
    orders = []
    results = []
    for r in rows:
        order = r.get("order")
        require(order is None or type(order) is int and 1 <= order <= MAX_NODES, "Visit order outside range")
        for key in ("first_answer", "retry_answer"):
            require(r.get(key) is None or r[key] in ("A", "B", "C", "D"), "Invalid answer")
        hint = r.get("hint_level")
        require(hint is None or type(hint) is int and hint in (0, 1, 2), "Invalid hint level")
        require(order is not None or all(r.get(k) is None for k in ("first_answer", "retry_answer", "hint_level")),
                "Unvisited row has answers: correct the visit order")
        if order is not None:
            orders.append((order, r["task_id"]))
        n = nodes[r["task_id"]]
        if n["type"] != "choice_question":
            require(all(r.get(k) is None for k in ("first_answer", "retry_answer", "hint_level")), "Non-question row has answers")
        else:
            first = r.get("first_answer")
            retry = r.get("retry_answer")
            results.append({"task_id": n["id"], "bank_id": n["bank_id"],
                            "first_answer": first, "first_correct": (first == n["correct_option"]) if first else None,
                            "retry_correct": (retry == n["correct_option"]) if retry else None,
                            "hint_level": hint,
                            "completion": "not_visited" if order is None else ("completed" if first else "missing_or_unreadable"),
                            "misconception": n["misconception_options"].get(first)})
    require(len({o for o, _ in orders}) == len(orders), "Duplicate visit order")
    require(len(orders) > 0, "Record at least one visited node")
    orders.sort()
    path = [key for _, key in orders]
    warnings = []
    if [o for o, _ in orders] != list(range(1, len(orders)+1)):
        warnings.append("Visit numbers contain gaps; the recorded sequence is preserved.")
    if path[0] != package["plan"]["entry_node"]:
        warnings.append("Recorded path does not start at the entry node.")
    lookup_rows = {r["task_id"]: r for r in rows}
    for a, b in zip(path, path[1:]):
        n = nodes[a]
        if n["type"] == "choice_question":
            answer = lookup_rows[a].get("first_answer")
            expected = next((r["next"] for r in n["routes"] if r["answer"] == answer), None)
        else:
            expected = n.get("next")
        if expected != b:
            warnings.append(f"{a} → {b}: differs from the first-answer route, or the answer is unknown.")
    if nodes[path[-1]]["type"] != "finish":
        warnings.append("No finish node was recorded.")
    eligible = [r for r in results if r["first_correct"] is not None]
    independent = [r for r in eligible if r["hint_level"] == 0]
    return {
        "package_id": package["id"], "source": trace["source"], "path": path,
        "results": results, "warnings": warnings,
        "first_correct": sum(r["first_correct"] for r in eligible), "first_total": len(eligible),
        "independent_correct": sum(r["first_correct"] for r in independent),
        "independent_total": len(independent),
        "note": "Descriptive observations only; no claim of learning gain or stable mastery.",
    }


def content_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_config(config):
    require(isinstance(config, dict), "Teaching config must be an object")
    if config.get("custom_topic"):
        topic=text(config.get("topic"),"Topic",160)
        background=text(config.get("background"),"Topic background",12000)
        language=config.get("language","en")
        require(language in ("en","zh"),"Unsupported language")
        size=config.get("batch_size",10);batches=config.get("batch_count",3)
        require(type(size) is int and 5<=size<=10,"Each batch needs 5–10 questions")
        require(type(batches) is int and 2<=batches<=3,"Choose 2–3 batches for offline branching")
        days=config.get("offline_days",3);pages=config.get("max_pages",30)
        require(type(days) is int and 1<=days<=14,"Invalid offline interval")
        require(type(pages) is int and 6<=pages<=60,"Choose a 6–60 page budget")
        return {"custom_topic":True,"unit_id":DEFAULT_UNIT,"topic":topic,"background":background,
                "topic_id":content_hash({"topic":topic,"background":background})[:16],
                "question_count":size*batches,"batch_size":size,"batch_count":batches,
                "language":language,"offline_days":days,"max_pages":pages,"print_mode":"black_white",
                "include_reference_bank":config.get("include_reference_bank") is True,
                "goal":text(config.get("goal") or topic,"Goal",700)}
    days, pages = config.get("offline_days", 3), config.get("max_pages", 6)
    count = config.get("question_count", 3)
    unit_id = config.get("unit_id", DEFAULT_UNIT)
    unit_bank(unit_id)
    language = config.get("language", "en")
    require(language in UNITS[unit_id]["languages"], "Unsupported language")
    require(type(count) is int and 2 <= count <= 4, "Question count must be 2–4")
    require(type(days) is int and 1 <= days <= 14, "Offline interval must be 1–14 days")
    require(type(pages) is int and count <= pages <= 12, "Page budget must cover each question (up to 12 pages)")
    return {"offline_days": days, "max_pages": pages, "unit_id": unit_id, "question_count": count, "language": language, "print_mode": "black_white",
            "goal": text(config.get("goal", "Use inverse operations to solve linear equations."), "Goal", 400)}

