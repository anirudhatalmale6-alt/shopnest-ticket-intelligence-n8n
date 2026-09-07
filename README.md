# ShopNest Global — AI Ticket Intelligence (n8n, no-code track)

An n8n workflow that reads 30 raw customer support tickets and, for each one,
produces a summary, an LLM-as-a-Judge score for that summary, a policy-grounded
customer reply, and an LLM-as-a-Judge score for that reply — then writes
everything to a single consolidated CSV.

Built for the Great Learning *Generative and Agentic AI Foundations* project,
**no-code (n8n) track**.

---

## What is and is not proven

| Claim | Status | How it was checked |
|---|---|---|
| The graph runs end to end on all 30 tickets | **Proven** | CLI execution; 120 endpoint calls, exactly 30 per stage |
| Every expression resolves; no blank columns | **Proven** | `verify_output.py` — 14/14 columns populated on all 30 rows |
| Scores land inside their declared range | **Proven** | `verify_output.py` range check |
| `overall_score` really is the sum of its parts | **Proven** | `verify_output.py` arithmetic check |
| The CSV has the columns the brief names | **Proven** | `verify_output.py` required-column check |
| **The quality of the generated text** | **NOT proven** | every run so far used the mock endpoint |

The last row is the important one. No real LLM has run through this yet, because
no API key was available on the build machine. Every generated field currently
reads `[MOCK]` **on purpose**, so a mock result can never be mistaken for a real
one. Swapping in the lab credential changes no wiring — see below.

---

## Architecture — and why it is what it is

The node-by-node structure is **not** a design choice. It follows the Great
Learning *Project 1 Solution Approach & Guidelines* document exactly, because
the marking scheme checks screenshots against it.

```
Run Pipeline (Manual Trigger)
  └─ 1. Read Ticket CSV          Read/Write Files from Disk
     └─ 2. Extract Ticket Data   Extract from File (CSV)   → 30 items
        └─ 3. Summarization                  Basic LLM Chain
        └─ 4. Evaluation for Summarization   Basic LLM Chain
        └─ 5. Response Generation            Basic LLM Chain
        └─ 6. Evaluation for Response Gen.   Basic LLM Chain
           └─ 7. Extract the Outputs   Edit Fields (manual mapping)
              └─ 8. Convert to File    → CSV
                 └─ 9. Save the Data   Read/Write Files from Disk
```

Each of the four Basic LLM Chains carries two sub-nodes, again as prescribed: an
**OpenAI Chat Model** and a **Structured Output Parser** (schema type *Manual*).
18 nodes in total.

There is no loop node. n8n's chain nodes process every input item, so 30 tickets
in gives 30 items out at every stage.

### Field names are fixed by the brief

The evaluation criteria and output columns are taken **verbatim** from the
guidelines. Do not rename them:

| Stage | Schema fields |
|---|---|
| Summarization | `summary` |
| Evaluation for Summarization | `information_extraction_score`, `information_extraction_reasoning`, `field_coverage_score`, `field_coverage_reasoning` |
| Response Generation | `response` |
| Evaluation for Response Generation | `issue_addressal_score`, `issue_addressal_reasoning`, `resolution_clarity_score`, `resolution_clarity_reasoning`, `overall_score`, `overall_reasoning` |

Scores run **1–3** per criterion, and `overall_score` is the sum of the two
response criteria, so 2–6. The 1–3 scale is not invented — it comes from the
course's own reference notebook: *"LLM-as-Judge scores Information Extraction
and Field Coverage (each 1-3)"*.

### Temperature is set per stage, deliberately

| Stage | Temp | Reason |
|---|---|---|
| Summarization | 0.2 | Summarising is extraction. Creative variation here appears as invented detail. |
| Both judges | 0.0 | A score that changes between runs cannot be used to track quality over time. |
| Response Generation | 0.4 | Enough variation for natural, non-templated warmth. Policy is enforced by the prompt, not by low entropy. |

### Token caps, and a failure that lies about its cause

| Stage | Max tokens |
|---|---|
| Summarization | 400 |
| Evaluation for Summarization | 500 |
| Response Generation | **1500** |
| Evaluation for Response Generation | **1200** |

The last two were originally 600, and that was wrong. In the lab, Response
Generation failed on its first item with:

> Model output doesn't fit required format

That reads like a schema problem. It was not. The model was producing exactly
the right shape — the input to the parser began
`{"output":{"response":"Dear Customer,\n\nThank you for reaching out…` — but the
completion hit the 600-token cap and **stopped mid-sentence**. Truncated JSON
does not parse, and the parser reports the only thing it can see: the format
didn't match.

The reply itself (110–180 words) plus the JSON wrapper plus the parser's own
injected format instructions do not fit in 600 tokens. The response judge writes
three scores and three free-text reasonings, so it was raised too.

**The general lesson: when a structured-output parser rejects a well-formed
model, check the length cap before you touch the schema.** Headroom costs
nothing — the model stops when the reply is finished, not when the cap is.

