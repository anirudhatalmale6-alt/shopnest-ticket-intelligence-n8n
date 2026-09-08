#!/usr/bin/env python3
"""
Builds the ShopNest Global ticket-intelligence workflow for n8n.

The node-by-node architecture here is NOT a free choice. It follows the Great
Learning "Project 1 Solution Approach & Guidelines" document exactly:

    Node 1  Read/Write Files from Disk   (read the ticket CSV)
    Node 2  Extract from File            (CSV -> one item per ticket)
    Node 3  Basic LLM Chain              Summarisation
    Node 4  Basic LLM Chain              Evaluation for Summarisation
    Node 5  Basic LLM Chain              Response Generation
    Node 6  Basic LLM Chain              Evaluation for Response Generation
    Node 7  Edit Fields                  manual mapping to the output columns
    Node 8  Convert to File              -> CSV
    Node 9  Read/Write Files from Disk   (write the consolidated CSV)

Each Basic LLM Chain carries two sub-nodes, again as prescribed: an OpenAI Chat
Model and a Structured Output Parser with a manual schema.

The output-parser schemas and the four evaluation criteria names come verbatim
from the guidelines. The 1-3 scoring scale comes from the course's own reference
notebook ("LLM-as-Judge scores ... each 1-3"). Do not renumber them - the marking
scheme looks for these exact fields.

Usage:
    python3 build_workflow.py                 # ships with /data placeholder paths
    python3 build_workflow.py --local <dir>   # test copy -> test/wf_local.json
"""

import argparse
import hashlib
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "prompts")

MODEL = "gpt-4o-mini"
CRED = {"openAiApi": {"id": "SHOPNEST_OPENAI", "name": "Great Learning AI (OpenAI + Gemini)"}}

# Pinned node versions. The lab may run an older n8n than this machine, so each
# is the lowest version that still supports what the guidelines ask for.
V_CHAIN = 1.6          # chainLlm: promptType "define" + hasOutputParser
V_LM = 1.2             # lmChatOpenAi: model as a resourceLocator, Chat Completions
V_PARSER = 1.2         # outputParserStructured: schemaType "manual"

TICKETS = "$('Extract Ticket Data').item.json"


def nid(name):
    """Stable UUID per node name so rebuilds do not churn the diff."""
    h = hashlib.sha1(("shopnest:" + name).encode()).digest()
    return str(uuid.UUID(bytes=h[:16], version=4))


def sysmsg(name):
    with open(os.path.join(P, name), encoding="utf-8") as f:
        return f.read().rstrip()


def schema(props, required=None):
    """A JSON Schema for the Structured Output Parser's manual mode."""
    return {
        "type": "object",
        "properties": props,
        "required": required if required is not None else list(props),
        "additionalProperties": False,
    }


def s_str(desc):
    return {"type": "string", "description": desc}


def s_score(desc, lo=1, hi=3):
    return {"type": "integer", "minimum": lo, "maximum": hi, "description": desc}


# --------------------------------------------------------------------------
# node factories
# --------------------------------------------------------------------------

# n8n's Structured Output Parser strips a markdown fence ONLY when it finds the
# opening ``` AND a matching closing ```. gpt-4o-mini regularly opens a ```json
# block and never closes it; the parser then leaves the backticks in place and
# JSON.parse dies on the first character. The reported error is "Model output
# doesn't fit required format", which points at the schema and not at the fence.
# Verified against the real parser source: open-fence-only throws, both-fences
# and no-fence both parse. Asking for no fence at all is the robust option -
# there is then nothing to strip.
NO_FENCE = "Return raw JSON only. Do not use markdown code fences or backticks."


def chain_node(name, x, y, system_text, user_text, notes):
    """A Basic LLM Chain. Its model and parser arrive as sub-nodes."""
    return {
        "parameters": {
            "promptType": "define",
            "text": user_text.rstrip("\n") + "\n" + NO_FENCE,
            "hasOutputParser": True,
            "messages": {"messageValues": [
                {"type": "SystemMessagePromptTemplate", "message": system_text},
            ]},
        },
        "type": "@n8n/n8n-nodes-langchain.chainLlm",
        "typeVersion": V_CHAIN,
        "position": [x, y],
        "id": nid(name),
        "name": name,
        "notes": notes,
        "notesInFlow": True,
    }


