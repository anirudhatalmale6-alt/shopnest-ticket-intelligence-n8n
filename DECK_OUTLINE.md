# Submission deck — slide-by-slide content

For the No-Code track the graded artefact is a **PDF presentation**, not the n8n
JSON. This is the content for it, written to drop into whatever template the
course provides.

**Two rules before you use any of this.**

1. **Put the insights in your own words.** The course marks copied submissions
   zero, and you will be asked to explain your design choices. Everything below is
   written to help you understand *why* each decision was made so you can defend
   it — not to be pasted verbatim.
2. **Every score on these slides is currently a placeholder.** All figures marked
   🔴 come from runs against a mock endpoint and are meaningless as quality
   measures. Re-run with a real OpenAI key and replace them. Figures marked 🟢 are
   real — they are computed from the ticket text itself and will not change.

---

## Slide 1 — Title

Support Ticket Analysis — AI Ticket Intelligence POC for ShopNest Global
No-Code Track · n8n · Generative and Agentic AI Foundations
[your name] · [date]

---

## Slide 2 — The business problem

ShopNest Global: 30+ countries, 50M+ active customers, 2,000+ support agents,
200,000 orders a day. Every order can produce a delay, a payment failure, a wrong
item or a return — and each of those becomes a ticket.

The problem is not ticket *volume*. It is that tickets arrive unreadable:

- **Overloaded** — the real issue is buried under paragraphs of history and
  frustration. In this dataset the longest ticket runs **184 words** and mentions
  the actual request in the final sentence. 🟢
- **Shorthand** — "Ord SNX-8902 ACH debit failed... Need NDD before the 15th. Pls
  check PG logs and escalate to L2." Correct, dense, and unreadable to a new agent.
- **Too sparse** — one ticket in this set reads, in full: *"not working. please
  help."* **3 words.** 🟢

Spread: **3 to 184 words, averaging 80**. 🟢 That variance is the whole problem —
there is no single reading strategy that works.

**Cost:** agents burn 2–3 minutes per ticket *before* resolution work starts. At
peak (15,000 tickets/day) that is roughly **625 agent-hours a day** spent decoding
rather than resolving.

---

## Slide 3 — Objective

Build a POC that:
1. Reads a raw ticket and produces a clean, accurate summary an agent can act on
   at first read.
2. Drafts a professional, empathetic reply with a clear next step, for human review.
3. **Scores both automatically**, so quality is measurable, consistent and
   auditable rather than a matter of opinion.

Point 3 is the one that makes this deployable. Anyone can generate a summary. The
question a business actually needs answered is *"how do we know it's any good, at
15,000 a day, without reading them all?"*

---

## Slide 4 — Solution architecture

**[SCREENSHOT: `screenshots/01_full_workflow_canvas.png`]**

Trigger → Config → Read CSV → Parse → Clean → **loop per ticket**:
Summarise → Judge Summary → Generate Response → Judge Response → Consolidate
→ then three output branches: consolidated CSV, human-review queue, quality stats.

**Why a loop rather than a batch of 30.** Isolation. One malformed ticket cannot
take down the run — it fails alone, gets logged, and the other 29 complete. At
production volume that difference is the difference between a bad night and a
lost night.

**Why the judges sit inline, not as a separate afterwards-job.** The score has to
be attached to the row it describes. A quality process that runs separately is a
quality process that gets skipped.

---

## Slide 5 — Stage 1: Summarisation

**[SCREENSHOT: `screenshots/03_node_summarise_ticket.png`]**

| Choice | Value | Why |
|---|---|---|
| Model | gpt-4o-mini | Bounded extraction and classification, not open reasoning. At 15,000/day × 4 calls, model cost dominates the business case. Start cheap; the judge scores tell you objectively if you need to upgrade. |
| Temperature | **0.2** | Extraction. Creativity here means an invented order ID. |
| Max tokens | 500 | Enough for the structured record, capped so a runaway response can't inflate cost. |
| Technique | Role-based zero-shot + strict JSON schema + explicit negative rules | See below. |

**Why zero-shot and not few-shot.** With 12 issue categories and ticket styles
ranging from 3 words to 184, any small set of examples biases the model toward the
shapes it was shown. Instead the system message pins a role, an exhaustive
category enum, an exact output schema, and hard prohibitions.

