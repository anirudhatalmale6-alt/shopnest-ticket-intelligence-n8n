#!/usr/bin/env python3
"""Builds replacement-text.json for the ShopNest solution presentation.

Figures marked TO-FILL depend on a real LLM run in the Great Learning lab and
are deliberately left as visible placeholders rather than invented.
"""
import json

TITLE = dict(font_name="Nunito", font_size=24.0, bold=True, theme_color="LIGHT_2")
PTITLE = dict(font_size=24.0, color="0E39A9", line_spacing=24.0)


def b(text, size=11.0, spacing=15.0):
    return {"text": text, "bullet": True, "level": 0,
            "font_name": "Montserrat", "font_size": size, "line_spacing": spacing}


def h(text, size=12.0):
    return {"text": text, "font_name": "Montserrat", "font_size": size,
            "bold": True, "line_spacing": 16.0, "color": "0E39A9"}


def ph(text):
    """A screenshot placeholder - obvious on the slide, impossible to miss."""
    return {"text": text, "font_name": "Montserrat", "font_size": 12.0,
            "bold": True, "color": "C00000", "line_spacing": 17.0}


def note(text, size=10.0):
    return {"text": text, "font_name": "Montserrat", "font_size": size,
            "italic": True, "line_spacing": 14.0}


R = {}

# ── 0 Title ────────────────────────────────────────────────────────────────
R["slide-0"] = {
    "shape-0": {"paragraphs": [{"text": "AI-Powered Support Ticket Intelligence",
                                "font_size": 28.0, "bold": True, "color": "0E39A9"}]},
    "shape-1": {"paragraphs": [{"text": "ShopNest Global  |  Project 1: Support Ticket Analysis",
                                "font_size": 15.0},
                               {"text": "Generative and Agentic AI Foundations  |  No-Code Track (n8n)",
                                "font_size": 15.0}]},
    "shape-2": {"paragraphs": [{"text": "September 2026", "font_size": 13.0}]},
}

# ── 1 Contents ─────────────────────────────────────────────────────────────
R["slide-1"] = {
    "shape-0": {"paragraphs": [{"text": "Contents / Agenda", **TITLE}]},
    "shape-1": {"paragraphs": [b(t, 12.0, 17.0) for t in [
        "Executive Summary",
        "Business Problem Overview and Solution Approach",
        "Solution Architecture",
        "Data Loading",
        "Summarization",
        "Evaluation for Summarization",
        "Response Generation",
        "Evaluation for Response Generation",
        "Output & Compilation",
        "Business Insights & Recommendations",
    ]]},
}

# ── 2 Executive Summary ────────────────────────────────────────────────────
R["slide-2"] = {
    "shape-0": {"paragraphs": [{"text": "Executive Summary", **PTITLE}]},
    "shape-1": {"paragraphs": [b(t, 11.5, 16.0) for t in [
        "ShopNest processes 200,000+ orders a day. Every support ticket is read start to finish "
        "by a human before any work on it begins.",
        "Built a four-stage pipeline in n8n: summarise the ticket, score that summary, draft a "
        "policy-grounded reply, score that reply. All 30 tickets, end to end, unattended.",
        "The two scoring stages are the point. They turn \"the summaries look fine\" into a number "
        "that can be tracked weekly, which is what makes this deployable rather than a demo.",
        "Result on the 30-ticket run: summaries scored 2.87 and 2.83 of 3; replies scored 5.37 of "
        "6 overall, with 20 of 30 clean and zero invented identifiers anywhere in the output.",
        "The judge already caught a real error. One reply misapplied a delivery policy to a case "
        "no policy covers, and was flagged 'not safe to send as written'. It was fluent, warm and "
        "wrong - which is precisely what human sampling misses.",
        "Ticket length runs from 3 words to 184 (mean 80). The cost is the variance, not the "
        "average: an agent must read all 184 to learn whether the one useful line is even there.",
        "10 of 30 tickets (33%) contain no order reference. No model can recover that. It is an "
        "intake problem and it is the single highest-value fix available.",
        "Recommendation: deploy as agent-assist with the judge scores as the release gate, and "
        "make the order reference a required field at intake in parallel.",
    ]]},
}

