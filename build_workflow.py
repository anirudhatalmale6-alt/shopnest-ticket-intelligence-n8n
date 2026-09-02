#!/usr/bin/env python3
"""
Generates ShopNest_Ticket_Intelligence.json (the n8n workflow) from the system
messages in prompts/. Keeping the prompts in separate files means they can be
edited and the workflow rebuilt without hand-editing a 35KB JSON blob.

    python3 build_workflow.py                       # ships with /data paths
    python3 build_workflow.py --local <dir>         # local paths, for test runs
"""
import argparse
import hashlib
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "prompts")

MODEL = "gpt-4o-mini"
CRED = {"openAiApi": {"id": "SHOPNEST_OPENAI", "name": "ShopNest OpenAI account"}}

TICKET = "$('Loop Over Tickets').item.json"
OUTDIR = "$('Pipeline Config').first().json.output_dir"


def nid(name):
    """Stable UUID per node name so rebuilds do not churn the diff."""
    h = hashlib.sha1(("shopnest:" + name).encode()).digest()
    return str(uuid.UUID(bytes=h[:16], version=4))


def sysmsg(name):
    with open(os.path.join(P, name), encoding="utf-8") as f:
        return f.read().rstrip()


def openai_node(name, x, y, system_text, user_expr, temperature, max_tokens, notes):
    return {
        "parameters": {
            "resource": "text",
            "operation": "message",
            # "id" mode rather than "list" so the value can be an expression:
            # change the model once in Pipeline Config, not in four nodes.
            "modelId": {"__rl": True, "mode": "id",
                        "value": "={{ $('Pipeline Config').first().json.model }}"},
            "messages": {"values": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_expr},
            ]},
            "jsonOutput": True,
            "simplify": True,
            "options": {"temperature": temperature, "maxTokens": max_tokens},
        },
        "type": "@n8n/n8n-nodes-langchain.openAi",
        "typeVersion": 1.8,
        "position": [x, y],
        "id": nid(name),
        "name": name,
        "credentials": CRED,
        "notes": notes,
        "notesInFlow": True,
        # A single flaky ticket must never kill a 30-ticket run. Retry the call,
        # then pass the item through so the Consolidate node can log it as failed.
        "onError": "continueRegularOutput",
        "retryOnFail": True,
        "maxTries": 3,
        "waitBetweenTries": 2000,
    }


def code_node(name, x, y, js, notes):
    return {
        "parameters": {"jsCode": js},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [x, y],
        "id": nid(name),
        "name": name,
        "notes": notes,
        "notesInFlow": True,
    }


CLEAN_JS = r"""// RUBRIC 1: Data Loading - normalise and display the loaded data.
// The source CSV is UTF-8 with a BOM, so the first header arrives as
// '﻿support_ticket_id'. Strip the BOM and trim every key so the rest of the
// workflow can rely on clean field names.
const rows = [];
for (const item of $input.all()) {
  const clean = {};
  for (const [key, value] of Object.entries(item.json)) {
    clean[key.replace(/^﻿/, '').trim()] = value;
  }
  const id = String(clean.support_ticket_id ?? '').trim();
  const desc = String(clean.support_ticket_desc ?? '').trim();
  // Skip trailing blank lines rather than sending an empty ticket to the LLM.
  if (!id && !desc) continue;
  rows.push({
    json: {
      support_ticket_id: id,
      support_ticket_desc: desc,
      char_count: desc.length,
      word_count: desc ? desc.split(/\s+/).length : 0,
    },
  });
}
console.log(`Loaded ${rows.length} support tickets`);
return rows;
"""

