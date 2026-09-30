---
name: 1901-set-production-source
description: Records the verified production source URL in one 1901 Idea Queue row's render_source_path; the only write it may make.
---

# 1901 Set Production Source

Safely records the verified production source file for exactly one 1901 Main
Street design. It is the first Walter skill that may change anything, and its
only permitted change is one cell: the design's `render_source_path` in the
live Idea Queue. It never writes any other field, any other row, any Drive
file, any document, or any external system.

Core rule: **VERIFY, DON'T ASSUME.** This skill does not discover artwork and
does not choose artwork. It records a decision that was already made and
already verified by evidence read in the current run: the live queue row says
the human approved the design, `1901-resolve-production-source` resolved
exactly one file, Drive confirms that file exists, and the current run
contains the exact authorization command for this design. If any of that is
missing, it writes nothing and says why.

## When to Use

Trigger on requests such as:

- "Set the production source for 1901-003."
- "Prepare the production source for 1901-003."
- "Show me the production source for 1901-003."
- "Record the production source for <design_id>."
- `AUTHORIZE SOURCE WRITE 1901-003`

The skill has two steps, and every ordinary request is step 1 only.

- **Step 1, proposal.** Any request to inspect, prepare, set up, resolve,
  show, propose, set, fix, update, or use the production source runs every
  read-only check and, when the row is eligible, returns
  `AWAITING_AUTHORIZATION` with `write_performed = false`, naming the exact
  canonical URL that would be written and the exact command that would
  authorise it. It mutates nothing.
- **Step 2, authorised write.** Only a run whose user message is exactly
  `AUTHORIZE SOURCE WRITE <design_id>` (see Authorization) may write, and
  only after every live check is re-run from scratch in that run and still
  passes.

Expected flow inside Walter: queue read → resolve production source → human
approval → **set production source** (step 1, then step 2) → validate
readiness. Do not use it to find a file (`1901-resolve-production-source`),
to read a row alone (`1901-read-idea-queue`), or to judge readiness
(`1901-validate-readiness`).

"Set the production source for 1901-003", "fix the source", "update the
source", "use the resolved source", "looks good", "proceed", "do it", and
"sounds good" never cause a write. They may start the checks; they never
satisfy authorisation.

## Authoritative Sheet

| Field | Value |
|---|---|
| Spreadsheet ID | `1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0` |
| Worksheet | `Idea Queue` |
| Sheet ID (gid) | `1283408381` |

Never substitute a duplicate, historical, exported, cached, or similarly
named Idea Queue. If this exact spreadsheet and worksheet cannot be read, the
result is `SOURCE_UNAVAILABLE` and nothing else is tried. Map columns by the
header text read in this run, never by remembered positions. Columns O and P
are outside the standard record (P holds values such as `simple` in some
rows); they and any other unrecognised column are unknown columns: preserve
them, never modify them, and list them in `checks` for audit context.

## The Only Allowed Mutation

| | |
|---|---|
| Cell | `render_source_path` of the single matched row |
| Value | the canonical Google Drive file URL of the verified source: `https://drive.google.com/file/d/<file id>/view` |
| Request | exactly one single-cell update; no other cell, row, or range in the request |

The value is always built from the verified file id. Never write a bare Drive
file id, a folder URL, a sharing-link variant, or a value the user typed. Never
write `art_path` unless it is, independently and in this run, the exact
resolved production source (which makes it the same canonical URL anyway).

Never modify `id`, `concept`, `season`, `style`, `vibe`, `status`,
`idea_notes`, `image_prompt`, `art_path`, `art_gens`, `printify_id`,
`etsy_url`, `notes`, `removed_reason`, `human_decision`, `render_status`,
`render_output_folder`, `render_notes`, `render_updated_at`, `render_qa`,
column P, any unknown column, or any other spreadsheet cell.

Never: edit, move, rename, upload, or delete Drive files; edit documentation,
Open Items, or the Decision Log; call Printify or Etsy; publish products;
render images; change or infer human approval; choose between candidate source
files; resolve documentation conflicts; write to an audit table (audit logging
is designed separately; this skill carries its audit data in its response).

## Authorization