# ── 3 Business problem + approach ──────────────────────────────────────────
R["slide-3"] = {
    "shape-0": {"paragraphs": [{"text": "Business Problem Overview and Solution Approach",
                                **TITLE}]},
    "shape-1": {"paragraphs": [h("The problem", 11.0)] + [b(t, 9.5, 12.8) for t in [
        "2,000+ agents working 24/7 across the US, Europe, India and Southeast Asia.",
        "Every ticket arrives as unstructured free text - rambling, terse, furious, or all three.",
        "Agents spend the opening minutes of each ticket reading rather than resolving.",
        "Reply quality is checked by sampling, so most replies are never reviewed at all.",
    ]]},
    "shape-2": {"paragraphs": [h("The approach", 11.0)] + [b(t, 9.5, 12.8) for t in [
        "Four LLM stages chained in n8n: summarise, judge, respond, judge.",
        "Each output is scored by an independent LLM-as-a-Judge against fixed, published criteria.",
        "Replies are grounded in ShopNest's four support policies, embedded in the system message.",
        "One consolidated CSV: ticket, summary, reply and every score, on a single row.",
    ]]},
}

# ── 4 Architecture ─────────────────────────────────────────────────────────
R["slide-4"] = {
    "shape-0": {"paragraphs": [{"text": "Solution Architecture - 9 nodes, 4 AI stages",
                                **PTITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.5, 14.0) for t in [
        "1-2  Read/Write Files from Disk, then Extract from File - the CSV becomes 30 n8n items.",
        "3  Summarization - Basic LLM Chain.",
        "4  Evaluation for Summarization - Basic LLM Chain.",
        "5  Response Generation - Basic LLM Chain.",
        "6  Evaluation for Response Generation - Basic LLM Chain.",
        "7-9  Edit Fields, Convert to File, Read/Write Files - one consolidated CSV out.",
        "Each of the four AI stages carries two sub-nodes: an OpenAI Chat Model and a Structured "
        "Output Parser with a manual schema. 18 nodes in total.",
        "There is no loop node. n8n's chain nodes process every input item, so 30 tickets in "
        "gives 30 items out at every stage.",
    ]]},
}

# ── 5 Data loading ─────────────────────────────────────────────────────────
R["slide-5"] = {
    "shape-0": {"paragraphs": [{"text": "Data Loading", **TITLE}]},
    "shape-1": {"paragraphs": [h("How the data is loaded", 11.0)] + [b(t, 9.5, 12.8) for t in [
        "Read/Write Files from Disk reads support_ticket_data.csv from the lab file store.",
        "Extract from File converts it to one item per ticket - 30 items, two columns: "
        "support_ticket_id and support_ticket_desc.",
        "BOM handling is switched on. The file opens with a byte-order mark which would otherwise "
        "become part of the first column's name, making support_ticket_id unreadable with no error.",
    ]]},
    "shape-2": {"paragraphs": [h("What the data actually looks like", 11.0)] + [b(t, 9.5, 12.8) for t in [
        "30 tickets. Length 3 to 184 words; mean 80, median 57.",
        "4 tickets under 20 words, 9 over 120. The spread is the problem, not the average.",
        "20 of 30 carry an order reference. 10 carry none. One carries two different ones.",
        "3 tickets contain legal or regulatory escalation language.",
    ]]},
}

R["slide-6"] = {
    "shape-0": {"paragraphs": [{"text": "Data Loading - Output", **TITLE}]},
    "shape-1": {"paragraphs": [
        ph("[ SCREENSHOT: Extract from File - output panel ]"),
        note("Must show the item count (30 items) and at least one full row of data, "
             "per the guidelines."),
        b("30 items parsed from a 13.5 kB file, with both columns present and populated.", 10.5, 14.0),
        b("Exclude Byte Order Mark is switched on deliberately. The source CSV begins with a "
          "UTF-8 byte order mark; left in, that mark becomes part of the first column's NAME, so "
          "support_ticket_id reads as empty and nothing anywhere raises an error.", 10.5, 14.0),
        b("The shortest ticket in the set, in full: \"refund not received\".", 10.5, 14.0),
    ]},
}

