#!/usr/bin/env python3
"""Local, single-teacher PAPER AI prototype. Python 3.10+, no pip dependencies."""
import argparse
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from providers import PRESETS,validate_provider,build_request,response_content,parse_json_content
from workbook import validate_workbook, compile_workbook, validate_summary, topic_state

from core import (BANK, VERSION, PROMPT_VERSION, ValidationError, require, text,
                  public_question, public_package, diagnostic_score, state_for,
                  demo_proposal, validate_proposal, compile_plan, evaluate_trace,
                  content_hash, validate_config, UNITS, DEFAULT_UNIT, localized_question, unit_bank, validate_plan)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
LOCK = threading.RLock()
def load_provider(path=None):
    """Environment overrides ignored local JSON; never expose the key in responses."""
    path = Path(path) if path else ROOT / "data" / "provider.json"
    settings = {}
    if path.exists():
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            raise ValidationError("Cannot read provider.json; check JSON syntax") from None
        require(isinstance(settings, dict), "Provider config must be an object")
    provider = {}
    defaults = {"base_url": "https://api.deepseek.com", "model": "deepseek-flash", "api_key": "", "provider":"deepseek", "protocol":"chat", "json_mode":"auto"}
    for key, default in defaults.items():
        value = os.environ.get("PAPER_AI_" + key.upper(), settings.get(key, default))
        require(isinstance(value, str), "Provider fields must be strings")
        provider[key] = value.strip()
    parsed = urlsplit(provider["base_url"])
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment, "Use an HTTPS provider URL without credentials")
    return validate_provider(provider)


