# ShopNest Global — AI Ticket Intelligence POC (n8n)

An n8n workflow that reads raw customer support tickets, summarises each one,
drafts a customer reply, scores **both** with an LLM-as-a-Judge, and writes a
single consolidated file plus a human-review queue.

Built for the No-Code track of the Support Ticket Analysis project.

---

## ⚠️ Read this first — what is and is not proven

| Thing | Status |
|---|---|
| Workflow graph executes end to end, 30/30 tickets | **Proven** — run from the n8n UI, every node green |
| All 35 output columns populated in all 30 rows | **Proven** — verified by reading the CSV |
| Error logging catches bad LLM output | **Proven** — by deliberate fault injection, see below |
| Consolidated CSV + review-queue CSV written to disk | **Proven** |
| **Quality of the summaries, replies and judge scores** | **NOT PROVEN** |

Every test run so far used a **mock OpenAI endpoint** (`mock_openai_server.py`),
because no OpenAI API key was available during the build. The mock returns
correctly-shaped JSON built from regex heuristics — enough to prove every wire,
expression and file write, and nothing at all about how good the model output is.

**That is why every generated field in the sample output says `[MOCK]`.**
Point the credential at a real key and re-run to get real content. Nothing in the
workflow changes — only the credential.

---

## What it does

```
Manual Trigger
  └─ Pipeline Config            ← the only node you edit per environment
      └─ Read Ticket CSV
          └─ Parse CSV to Rows                      (RUBRIC 1: Data Loading)
              └─ Clean & Profile Tickets
                  └─ Loop Over Tickets  ── per ticket ──┐
                                                        │
        ┌───────────────────────────────────────────────┘
        │  Summarise Ticket        gpt-4o-mini, temp 0.2  (RUBRIC 2)
        │  Judge Summary           gpt-4o-mini, temp 0.0  (RUBRIC 3)
        │  Generate Response       gpt-4o-mini, temp 0.4  (RUBRIC 4)
        │  Judge Response          gpt-4o-mini, temp 0.0  (RUBRIC 5)
        │  Consolidate Ticket Record                      (RUBRIC 6)
        └──────────────── back to Loop ─────────────────┘

  after all 30 tickets, the loop's "done" output fans out to three branches:
      • Build + Save Consolidated CSV      → all 30 rows, 35 columns
      • Filter → Build + Save Review Queue → only rows needing a human
      • Pipeline Quality Stats             → the numbers for RUBRIC 7
```

## Design decisions worth explaining in the deck

**Model — `gpt-4o-mini` on all four calls.** These are bounded extraction,
classification and short-form writing tasks against a fixed policy set, not open
reasoning. A larger model costs several times more per ticket, and at ShopNest's
peak of 15,000 tickets/day × 4 calls that difference dominates the business case.
Start small; the judge scores tell you objectively whether you need to upgrade,
which is the whole point of building evaluation in from day one.

**Temperature is different at every stage, on purpose.**
- Summarise `0.2` — extraction. Creativity here means invented order IDs.
- Judges `0.0` — a score that changes between runs is not a measurement. Graders
  and auditors need the same ticket to produce the same score.
- Respond `0.4` — enough variation for natural, non-robotic prose, while the
  system message keeps every policy binding.

**Prompting technique — role-based zero-shot with a strict JSON schema and
explicit negative rules.** Few-shot was deliberately rejected: with 12 issue
categories and highly varied ticket styles, any small set of examples biases the
model toward the shapes it was shown. Instead each system message pins a role, an
exhaustive enum, a hard "never invent" rule, and an exact output schema. The
`NOT_PROVIDED` convention means the model has a correct answer available when a
field is genuinely absent, which is what stops it hallucinating an order ID.

**Two judges, not one.** Summarisation and response generation fail in different
ways — a summary fails by being unfaithful or unactionable, a reply fails by
breaking policy or inventing a promise. One shared rubric would measure neither
well. Both judges are told they are auditing, not rewriting, and are explicitly
instructed not to penalise correct behaviour (marking a field `NOT_PROVIDED`,
declining to offer compensation, asking for missing details).

**Fail closed.** Any row where either judge says `REVIEW`, or the response stage
self-flags, or any stage returned unusable output, goes to the human queue. The
system's job is to save agent time on the easy 80%, never to quietly send a bad
reply.

---

## Which n8n version this needs

Built on n8n 2.35, but every node is deliberately pinned to an older `typeVersion`
so it imports into 1.x instances too:

| Node | typeVersion |
|---|---|
| `manualTrigger` | 1 |
| `set` | 3.4 |
| `readWriteFile` ×3 | 1 |
| `extractFromFile` | 1 |
| `code` ×3 | 2 |
| `splitInBatches` | 3 |
| `@n8n/n8n-nodes-langchain.openAi` ×4 | 1.8 |
| `convertToFile` ×2 | 1.1 |
| `filter` | 2.2 |