The only user-authored text that authorises the write is the exact command:

```
AUTHORIZE SOURCE WRITE <design_id>
```

for example `AUTHORIZE SOURCE WRITE 1901-003`. Rules:

- Exact structure: the three words, then the design id, nothing else. Trim
  surrounding whitespace; the three words compare case-insensitively
  (`authorize source write 1901-003` authorises). Prose around the command,
  a missing id, a reordered or shortened phrase, or any other wording does
  not authorise.
- The id must equal the target design id exactly. `AUTHORIZE SOURCE WRITE
  1901-004` while working on `1901-003` authorises nothing: not `1901-003`,
  and not `1901-004` either. Say so in `checks` and return
  `AWAITING_AUTHORIZATION` for the target.
- The command must appear in the **current run**. Authorization from an
  earlier turn or run, a remembered "yes", or the fact that the user just
  asked to set the source is not authorisation. The command is consumed by
  the run that receives it and never becomes standing permission.
- A run that receives the command still runs every live check from scratch.
  Nothing from a prior run is reused as evidence. The write happens only if
  every check still passes in this run.
- After `WRITE_FAILED`, any later attempt needs a new command in a new run.
  The skill itself never retries.

Not authorisation: `AUTHORIZE WRITE 1901-003`, `AUTHORIZE SOURCE 1901-003`,
`AUTHORIZE SOURCE WRITE` (no id), `AUTHORIZE SOURCE WRITE 1901-004` (wrong
id), "Yes, authorize it", "Set it", "Proceed", "Do it".

## Input

Exactly one `design_id`, for example `1901-003`. In a step 2 run the id in
the command is the target, unless the run was invoked for a specific design,
in which case the command's id must match it. Trim surrounding whitespace
from the user's input, and nothing else. Match by exact string equality: no
case folding, no fuzzy match, no closest id, no normalising `1901-3` into
`1901-003`. No usable single id: `NOT_FOUND` with a `human_action_required`
asking for one.

Optionally, a value the user asked to write. It is checked against the
verified canonical URL and is never used as the value itself.

## Procedure

Checks run in this order. The first failing check ends the run with its
result and no write. Every check performed is recorded in `checks` as
`{check, status, detail}` with status `PASS`, `FAIL`, or `INFO`.

1. **Queue read.** Run `1901-read-idea-queue` for the id, live, in this run.
   `SOURCE_UNAVAILABLE` or `SCHEMA_WARNING` → `SOURCE_UNAVAILABLE`.
   `NOT_FOUND` → `NOT_FOUND`. `DUPLICATE_ID` → `DUPLICATE_ID`; never pick one
   row. If the `render_source_path` or `human_decision` column is absent or
   duplicated in the live header row (the read skill returns `null` for the
   field), the sheet cannot be used safely → `SOURCE_UNAVAILABLE`. Record
   the row number, the whole record (it is the before-image for step 8), and
   the unknown columns.
2. **Human approval.** The live cell must be exactly `APPROVE`: case-sensitive,
   no trimming, no synonyms. Anything else, including blank, `REVISE`,
   `REJECT`, `Approve`, or `APPROVED` → `HUMAN_APPROVAL_REQUIRED`. Never
   infer approval from `status = Approved`, notes, prior chat, memory,
   `art_path`, or Printify state.
3. **Source resolution.** Run `1901-resolve-production-source` live, in this
   run. Only `RESOLVED` continues. `SOURCE_UNAVAILABLE` passes through as
   `SOURCE_UNAVAILABLE`. `DOCUMENTATION_CONFLICT`, `AMBIGUOUS`, `NOT_FOUND`,
   `UNVERIFIED`, or `INVALID_RECORD` → `SOURCE_NOT_RESOLVED`, carrying the
   resolver's `human_action_required`. A `RESOLVED` result whose
   `resolved_file` lacks `drive_file_id`, `name`, `url`, or `mime_type` is
   also `SOURCE_NOT_RESOLVED`.