def model_node(name, x, y, temperature, max_tokens, notes):
    """An OpenAI Chat Model sub-node. Temperature is per-stage on purpose."""
    return {
        "parameters": {
            "model": {"__rl": True, "mode": "list", "value": MODEL,
                      "cachedResultName": MODEL},
            "options": {"temperature": temperature, "maxTokens": max_tokens},
        },
        "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
        "typeVersion": V_LM,
        "position": [x, y],
        "id": nid(name),
        "name": name,
        "credentials": CRED,
        "notes": notes,
        "notesInFlow": True,
    }


def parser_node(name, x, y, json_schema, notes):
    return {
        "parameters": {
            "schemaType": "manual",
            "inputSchema": json.dumps(json_schema, indent=2),
        },
        "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
        "typeVersion": V_PARSER,
        "position": [x, y],
        "id": nid(name),
        "name": name,
        "notes": notes,
        "notesInFlow": True,
    }


# --------------------------------------------------------------------------
# the four LLM stages
# --------------------------------------------------------------------------

STAGES = [
    dict(
        chain="Summarization",
        model="Summarisation Model",
        parser="Summary Schema",
        x=340,
        system="01_summarise_system.txt",
        # The raw ticket text, straight from the CSV.
        user=(
            '=Ticket: "{{ ' + TICKETS + '.support_ticket_desc }}"\n'
            "Summary:"
        ),
        # Temperature 0.2: near-deterministic. A summary is an extraction task -
        # creative variation here shows up as invented detail.
        temperature=0.2,
        max_tokens=400,
        schema=schema({"summary": s_str("The summary paragraph.")}),
        chain_notes="Stage 1 of 4. Raw ticket in, clean factual summary out.",
        model_notes="Temp 0.2 - extraction, not creativity.",
        parser_notes="Forces the single 'summary' field from the guidelines.",
    ),
    dict(
        chain="Evaluation for Summarization",
        model="Summary Judge Model",
        parser="Summary Evaluation Schema",
        x=780,
        system="02_judge_summary_system.txt",
        # The judge needs BOTH the original and the summary, so it reaches back
        # to the CSV rather than reading only the previous node's output.
        user=(
            '=Original Ticket: "{{ ' + TICKETS + '.support_ticket_desc }}"\n'
            'Ticket Summary: "{{ $json.output.summary }}"\n'
            "Evaluate the summary."
        ),
        # Temperature 0.0: a score that changes between runs cannot be used to
        # track quality over time.
        temperature=0.0,
        max_tokens=500,
        schema=schema({
            "information_extraction_score": s_score("1-3. Faithfulness to the ticket."),
            "information_extraction_reasoning": s_str("Evidence for that score."),
            "field_coverage_score": s_score("1-3. Did it carry across what an agent needs."),
            "field_coverage_reasoning": s_str("Evidence for that score."),
        }),
        chain_notes="Stage 2 of 4. LLM-as-a-Judge: scores the summary 1-3 on two criteria.",
        model_notes="Temp 0.0 - scores must be reproducible run to run.",
        parser_notes="Field names are taken verbatim from the project guidelines.",
    ),
    dict(
        chain="Response Generation",
        model="Response Model",
        parser="Response Schema",
        x=1220,
        system="03_respond_system.txt",
        # Replies are written from the SUMMARY, not the raw ticket - that is the
        # point of summarising first, and it keeps abuse out of the reply path.
        user='=Ticket Summary: "{{ $(\'Summarization\').item.json.output.summary }}"',
        # Temperature 0.4: enough variation for natural, non-templated warmth.
        # The policies are enforced by the system message, not by low entropy.
        temperature=0.4,
        # 1500, not 600. A 110-180 word reply plus the JSON wrapper and the
        # parser's own format instructions overran 600 in the lab, and the
        # completion stopped mid-sentence. Truncated JSON does not parse, so
        # the chain failed with "Model output doesn't fit required format" -
        # a format error whose real cause is a length cap. Headroom is free
        # here; the model stops when the reply is done, not when the cap is.
        max_tokens=1500,
        schema=schema({"response": s_str("The complete customer reply.")}),
        chain_notes="Stage 3 of 4. Summary in, policy-grounded customer reply out.",
        model_notes="Temp 0.4 - natural tone; policy is enforced by the prompt.",
        parser_notes="Forces the single 'response' field from the guidelines.",
    ),
    dict(
        chain="Evaluation for Response Generation",
        model="Response Judge Model",
        parser="Response Evaluation Schema",
        x=1660,
        system="04_judge_response_system.txt",
        user=(
            '=Ticket Summary: "{{ $(\'Summarization\').item.json.output.summary }}"\n'
            'Generated Response: "{{ $json.output.response }}"\n'
            "Evaluate the response."
        ),
        temperature=0.0,
        # Three scores and three free-text reasonings - the largest payload of
        # the four stages. Raised with Response Model for the same reason.
        max_tokens=1200,
        schema=schema({
            "issue_addressal_score": s_score("1-3. Does it address the issue, within policy."),
            "issue_addressal_reasoning": s_str("Evidence for that score."),
            "resolution_clarity_score": s_score("1-3. Is the next step unambiguous."),
            "resolution_clarity_reasoning": s_str("Evidence for that score."),
            "overall_score": s_score("Sum of the two scores above.", 2, 6),
            "overall_reasoning": s_str("Is this safe to send as written."),
        }),
        chain_notes="Stage 4 of 4. LLM-as-a-Judge: scores the reply, overall = sum of both.",
        model_notes="Temp 0.0 - scores must be reproducible run to run.",
        parser_notes="Field names are taken verbatim from the project guidelines.",
    ),
]