**The single most important line in the prompt** is the instruction never to
invent, paired with a `NOT_PROVIDED` convention. Giving the model a *correct
answer for the absent case* is what stops it hallucinating an order ID — without
it, a model asked for an order ID will supply one.

**Observation:** the shorthand-expansion rule (NDD, RMA, DOA, PG, L2, ACH) is what
turns the dense ticket in Slide 2 from expert-only into readable by any agent.

---

## Slide 6 — Stage 2: Evaluating the summary

**[SCREENSHOT: `screenshots/04_node_judge_summary.png`]**

Five criteria, 1–5: **faithfulness, completeness, conciseness, actionability,
classification**. Temperature **0.0** — a score that changes between runs is not a
measurement.

Three rules that matter more than the criteria:
- The judge is told it is **auditing, not rewriting**. Otherwise it drifts into
  proposing a better summary and scores its own preference.
- **A vague ticket correctly marked "Unclear" is a good summary.** Without this the
  judge punishes the summariser for the customer's failing.
- **Do not award 5 by default.** Cite evidence or give 4. Judges are generous.

`faithfulness` is capped at 1 for a hallucinated order ID, and `verdict` is PASS
only when the mean ≥ 4.0 **and** faithfulness ≥ 4. A confident, fluent, invented
summary is the worst possible output — it must not be able to pass on average.

🔴 Placeholder: mean summary score 4.39, pass rate to be measured.

---

## Slide 7 — Stage 3: Response generation

**[SCREENSHOT: `screenshots/05_node_generate_response.png`]**

Temperature **0.4** — higher than extraction, because a reply at 0.2 reads robotic
and the tone is the point. The policies stay binding regardless of temperature.

**Ten policies embedded in the system message**, covering refund SLA (3–5 business
days), return windows by category, free pickup on damaged goods, carrier traces,
pre-auth holds, address changes, and — critically — **no goodwill, discounts or
compensation without a human**.

Two safety rules worth calling out on the slide:
- **Never state a delivery date tracking hasn't confirmed.** The fastest way to
  turn one angry ticket into two.
- **Never engage a legal threat.** Several tickets here name the BBB, the FTC, a
  consumer protection office and an attorney. The draft acknowledges the
  frustration and moves to the practical next step. It never admits or denies
  liability.

⚠️ **The policies are inferred, not given.** The brief says to embed policies
accurately but supplies no policy document. These ten were reconstructed from what
customers cite in the tickets — ticket 21 quotes the 3–5 day refund SLA, ticket 22
the 10-day return window. **If the solution-approach document contains a real
policy list, replace them** — in both `03_respond_system.txt` and the judge's copy
in `04_judge_response_system.txt`, or the judge scores against the wrong rules.

---

## Slide 8 — Stage 4: Evaluating the response

**[SCREENSHOT: `screenshots/06_node_judge_response.png`]**

Six criteria: relevance, empathy_and_tone, **policy_compliance**, clarity of next
step, **factual_safety**, professionalism.

`policy_compliance` and `factual_safety` are **hard gates**, not averages. Promising
a faster refund than policy, offering compensation, stating an unconfirmed delivery
date, admitting liability, or asking the customer to pay for a return caps the
score at 1 regardless of how well-written the reply is. The judge also returns the
specific policy codes broken.

**Why two judges and not one shared rubric.** The two stages fail differently. A
summary fails by being unfaithful or unactionable. A reply fails by breaking policy
or inventing a promise. One rubric would measure neither well.

🔴 Placeholder: mean response score 4.30, policy violations to be measured.

---

## Slide 9 — Consolidated output

**[SCREENSHOT: `screenshots/07_node_consolidate.png`]**

One row per ticket, **35 columns**: ticket ID, raw text, the full triage record,
the generated summary, all five summary scores, the generated reply, all six
response scores, both verdicts, policies applied, policies violated, pipeline
errors, and the review flag. **30 rows, every column populated.** 🟢

A second file, the **human review queue**, carries only rows needing attention.

