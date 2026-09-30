"""Offline reference for 1901-set-production-source. Fixtures only; no network."""
import json, copy, re, datetime

SPREADSHEET = "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0"
SHEET = "Idea Queue"
GID = "1283408381"
TS = "2026-09-30T23:58:00Z"  # fixed for byte-stable examples

QUEUE = ["id","concept","season","style","vibe","status","idea_notes","image_prompt","art_path",
         "art_gens","printify_id","etsy_url","notes","removed_reason"]
RENDER = ["human_decision","render_status","render_source_path","render_output_folder",
          "render_notes","render_updated_at","render_qa"]
EXPECTED = QUEUE + RENDER
COMPARE = ["human_decision","status","art_path","render_status","render_qa"]

def col_letter(i):
    s=""; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s

def canonical(file_id): return f"https://drive.google.com/file/d/{file_id}/view"

class Sheet:
    """Fixture spreadsheet. Records every cell write."""
    def __init__(self, headers, rows, readable=True):
        self.headers=headers; self.rows=rows; self.readable=readable; self.writes=[]; self.fail_next_write=False
    def read_row(self, design_id):
        if not self.readable: return {"result":"SOURCE_UNAVAILABLE"}
        hdr=[h.strip() for h in self.headers]
        if hdr.count("id")!=1: return {"result":"SCHEMA_WARNING"}
        idx=hdr.index("id")
        matches=[n for n,r in enumerate(self.rows, start=2) if (r[idx] if idx<len(r) else "")==design_id]
        if not matches: return {"result":"NOT_FOUND","matching_rows":[]}
        if len(matches)>1: return {"result":"DUPLICATE_ID","matching_rows":matches}
        n=matches[0]; r=self.rows[n-2]
        rec={}
        for f in EXPECTED:
            rec[f] = (r[hdr.index(f)] if hdr.index(f)<len(r) else "") if hdr.count(f)==1 else None
        unknown=[{"column":col_letter(i),"header":h,"value":r[i]} for i,h in enumerate(hdr) if h not in EXPECTED and i<len(r) and r[i]!=""]
        return {"result":"FOUND","row_number":n,"record":rec,"unknown_columns":unknown}
    def write_cell(self, row_number, header, value):
        hdr=[h.strip() for h in self.headers]; c=hdr.index(header)
        self.writes.append({"range":f"'{SHEET}'!{col_letter(c)}{row_number}","value":value})
        if self.fail_next_write: self.fail_next_write=False; return  # simulate: API says ok, cell not changed
        r=self.rows[row_number-2]
        while len(r)<=c: r.append("")
        r[c]=value
        return True

class Drive:
    def __init__(self, files, readable=True): self.files=files; self.readable=readable; self.mutations=[]
    def get(self, fid):
        if not self.readable: return "UNAVAILABLE"
        return self.files.get(fid)

COMMAND_WORDS = ("AUTHORIZE", "SOURCE", "WRITE")

def authorization_command(message, design_id):
    """Return the exact command text if `message` is the authorization command for `design_id`,
    the id it names if it is the command for a different id, else None. Trim surrounding
    whitespace; the three words compare case-insensitively; the id must equal the target exactly."""
    if not isinstance(message, str): return None
    parts = message.strip().split()
    if len(parts) != 4 or tuple(w.upper() for w in parts[:3]) != COMMAND_WORDS: return None
    return ("OK", message.strip()) if parts[3] == design_id else ("OTHER_ID", parts[3])