# The consolidated output. The first four columns are the ones the guidelines
# name explicitly; the evaluation columns follow so every score is auditable
# next to the text that earned it.
OUTPUT_FIELDS = [
    ("support_ticket_id", "string", "={{ " + TICKETS + ".support_ticket_id }}"),
    ("support_ticket_desc", "string", "={{ " + TICKETS + ".support_ticket_desc }}"),
    ("summarisation", "string", "={{ $('Summarization').item.json.output.summary }}"),
    ("response_generation", "string",
     "={{ $('Response Generation').item.json.output.response }}"),
    ("information_extraction_score", "number",
     "={{ $('Evaluation for Summarization').item.json.output.information_extraction_score }}"),
    ("information_extraction_reasoning", "string",
     "={{ $('Evaluation for Summarization').item.json.output.information_extraction_reasoning }}"),
    ("field_coverage_score", "number",
     "={{ $('Evaluation for Summarization').item.json.output.field_coverage_score }}"),
    ("field_coverage_reasoning", "string",
     "={{ $('Evaluation for Summarization').item.json.output.field_coverage_reasoning }}"),
    ("issue_addressal_score", "number", "={{ $json.output.issue_addressal_score }}"),
    ("issue_addressal_reasoning", "string", "={{ $json.output.issue_addressal_reasoning }}"),
    ("resolution_clarity_score", "number", "={{ $json.output.resolution_clarity_score }}"),
    ("resolution_clarity_reasoning", "string",
     "={{ $json.output.resolution_clarity_reasoning }}"),
    ("overall_score", "number", "={{ $json.output.overall_score }}"),
    ("overall_reasoning", "string", "={{ $json.output.overall_reasoning }}"),
]