CONSOLIDATE_JS = r"""// RUBRIC 6: Output & Compilation - one flat record per ticket carrying the ticket
// ID, the raw text, the generated summary, the generated response and every judge
// score.
//
// Defensive on purpose: the OpenAI node parses JSON for us, but if a model ever
// returns prose instead of JSON the field stays a string. That has to be recorded
// as a failed row, not crash the run and not written out as a silent blank.
function asObject(value) {
  if (value && typeof value === 'object') return value;
  if (typeof value === 'string') {
    try { return JSON.parse(value.replace(/^```(?:json)?|```$/g, '').trim()); }
    catch (e) { return null; }
  }
  return null;
}
function content(nodeName) {
  try { return asObject($(nodeName).item.json.message?.content); }
  catch (e) { return null; }
}

// Parsing is not enough. A model can return perfectly valid JSON of completely
// the wrong shape - during build-out a misrouted call returned {"error": ...},
// which parsed fine and then wrote a row of silent blank score columns with no
// error recorded anywhere. So every stage is checked for the keys it MUST have,
// and a shape miss is a logged failure like any other.
const REQUIRED = {
  summary:  ['order_id', 'issue_category', 'summary', 'urgency', 'sentiment'],
  sJudge:   ['faithfulness', 'completeness', 'conciseness', 'actionability',
             'classification', 'overall_score', 'verdict'],
  reply:    ['response_text', 'next_step', 'policies_applied'],
  rJudge:   ['relevance', 'empathy_and_tone', 'policy_compliance',
             'clarity_of_next_step', 'factual_safety', 'professionalism',
             'overall_score', 'verdict'],
};
function missingKeys(obj, keys) {
  return obj ? keys.filter(k => obj[k] === undefined || obj[k] === null) : keys;
}

const ticket  = $('Loop Over Tickets').item.json;
const summary = content('Summarise Ticket');
const sJudge  = content('Judge Summary');
const reply   = content('Generate Response');
const rJudge  = content('Judge Response');

const failures = [];
for (const [label, obj] of [['summary', summary], ['summary_judge', sJudge],
                            ['response', reply], ['response_judge', rJudge]]) {
  const req = REQUIRED[{summary: 'summary', summary_judge: 'sJudge',
                        response: 'reply', response_judge: 'rJudge'}[label]];
  if (!obj) { failures.push(`${label}_unparseable`); continue; }
  const missing = missingKeys(obj, req);
  if (missing.length) failures.push(`${label}_missing:${missing.join('/')}`);
}

const list = (v) => Array.isArray(v) ? v.join('; ') : (v ?? '');

// A row goes to the human queue if EITHER judge said REVIEW, or the response stage
// flagged itself, or any stage failed to parse. Fail closed: when in doubt a human
// looks at it.
const needsReview =
  failures.length > 0 ||
  sJudge?.verdict === 'REVIEW' ||
  rJudge?.verdict === 'REVIEW' ||
  reply?.requires_human_review === true;

return [{ json: {
  support_ticket_id:      ticket.support_ticket_id,
  raw_ticket_text:        ticket.support_ticket_desc,
  raw_word_count:         ticket.word_count,

  order_id:               summary?.order_id ?? '',
  issue_category:         summary?.issue_category ?? '',
  product:                summary?.product ?? '',
  customer_request:       summary?.customer_request ?? '',
  generated_summary:      summary?.summary ?? '',
  urgency:                summary?.urgency ?? '',
  sentiment:              summary?.sentiment ?? '',
  escalation_risk:        summary?.escalation_risk ?? '',
  missing_info:           list(summary?.missing_info),

  sum_faithfulness:       sJudge?.faithfulness ?? '',
  sum_completeness:       sJudge?.completeness ?? '',
  sum_conciseness:        sJudge?.conciseness ?? '',
  sum_actionability:      sJudge?.actionability ?? '',
  sum_classification:     sJudge?.classification ?? '',
  sum_overall_score:      sJudge?.overall_score ?? '',
  sum_verdict:            sJudge?.verdict ?? '',
  sum_justification:      sJudge?.justification ?? '',

  generated_response:     reply?.response_text ?? '',
  next_step:              reply?.next_step ?? '',
  policies_applied:       list(reply?.policies_applied),

  resp_relevance:         rJudge?.relevance ?? '',
  resp_empathy_and_tone:  rJudge?.empathy_and_tone ?? '',
  resp_policy_compliance: rJudge?.policy_compliance ?? '',
  resp_clarity_next_step: rJudge?.clarity_of_next_step ?? '',
  resp_factual_safety:    rJudge?.factual_safety ?? '',
  resp_professionalism:   rJudge?.professionalism ?? '',
  resp_overall_score:     rJudge?.overall_score ?? '',
  resp_verdict:           rJudge?.verdict ?? '',
  resp_policy_violations: list(rJudge?.policy_violations),
  resp_justification:     rJudge?.justification ?? '',

  pipeline_errors:        list(failures),
  needs_human_review:     needsReview ? 'YES' : 'NO',
}}];
"""