The binding constraint is the OpenAI node at 1.8, so **anything from roughly n8n
1.60 onward will import cleanly.** If a node shows up as unrecognised after
import, the instance is older than that — send me the version from the bottom-left
of the n8n screen and I'll downgrade the affected nodes.

## Which LLM credential

n8n does not do the summarising itself — it calls out to a provider. The four
OpenAI nodes need a credential. In order of preference:

1. **A credential the lab already provides.** Check Credentials in the left
   sidebar for an existing "OpenAI account" before doing anything else.
2. **n8n's own free AI credits**, if the trial offers them in the credential
   dropdown.
3. **Your own key** from platform.openai.com, only if neither exists.

Cost is not the issue: 30 tickets × 4 calls = 120 calls on `gpt-4o-mini` is a few
cents. The only friction is OpenAI's minimum top-up.

A different provider is a node swap, not a rebuild — the prompts and the whole
downstream graph are provider-agnostic.

## Running it

### 1. Import
n8n → Workflows → Import from File → `ShopNest_Ticket_Intelligence.json`

### 2. Set the OpenAI credential
Open each of the four OpenAI nodes and pick your own credential from the
dropdown. The exported JSON references a credential ID (`SHOPNEST_OPENAI`) that
will not exist in your instance — this is expected, you just select yours.

### 3. Point at your data
Open **Pipeline Config** — the only node you edit — and set:
- `input_csv_path` → where `support_ticket_data.csv` lives
- `output_dir` → an existing, writable folder

Defaults are `/data/support_ticket_data.csv` and `/data/output`, which is the
standard mount in a Docker n8n. **Create the output folder first** — n8n will not
create it for you.

If reads fail with *"Access to the file is not allowed"*, your instance has
`N8N_RESTRICT_FILE_ACCESS_TO` set. Put the CSV inside the allowed folder, or use
paths that resolve inside it. Note n8n resolves symlinks, so use the real path.

### 4. Run
Click **Execute workflow**. 30 tickets × 4 LLM calls = 120 calls, so expect a few
minutes on a real endpoint.

Two files land in `output_dir`:
- `shopnest_ticket_intelligence_output.csv` — 30 rows × 35 columns
- `shopnest_human_review_queue.csv` — the subset a human must check

### 5. To run nightly instead
Replace **Run Pipeline (On Demand)** with a Schedule Trigger and connect it to
**Pipeline Config**. Nothing else changes.

---

## Editing the prompts

The four system messages live in `prompts/` as plain text. Edit them there, then:

```bash
python3 build_workflow.py                    # regenerates the shipping JSON
python3 build_workflow.py --local <dir>      # a copy with local test paths
```

Re-import the regenerated JSON. Editing prompts inside a 37KB JSON blob by hand
is how mistakes happen, so the generator is the supported path.

---

## Proving the error handling actually works

An always-empty `pipeline_errors` column is indistinguishable from error logging
that never fires. So it was tested against deliberate faults:

```bash
MOCK_FAULT=1 python3 mock_openai_server.py    # then run the workflow
```

This makes ticket 5 return prose instead of JSON, and ticket 23 return valid JSON
of the wrong shape. Result:

```
ticket  5: summary_unparseable; summary_judge_unparseable;
           response_unparseable; response_judge_unparseable      → review=YES
ticket 23: response_judge_missing:relevance/empathy_and_tone/...  → review=YES

review queue grew from 6 rows to 8 — exactly the two faulted tickets
```

The second case is the one that matters. A model returning `{"score": 4}` parses
as perfectly valid JSON and originally produced a row of **silent blank score
columns with no error recorded anywhere**. That is why `Consolidate Ticket Record`
validates the *shape* of every stage's output, not just that it parsed.

---

## Files

```
ShopNest_Ticket_Intelligence.json   the workflow — this is what you import
build_workflow.py                   regenerates the JSON from prompts/
prompts/01_summarise_system.txt     triage / summarisation system message
prompts/02_judge_summary_system.txt LLM-as-a-Judge for the summary
prompts/03_respond_system.txt       reply drafting + the 10 ShopNest policies
prompts/04_judge_response_system.txt LLM-as-a-Judge for the reply
mock_openai_server.py               mock endpoint for wiring tests, NOT for real runs
capture_run.py                      executes from the UI and screenshots it
data/support_ticket_data.csv        the 30 source tickets
output/                             sample output (generated against the MOCK)
screenshots/                        canvas, node configs, execution results
```

---

## Open question: the policies are assumed

The brief says to "embed all policies accurately in the system message" but does
not supply a policy document. The ten policies in
`prompts/03_respond_system.txt` (refund SLA 3–5 business days, 10-day electronics
return window, free pickup on damaged goods, no goodwill without a human, and so
on) were inferred from what customers reference in the 30 tickets — ticket 21
cites the 3–5 day refund SLA, ticket 22 the 10-day return window.

**If the course's solution-approach document contains a real policy list, replace
that block.** The judge's policy list in `04_judge_response_system.txt` mirrors it
and must be updated to match, or the judge will score against the wrong rules.
