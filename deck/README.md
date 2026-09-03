# Solution presentation

The graded submission for the no-code track is a PDF presentation, not the n8n
JSON — the brief says so outright: *"The n8n JSON file is not required."*

`ShopNest_Solution_Presentation.pptx` is built into the Great Learning template,
23 slides, following the template's own section order.

## What is finished and what is not

Everything that does not depend on a live model run is written: the problem
framing, the architecture, every design rationale (model choice, temperature per
stage, prompting technique), the four embedded policies, the evaluation criteria,
and the business insights and recommendations.

Two kinds of gap remain, both marked in **red** on the slides so they cannot be
missed:

- `[ SCREENSHOT: ... ]` — must be captured from a real run in the learner's own
  lab, with their file paths and real output. Local screenshots would show mock
  text and the wrong paths.
- `TO FILL FROM THE RUN:` — observations that depend on real scores. These are
  deliberately left blank rather than invented.

The business insights carry **real** figures throughout. They are computed from
the ticket text itself, so they hold regardless of which model runs:

| Figure | Value |
|---|---|
| Tickets | 30 |
| Length | 3 to 184 words; mean 80, median 57 |
| Under 20 words / over 120 | 4 / 9 |
| Carrying an order reference | 20 of 30 |
| Carrying none | 10 of 30 |
| Carrying two different ones | 1 (ticket 6) |
| Using legal or escalation language | 4 (tickets 1, 10, 11, 24) |

## Rebuilding

```
python3 /opt/freelancer/skills/pptx/scripts/rearrange.py template.pptx working.pptx \
  0,1,2,3,11,4,4,5,5,6,6,7,7,7,8,8,9,11,11,10,11,11,12
python3 resize_bodies.py          # fix the template's undersized boxes, strip decoration
python3 /opt/freelancer/skills/pptx/scripts/inventory.py working.pptx text-inventory.json
python3 make_replacements.py      # all slide copy lives here
python3 /opt/freelancer/skills/pptx/scripts/replace.py \
  working.pptx replacement-text.json ShopNest_Solution_Presentation.pptx
```

`resize_bodies.py` exists because the template's body placeholders are sized for
a single line of instruction text, and it also strips two kinds of leftover
decoration: empty body text boxes that render as stray bullet dots, and the small
0.21" bullet glyphs, which are placed one per line of the template's placeholder
text and so end up miscounted against real content. The APPENDIX divider is an
empty shape too, but a 10"-wide solid bar — hence the split by shape type.