PROVIDER = load_provider()


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS generation_jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS packages (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS traces (package_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL, evaluation TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS trace_history (package_id TEXT, revision INTEGER, data TEXT, evaluation TEXT, PRIMARY KEY(package_id, revision))")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, table, key):
        require(table in ("students", "packages"), "Invalid table")
        with self.connect() as db:
            row = db.execute(f"SELECT data FROM {table} WHERE id=?", (key,)).fetchone()
        require(row is not None, "Record not found")
        return json.loads(row[0])

    def save(self, table, obj):
        with self.connect() as db:
            if table == "students":
                db.execute("INSERT INTO students VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                           (obj["id"], json.dumps(obj)))
            elif table == "packages":
                db.execute("INSERT INTO packages VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                           (obj["id"], obj["student_id"], json.dumps(obj)))
            else:
                raise ValidationError("Invalid table")

    def packages(self, student_id=None):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM packages" + (" WHERE student_id=?" if student_id else ""),
                              (student_id,) if student_id else ()).fetchall()
        return sorted([json.loads(r[0]) for r in rows], key=lambda x: x["created_at"])

    def evaluations(self, student_id):
        with self.connect() as db:
            rows = db.execute("SELECT t.evaluation, p.data FROM traces t JOIN packages p ON p.id=t.package_id WHERE p.student_id=?",
                              (student_id,)).fetchall()
        return [json.loads(r[0]) for r in sorted(rows, key=lambda r: json.loads(r[1])["round"])]

    def student_view(self, student):
        result = copy.deepcopy(student)
        result["state"] = state_for(student, [e for e in self.evaluations(student["id"]) if not e.get("topic_id")])
        return result

    def bootstrap(self):
        with self.connect() as db:
            students = [self.student_view(json.loads(r[0])) for r in db.execute("SELECT data FROM students ORDER BY id")]
        packages = [{k: p[k] for k in ("id", "student_id", "round", "mode", "status", "created_at")}
                    | {"title": p["plan"]["title"]} for p in self.packages()]
        return {"version": VERSION, "students": students, "packages": packages,
                "diagnostic": [public_question(BANK[k]) for k in ("D01", "D02", "D03")],
                "units": [{"id": u["id"], "version": u["version"], "title": u["title"], "languages": u["languages"]} for u in UNITS.values()],
                "provider_presets": PRESETS,
                "provider": {**{k:v for k,v in PROVIDER.items() if k!="api_key"},
                             "configured": bool(PROVIDER["api_key"] and PROVIDER["model"])}}


def ai_plan(request_data, provider):
    require(provider["api_key"] and provider["model"], "Configure an API key and model before selecting live AI")
    count = request_data.get("constraints", {}).get("question_count", 3)
    language = request_data.get("constraints", {}).get("language", "en")
    custom=request_data.get("constraints",{}).get("custom_topic")
    summarising=request_data.get("operation")=="summary"
    prompt_file="learning_summary.md" if summarising else "custom_workbook.md" if custom else "author_lesson.md"
    system = (ROOT / "prompts" / prompt_file).read_text(encoding="utf-8")
    system += f"\nCurrent packet: exactly {count} questions; visible language {language}; batch_size {request_data.get('constraints',{}).get('batch_size',0)}." if custom else f"\nCurrent packet: exactly {count} questions; {count-1} coach notes; visible language {language}."
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": json.dumps(request_data, ensure_ascii=False)}]
    attempts = []
    started = time.monotonic()
    for attempt in range(2):
        endpoint,headers,payload=build_request(provider,messages,16000 if custom else 6000)
        req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw_bytes = response.read(600_001)
            require(len(raw_bytes) <= 600_000, "AI response exceeded size limit")
            body = json.loads(raw_bytes)
            content,finish,usage=response_content(body,provider)
            require(isinstance(content, str) and len(content) <= 180000, "Missing or excessive model content")
        except urllib.error.HTTPError as exc:
            exc.close()
            raise ValidationError(f"AI provider returned HTTP {exc.code}. Check endpoint, key, model and JSON-mode support. No demo fallback was used.") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ValidationError("AI connection failed or timed out. No demo fallback was used.") from None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ValidationError("AI provider returned an unexpected response envelope") from None
        try:
            require(bool(content.strip()), "AI returned empty JSON content (finish reason: " + str(finish) + ")")
            proposal = parse_json_content(content)
            if summarising:validate_summary(proposal,request_data["student_state"])
            elif custom:
                validate_workbook(proposal,request_data["student_state"],count,request_data["constraints"]["batch_size"])
                catalog_ids={q["id"] for q in request_data.get("catalog",[])}
                require(all(q.get("reference_id") in catalog_ids for q in proposal["questions"] if q["origin"]=="bank_adapted"),"Unknown reference bank ID")
            else:validate_proposal(proposal, request_data["student_state"], count)
            attempts.append({"content": content, "validation": "passed", "usage": usage, "finish_reason": finish})
            return proposal, {"provider": provider["base_url"], "model": body.get("model", provider["model"]),
                              "prompt_version": "paper-summary-1" if request_data.get("operation")=="summary" else "paper-workbook-3" if request_data.get("constraints",{}).get("custom_topic") else PROMPT_VERSION, "system_prompt": system,
                              "attempts": attempts, "elapsed_seconds": round(time.monotonic()-started, 2)}
        except (json.JSONDecodeError, ValidationError) as exc:
            attempts.append({"content": content, "validation": str(exc), "usage": usage, "finish_reason": finish})
            messages += [{"role": "assistant", "content": content},
                         {"role": "user", "content": "Repair your JSON: " + str(exc)}]
    raise ValidationError("AI output could not be used after two attempts. Reduce the packet size or review the topic material. Details: " + attempts[-1]["validation"])


def generate(store, student_id, mode, config):
    require(mode in ("demo", "live"), "Mode must be demo or live")
    student = store.get("students", student_id)
    require(student.get("unit_id", DEFAULT_UNIT) == config["unit_id"], "Learner and teaching unit mismatch")
    bank = unit_bank(config["unit_id"])
    count = config["question_count"]
    evaluations = store.evaluations(student_id)
    if config.get("custom_topic"):
        evaluations=[e for e in evaluations if e.get("topic_id")==config["topic_id"]]
        student=copy.deepcopy(student);student["diagnostic"]={}
    state = topic_state(student,evaluations,config) if config.get("custom_topic") else state_for(student, evaluations)
    existing = store.packages(student_id)
    used = [n["bank_id"] for p in existing for n in p["plan"]["nodes"] if "bank_id" in n and n.get("origin") != "ai_generated"]
    request_data = {"schema_version": "2.0",
                    "learner_context": {"grade": student.get("grade"), "synthetic": student.get("synthetic", False)},
                    "unit_context": {k:UNITS[config["unit_id"]][k] for k in ("id","title","skills","verification")},
                    "historical_questions": [{"package_id":p["id"],"status":p["status"],"questions":[n for n in p["plan"]["nodes"] if n["type"]=="choice_question" ]} for p in existing if not config.get("custom_topic") or p["config"].get("topic_id")==config["topic_id"]], "student_id": student_id, "student_state": state,
                    "confirmed_evaluations": evaluations, "constraints": config,
                    "used_question_ids": used,
                    "diagnostic_context": [localized_question(bank[k], config["language"]) for k in UNITS[config["unit_id"]]["diagnostic_ids"]],
                    "catalog": [localized_question(q, config["language"]) for q in bank.values() if q["id"] not in UNITS[config["unit_id"]]["diagnostic_ids"]]}
    if config.get("custom_topic"):
        request_data["diagnostic_context"]=[]
        request_data["unit_context"]={"id":config["topic_id"],"title":config["topic"],"verification":"teacher_review"}
        if not config.get("include_reference_bank"):request_data["catalog"]=[]
        require(mode=="live","Custom topics require live AI. Configure the AI connection first; use legacy mode for rules rehearsal.")
    if mode == "live":
        proposal, audit = ai_plan(request_data, dict(PROVIDER))
    else:
        proposal = demo_proposal(state, used, count, config["language"])
        audit = {"provider": "local deterministic rehearsal", "model": None,
                 "prompt_version": None, "notice": "No AI call. This is a rules-based demo, not experimental evidence."}
    if config.get("custom_topic"):
        validate_workbook(proposal,state,count,config["batch_size"])
        plan=compile_workbook(proposal,config)
        proposal["question_ids"]=[q["id"] for q in proposal["questions"]]
        proposal["coach_notes"]=[]
    else:
        validate_proposal(proposal, state, count)
        plan = compile_plan(proposal, config)
        require(config["max_pages"] >= count, "Page budget is too small")
    with LOCK:
        # Refresh round number after remote call; teacher can generate on another tab.
        existing = store.packages(student_id)
        package = {"id": "PKG-" + secrets.token_hex(5).upper(), "student_id": student_id,
                   "round": max((p["round"] for p in existing), default=0)+1, "version": 1, "created_at": now(), "status": "draft",
                   "sheet_code": secrets.token_hex(3).upper(), "student_token": secrets.token_urlsafe(24),
                   "mode": mode, "config": config, "proposal": proposal, "plan": plan,
                   "request": request_data, "audit": audit, "plan_hash": content_hash(plan),
                   "compiler_version": VERSION, "template_version": "OMR-1", "pages": count, "unit_version": UNITS[config["unit_id"]]["version"],
                   "schedule": [{"task_id": f"Q{i+1}", "day": min(config["offline_days"], 1+i*config["offline_days"]//count)} for i in range(count)],
                   "reused_question_ids": [qid for qid in proposal["question_ids"] if qid in used]}
        if config.get("custom_topic"):
            package["learning_summary"]=proposal["learning_summary"]
            package["summary_evidence_refs"]=proposal["evidence_refs"]
            package["summary_as_of"]=len(evaluations)
            package["record_sheets"]=[]
            used_codes={p["sheet_code"] for p in store.packages()}
            used_codes.update(x["code"] for p in store.packages() for x in p.get("record_sheets",[]))
            for offset in range(0,count,8):
                code=secrets.token_hex(3).upper()
                while code in used_codes:code=secrets.token_hex(3).upper()
                used_codes.add(code)
                package["record_sheets"].append({"code":code,"page":len(package["record_sheets"])+1,
                    "task_ids":[f"Q{i+1}" for i in range(offset,min(offset+8,count))]})
        all_packages = store.packages()
        while any(p["sheet_code"] == package["sheet_code"] or any(s["code"]==package["sheet_code"] for s in p.get("record_sheets",[])) for p in all_packages):
            package["sheet_code"] = secrets.token_hex(3).upper()
        store.save("packages", package)
    return package


class Handler(BaseHTTPRequestHandler):
    server_version = "PaperAI/" + VERSION

    def log_message(self, fmt, *args):
        # Avoid logging student capability tokens in URLs.
        pass

    @property
    def store(self):
        return self.server.store

    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            require(self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"),
                    "This is a local-only teacher application")
            url = urlsplit(self.path)
            path = url.path
            query = parse_qs(url.query)
            if path == "/api/backup":
                from persistence import backup
                return self.send_json(backup(self.store))
            if path == "/api/jobs":
                with self.store.connect() as db:
                    jobs = [json.loads(r[0]) for r in db.execute("SELECT data FROM generation_jobs ORDER BY rowid DESC LIMIT 100")]
                return self.send_json({"jobs": jobs})
            if path == "/api/bootstrap":
                return self.send_json(self.store.bootstrap())
            if path.startswith("/api/packages/"):
                key = path.split("/")[-1]
                p = self.store.get("packages", key)
                with self.store.connect() as db:
                    row = db.execute("SELECT * FROM traces WHERE package_id=?", (key,)).fetchone()
                if row:
                    p["trace"] = json.loads(row["data"])
                    p["evaluation"] = json.loads(row["evaluation"])
                    p["trace_revision"] = row["revision"]
                return self.send_json(p)
            if path.startswith("/api/learn/"):
                p = self.store.get("packages", path.split("/")[-1])
                token = query.get("token", [""])[0]
                require(secrets.compare_digest(token, p["student_token"]), "Invalid student link")
                require(p["status"] != "draft", "Package has not been approved")
                return self.send_json(public_package(p))
            if path == "/api/export":
                bootstrap = self.store.bootstrap()
                packages = self.store.packages()
                for p in packages:
                    p.pop("student_token", None)
                with self.store.connect() as db:
                    traces = [{"package_id": r["package_id"], "revision": r["revision"],
                               "trace": json.loads(r["data"]), "evaluation": json.loads(r["evaluation"])}
                              for r in db.execute("SELECT * FROM traces")]
                return self.send_json({"schema_version": "1.0", "exported_at": now(),
                                       "notice": "Local teacher export. Review free text before sharing. Includes synthetic records when labelled.",
                                       "students": bootstrap["students"], "packages": packages, "traces": traces})
            static_path = STATIC / ("index.html" if path == "/" else path.lstrip("/"))
            require(static_path.resolve().is_relative_to(STATIC.resolve()) and static_path.is_file(), "File not found")
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}.get(static_path.suffix, "application/octet-stream")
            data = static_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except ValidationError as exc:
            self.send_json({"error": str(exc)}, 404 if "not found" in str(exc) else 400)
        except Exception:
            self.send_json({"error": "Unexpected server error; check the local application."}, 500)

    def do_POST(self):
        try:
            require(self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"),
                    "This is a local-only teacher application")
            require(self.headers.get("X-PaperAI") == "local-teacher", "Missing local request header")
            origin = self.headers.get("Origin")
            require(not origin or urlsplit(origin).netloc == self.headers.get("Host"), "Cross-origin request rejected")
            size = int(self.headers.get("Content-Length", "0"))
            require(0 < size <= 20000000, "Invalid request size")
            body = json.loads(self.rfile.read(size))
            require(isinstance(body, dict), "Request must be an object")
            path = urlsplit(self.path).path
            if path == "/api/pdf-ready":
                from pdf_export import acknowledge
                acknowledge(body.get("job"),body.get("ready") is True,body.get("error",""))
                return self.send_json({"ok":True})
            if path == "/api/pdf":
                from pdf_export import export_pdf
                ids=body.get("ids",[]);view=body.get("view","booklet");token=body.get("token","")
                require(isinstance(ids,list) and 1<=len(ids)<=50 and all(isinstance(i,str) for i in ids),"Invalid print selection")
                require(view in ("booklet","support","record","teacher"),"Unknown print view")
                if token:require(len(ids)==1 and view in ("booklet","record"),"Invalid student PDF selection")
                for key in ids:
                    package=self.store.get("packages",key)
                    require(package["status"]!="draft","Approve every package before printing.")
                    if token:require(secrets.compare_digest(token,package["student_token"]),"Invalid student link")
                data=export_pdf(self.server.server_port,ids,view,token)
                self.send_response(200);self.send_header("Content-Type","application/pdf")
                self.send_header("Content-Disposition",'attachment; filename="PAPER-AI-'+view+'.pdf"')
                self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
            if path == "/api/restore":
                from persistence import restore
                return self.send_json(restore(self.store, body))
            if path == "/api/settings":
                base = text(body.get("base_url"), "API base URL", 300).rstrip("/")
                parsed = urlsplit(base)
                require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                        "Use an HTTPS provider base URL without credentials or query parameters")
                model = text(body.get("model"), "Model", 120)
                key = body.get("api_key", "")
                require(isinstance(key, str) and len(key) <= 1000, "Invalid key")
                with LOCK:
                    require(base == PROVIDER["base_url"].rstrip("/") or key.strip(),
                            "Enter a new key when changing provider URL")
                    updated=dict(PROVIDER,base_url=base,model=model,provider=body.get("provider","custom"),protocol=body.get("protocol","chat"),json_mode=body.get("json_mode","auto"))
                    validate_provider(updated)
                    PROVIDER.update(updated)
                    if key:
                        PROVIDER["api_key"] = key.strip()
                return self.send_json({"configured": bool(PROVIDER["api_key"]), "note": "Key is held in server memory only."})
            if path == "/api/students":
                label = text(body.get("label"), "Anonymous alias", 50)
                grade = text(body.get("grade", "Secondary"), "Grade", 50)
                diag = body.get("diagnostic", {})
                unit_id = body.get("unit_id", DEFAULT_UNIT)
                diagnostic_score(diag, unit_id)
                obj = {"id": "S-"+secrets.token_hex(3).upper(), "label": label, "grade": grade,
                       "unit_id": unit_id, "class_name": text(body.get("class_name") or "Default", "Class", 80),
                       "diagnostic": diag, "synthetic": body.get("synthetic") is True, "created_at": now()}
                self.store.save("students", obj)
                return self.send_json(self.store.student_view(obj), 201)
            if path == "/api/seed":
                with LOCK:
                    with self.store.connect() as db:
                        existing = {r[0] for r in db.execute("SELECT id FROM students")}
                    for sid, label, supported in [("S-DEMO-A", "Alex · support example", True), ("S-DEMO-B", "Sam · transfer example", False)]:
                        if sid not in existing:
                            diag = {k: (next(iter(BANK[k]["misconception_options"])) if supported else BANK[k]["correct_option"])
                                    for k in ("D01", "D02", "D03")}
                            self.store.save("students", {"id": sid, "label": label, "grade": "Secondary",
                                                        "diagnostic": diag, "synthetic": True, "created_at": now()})
                return self.send_json(self.store.bootstrap())
            if path == "/api/generate":
                config = validate_config(body.get("config", {}))
                request_id = text(body.get("request_id") or secrets.token_hex(16), "Request ID", 100)
                fingerprint = content_hash({"student_id": body.get("student_id"), "mode": body.get("mode"), "config": config})
                with LOCK:
                    with self.store.connect() as db:
                        old = db.execute("SELECT data FROM generation_jobs WHERE id=?", (request_id,)).fetchone()
                        if old:
                            job = json.loads(old[0])
                            require(job["fingerprint"] == fingerprint, "Request ID conflicts with another generation")
                            if job["status"] == "complete":
                                return self.send_json(self.store.get("packages", job["package_id"]))
                            return self.send_json({"error": "Generation is " + job["status"] + ". Check recent jobs before starting again."}, 409)
                        job = {"id": request_id, "fingerprint": fingerprint, "student_id": body.get("student_id"), "status": "running", "created_at": now()}
                        db.execute("INSERT INTO generation_jobs VALUES (?,?)", (request_id, json.dumps(job)))
                try:
                    package = generate(self.store, body.get("student_id"), body.get("mode"), config)
                    job.update(status="complete", package_id=package["id"])
                except Exception:
                    job.update(status="failed")
                    raise
                finally:
                    with self.store.connect() as db:
                        db.execute("UPDATE generation_jobs SET data=? WHERE id=?", (json.dumps(job), request_id))
                return self.send_json(package, 201)
            if path.endswith("/summary") and path.startswith("/api/packages/"):
                package=self.store.get("packages",path.split("/")[3])
                student=self.store.get("students",package["student_id"])
                evaluations=self.store.evaluations(student["id"])
                if package["config"].get("custom_topic"):
                    evaluations=[e for e in evaluations if e.get("topic_id")==package["config"]["topic_id"]]
                    student["diagnostic"]={}
                state=topic_state(student,evaluations,package["config"]) if package["config"].get("custom_topic") else state_for(student,evaluations)
                request={"operation":"summary","constraints":package["config"],"student_state":state,
                         "confirmed_evaluations":evaluations,"questions":package["plan"]["nodes"],
                         "synthetic":student.get("synthetic",False)}
                summary,audit=ai_plan(request,dict(PROVIDER))
                with LOCK:
                    package=self.store.get("packages",package["id"])
                    latest=self.store.evaluations(student["id"])
                    if package["config"].get("custom_topic"):latest=[e for e in latest if e.get("topic_id")==package["config"]["topic_id"]]
                    require(content_hash(latest)==content_hash(evaluations),"Learning records changed during summary generation; generate it again.")
                    package["ai_summary"]={"content":summary,"audit":audit,"as_of":len(evaluations),"created_at":now()}
                    self.store.save("packages",package)
                return self.send_json(package["ai_summary"])
            if path.endswith("/edit") and path.startswith("/api/packages/"):
                with LOCK:
                    package = self.store.get("packages", path.split("/")[3])
                    require(package["status"] == "draft", "Only drafts can be edited")
                    require(body.get("plan_hash") == package["plan_hash"], "Draft changed; reload")
                    proposal = copy.deepcopy(package["proposal"])
                    for field in (("title", "reason", "coach_notes", "learning_summary", "lesson", "questions", "batch_feedback") if package["config"].get("custom_topic") else ("title", "reason", "coach_notes")):
                        if field in body: proposal[field] = body[field]
                    if package["config"].get("custom_topic"):
                        validate_workbook(proposal,package["request"]["student_state"],package["config"]["question_count"],package["config"]["batch_size"])
                    else:validate_proposal(proposal, package["request"]["student_state"], len(proposal["question_ids"]))
                    package["proposal"] = proposal
                    if package["config"].get("custom_topic"):package["learning_summary"]=proposal["learning_summary"]
                    package["plan"] = compile_workbook(proposal,package["config"]) if package["config"].get("custom_topic") else compile_plan(proposal, package["config"])
                    package["plan_hash"] = content_hash(package["plan"])
                    package["teacher_edited_at"] = now()
                    self.store.save("packages", package)
                return self.send_json(package)
            if path.endswith("/discard") and path.startswith("/api/packages/"):
                with LOCK:
                    key = path.split("/")[3]
                    package = self.store.get("packages", key)
                    require(package["status"] == "draft", "Only drafts can be discarded")
                    require(body.get("plan_hash") == package["plan_hash"], "Draft changed; reload")
                    with self.store.connect() as db:
                        db.execute("DELETE FROM packages WHERE id=?", (key,))
                return self.send_json({"discarded": key})
            if path.endswith("/approve") and path.startswith("/api/packages/"):
                key = path.split("/")[3]
                with LOCK:
                    p = self.store.get("packages", key)
                    require(body.get("plan_hash") == p["plan_hash"], "Plan changed; reload before approving")
                    require(body.get("reviewed") is True, "Confirm that you reviewed the questions and coach notes")
                    if p["status"] == "draft":
                        p["status"] = "issued"
                        p["approved_at"] = now()
                        self.store.save("packages", p)
                return self.send_json(p)
            if path.endswith("/trace") and path.startswith("/api/packages/"):
                key = path.split("/")[3]
                with LOCK:
                    p = self.store.get("packages", key)
                    require(p["status"] in ("issued", "evaluated"), "Approve the package before collecting records")
                    trace = body.get("trace")
                    result = evaluate_trace(p, trace)
                    with self.store.connect() as db:
                        old = db.execute("SELECT * FROM traces WHERE package_id=?", (key,)).fetchone()
                        revision = old["revision"] if old else 0
                        if old and json.loads(old["data"]) == trace:
                            return self.send_json({"evaluation": json.loads(old["evaluation"]), "revision": revision, "duplicate": True})
                        require(body.get("expected_revision", 0) == revision, "Record changed in another tab. Reload before saving.")
                        revision += 1
                        values = (key, revision, json.dumps(trace), json.dumps(result))
                        db.execute("INSERT INTO traces VALUES (?,?,?,?) ON CONFLICT(package_id) DO UPDATE SET revision=excluded.revision,data=excluded.data,evaluation=excluded.evaluation", values)
                        db.execute("INSERT INTO trace_history VALUES (?,?,?,?)", values)
                        p["status"] = "evaluated"
                        p.pop("ai_summary",None)
                        db.execute("UPDATE packages SET data=? WHERE id=?", (json.dumps(p), key))
                return self.send_json({"evaluation": result, "revision": revision, "duplicate": False})
            raise ValidationError("Unknown operation")
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception:
            self.send_json({"error": "Unexpected server error. Your issued packages are unchanged."}, 500)


def make_server(port=8765, data=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.store = Store(data or ROOT / "data" / "paperai.sqlite3")
    with server.store.connect() as db:
        for row in db.execute("SELECT id,data FROM generation_jobs").fetchall():
            job = json.loads(row["data"])
            if job["status"] == "running":
                job["status"] = "interrupted"
                db.execute("UPDATE generation_jobs SET data=? WHERE id=?", (json.dumps(job), row["id"]))
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data", type=Path)
    args = parser.parse_args()
    server = make_server(args.port, args.data)
    print(f"PAPER AI {VERSION}: http://127.0.0.1:{server.server_port}", flush=True)
    print("Local single-teacher prototype. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