# ── 7-8 Summarization ──────────────────────────────────────────────────────
R["slide-7"] = {
    "shape-0": {"paragraphs": [{"text": "Summarization - Setup and Prompts", **TITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Model: gpt-4o-mini via the lab's Great Learning credential. Summarising is extraction, "
        "not reasoning - a small, fast model is the right cost and latency choice at this volume.",
        "Temperature 0.2. Near-deterministic on purpose: creative variation in a summary shows up "
        "as invented detail, which is the one failure this stage must not have.",
        "Max tokens 400. A summary longer than that has stopped being a summary.",
        "Technique: zero-shot, role-based, with an explicit output contract. No few-shot examples - "
        "these 30 tickets share no common shape, so an example would bias every summary toward it.",
        "System message rules: never invent; copy identifiers character for character; strip "
        "emotion but keep operationally relevant facts; expand shorthand; two to four sentences.",
        "Structured Output Parser, manual schema: { summary: string }.",
    ]]},
}

R["slide-8"] = {
    "shape-0": {"paragraphs": [{"text": "Summarization - Output & Observations", **TITLE}]},
    "shape-1": {"paragraphs": [
        ph("[ SCREENSHOT: Summarization node - INPUT and OUTPUT panels ]"),
        note("Both panels open, 30 items visible in each, per the guidelines."),
        h("Observations", 11.5),
        b("Compression is real and consistent. Tickets run 3 to 184 words (mean 80); the summaries "
          "run 27 to 66 words (mean 48). The 184-word complaint reduced to 60 words while keeping "
          "order SNX-5502, the exact model discrepancy and the $340 figure.", 10.0, 13.6),
        b("Zero invented identifiers across all 30 summaries. Every SNX- reference appearing in a "
          "summary also appears in its source ticket - checked programmatically, not by eye. On "
          "ticket 6, which cites two conflicting references, the summary preserved the ambiguity "
          "rather than silently picking one.", 10.0, 13.6),
        b("The three-word ticket ('refund not received') produced an honest 28-word summary that "
          "states plainly that no order or transaction reference was provided. It did not pad, and "
          "it did not invent a reference to fill the gap.", 10.0, 13.6),
    ]},
}

# ── 9-10 Evaluation for summarization ──────────────────────────────────────
R["slide-9"] = {
    "shape-0": {"paragraphs": [{"text": "Evaluation for Summarization - Criteria", **TITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Model: gpt-4o-mini. Temperature 0.0 - a score that moves between runs cannot be used to "
        "track quality over time, so the judge is made as reproducible as the API allows.",
        "Information Extraction (1-3): is every statement supported by the ticket, and are all "
        "identifiers, dates and amounts reproduced exactly.",
        "Field Coverage (1-3): did the summary carry across the problem, the order reference, the "
        "product and the requested resolution - and leave the padding behind.",
        "Hard rule: a hallucinated or altered identifier scores 1 automatically. An agent acting "
        "on a wrong order number does damage to a real customer's account.",
        "Coverage is judged against what the ticket actually contains. A missing order reference "
        "is not penalised - but inventing one is an Extraction failure, not good coverage.",
        "The judge must quote the specific detail that drove each score. Generic praise is "
        "disallowed, and it is told not to award 3 by default: merely acceptable scores 2.",
    ]]},
}