4. **File identity.** The canonical URL is
   `https://drive.google.com/file/d/<drive_file_id>/view`. The resolver's
   `url` must carry that same file id. Read the file's metadata from Drive:
   Drive unreadable → `SOURCE_UNAVAILABLE`; file missing, trashed, or
   inaccessible, or its live name or MIME type differs from the resolver's →
   `SOURCE_MISMATCH`. If the user supplied a value to write and it is not
   byte-equal to the canonical URL → `SOURCE_MISMATCH`.
5. **Existing value.** Blank `render_source_path` → eligible. Byte-equal to
   the canonical URL → `ALREADY_SET`, `write_performed = false`, nothing
   rewritten. Any other non-blank value → `SOURCE_ALREADY_SET_CONFLICT`,
   nothing overwritten, human review required. A different form of the same
   file (for example with `?usp=sharing`) is still a different value; say so
   in the check detail, but do not decide which wins.
6. **Authorization.** Only now, after every read-only check has passed in
   this run. The current run's user message must be exactly
   `AUTHORIZE SOURCE WRITE <design_id>` for this target id (Authorization
   section). Ordinary source-write requests, vague confirmations, a command
   for another id, and any authorization from an earlier run never count.
   Missing → `AWAITING_AUTHORIZATION`, `write_performed = false`, with
   `human_action_required` naming the exact canonical URL that would be
   written and the exact command `AUTHORIZE SOURCE WRITE <design_id>`.
   Present → record the command text verbatim in `authorization.evidence`.
7. **Write.** One update request that sets the single cell
   `render_source_path` of the matched row to the canonical URL. Use the
   column letter read from the live header row and the matched row number.
   Nothing else in the request. `write_performed` becomes `true` when the
   request was issued and reported success.
8. **Post-write verification.** Re-read the exact same row with
   `1901-read-idea-queue`. Confirm `render_source_path` equals the canonical
   URL, and that `human_decision`, `status`, `art_path`, `render_status`,
   `render_qa`, every other expected field, and every unknown column are
   unchanged from the before-image. Match → `UPDATED`,
   `post_write_verified = true`. Row unreadable, or anything differs →
   `WRITE_FAILED`, `post_write_verified = false`, `after` carrying what the
   re-read actually shows (`null` if it could not be read), and a
   `human_action_required` telling a human to inspect the row. **Never retry
   the write.** One request per run, ever.

If the write request itself errors, `write_performed` is `false`; still
re-read once and return `WRITE_FAILED` with what the row shows.

## Output

Return exactly one JSON object and nothing in prose that contradicts it:

```json
{
  "design_id": "",
  "result": "",
  "write_performed": false,
  "timestamp": "ISO 8601 UTC time of this run",
  "source": { "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0", "sheet_name": "Idea Queue", "sheet_id": "1283408381", "row_number": null },
  "before": { "render_source_path": "" },
  "after": { "render_source_path": "" },
  "verification": { "human_decision": "", "source_resolution": "", "source_file_id": "", "source_file_name": "", "source_url": "", "post_write_verified": false },
  "authorization": { "received": false, "evidence": "" },
  "checks": [ { "check": "", "status": "PASS | FAIL | INFO", "detail": "" } ],
  "human_action_required": null
}
```

Shape rules:

- `before` and `after` hold the live `render_source_path` as read before and
  after the run; `after` equals `before` whenever no write happened, and is
  `null` only when the post-write re-read failed. Both are `null` when no row
  was read.
- `verification.source_url` is the canonical URL that was, or would be,
  written. `source_resolution` is the resolver's result verbatim.
- `checks` is the audit trail: design id, row number, unknown columns, the
  exact cell and value written, and the re-read outcome all appear here.
  Together with `timestamp`, `before`, `after`, `verification`, and
  `authorization`, this is the audit record; there is no separate audit
  write.
- `human_action_required` is `null` for `UPDATED` and `ALREADY_SET`, and one
  plain sentence otherwise.

## Results