def run(design_id, sheet, drive, resolver, message="", proposed_value=None):
    """resolver: dict as 1901-resolve-production-source would return. message: the user's text in
    the CURRENT run (the only place authorization can come from). proposed_value: a value the
    user asked to write, if any."""
    auth = authorization_command(message, design_id)
    authorization = {"evidence": auth[1]} if auth and auth[0] == "OK" else None
    out={"design_id":"", "result":"", "write_performed":False, "timestamp":TS,
         "source":{"spreadsheet_id":SPREADSHEET,"sheet_name":SHEET,"sheet_id":GID,"row_number":None},
         "before":{"render_source_path":None}, "after":{"render_source_path":None},
         "verification":{"human_decision":None,"source_resolution":"","source_file_id":"","source_file_name":"","source_url":"","post_write_verified":False},
         "authorization":{"received":bool(authorization),"evidence":(authorization or {}).get("evidence","")},
         "checks":[], "human_action_required":None}
    checks=out["checks"]
    def done(result, action=None):
        out["result"]=result; out["human_action_required"]=action; return out
    def chk(name, status, detail): checks.append({"check":name,"status":status,"detail":detail})

    # 1 input
    did=(design_id or "").strip() if isinstance(design_id,str) else ""
    out["design_id"]=did
    if not did or any(ch.isspace() for ch in did):
        chk("input","FAIL","no single usable design_id was supplied")
        return done("NOT_FOUND","Supply exactly one design_id, then re-run.")
    chk("input","PASS",f"design_id '{did}' (trimmed)")

    # 2 queue read
    q=sheet.read_row(did)
    if q["result"]=="SOURCE_UNAVAILABLE":
        chk("queue_read","FAIL","the authoritative Idea Queue could not be read; nothing substituted")
        return done("SOURCE_UNAVAILABLE","Restore read access to the authoritative Idea Queue, then re-run.")
    if q["result"]=="SCHEMA_WARNING":
        chk("queue_read","FAIL","the id header is missing or duplicated; the sheet cannot be used safely")
        return done("SOURCE_UNAVAILABLE","Repair the Idea Queue header row (id header missing or duplicated), then re-run.")
    if q["result"]=="NOT_FOUND":
        chk("queue_read","FAIL",f"no row has id exactly equal to {did}")
        return done("NOT_FOUND",f"Correct the Idea Queue so exactly one row carries id {did}, then re-run.")
    if q["result"]=="DUPLICATE_ID":
        chk("queue_read","FAIL",f"rows {q['matching_rows']} all carry id {did}; none chosen")
        return done("DUPLICATE_ID",f"Resolve the duplicate Idea Queue rows for {did} (rows {', '.join(map(str,q['matching_rows']))}), then re-run.")
    rec=q["record"]; row=q["row_number"]; out["source"]["row_number"]=row
    chk("queue_read","PASS",f"exactly one row (sheet row {row}) carries id {did}")
    if rec["render_source_path"] is None or rec["human_decision"] is None:
        chk("schema","FAIL","render_source_path or human_decision column is missing or duplicated in the live header row")
        return done("SOURCE_UNAVAILABLE","Repair the Idea Queue header row so render_source_path and human_decision each appear exactly once, then re-run.")
    before=copy.deepcopy(rec); out["before"]["render_source_path"]=rec["render_source_path"]; out["after"]["render_source_path"]=rec["render_source_path"]
    out["verification"]["human_decision"]=rec["human_decision"]
    if q["unknown_columns"]:
        chk("unknown_columns","INFO","preserved, not modified: "+"; ".join(f"{u['column']} (header '{u['header']}') = '{u['value']}'" for u in q["unknown_columns"]))

    # 3 human approval
    if rec["human_decision"]!="APPROVE":
        chk("human_approval","FAIL",f"human_decision is '{rec['human_decision']}', not exactly APPROVE")
        return done("HUMAN_APPROVAL_REQUIRED",f"A human must set human_decision to APPROVE for {did} in the live Idea Queue before its production source can be recorded.")
    chk("human_approval","PASS","human_decision is exactly APPROVE")

    # 4 resolver
    res=resolver.get("result"); out["verification"]["source_resolution"]=res or ""
    if res=="SOURCE_UNAVAILABLE":
        chk("source_resolution","FAIL","1901-resolve-production-source could not read a required live source")
        return done("SOURCE_UNAVAILABLE","Restore read access to the sources 1901-resolve-production-source needs, then re-run.")
    if res!="RESOLVED":
        chk("source_resolution","FAIL",f"1901-resolve-production-source returned {res}; only RESOLVED permits a write")
        return done("SOURCE_NOT_RESOLVED",(resolver.get("human_action_required") or f"Resolve the production source for {did} (resolver returned {res}) before re-running."))
    rf=resolver.get("resolved_file") or {}
    missing=[k for k in ("drive_file_id","name","url","mime_type") if not rf.get(k)]
    if missing:
        chk("source_resolution","FAIL","RESOLVED but resolved_file lacks "+", ".join(missing))
        return done("SOURCE_NOT_RESOLVED",f"The resolver's RESOLVED output for {did} is incomplete ({', '.join(missing)} missing); re-run the resolver and confirm the file identity.")
    chk("source_resolution","PASS",f"RESOLVED: {rf['name']} (id {rf['drive_file_id']}, {rf['mime_type']})")

    # 5 file identity
    fid=rf["drive_file_id"]; target=canonical(fid)
    out["verification"].update({"source_file_id":fid,"source_file_name":rf["name"],"source_url":target})
    m=re.search(r"/d/([^/?#]+)", rf["url"]) or re.search(r"[?&]id=([^&#]+)", rf["url"])
    if not m or m.group(1)!=fid:
        chk("file_identity","FAIL",f"resolver url '{rf['url']}' does not carry file id {fid}")
        return done("SOURCE_MISMATCH",f"The resolver's url and drive_file_id for {did} disagree; re-run the resolver and confirm the file identity before any write.")
    f=drive.get(fid)
    if f=="UNAVAILABLE":
        chk("file_identity","FAIL","Google Drive could not be read; file existence not confirmed")
        return done("SOURCE_UNAVAILABLE","Restore read access to Google Drive, then re-run.")
    if not f or f.get("trashed"):
        chk("file_identity","FAIL",f"Drive file {fid} does not exist, is trashed, or is not accessible")
        return done("SOURCE_MISMATCH",f"The resolved source file for {did} (id {fid}) is missing or inaccessible in Drive; a human must confirm the source before any write.")
    if f["name"]!=rf["name"] or f["mime_type"]!=rf["mime_type"]:
        chk("file_identity","FAIL",f"live Drive metadata ({f['name']}, {f['mime_type']}) differs from the resolver's ({rf['name']}, {rf['mime_type']})")
        return done("SOURCE_MISMATCH",f"Live Drive metadata for {fid} does not match the resolved file for {did}; a human must confirm the source before any write.")
    if proposed_value is not None and proposed_value!=target:
        chk("file_identity","FAIL",f"the requested value '{proposed_value}' is not the canonical URL of the resolved file ({target})")
        return done("SOURCE_MISMATCH",f"The value requested for {did} does not match the verified source; only {target} may be written. Re-check which file was resolved.")
    chk("file_identity","PASS",f"Drive file {fid} exists and matches; canonical URL {target}")

    # 6 existing value
    cur=rec["render_source_path"]
    if cur==target:
        chk("existing_value","PASS","render_source_path already equals the canonical URL; nothing to write")
        return done("ALREADY_SET",None)
    if cur!="":
        same = (re.search(r"/d/([^/?#]+)", cur) or re.search(r"[?&]id=([^&#]+)", cur))
        note = " (it appears to reference the same file id in a different form; still not overwritten)" if same and same.group(1)==fid else ""
        chk("existing_value","FAIL",f"render_source_path is already '{cur}', which differs from '{target}'{note}")
        return done("SOURCE_ALREADY_SET_CONFLICT",f"render_source_path for {did} already holds a different value; a human must decide which value is correct and change the cell manually. Walter will not overwrite it.")
    chk("existing_value","PASS","render_source_path is blank; eligible for write")

    # 7 authorization
    if not authorization:
        if auth and auth[0] == "OTHER_ID":
            chk("authorization","FAIL",f"the command names {auth[1]}, not the target {did}; it authorizes nothing in this run")
        else:
            chk("authorization","FAIL","the current run does not contain the exact command AUTHORIZE SOURCE WRITE "+did+"; ordinary requests and vague confirmations never authorize a write")
        return done("AWAITING_AUTHORIZATION",f"No write performed. Row {row} is eligible: render_source_path would be set to {target}. To authorize exactly this write, send exactly: AUTHORIZE SOURCE WRITE {did}")
    chk("authorization","PASS",f"current run contains the exact command: {authorization['evidence']}")

    # 8 write: exactly one cell
    ok=sheet.write_cell(row,"render_source_path",target)
    out["write_performed"]=bool(ok) or ok is None  # request issued and reported success
    chk("write","PASS" if out["write_performed"] else "FAIL",f"one update request: '{SHEET}'!{col_letter([h.strip() for h in sheet.headers].index('render_source_path'))}{row} = {target}")

    # 9 re-read
    q2=sheet.read_row(did)
    if q2["result"]!="FOUND" or q2["row_number"]!=row:
        chk("post_write_reread","FAIL","the row could not be re-read after the write; state unknown")
        out["after"]["render_source_path"]=None
        return done("WRITE_FAILED",f"Inspect Idea Queue row {row} for {did} manually: the write was issued but the row could not be re-read. Do not re-run until the cell has been checked.")
    rec2=q2["record"]; out["after"]["render_source_path"]=rec2["render_source_path"]
    problems=[]
    if rec2["render_source_path"]!=target: problems.append(f"render_source_path is '{rec2['render_source_path']}', expected '{target}'")
    for f_ in EXPECTED:
        if f_=="render_source_path": continue
        if rec2[f_]!=before[f_]: problems.append(f"{f_} changed from '{before[f_]}' to '{rec2[f_]}'")
    if q2["unknown_columns"]!=q["unknown_columns"]: problems.append("an unknown column changed")
    if problems:
        chk("post_write_reread","FAIL","; ".join(problems))
        return done("WRITE_FAILED",f"Inspect Idea Queue row {row} for {did} manually and correct it by hand: {'; '.join(problems)}. No retry was attempted.")
    out["verification"]["post_write_verified"]=True
    chk("post_write_reread","PASS","render_source_path equals the intended URL; "+", ".join(COMPARE)+" and every other field are unchanged")
    return done("UPDATED",None)
