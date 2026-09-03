#!/usr/bin/env python3
"""
MOCK OpenAI-compatible endpoint - WIRING TEST ONLY.

This exists for one reason: to prove the n8n workflow graph executes end to end
(all 30 tickets, every expression resolving, every column landing in the CSV)
WITHOUT a real OpenAI key.

It does NOT prove anything about LLM output quality. The JSON it returns is
produced by crude regex/keyword heuristics, not by a language model. Any file
generated while this server is running is suffixed _MOCKED_LLM and must never be
presented as a real pipeline result.

Point the n8n openAiApi credential's Base URL at http://127.0.0.1:$PORT/v1
"""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("MOCK_PORT", "18400"))

CATEGORY_RULES = [
    (r"charged twice|duplicate charge|two charges", "Duplicate Charge"),
    (r"wrong (model|item|size)|sent some random|not the .* model|19 cubic", "Wrong Item"),
    (r"cracked|dent|damaged|would not turn on|doa|dead on arrival|grinding noise", "Damaged or Defective Item"),
    (r"charjer is mising|missing from the box|charger is missing", "Missing Item or Part"),
    (r"refund has not posted|refund not received|not refunded|refund is being processed", "Refund Delay"),
    (r"payment gateway|ach debit failed|declined|pre-?auth|502 error|txn still failing", "Payment Failure"),
    (r"return window|standard return", "Policy Question"),
    (r"wrong apartment|update .* address|entered the wrong", "Order Modification"),
    (r"return it and get a replacement|want to return", "Return or Exchange"),
    (r"still (has ?n[o']?t|not) (shown up|arrived|delivered)|never (arrived|delivered)|not delivered|nothing came", "Non-Delivery"),
    (r"delay|still.*processing|tracking has not updated|out for delivery for three days|past estimated", "Delivery Delay"),
]

ANGRY = r"beyond frustrated|worst experience|had it with|do not for a second|unacceptable|shocking|genuinely shocking"
FRUSTRATED = r"disappointed|annoyed|frustrat|pretty annoyed|had enough"
POSITIVE = r"genuinely love|everything looks great|incredibly helpful"
ESCALATION = r"better business bureau|bbb|ftc|consumer protection|attorney|dispute the charge|switch platforms"


def find_order_id(text):
    ids = re.findall(r"SNX[-\s]?\d{3,4}", text, re.I)
    ids = [i.upper().replace(" ", "-") for i in ids]
    if not ids:
        return "NOT_PROVIDED"
    uniq = list(dict.fromkeys(ids))
    return " OR ".join(uniq[:2])


def classify(text):
    low = text.lower()
    for pattern, label in CATEGORY_RULES:
        if re.search(pattern, low):
            return label
    if len(low.split()) < 8:
        return "Unclear"
    return "Delivery Delay"


def raw_ticket_from(user_msg):
    m = re.search(r"RAW TICKET:\s*(.*?)(?:\n\nTRIAGE RECORD|\n\nGENERATED|$)", user_msg, re.S)
    return (m.group(1) if m else user_msg).strip()


def stage_of(system_msg):
    # Collapse newlines first - the system messages are hard-wrapped, so phrases
    # like "auditing the summarisation stage" span a line break in the source.
    s = " ".join(system_msg.lower().split())
    if "triage analyst" in s:
        return "summarise"
    if "auditing the summarisation stage" in s:
        return "judge_summary"
    if "senior customer support agent" in s:
        return "respond"
    if "auditing the response-generation stage" in s:
        return "judge_response"
    return "unknown"


def build(stage, user_msg):
    ticket = raw_ticket_from(user_msg)
    low = ticket.lower()
    category = classify(ticket)
    order_id = find_order_id(ticket)
    vague = category == "Unclear"

    # The four schemas below are the ones named in the Great Learning guidelines.
    # If those field names change, this mock must change with them - a mock that
    # returns the old shape is exactly how a run goes green with blank columns.

    if stage == "summarise":
        return {
            "summary": f"[MOCK SUMMARY] {category} on order {order_id}. "
                       "Produced by the mock endpoint by keyword matching, "
                       "not by a language model."
        }

    if stage == "judge_summary":
        base = 2 if vague else 3
        return {
            "information_extraction_score": 3,
            "information_extraction_reasoning":
                "[MOCK] wiring-test score, not a real evaluation.",
            "field_coverage_score": base,
            "field_coverage_reasoning":
                "[MOCK] wiring-test score, not a real evaluation.",
        }

    if stage == "respond":
        return {
            "response": ("Dear Customer,\n\n[MOCK REPLY] This text was produced by "
                         "the mock endpoint for wiring tests, not by an LLM. "
                         f"Issue: {category}, order {order_id}.\n\n"
                         "Kind regards,\nThe ShopNest Support Team")
        }

    if stage == "judge_response":
        issue = 2 if vague else 3
        clarity = 3
        return {
            "issue_addressal_score": issue,
            "issue_addressal_reasoning":
                "[MOCK] wiring-test score, not a real evaluation.",
            "resolution_clarity_score": clarity,
            "resolution_clarity_reasoning":
                "[MOCK] wiring-test score, not a real evaluation.",
            "overall_score": issue + clarity,
            "overall_reasoning":
                "[MOCK] wiring-test score, not a real evaluation.",
        }

    return {"error": "unrecognised stage"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            self._send(200, {"object": "list", "data": [
                {"id": "gpt-4o-mini", "object": "model", "owned_by": "mock"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or b"{}")
        messages = req.get("messages", [])
        # The n8n node prepends its own "output JSON" system message when
        # jsonOutput is on, so take the LAST system message as ours.
        systems = [m["content"] for m in messages if m.get("role") == "system"]
        users = [m["content"] for m in messages if m.get("role") == "user"]
        system_msg = systems[-1] if systems else ""
        user_msg = users[-1] if users else ""

        stage = stage_of(system_msg)

        # Fault injection - the negative control. Without this, an always-empty
        # pipeline_errors column is indistinguishable from error logging that
        # simply never fires. Set MOCK_FAULT=1 to make two specific tickets fail
        # in two different ways and confirm the workflow catches both.
        fault = None
        if os.environ.get("MOCK_FAULT") == "1":
            if "refund not received" in user_msg:
                fault = "prose"          # not JSON at all
            elif "DOA unit" in user_msg and stage == "judge_response":
                fault = "wrong_shape"    # valid JSON, wrong keys

        if fault == "prose":
            content_str = "I'm sorry, I can't produce that as JSON right now."
        elif fault == "wrong_shape":
            content_str = json.dumps({"score": 4, "comment": "looks fine"})
        else:
            # n8n's Structured Output Parser validates against a schema wrapped in
            # an "output" key - its own hint says so: { "output": { ... } }. A real
            # model produces this because the parser injects format instructions
            # into the prompt. Returning the bare object instead does NOT raise:
            # the parser strips the unknown keys and hands back {}, which travels
            # all the way to a CSV of blank columns with the run still green.
            content_str = json.dumps({"output": build(stage, user_msg)})

        # Log the model verbatim, with no default substituted. The model name is
        # driven by an expression in Pipeline Config, and an expression that
        # failed to resolve would otherwise be masked by a fallback further down.
        sys.stderr.write(f"[mock] stage={stage} fault={fault} "
                         f"model={req.get('model')!r}\n")
        sys.stderr.flush()

        self._send(200, {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "model": req.get("model", "gpt-4o-mini"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content_str},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"MOCK OpenAI endpoint on http://127.0.0.1:{PORT}/v1 - WIRING TEST ONLY")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