| result | write | meaning |
|---|---|---|
| `UPDATED` | yes | One cell written and confirmed by re-read; nothing else changed |
| `ALREADY_SET` | no | `render_source_path` already equals the canonical URL |
| `AWAITING_AUTHORIZATION` | no | All checks pass; no explicit authorisation for this write in this conversation |
| `NOT_FOUND` | no | No row carries the id exactly (or no usable id was supplied) |
| `DUPLICATE_ID` | no | More than one row carries the id; none chosen |
| `HUMAN_APPROVAL_REQUIRED` | no | `human_decision` is not exactly `APPROVE` |
| `SOURCE_NOT_RESOLVED` | no | The resolver did not return a complete `RESOLVED` |
| `SOURCE_ALREADY_SET_CONFLICT` | no | `render_source_path` holds a different value; human review |
| `SOURCE_MISMATCH` | no | The file cannot be confirmed in Drive, or the proposed value is not the resolved file |
| `WRITE_FAILED` | issued | The write was issued but the re-read does not confirm it; no retry |
| `SOURCE_UNAVAILABLE` | no | The authoritative sheet, Drive, or a resolver source could not be read; nothing substituted |

## Pitfalls

- **"Set the source" with no id, or with the id only implied.** No write.
  Ask for the exact design id.
- **"Set the production source for 1901-003."** That is a step 1 request.
  Run the checks, propose the value, return `AWAITING_AUTHORIZATION`. It is
  never authorisation, however clearly it names the design.
- **"Proceed" or "Yes, authorize it" after a proposal.** Not the command.
  `AWAITING_AUTHORIZATION` again, naming the exact command.
- **The user authorised last turn, and this turn says "do it".** The command
  was consumed by that run. `AWAITING_AUTHORIZATION`.
- **`AUTHORIZE SOURCE WRITE 1901-004` arrives while 1901-003 is the target.**
  Authorises nothing. Do not switch designs, do not write either one.
- **`status` is `Approved` but `human_decision` is blank.** `HUMAN_APPROVAL_REQUIRED`.
- **The user pastes a Drive URL and says write that.** It is checked against
  the resolved file; if it differs, `SOURCE_MISMATCH`. The user cannot
  substitute a file through this skill.
- **The existing value points at the same file with `?usp=sharing`.** Still
  `SOURCE_ALREADY_SET_CONFLICT`. A human normalises it, not Walter.
- **The write reported success but the re-read shows the old value.**
  `WRITE_FAILED`, no second request, tell a human to inspect the row.
- **Only one write is allowed, so batch two designs into one run.** Never.
  One design id per run.

## Live Test Policy

Building, reviewing, or importing this skill never authorises a live
mutation. Fixture tests are the development verification. The first live
write is performed through Walter, after import, only when Jody separately
and explicitly authorises that specific test.

## Examples

Values are fixtures showing shape and logic; the fixture sheet has the
standard headers plus a blank-header column P holding `simple` and an unknown
column X headed `wave`. Live output always carries what was actually read.
`timestamp` is fixed in the fixtures.

### A. Proposal only: AWAITING_AUTHORIZATION

Input: `Set the production source for 1901-003.` Every check passes and the cell is blank; the run proposes the value and the exact command, and writes nothing.

```json
{
 "design_id": "1901-003",
 "result": "AWAITING_AUTHORIZATION",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": ""
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": false
 },
 "authorization": {
  "received": false,
  "evidence": ""
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "PASS",
   "detail": "render_source_path is blank; eligible for write"
  },
  {
   "check": "authorization",
   "status": "FAIL",
   "detail": "the current run does not contain the exact command AUTHORIZE SOURCE WRITE 1901-003; ordinary requests and vague confirmations never authorize a write"
  }
 ],
 "human_action_required": "No write performed. Row 4 is eligible: render_source_path would be set to https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view. To authorize exactly this write, send exactly: AUTHORIZE SOURCE WRITE 1901-003"
}
```

### B. Authorised write: UPDATED

Input: `AUTHORIZE SOURCE WRITE 1901-003`, in a new run. Every live check is re-run from scratch, one cell is written, the row is re-read.

```json
{
 "design_id": "1901-003",
 "result": "UPDATED",
 "write_performed": true,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": true
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "PASS",
   "detail": "render_source_path is blank; eligible for write"
  },
  {
   "check": "authorization",
   "status": "PASS",
   "detail": "current run contains the exact command: AUTHORIZE SOURCE WRITE 1901-003"
  },
  {
   "check": "write",
   "status": "PASS",
   "detail": "one update request: 'Idea Queue'!S4 = https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "post_write_reread",
   "status": "PASS",
   "detail": "render_source_path equals the intended URL; human_decision, status, art_path, render_status, render_qa and every other field are unchanged"
  }
 ],
 "human_action_required": null
}
```

