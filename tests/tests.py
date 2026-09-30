import json, copy, sys
from ref import *

HDR = QUEUE + ["", ""] + RENDER + ["wave"]   # A..N queue, O blank, P blank-header (holds 'simple'), Q..W render, X unknown 'wave'
FID = "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh"
def row(id_, hd="APPROVE", rsp="", p="simple", extra="2"):
    return [id_, "Stamp concept", "Fall", "Stamp", "Nostalgic", "Approved", "Stamp concept, circular and square explorations",
            "vintage postage stamp of a porch", canonical(FID), "3", "", "", "Approved: Redraw C stamp remaster", "",
            "", p, hd, "", rsp, "", "", "", "", extra]
def sheet(**kw): return Sheet(list(HDR), [row("1901-001", hd="", extra=""), row("1901-002", hd="REVISE"), row("1901-003", **kw)])
def drive(): return Drive({FID: {"name": "1901-003-redraw-c-stamp.png", "mime_type": "image/png"}})
RES_OK = {"result": "RESOLVED", "resolved_file": {"drive_file_id": FID, "name": "1901-003-redraw-c-stamp.png", "url": canonical(FID), "mime_type": "image/png"}}
AUTH = {"evidence": "User wrote \"Authorize the render_source_path update for 1901-003.\" in the current conversation, after seeing the resolved file."}

examples = {}
def T(n, name, out, result, wrote, sh, dr, extra_ok=None):
    assert out["result"] == result, (n, out["result"], result)
    assert out["write_performed"] is wrote, (n, "write_performed")
    if not wrote: assert sh.writes == [], (n, sh.writes)
    assert dr.mutations == [], n
    if extra_ok: extra_ok(out, sh)
    print(f"{n:>2}. PASS {name}: {result}, writes={sh.writes}")
    examples[n] = out

# 1 approved + verified + authorized
sh, dr = sheet(), drive(); snap = copy.deepcopy(sh.rows)
o = run("1901-003", sh, dr, RES_OK, AUTH)
def only_one_cell(o, sh):
    assert sh.writes == [{"range": "'Idea Queue'!S4", "value": canonical(FID)}], sh.writes
    for i, r in enumerate(sh.rows):
        for j, v in enumerate(r):
            if (i, j) != (2, 18): assert v == snap[i][j], ("cell changed", i, j)
    assert o["verification"]["post_write_verified"] is True and o["after"]["render_source_path"] == canonical(FID)
T(1, "approved+verified+authorized", o, "UPDATED", True, sh, dr, only_one_cell)
# 2 no authorization
sh, dr = sheet(), drive(); T(2, "no authorization", run("1901-003", sh, dr, RES_OK, None), "AWAITING_AUTHORIZATION", False, sh, dr)
# 3 resolver not RESOLVED
sh, dr = sheet(), drive(); T(3, "resolver AMBIGUOUS", run("1901-003", sh, dr, {"result": "AMBIGUOUS", "human_action_required": "Jody or Ame: record which of the listed files is the approved artwork for this design, then re-run."}, AUTH), "SOURCE_NOT_RESOLVED", False, sh, dr)
# 4 blank human_decision
sh, dr = sheet(hd=""), drive(); T(4, "blank human_decision", run("1901-003", sh, dr, RES_OK, AUTH), "HUMAN_APPROVAL_REQUIRED", False, sh, dr)
# 5 REVISE
sh, dr = sheet(hd="REVISE"), drive(); T(5, "REVISE", run("1901-003", sh, dr, RES_OK, AUTH), "HUMAN_APPROVAL_REQUIRED", False, sh, dr)
# 6 REJECT
sh, dr = sheet(hd="REJECT"), drive(); T(6, "REJECT", run("1901-003", sh, dr, RES_OK, AUTH), "HUMAN_APPROVAL_REQUIRED", False, sh, dr)
# 7 existing different value
sh, dr = sheet(rsp="https://drive.google.com/file/d/1OLDfileAAAAAAAAAAAAAAAAAAAAAAAAAA/view"), drive()
T(7, "existing different", run("1901-003", sh, dr, RES_OK, AUTH), "SOURCE_ALREADY_SET_CONFLICT", False, sh, dr)
# 8 existing identical
sh, dr = sheet(rsp=canonical(FID)), drive(); T(8, "existing identical", run("1901-003", sh, dr, RES_OK, AUTH), "ALREADY_SET", False, sh, dr)
# 9 duplicate id
sh, dr = sheet(), drive(); sh.rows.append(row("1901-003")); T(9, "duplicate id", run("1901-003", sh, dr, RES_OK, AUTH), "DUPLICATE_ID", False, sh, dr)
# 10 unknown columns preserved (checked inside test 1's cell diff too)
sh, dr = sheet(), drive(); o = run("1901-003", sh, dr, RES_OK, AUTH)
def unk(o, sh):
    assert sh.rows[2][15] == "simple" and sh.rows[2][23] == "2"
    assert any(c["check"] == "unknown_columns" and "X (header 'wave') = '2'" in c["detail"] for c in o["checks"])
