"""Teaching contracts, audited arithmetic bank, paper graph and trace evaluation.

All catalog content is author-created demonstration material. No third-party bank.
"""
import copy
import hashlib
import json
import re

VERSION = "0.1.0"
PROMPT_VERSION = "paper-planner-1"
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


BANK = {q["id"]: q for q in [
    make_question("D01", 1, 2, 6, "foundation"),
    make_question("D02", 1, -3, 4, "foundation"),
    make_question("D03", 2, 4, 12, "transfer"),
    make_question("F01", 1, 3, 7, "foundation"),
    make_question("F02", 1, 5, 12, "foundation"),
    make_question("F03", 1, -4, 5, "foundation"),
    make_question("F04", 1, 6, 15, "foundation"),
    make_question("F05", 1, -7, 3, "foundation"),
    make_question("F06", 1, 8, 11, "foundation"),
    make_question("T01", 2, 6, 16, "transfer"),
    make_question("T02", 3, -6, 15, "transfer"),
    make_question("T03", 2, -4, 10, "transfer"),
    make_question("T04", 3, 9, 24, "transfer"),
    make_question("T05", 4, -8, 12, "transfer"),
    make_question("T06", 2, 10, 6, "transfer"),
]}


def public_question(q):
    return {k: copy.deepcopy(q[k]) for k in ("id", "skill", "level", "prompt", "options", "hints")}


def diagnostic_score(answers):
    require(isinstance(answers, dict), "diagnostic must be an object")
    require(not (set(answers) - {"D01", "D02", "D03"}), "Unknown diagnostic task")
    observations = []
    for qid in ("D01", "D02", "D03"):
        value = answers.get(qid)
        require(value is None or value in ("A", "B", "C", "D"), "Invalid diagnostic answer")
        if value is not None:
            observations.append({"task_id": qid, "answer": value,
                                 "correct": value == BANK[qid]["correct_option"],
                                 "misconception": BANK[qid]["misconception_options"].get(value)})
    return observations


def state_for(student, evaluations):
    diag = diagnostic_score(student.get("diagnostic", {}))
    evidence = [{"ref": f"diagnostic:{r['task_id']}", **r} for r in diag]
    for evaluation in evaluations:
        for result in evaluation["results"]:
            if result["first_correct"] is not None:
                evidence.append({"ref": f"{evaluation['package_id']}:{result['task_id']}",
                                 "correct": result["first_correct"],
                                 "independent": result["hint_level"] == 0,
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
        ready = len(diag) == 3 and all(r["correct"] for r in diag)
    return {
        "version": len(evaluations) + 1,
        "status": "ready_for_transfer_check" if ready else ("needs_support_check" if total else "unknown"),
        "recent_correct": correct, "recent_total": total,
        "hypotheses": ([{"label": "sign_change", "status": "needs_verification",
                         "evidence_refs": [r["ref"] for r in recent if r.get("misconception") == "sign_change"]}]
                       if any(r.get("misconception") == "sign_change" for r in recent) else []),
        "evidence": evidence,
        "note": "Demonstration heuristic, not a validated mastery score. Prompt use is self-reported.",
    }


def demo_proposal(state, used_ids):
    level = "transfer" if state["status"] == "ready_for_transfer_check" else "foundation"
    choices = [q["id"] for q in BANK.values() if q["level"] == level and not q["id"].startswith("D")]
    fresh = [q for q in choices if q not in used_ids]
    selected = (fresh + [q for q in choices if q in used_ids])[:3]
    return {
        "title": "Independent transfer check" if level == "transfer" else "Keeping equations balanced",
        "question_ids": selected,
        "reason": ("Recent answers support checking transfer with new coefficient equations."
                   if level == "transfer" else "Gather more independent evidence and practise inverse operations before progressing."),
        "coach_notes": ["Apply the same operation to both sides. Check your result in the original equation."] * 2,
        "evidence_refs": [r["ref"] for r in state["evidence"][-6:]],
    }


def validate_proposal(proposal, state):
    require(isinstance(proposal, dict), "AI response must be a JSON object")
    text(proposal.get("title"), "title", 90)
    text(proposal.get("reason"), "reason", 700)
    ids = proposal.get("question_ids")
    require(isinstance(ids, list) and len(ids) == 3 and all(isinstance(x, str) for x in ids),
            "question_ids must contain exactly 3 strings")
    require(len(set(ids)) == 3, "Select 3 distinct questions")
    require(all(x in BANK and not x.startswith("D") for x in ids), "Unknown or diagnostic-only question selected")
    notes = proposal.get("coach_notes")
    require(isinstance(notes, list) and len(notes) == 2, "Two coach_notes required")
    for note in notes:
        text(note, "coach note", 450)
    refs = proposal.get("evidence_refs")
    allowed = {r["ref"] for r in state["evidence"]}
    require(isinstance(refs, list) and all(isinstance(x, str) and x in allowed for x in refs), "Unknown evidence reference")
    require(not allowed or len(refs) > 0, "Reference at least one observed item")
    return copy.deepcopy(proposal)


def compile_plan(proposal):
    nodes = []
    for i, qid in enumerate(proposal["question_ids"], 1):
        q = copy.deepcopy(BANK[qid])
        node = {**q, "id": f"Q{i}", "bank_id": qid, "type": "choice_question"}
        next_node = f"Q{i+1}" if i < 3 else "END"
        node["routes"] = [{"answer": o["id"], "next": next_node if o["id"] == q["correct_option"] or i == 3 else f"R{i}"}
                          for o in q["options"]]
        nodes.append(node)
        if i < 3:
            nodes.append({"id": f"R{i}", "type": "explanation", "text": q["explanation"],
                          "coach_note": proposal["coach_notes"][i-1], "next": next_node})
    nodes.append({"id": "END", "type": "finish", "text": "Check your record sheet and return it to your teacher."})
    plan = {"title": proposal["title"], "entry_node": "Q1", "nodes": nodes}
    validate_plan(plan)
    return plan


def validate_plan(plan):
    require(isinstance(plan, dict), "Plan must be an object")
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
            require(n.get("bank_id") in BANK, "Unverified question source")
            original = BANK[n["bank_id"]]
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
    result["plan"] = copy.deepcopy(package["plan"])
    for n in result["plan"]["nodes"]:
        for secret in ("correct_option", "misconception_options", "equation"):
            n.pop(secret, None)
        if n["type"] == "choice_question":
            n.pop("explanation", None)
    # Remedial explanations intentionally reveal worked solutions, as teaching content.
    return result


def evaluate_trace(package, trace):
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
    days, pages = config.get("offline_days", 3), config.get("max_pages", 6)
    require(type(days) is int and 1 <= days <= 14, "Offline interval must be 1–14 days")
    require(type(pages) is int and 3 <= pages <= 12, "Booklet page budget must be 3–12")
    return {"offline_days": days, "max_pages": pages, "language": "en", "print_mode": "black_white",
            "goal": text(config.get("goal", "Use inverse operations to solve linear equations."), "Goal", 400)}