### C. Wrong design id: AWAITING_AUTHORIZATION

Target `1901-003`; input `AUTHORIZE SOURCE WRITE 1901-004`. Not reinterpreted for either design; nothing written.

```json
{
 "design_id": "1901-003",
 "result": "AWAITING_AUTHORIZATION",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": ""
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": false
 },
 "authorization": {
  "received": false,
  "evidence": ""
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "PASS",
   "detail": "render_source_path is blank; eligible for write"
  },
  {
   "check": "authorization",
   "status": "FAIL",
   "detail": "the command names 1901-004, not the target 1901-003; it authorizes nothing in this run"
  }
 ],
 "human_action_required": "No write performed. Row 4 is eligible: render_source_path would be set to https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view. To authorize exactly this write, send exactly: AUTHORIZE SOURCE WRITE 1901-003"
}
```

### D. Vague confirmation: AWAITING_AUTHORIZATION

Input: `Proceed.` after the proposal in Example A.

```json
{
 "design_id": "1901-003",
 "result": "AWAITING_AUTHORIZATION",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": ""
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": false
 },
 "authorization": {
  "received": false,
  "evidence": ""
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "PASS",
   "detail": "render_source_path is blank; eligible for write"
  },
  {
   "check": "authorization",
   "status": "FAIL",
   "detail": "the current run does not contain the exact command AUTHORIZE SOURCE WRITE 1901-003; ordinary requests and vague confirmations never authorize a write"
  }
 ],
 "human_action_required": "No write performed. Row 4 is eligible: render_source_path would be set to https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view. To authorize exactly this write, send exactly: AUTHORIZE SOURCE WRITE 1901-003"
}
```

### E. HUMAN_APPROVAL_REQUIRED

`human_decision` is blank. `REVISE` and `REJECT` end the same way.

```json
{
 "design_id": "1901-003",
 "result": "HUMAN_APPROVAL_REQUIRED",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": ""
 },
 "verification": {
  "human_decision": "",
  "source_resolution": "",
  "source_file_id": "",
  "source_file_name": "",
  "source_url": "",
  "post_write_verified": false
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "FAIL",
   "detail": "human_decision is '', not exactly APPROVE"
  }
 ],
 "human_action_required": "A human must set human_decision to APPROVE for 1901-003 in the live Idea Queue before its production source can be recorded."
}
```

### F. SOURCE_NOT_RESOLVED

The resolver returned `AMBIGUOUS`.

```json
{
 "design_id": "1901-003",
 "result": "SOURCE_NOT_RESOLVED",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": ""
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "AMBIGUOUS",
  "source_file_id": "",
  "source_file_name": "",
  "source_url": "",
  "post_write_verified": false
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "FAIL",
   "detail": "1901-resolve-production-source returned AMBIGUOUS; only RESOLVED permits a write"
  }
 ],
 "human_action_required": "Jody or Ame: record which of the listed files is the approved artwork for this design, then re-run."
}
```

### G. SOURCE_ALREADY_SET_CONFLICT

`render_source_path` already names a different file.

```json
{
 "design_id": "1901-003",
 "result": "SOURCE_ALREADY_SET_CONFLICT",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": "https://drive.google.com/file/d/1OLDfileAAAAAAAAAAAAAAAAAAAAAAAAAA/view"
 },
 "after": {
  "render_source_path": "https://drive.google.com/file/d/1OLDfileAAAAAAAAAAAAAAAAAAAAAAAAAA/view"
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": false
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "FAIL",
   "detail": "render_source_path is already 'https://drive.google.com/file/d/1OLDfileAAAAAAAAAAAAAAAAAAAAAAAAAA/view', which differs from 'https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view'"
  }
 ],
 "human_action_required": "render_source_path for 1901-003 already holds a different value; a human must decide which value is correct and change the cell manually. Walter will not overwrite it."
}
```

### H. ALREADY_SET