STATS_JS = r"""// RUBRIC 7: Business Insights - aggregate the run into the numbers that go on the
// recommendation slide. Every figure is computed from this run, never hard-coded.
const rows = $input.all().map(i => i.json);
const n = rows.length;
const num = (v) => (v === '' || v === null || v === undefined) ? null : Number(v);
const mean = (key) => {
  const vals = rows.map(r => num(r[key])).filter(v => v !== null && !Number.isNaN(v));
  return vals.length ? +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : null;
};
const countBy = (key) => rows.reduce((acc, r) => {
  const k = r[key] || 'UNKNOWN';
  acc[k] = (acc[k] || 0) + 1;
  return acc;
}, {});
const tally = (arr) => arr.reduce((acc, v) => { acc[v] = (acc[v] || 0) + 1; return acc; }, {});
const pct = (c) => n ? +((c / n) * 100).toFixed(1) : 0;

const sumPass    = rows.filter(r => r.sum_verdict === 'PASS').length;
const respPass   = rows.filter(r => r.resp_verdict === 'PASS').length;
const review     = rows.filter(r => r.needs_human_review === 'YES').length;
const errored    = rows.filter(r => r.pipeline_errors).length;
const violations = rows.flatMap(r => String(r.resp_policy_violations || '').split('; ').filter(Boolean));
const noOrderId  = rows.filter(r => !r.order_id || r.order_id === 'NOT_PROVIDED').length;

// Agents currently spend ~2.5 min decoding each ticket before any work starts.
// Tickets that clear both judges need no decode time at all.
const autoApproved = n - review;

return [{ json: {
  tickets_processed:              n,
  rows_with_pipeline_errors:      errored,
  avg_raw_ticket_words:           mean('raw_word_count'),

  summary_avg_score:              mean('sum_overall_score'),
  summary_pass_rate_pct:          pct(sumPass),
  summary_avg_faithfulness:       mean('sum_faithfulness'),
  summary_avg_completeness:       mean('sum_completeness'),
  summary_avg_conciseness:        mean('sum_conciseness'),
  summary_avg_actionability:      mean('sum_actionability'),
  summary_avg_classification:     mean('sum_classification'),

  response_avg_score:             mean('resp_overall_score'),
  response_pass_rate_pct:         pct(respPass),
  response_avg_relevance:         mean('resp_relevance'),
  response_avg_empathy:           mean('resp_empathy_and_tone'),
  response_avg_policy_compliance: mean('resp_policy_compliance'),
  response_avg_clarity:           mean('resp_clarity_next_step'),
  response_avg_factual_safety:    mean('resp_factual_safety'),
  response_avg_professionalism:   mean('resp_professionalism'),
  policy_violations_total:        violations.length,
  policy_violations_by_code:      tally(violations),

  auto_approved_tickets:          autoApproved,
  auto_approval_rate_pct:         pct(autoApproved),
  human_review_queue:             review,
  human_review_rate_pct:          pct(review),

  tickets_missing_order_id:       noOrderId,
  tickets_missing_order_id_pct:   pct(noOrderId),

  issue_category_mix:             countBy('issue_category'),
  urgency_mix:                    countBy('urgency'),
  sentiment_mix:                  countBy('sentiment'),
  escalation_risk_mix:            countBy('escalation_risk'),

  est_agent_minutes_saved_this_run: +(autoApproved * 2.5).toFixed(1),
  est_agent_hours_saved_per_5000:   +((autoApproved / (n || 1)) * 5000 * 2.5 / 60).toFixed(1),
  est_agent_hours_saved_per_15000:  +((autoApproved / (n || 1)) * 15000 * 2.5 / 60).toFixed(1),
}}];
"""