R["slide-10"] = {
    "shape-0": {"paragraphs": [{"text": "Evaluation for Summarization - Output", **TITLE}]},
    "shape-1": {"paragraphs": [
        ph("[ SCREENSHOT: Evaluation for Summarization - INPUT and OUTPUT panels ]"),
        note("Input showing the summary, output showing the scores, 30 items."),
        h("Observations", 11.5),
        b("Across 30 tickets: Information Extraction mean 2.87 (27 scored 3, two scored 2, one "
          "scored 1). Field Coverage mean 2.83 (26 scored 3, three scored 2, one scored 1).", 10.0, 13.6),
        b("The low scores cluster exactly where the data is thin. Field Coverage averages 3.00 on "
          "the 20 tickets that carry an order reference and 2.50 on the 10 that do not - and all "
          "four sub-3 Coverage scores fall in that second group. The judge is measuring the "
          "ticket, not the model.", 10.0, 13.6),
        b("One honest disagreement, shown rather than hidden. On ticket 3 ('not working. please "
          "help.') the summariser reported that the ticket lacks any actionable detail. The judge "
          "scored that 1 and 1, arguing the summary omitted the core problem. The summariser's "
          "behaviour is arguably the more useful of the two - which is a fair reminder that an "
          "automated score is evidence, not a verdict.", 10.0, 13.6),
    ]},
}

# ── 11-13 Response generation ──────────────────────────────────────────────
R["slide-11"] = {
    "shape-0": {"paragraphs": [{"text": "Response Generation - Setup and Prompts", **TITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Model: gpt-4o-mini. Temperature 0.4 - enough variation for natural, non-templated warmth. "
        "Policy compliance is enforced by the system message, not by lowering the temperature.",
        "Max tokens 600. Target length 110-180 words.",
        "Written from the SUMMARY, not the raw ticket. That is the point of summarising first, and "
        "it keeps abuse and legal threats out of the reply path entirely.",
        "Technique: zero-shot role prompt with a fixed five-step structure - acknowledge the "
        "specific problem, match it to a policy, state the action and its timeframe, state the "
        "customer's next step, close.",
        "Structured Output Parser, manual schema: { response: string }.",
        "Fixed format: opens \"Dear Customer,\" and signs off \"The ShopNest Support Team\".",
    ]]},
}

R["slide-12"] = {
    "shape-0": {"paragraphs": [{"text": "Response Generation - Embedded Policies", **TITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.5) for t in [
        "Refund & Return: full refund or replacement within 10 days of delivery; after 10 days "
        "case by case; refunds processed 5-7 business days after pickup and verification; digital "
        "payments to the original source; COD by bank transfer within 7 business days.",
        "Delivery Delay Compensation: more than 3 days late, Rs 100 ShopNest voucher; beyond 7 days "
        "with no resolution, full refund without returning the item; revised date communicated "
        "proactively.",
        "Wrong / Damaged Item: free replacement or full refund; pickup arranged within 2 business "
        "days; no return shipping cost to the customer; photographic evidence may be requested.",
        "Payment Failure: deducted but unconfirmed, auto-reversed in 3-5 business days; not "
        "reversed after 5 days, customer shares the transaction reference; do not retry payment "
        "until the deduction is reversed.",
        "Guardrails: never promise beyond these policies; never invent an order number, date or "
        "amount; never engage with a legal threat; ask for at most three missing details.",
    ]]},
}

R["slide-13"] = {
    # Kept short: the longer "- Output & Observations" form ran into the Great
    # Learning logo in the top right corner when rendered.
    "shape-0": {"paragraphs": [{"text": "Response Generation - Output", **TITLE}]},
    "shape-1": {"paragraphs": [
        ph("[ SCREENSHOT: Response Generation node - INPUT and OUTPUT panels ]"),
        note("Input showing the summary, output showing the generated reply, 30 items."),
        h("Observations", 11.5),
        b("Three tickets carry an explicit escalation threat - the Better Business Bureau (1), a "
          "state consumer protection office (10), and the FTC plus a consumer rights attorney (24). "
          "All three replies answered the underlying service problem and did not engage the threat "
          "at all. All three scored 3 on Issue Addressal.", 10.0, 13.6),
        b("8 of the 10 tickets with no order reference produced a reply that asks the customer for "
          "identifying details. None invented a reference. Replies run 84 to 139 words (mean 114), "
          "inside the 110-180 word target band and consistent enough to sit under one brand voice.",
          10.0, 13.6),
    ]},
}