---

## The policies are the real ones

The four ShopNest policies in `prompts/03_respond_system.txt` are transcribed
from the guidelines PDF. An earlier draft of this project used **invented**
policies inferred from the tickets; those have been deleted.

The policies live in **two files** — the generator (`03`) and the judge's mirror
(`04`). Change them together, or the judge will score replies against rules the
generator never saw.

---

## Running it in the Great Learning lab

### 1. Import
`ShopNest_Ticket_Intelligence.json` → in n8n, **⋯ → Import from File**.
All 18 nodes appear already wired.

### 2. Pick the credential
Open each of the four **OpenAI Chat Model** sub-nodes and select
`Great Learning AI (OpenAI + Gemini)` from the dropdown. The lab provides it —
nothing to create, nothing to pay for. The JSON references a placeholder
credential ID that will not exist in your instance; that is expected.

### 3. Set the two file paths
Only two nodes hold a path, and both are marked *EDIT ME*:

- **Read Ticket CSV** → `fileSelector`
- **Save the Data** → `fileName`

Use the lab's own convention, `/data/learner-<your-lab-id>/files/…`. The
guidelines describe how to find your lab id: upload the dataset via **Manage
Files**, then use **Copy Path** on any existing file and replace the filename.

### 4. Execute, then verify
Press **Execute Workflow**. Then download the output CSV and run:

```
python3 verify_output.py <the-csv> --rows 30
```

**Do not skip this.** See below for why an all-green run is not evidence.

---

## Why `verify_output.py` exists

n8n's Structured Output Parser validates the model's reply against a schema
wrapped in an `output` key. When the reply does not match that shape, **the
parser does not raise an error** — it strips the unrecognised keys and returns
an empty object.

That empty object flows through the rest of the graph perfectly happily. Every
node turns green, the execution reports `success`, the CSV is written with
exactly 30 rows — and every generated column is blank.

This happened during build-out and it is completely silent. An execution status
is not evidence that the pipeline produced anything. `verify_output.py` checks
the artefact instead: row count, required columns, no column blank across all
rows, no blank cell in a required column, every score inside its range,
`overall_score` equal to the sum of its parts, and whether the run was mocked.

---

## Editing the prompts

The four system messages are plain text under `prompts/`, so they can be edited
without touching the workflow JSON:

| File | Used by |
|---|---|
| `01_summarise_system.txt` | Summarization |
| `02_judge_summary_system.txt` | Evaluation for Summarization |
| `03_respond_system.txt` | Response Generation (holds the four policies) |
| `04_judge_response_system.txt` | Evaluation for Response Generation (mirrors them) |

Then regenerate — the workflow JSON is built, not hand-edited:

```
python3 build_workflow.py                 # the shipping file
python3 build_workflow.py --local <dir>   # test copy -> test/wf_local.json
```

`--local` writes to `test/wf_local.json`, never to the shipping JSON — it bakes
in absolute machine paths, and overwriting the deliverable with them is silent.

---

## Node versions

Pinned to the lowest version that supports what the guidelines ask for, so the
file imports into an older lab instance:

| Node | typeVersion |
|---|---|
| Manual Trigger | 1 |
| Read/Write Files from Disk | 1 |
| Extract from File | 1 |
| Basic LLM Chain | 1.6 |
| OpenAI Chat Model | 1.2 |
| Structured Output Parser | 1.2 |
| Edit Fields (Set) | 3.4 |
| Convert to File | 1.1 |

Basic LLM Chain at 1.6 is the binding constraint — roughly n8n 1.60+ imports
cleanly.

---

## A trap worth knowing about

`support_ticket_data.csv` begins with a UTF-8 byte order mark. Left alone, that
mark becomes part of the first column's *name*, so `support_ticket_id` reads as
empty and no error is raised anywhere. **Extract Ticket Data** therefore has
`enableBOM` switched on.

---

## Testing without an API key

`mock_openai_server.py` is a local OpenAI-compatible endpoint used to prove the
wiring. It is **not** a language model — it answers with keyword-matched
boilerplate and stamps `[MOCK]` on everything.

```
MOCK_PORT=18400 python3 mock_openai_server.py
```

Then point the credential's **Base URL** at `http://127.0.0.1:18400/v1`.

Note that the mock must wrap its payload in the `output` key the Structured
Output Parser expects. Returning the bare object is what produced the silent
blank-column run described above.

---

## Files

| Path | What it is |
|---|---|
| `ShopNest_Ticket_Intelligence.json` | **The deliverable.** Import this. |
| `build_workflow.py` | Generates the above. Edit here, not the JSON. |
| `prompts/*.txt` | The four system messages. |
| `verify_output.py` | Checks the output CSV. Run after every execution. |
| `mock_openai_server.py` | Local test endpoint, no API key needed. |
| `output/` | Result of the most recent local run (mocked). |