T(10, "unknown columns preserved", o, "UPDATED", True, sh, dr, unk)
# 11 column P 'simple' unchanged
sh, dr = sheet(), drive(); o = run("1901-003", sh, dr, RES_OK, AUTH)
T(11, "column P unchanged", o, "UPDATED", True, sh, dr, lambda o, sh: (sh.rows[2][15] == "simple") or sys.exit("P changed"))
# 12 post-write reread confirms fields unchanged
sh, dr = sheet(), drive(); o = run("1901-003", sh, dr, RES_OK, AUTH)
def reread(o, sh):
    c = [c for c in o["checks"] if c["check"] == "post_write_reread"][0]; assert c["status"] == "PASS"
    assert sh.rows[2][16] == "APPROVE" and sh.rows[2][5] == "Approved" and sh.rows[2][8] == canonical(FID) and sh.rows[2][17] == "" and sh.rows[2][22] == ""
T(12, "post-write reread", o, "UPDATED", True, sh, dr, reread)
# 13 failed post-write verification: exactly one write, no retry
sh, dr = sheet(), drive(); sh.fail_next_write = True; o = run("1901-003", sh, dr, RES_OK, AUTH)
T(13, "failed verification, no retry", o, "WRITE_FAILED", True, sh, dr, lambda o, sh: (len(sh.writes) == 1 and o["verification"]["post_write_verified"] is False) or sys.exit("retry!"))
# 14/15: no Drive / Printify / Etsy mutation — asserted in every T() via dr.mutations; ref.py has no such calls
import inspect, re as _re
src = inspect.getsource(sys.modules["ref"])
assert not _re.search(r"printify\w*\(|etsy\w*\(|drive\.\w*(update|delete|create|move|copy|upload|rename)", src, _re.I), "forbidden call in ref"
print("14. PASS no Drive mutation (harness Drive has no write path; mutations list empty in every case)")
print("15. PASS no Printify/Etsy mutation (no such call exists in the reference)")
# extra: SOURCE_UNAVAILABLE and NOT_FOUND and SOURCE_MISMATCH
sh, dr = Sheet(list(HDR), [], readable=False), drive(); T(16, "sheet unreadable", run("1901-003", sh, dr, RES_OK, AUTH), "SOURCE_UNAVAILABLE", False, sh, dr)
sh, dr = sheet(), drive(); T(17, "not found", run("1901-999", sh, dr, RES_OK, AUTH), "NOT_FOUND", False, sh, dr)
sh, dr = sheet(), drive(); T(18, "proposed value mismatch", run("1901-003", sh, dr, RES_OK, AUTH, proposed_value="https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz012345"), "SOURCE_MISMATCH", False, sh, dr)
sh, dr = sheet(), Drive({}); T(19, "file gone", run("1901-003", sh, dr, RES_OK, AUTH), "SOURCE_MISMATCH", False, sh, dr)
sh, dr = sheet(rsp=canonical(FID) + "?usp=sharing"), drive(); T(20, "same file, non-canonical existing", run("1901-003", sh, dr, RES_OK, AUTH), "SOURCE_ALREADY_SET_CONFLICT", False, sh, dr)
print("ALL PASS")
if "--dump" in sys.argv:
  for n in (1, 2, 4, 3, 7, 8, 13, 9):
      open(f"ex{n}.json", "w").write(json.dumps(examples[n], indent=1, ensure_ascii=False) + "\n")