def build(input_csv, output_csv):
    nodes = []
    conn = {}

    def link(src, dst):
        conn.setdefault(src, {}).setdefault("main", [[]])[0].append(
            {"node": dst, "type": "main", "index": 0})

    nodes.append({
        "parameters": {},
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [-120, 300],
        "id": nid("Run Pipeline"),
        "name": "Run Pipeline",
        "notes": "Press Execute Workflow. Swap for a Schedule Trigger to run nightly.",
        "notesInFlow": True,
    })

    # Node 1 - read the CSV off disk.
    nodes.append({
        "parameters": {"fileSelector": input_csv, "options": {}},
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [100, 300],
        "id": nid("Read Ticket CSV"),
        "name": "Read Ticket CSV",
        "notes": "EDIT ME: path to support_ticket_data.csv in your n8n instance.",
        "notesInFlow": True,
    })

    # Node 2 - CSV to one item per ticket. enableBOM matters: the supplied file
    # starts with a UTF-8 byte order mark, which without this becomes part of
    # the first column name and makes support_ticket_id silently unreadable.
    nodes.append({
        "parameters": {
            "operation": "csv",
            "binaryPropertyName": "data",
            "options": {"enableBOM": True, "headerRow": True},
        },
        "type": "n8n-nodes-base.extractFromFile",
        "typeVersion": 1,
        "position": [320, 300],
        "id": nid("Extract Ticket Data"),
        "name": "Extract Ticket Data",
        "notes": "30 tickets in, 30 items out. BOM stripping on - see README.",
        "notesInFlow": True,
    })

    link("Run Pipeline", "Read Ticket CSV")
    link("Read Ticket CSV", "Extract Ticket Data")

    # Nodes 3-6 - the four LLM stages, each with its two sub-nodes.
    prev = "Extract Ticket Data"
    for s in STAGES:
        nodes.append(chain_node(s["chain"], s["x"], 300,
                                sysmsg(s["system"]), s["user"], s["chain_notes"]))
        nodes.append(model_node(s["model"], s["x"] - 60, 520,
                                s["temperature"], s["max_tokens"], s["model_notes"]))
        nodes.append(parser_node(s["parser"], s["x"] + 140, 520,
                                 s["schema"], s["parser_notes"]))
        link(prev, s["chain"])
        # Sub-node connections run from the sub-node up into its chain.
        conn[s["model"]] = {"ai_languageModel": [[
            {"node": s["chain"], "type": "ai_languageModel", "index": 0}]]}
        conn[s["parser"]] = {"ai_outputParser": [[
            {"node": s["chain"], "type": "ai_outputParser", "index": 0}]]}
        prev = s["chain"]

    # Node 7 - manual mapping into the output columns.
    nodes.append({
        "parameters": {
            "assignments": {"assignments": [
                {"id": f"col-{i}", "name": n, "value": v, "type": t}
                for i, (n, t, v) in enumerate(OUTPUT_FIELDS)
            ]},
            "includeOtherFields": False,
            "options": {},
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [2100, 300],
        "id": nid("Extract the Outputs"),
        "name": "Extract the Outputs",
        "notes": "One row per ticket. First four columns are the ones the brief names.",
        "notesInFlow": True,
    })

    # Node 8 - rows to a CSV file.
    nodes.append({
        "parameters": {"operation": "csv", "options": {"fileName": "shopnest_output.csv"}},
        "type": "n8n-nodes-base.convertToFile",
        "typeVersion": 1.1,
        "position": [2320, 300],
        "id": nid("Convert to File"),
        "name": "Convert to File",
        "notes": "All 30 rows into a single CSV in the binary field 'data'.",
        "notesInFlow": True,
    })

    # Node 9 - write it back to disk.
    nodes.append({
        "parameters": {
            "operation": "write",
            "fileName": output_csv,
            "dataPropertyName": "data",
            "options": {},
        },
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [2540, 300],
        "id": nid("Save the Data"),
        "name": "Save the Data",
        "notes": "EDIT ME: where the consolidated CSV is written.",
        "notesInFlow": True,
    })

    link("Evaluation for Response Generation", "Extract the Outputs")
    link("Extract the Outputs", "Convert to File")
    link("Convert to File", "Save the Data")

    return {
        "id": nid("workflow-root"),
        "name": "ShopNest Global - AI Ticket Intelligence POC",
        "nodes": nodes,
        "connections": conn,
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
                   os.path.join(a.local, "output", "shopnest_ticket_output.csv"))
    else:
        # The lab's own convention, from the guidelines PDF.
        wf = build("/data/learner-<your-lab-id>/files/support_ticket_data.csv",
                   "/data/learner-<your-lab-id>/files/shopnest_ticket_output.csv")

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print(f"wrote {a.out} ({len(wf['nodes'])} nodes, {os.path.getsize(a.out)} bytes)")