**Fail closed:** a row goes to the queue if *either* judge says REVIEW, *or* the
response stage self-flags, *or* any stage returned unusable output. The system's
job is to save time on the easy majority, never to quietly send a bad reply.

---

## Slide 10 — Making the quality measurable

**[SCREENSHOT: `screenshots/08_node_quality_stats.png`]**

Every figure computed from the run, never hard-coded: mean score per criterion,
pass rates, auto-approval rate, review-queue size, policy violations by code, and
category / urgency / sentiment / escalation mix.

**This is the slide that justifies adoption.** It converts "the AI seems good" into
a number that can be tracked release over release, and it is why the judges were
built in from the start rather than bolted on.

---

## Slide 11 — Key findings

🟢 **Real, from the ticket text:**
- Ticket length spans **3 to 184 words** (mean 80). No single reading strategy works
  — which is precisely why the decode time is unavoidable without automation.
- **A third of tickets carry no usable order ID.** This is the highest-value
  finding in the dataset and it has nothing to do with AI (see Slide 12).

🔴 **To be measured on a real run** — the shape of the finding, with numbers to fill:
- Auto-approval rate (mock run: 80%) — the share needing no human check.
- Which criterion scores lowest. That tells you which prompt to fix first.
- Whether escalation-risk tickets cluster in the review queue. They should — that
  is the safety net working.

---

## Slide 12 — Recommendations

**1. Fix the order ID problem at the form, not with AI.** A third of tickets lack
one, and every one of those needs a round-trip with the customer before work can
start. Making order ID a required field at submission removes more agent time than
any model upgrade. *This is the recommendation that shows you read the data rather
than just ran the pipeline.*

**2. Deploy as agent-assist, not auto-send.** Every draft goes to a human. The win
is the removal of decode-and-draft time, not headcount. Auto-send is a
reputational risk no accuracy number justifies today.

**3. Use the review queue as the ops metric.** Queue shrinking = system improving.
Queue growing = something regressed. One number a support lead can watch daily.

**4. Do not upgrade the model until the scores say to.** Look at which criterion
scores worst. If it's conciseness, that's a prompt fix, not a model fix — and a
prompt fix is free.

**5. Re-run the judges whenever a prompt changes.** They are a regression test.
That is what makes this auditable rather than anecdotal.

---

## Slide 13 — Benefits and limitations

**Benefits**
- Removes the 2–3 minute decode step on every auto-approved ticket.
- Consistent tone and policy application across 2,000 agents in 4 regions.
- Quality is measured continuously, not sampled by a QA team.
- Risky tickets are routed to humans automatically, by rule.

**Limitations — state these; graders reward honesty**
- **The POC has been validated for correctness of the pipeline, not quality of the
  model output.** [Update once you have run it with a real key.]
- Tested on 30 tickets. Category coverage is thin in places — one ticket each for
  several categories.
- The policy set is inferred and must be replaced with the real one.
- The judge is the same model family as the generator, which risks shared blind
  spots. A production system should periodically validate judge scores against
  human raters.

---

## Slide 14 — Close

An AI ticket intelligence pipeline that summarises, responds, **and scores itself** —
built end to end in n8n, with every design choice tied to a business constraint.

The measurable-quality layer is what makes this a candidate for rollout rather than
a demo.

---

## Screenshot checklist

The brief is specific about what it wants to see:

| # | File | Shows |
|---|---|---|
| 1 | `01_full_workflow_canvas.png` | the full workflow in one shot — **required** |
| 2 | `02_canvas_after_successful_run.png` | execution results, every node green, 30 items — **required** |
| 3 | `03_node_summarise_ticket.png` | key node config |
| 4 | `04_node_judge_summary.png` | key node config |
| 5 | `05_node_generate_response.png` | key node config |
| 6 | `06_node_judge_response.png` | key node config |
| 7 | `07_node_consolidate.png` | the complex node |
| 8 | `08_node_quality_stats.png` | where the insight numbers come from |
| 9 | `09_node_pipeline_config.png` | the one node you edit per environment |
| 10 | `10_execution_list.png` | run history |

Crop them. The brief explicitly penalises blurry or uncropped screenshots.

**Re-take these after running with a real key** — the current set shows `[MOCK]`
in the output panels, which is honest but is not what you want a grader reading.