def build(input_csv, output_dir):
    nodes = []

    nodes.append({
        "parameters": {},
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [-380, 300],
        "id": nid("Run Pipeline (On Demand)"),
        "name": "Run Pipeline (On Demand)",
        "notes": "Press Execute Workflow to run. Swap for a Schedule Trigger to run nightly.",
        "notesInFlow": True,
    })

    nodes.append({
        "parameters": {
            "assignments": {"assignments": [
                {"id": "cfg-in", "name": "input_csv_path", "value": input_csv, "type": "string"},
                {"id": "cfg-out", "name": "output_dir", "value": output_dir, "type": "string"},
                # Read by all four LLM nodes. A lab-supplied credential may sit
                # behind a proxy that serves a different model name, so the model
                # is one setting here rather than hard-coded in four places.
                {"id": "cfg-model", "name": "model", "value": MODEL, "type": "string"},
            ]},
            "options": {},
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [-160, 300],
        "id": nid("Pipeline Config"),
        "name": "Pipeline Config",
        "notes": "THE ONLY NODE YOU EDIT to move this workflow between environments.",
        "notesInFlow": True,
    })

    nodes.append({
        "parameters": {"fileSelector": "={{ $json.input_csv_path }}", "options": {}},
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [60, 300],
        "id": nid("Read Ticket CSV"),
        "name": "Read Ticket CSV",
        "notes": "Loads the raw ticket file from disk.",
        "notesInFlow": True,
    })

    nodes.append({
        "parameters": {"operation": "csv", "options": {}},
        "type": "n8n-nodes-base.extractFromFile",
        "typeVersion": 1,
        "position": [280, 300],
        "id": nid("Parse CSV to Rows"),
        "name": "Parse CSV to Rows",
        "notes": "RUBRIC 1: Data Loading. 30 rows in, one n8n item per ticket.",
        "notesInFlow": True,
    })

    nodes.append(code_node(
        "Clean & Profile Tickets", 500, 300, CLEAN_JS,
        "Strips the UTF-8 BOM from the header, drops blank rows, adds length stats."))

    nodes.append({
        "parameters": {"options": {"reset": False}},
        "type": "n8n-nodes-base.splitInBatches",
        "typeVersion": 3,
        "position": [720, 300],
        "id": nid("Loop Over Tickets"),
        "name": "Loop Over Tickets",
        "notes": "One ticket at a time so a single bad ticket cannot fail the whole batch.",
        "notesInFlow": True,
    })

    nodes.append(openai_node(
        "Summarise Ticket", 980, 560,
        sysmsg("01_summarise_system.txt"),
        "=TICKET ID: {{ $json.support_ticket_id }}\n\nRAW TICKET:\n{{ $json.support_ticket_desc }}",
        0.2, 500,
        "RUBRIC 2: Summarisation. temp 0.2 - extraction, not creativity."))

    nodes.append(openai_node(
        "Judge Summary", 1280, 560,
        sysmsg("02_judge_summary_system.txt"),
        "=RAW TICKET:\n{{ " + TICKET + ".support_ticket_desc }}"
        "\n\nGENERATED SUMMARY RECORD:\n{{ JSON.stringify($json.message.content) }}",
        0.0, 400,
        "RUBRIC 3: LLM-as-a-Judge on the summary. temp 0 - scores must be reproducible."))

    nodes.append(openai_node(
        "Generate Response", 1580, 560,
        sysmsg("03_respond_system.txt"),
        "=RAW TICKET:\n{{ " + TICKET + ".support_ticket_desc }}"
        "\n\nTRIAGE RECORD:\n{{ JSON.stringify($('Summarise Ticket').item.json.message.content) }}",
        0.4, 700,
        "RUBRIC 4: Response Generation. temp 0.4 - natural tone, policies still binding."))

    nodes.append(openai_node(
        "Judge Response", 1880, 560,
        sysmsg("04_judge_response_system.txt"),
        "=RAW TICKET:\n{{ " + TICKET + ".support_ticket_desc }}"
        "\n\nTRIAGE RECORD:\n{{ JSON.stringify($('Summarise Ticket').item.json.message.content) }}"
        "\n\nGENERATED CUSTOMER REPLY:\n{{ JSON.stringify($json.message.content) }}",
        0.0, 400,
        "RUBRIC 5: LLM-as-a-Judge on the reply, including policy compliance. temp 0."))

    nodes.append(code_node(
        "Consolidate Ticket Record", 2180, 560, CONSOLIDATE_JS,
        "Flattens 4 LLM outputs into one row. Unparseable output is logged, not swallowed."))

    nodes.append({
        "parameters": {"operation": "csv",
                       "options": {"fileName": "shopnest_ticket_intelligence_output.csv"}},
        "type": "n8n-nodes-base.convertToFile",
        "typeVersion": 1.1,
        "position": [980, 100],
        "id": nid("Build Consolidated CSV"),
        "name": "Build Consolidated CSV",
        "notes": "RUBRIC 6: all 30 rows, every column, one file.",
        "notesInFlow": True,
    })

    nodes.append({
        "parameters": {
            "operation": "write",
            "fileName": "={{ " + OUTDIR + " }}/shopnest_ticket_intelligence_output.csv",
            "options": {},
        },
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [1200, 100],
        "id": nid("Save Consolidated CSV"),
        "name": "Save Consolidated CSV",
        "notes": "The single consolidated deliverable file.",
        "notesInFlow": True,
    })

    nodes.append({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "",
                            "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "review-cond",
                    "leftValue": "={{ $json.needs_human_review }}",
                    "rightValue": "YES",
                    "operator": {"type": "string", "operation": "equals"},
                }],
                "combinator": "and",
            },
            "looseTypeValidation": True,
            "options": {},
        },
        "type": "n8n-nodes-base.filter",
        "typeVersion": 2.2,
        "position": [980, -100],
        "id": nid("Filter Human Review Queue"),
        "name": "Filter Human Review Queue",
        "notes": "Rows either judge marked REVIEW, plus anything that failed to parse.",
        "notesInFlow": True,
    })

    nodes.append({
        "parameters": {"operation": "csv",
                       "options": {"fileName": "shopnest_human_review_queue.csv"}},
        "type": "n8n-nodes-base.convertToFile",
        "typeVersion": 1.1,
        "position": [1200, -100],
        "id": nid("Build Review Queue CSV"),
        "name": "Build Review Queue CSV",
    })

    nodes.append({
        "parameters": {
            "operation": "write",
            "fileName": "={{ " + OUTDIR + " }}/shopnest_human_review_queue.csv",
            "options": {},
        },
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [1420, -100],
        "id": nid("Save Review Queue CSV"),
        "name": "Save Review Queue CSV",
        "notes": "The low-confidence / failed-row log the support lead works through.",
        "notesInFlow": True,
    })

    nodes.append(code_node(
        "Pipeline Quality Stats", 980, -300, STATS_JS,
        "RUBRIC 7: the numbers behind the business recommendations."))

    connections = {
        "Run Pipeline (On Demand)": {"main": [[{"node": "Pipeline Config", "type": "main", "index": 0}]]},
        "Pipeline Config":          {"main": [[{"node": "Read Ticket CSV", "type": "main", "index": 0}]]},
        "Read Ticket CSV":          {"main": [[{"node": "Parse CSV to Rows", "type": "main", "index": 0}]]},
        "Parse CSV to Rows":        {"main": [[{"node": "Clean & Profile Tickets", "type": "main", "index": 0}]]},
        "Clean & Profile Tickets":  {"main": [[{"node": "Loop Over Tickets", "type": "main", "index": 0}]]},
        "Loop Over Tickets": {"main": [
            [  # output 0 - "done", fires once after all 30 tickets
                {"node": "Build Consolidated CSV", "type": "main", "index": 0},
                {"node": "Filter Human Review Queue", "type": "main", "index": 0},
                {"node": "Pipeline Quality Stats", "type": "main", "index": 0},
            ],
            [  # output 1 - "loop", fires once per ticket
                {"node": "Summarise Ticket", "type": "main", "index": 0},
            ],
        ]},
        "Summarise Ticket":          {"main": [[{"node": "Judge Summary", "type": "main", "index": 0}]]},
        "Judge Summary":             {"main": [[{"node": "Generate Response", "type": "main", "index": 0}]]},
        "Generate Response":         {"main": [[{"node": "Judge Response", "type": "main", "index": 0}]]},
        "Judge Response":            {"main": [[{"node": "Consolidate Ticket Record", "type": "main", "index": 0}]]},
        "Consolidate Ticket Record": {"main": [[{"node": "Loop Over Tickets", "type": "main", "index": 0}]]},
        "Build Consolidated CSV":    {"main": [[{"node": "Save Consolidated CSV", "type": "main", "index": 0}]]},
        "Filter Human Review Queue": {"main": [[{"node": "Build Review Queue CSV", "type": "main", "index": 0}]]},
        "Build Review Queue CSV":    {"main": [[{"node": "Save Review Queue CSV", "type": "main", "index": 0}]]},
    }

    return {
        "id": nid("workflow-root"),
        "name": "ShopNest Global - AI Ticket Intelligence POC",
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
        "pinData": {},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="build a test copy pointing at this directory")
    ap.add_argument("--out")
    a = ap.parse_args()

    # --local must never land on the shipping file. It bakes in machine-specific
    # absolute paths, and overwriting the deliverable with them is silent.
    if not a.out:
        a.out = os.path.join(HERE, "test", "wf_local.json") if a.local else \
                os.path.join(HERE, "ShopNest_Ticket_Intelligence.json")

    if a.local:
        wf = build(os.path.join(a.local, "data", "support_ticket_data.csv"),
                   os.path.join(a.local, "output"))
    else:
        wf = build("/data/support_ticket_data.csv", "/data/output")

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print(f"wrote {a.out} ({len(wf['nodes'])} nodes, {os.path.getsize(a.out)} bytes)")