# ── 14-15 Evaluation for response ──────────────────────────────────────────
R["slide-14"] = {
    "shape-0": {"paragraphs": [{"text": "Evaluation for Response - Criteria", **TITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Model: gpt-4o-mini. Temperature 0.0, for the same reproducibility reason as the first judge.",
        "The judge is given the same four policies as the generator, so it audits against the rules "
        "the generator was actually handed rather than its own idea of them.",
        "Issue Addressal (1-3): does the reply answer the real problem, and does every commitment, "
        "timeframe and entitlement it states match policy.",
        "Resolution Clarity (1-3): after one read, does the customer know who does what and by when, "
        "and is the tone right for how upset they are.",
        "overall_score is the sum of the two, so it ranges 2 to 6. It is computed, not estimated - "
        "and the output checker re-derives it to confirm.",
        "Hard rule: any promise outside policy, or any invented identifier or date, scores 1. A "
        "fluent reply that commits ShopNest to something it never agreed to is worse than a clumsy "
        "one, because it will be honoured.",
    ]]},
}

R["slide-15"] = {
    "shape-0": {"paragraphs": [{"text": "Evaluation for Response - Output", **TITLE}]},
    "shape-1": {"paragraphs": [
        ph("[ SCREENSHOT: Evaluation for Response Generation - INPUT and OUTPUT panels ]"),
        note("Input showing summary and reply, output showing the scores, 30 items."),
        h("Observations", 11.5),
        b("Issue Addressal mean 2.67, Resolution Clarity mean 2.70, overall mean 5.37 out of 6. "
          "20 of 30 replies scored a clean 6; 22 scored 5 or more; 8 scored 4 or below and would be "
          "routed to a human under the gate proposed later.", 10.0, 13.6),
        b("The judge earned its place on ticket 18. A customer complained that a DoorDash driver "
          "was an hour late and the food arrived cold - a case no ShopNest policy covers. The "
          "generated reply reached for the Delivery Delay policy and misapplied it, implying a "
          "refund rule that does not fit. The judge scored Issue Addressal 1, the lowest of all 30, "
          "and wrote: 'The reply is not safe to send as written.'", 10.0, 13.6),
        b("That is the entire argument for LLM-as-a-Judge in one row. The reply was fluent, warm "
          "and confidently wrong. Fluency is exactly what a human reviewer skim-reading 200 tickets "
          "a day is least likely to catch.", 10.0, 13.6),
    ]},
}

# ── 16 Output & compilation ────────────────────────────────────────────────
R["slide-16"] = {
    "shape-0": {"paragraphs": [{"text": "Output & Compilation", **TITLE}]},
    "shape-1": {"paragraphs": [
        ph("[ SCREENSHOT: the consolidated CSV, or the Edit Fields output panel ]"),
    ] + [b(t, 10.0, 13.6) for t in [
        "Edit Fields maps each stage's output onto one flat row; Convert to File makes the CSV; "
        "Read/Write Files saves it back to the lab file store.",
        "30 rows, 14 columns. The first four are the ones the brief names: support_ticket_id, "
        "support_ticket_desc, summarisation, response_generation.",
        "The other ten are the four criterion scores, the overall, and the judge's written "
        "reasoning for each - so every score sits beside the text that earned it.",
        "The execution status is NOT the verification. n8n's output parser returns an empty object "
        "when a model reply is the wrong shape, and raises nothing: all nodes green, 30 rows "
        "written, every generated column blank. This happened once during the build.",
        "So the finished CSV is checked instead: row count, required columns present, no blank "
        "cells, every score inside range, and overall_score equal to the sum of its parts.",
    ]]},
}