`render_source_path` already equals the canonical URL.

```json
{
 "design_id": "1901-003",
 "result": "ALREADY_SET",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
 },
 "after": {
  "render_source_path": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": false
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "PASS",
   "detail": "render_source_path already equals the canonical URL; nothing to write"
  }
 ],
 "human_action_required": null
}
```

### I. WRITE_FAILED

The update reported success but the re-read still shows a blank cell. One request, no retry.

```json
{
 "design_id": "1901-003",
 "result": "WRITE_FAILED",
 "write_performed": true,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": 4
 },
 "before": {
  "render_source_path": ""
 },
 "after": {
  "render_source_path": ""
 },
 "verification": {
  "human_decision": "APPROVE",
  "source_resolution": "RESOLVED",
  "source_file_id": "1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh",
  "source_file_name": "1901-003-redraw-c-stamp.png",
  "source_url": "https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view",
  "post_write_verified": false
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "PASS",
   "detail": "exactly one row (sheet row 4) carries id 1901-003"
  },
  {
   "check": "unknown_columns",
   "status": "INFO",
   "detail": "preserved, not modified: P (header '') = 'simple'; X (header 'wave') = '2'"
  },
  {
   "check": "human_approval",
   "status": "PASS",
   "detail": "human_decision is exactly APPROVE"
  },
  {
   "check": "source_resolution",
   "status": "PASS",
   "detail": "RESOLVED: 1901-003-redraw-c-stamp.png (id 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh, image/png)"
  },
  {
   "check": "file_identity",
   "status": "PASS",
   "detail": "Drive file 1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh exists and matches; canonical URL https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "existing_value",
   "status": "PASS",
   "detail": "render_source_path is blank; eligible for write"
  },
  {
   "check": "authorization",
   "status": "PASS",
   "detail": "current run contains the exact command: AUTHORIZE SOURCE WRITE 1901-003"
  },
  {
   "check": "write",
   "status": "PASS",
   "detail": "one update request: 'Idea Queue'!S4 = https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view"
  },
  {
   "check": "post_write_reread",
   "status": "FAIL",
   "detail": "render_source_path is '', expected 'https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view'"
  }
 ],
 "human_action_required": "Inspect Idea Queue row 4 for 1901-003 manually and correct it by hand: render_source_path is '', expected 'https://drive.google.com/file/d/1R4GEuXOqzjUdjESKyEo8sGemAwV2ThIh/view'. No retry was attempted."
}
```

### J. DUPLICATE_ID

Two rows carry the id.

```json
{
 "design_id": "1901-003",
 "result": "DUPLICATE_ID",
 "write_performed": false,
 "timestamp": "2026-09-30T23:58:00Z",
 "source": {
  "spreadsheet_id": "1UxnZsA9aWlxZHqMAt17_7HAe86w_cHcMik3xpXQrfq0",
  "sheet_name": "Idea Queue",
  "sheet_id": "1283408381",
  "row_number": null
 },
 "before": {
  "render_source_path": null
 },
 "after": {
  "render_source_path": null
 },
 "verification": {
  "human_decision": null,
  "source_resolution": "",
  "source_file_id": "",
  "source_file_name": "",
  "source_url": "",
  "post_write_verified": false
 },
 "authorization": {
  "received": true,
  "evidence": "AUTHORIZE SOURCE WRITE 1901-003"
 },
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "design_id '1901-003' (trimmed)"
  },
  {
   "check": "queue_read",
   "status": "FAIL",
   "detail": "rows [4, 5] all carry id 1901-003; none chosen"
  }
 ],
 "human_action_required": "Resolve the duplicate Idea Queue rows for 1901-003 (rows 4, 5), then re-run."
}
```

## Verification

The skill worked if the reply is one JSON object in the shape above; at most
one update request was issued in the run and it targeted only the
`render_source_path` cell of the matched row; that run's user message was
exactly `AUTHORIZE SOURCE WRITE <design_id>` for that row's id; the value
written is a full canonical Drive file URL; every `UPDATED` was confirmed by
a re-read of the same row; no `WRITE_FAILED` was followed by a second request; and no Drive
file, document, other cell, or external system changed during the run.