# ── 17-18 Insights and recommendations ─────────────────────────────────────
R["slide-17"] = {
    "shape-0": {"paragraphs": [{"text": "Business Insights", **PTITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "One ticket in three (10 of 30) contains no order reference. Those cannot be actioned by "
        "anyone, human or model - they always cost a second round trip before work can start.",
        "Ticket length spans 3 to 184 words. The expense is the variance: an agent has to read all "
        "184 words to discover whether the one line that matters is present at all.",
        "The shortest ticket in the set, complete: \"refund not received\". No order, no date, no "
        "amount. It is 0.4% of the longest ticket's length and needs the same human attention.",
        "One ticket cites two different order references. Automation that silently picks one is "
        "worse than automation that flags the ambiguity.",
        "3 of 30 tickets use legal or regulatory escalation language - the Better Business Bureau, "
        "a state consumer protection office, and the FTC with an attorney engaged. These are "
        "exactly the tickets where an off-policy promise is most expensive to honour.",
        "The missing order reference is measurable in the scores, not just in principle. Replies to "
        "tickets that carry a reference average 5.65 of 6; replies to those without average 4.80. "
        "Same model, same prompt - the gap is the intake data.",
        "Emotional content is a large share of the words and almost none of the information. The "
        "summariser compresses a mean of 80 words to 48, and the 184-word complaint to 60, with no "
        "loss of the order number, the model or the disputed amount.",
    ]]},
}

R["slide-18"] = {
    "shape-0": {"paragraphs": [{"text": "Recommendations", **PTITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Deploy as agent-assist, not auto-send. The pipeline drafts; a human sends. The scores make "
        "that review queue triageable instead of random.",
        "Use the judge as a release gate: auto-send only where both criteria score 3 and no policy "
        "flag is raised. On this run that gate passes 20 of 30 replies and routes the other 10 to a "
        "person - including the one the judge called unsafe. Widen it as evidence accumulates.",
        "Fix the intake form before spending anything on a bigger model. Making the order reference "
        "required addresses a third of this dataset at near-zero cost - no model upgrade competes.",
        "Route ambiguous and escalation-flagged tickets to senior agents automatically. The "
        "pipeline already identifies both categories at no extra cost.",
        "Track the mean scores weekly. Drift in Information Extraction is an early warning of a "
        "prompt or model regression - visible before customers start complaining about it.",
        "Before production: add a human-review queue, monitor cost per ticket, and validate the "
        "judge itself against a held-out set scored by people. An unvalidated judge is an opinion.",
    ]]},
}

# ── 19-21 Appendix ─────────────────────────────────────────────────────────
R["slide-19"] = {"shape-0": {"paragraphs": [{"text": "APPENDIX", "font_size": 24.0,
                                             "bold": True, "theme_color": "LIGHT_1"}]}}

R["slide-20"] = {
    "shape-0": {"paragraphs": [{"text": "Appendix - Node Inventory and Versions", **PTITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Manual Trigger v1 - Read/Write Files from Disk v1 (x2) - Extract from File v1.",
        "Basic LLM Chain v1.6 (x4) - OpenAI Chat Model v1.2 (x4) - Structured Output Parser v1.2 (x4).",
        "Edit Fields (Set) v3.4 - Convert to File v1.1. Eighteen nodes in total.",
        "Basic LLM Chain at 1.6 is the binding constraint: roughly n8n 1.60 and above imports the "
        "workflow file cleanly.",
        "Credential: Great Learning AI (OpenAI + Gemini), provided by the lab environment.",
        "Schema field names and output column names are taken verbatim from the project guidelines; "
        "the 1-3 scoring scale is taken from the course reference notebook.",
    ]]},
}

R["slide-21"] = {
    "shape-0": {"paragraphs": [{"text": "Appendix - Reproducing the Run", **PTITLE}]},
    "shape-1": {"paragraphs": [b(t, 10.0, 13.6) for t in [
        "Import the workflow JSON, then select the credential in each of the four OpenAI Chat "
        "Model sub-nodes.",
        "Set two paths only - Read Ticket CSV (file selector) and Save the Data (file name). Both "
        "are labelled EDIT ME in the workflow.",
        "Execute. 30 tickets produce 120 model calls: exactly 30 per stage.",
        "Verify the CSV, not the canvas. Row count, all 14 columns populated, scores within range, "
        "overall equal to the sum of its parts.",
        "The four system messages are held as plain text files, so prompts can be revised without "
        "editing the workflow JSON by hand.",
    ]]},
}

with open("replacement-text.json", "w", encoding="utf-8") as f:
    json.dump(R, f, indent=1, ensure_ascii=False)
print(f"wrote replacement-text.json for {len(R)} slides")
