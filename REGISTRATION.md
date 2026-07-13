# Recommended Luma Registration Form

Twelve questions for the event registration page, with the internal field each maps to
(see `pipeline/ingest.py` `COLUMN_MAP` for header matching and `app/models.py` for enums).

**Design principle:** collect facts and constraints on the form; measure chemistry at the
event. Speed-dating research shows stated trait preferences don't predict who people
actually choose in person — so the form captures alignment facts (commitment, runway,
ambition, equity) and complementarity facts (role, edge, proof of work), and leaves
interpersonal fit to the rounds themselves.

---

### 1. Primary role

> **What do you bring day-to-day?**

Options: Engineering / Product / GTM (sales, marketing, growth) / Science / Ops / Policy

Maps to: `role` (`primary role`)

Rationale: Founding teams need complementary functional skills; role is the first axis of complementarity (Wasserman).

### 2. Role needed

> **What role are you most looking for in a cofounder?**

Options: Engineering / Product / GTM / Science / Ops / Policy / **Open — convince me**

Maps to: `role_needed` (`role needed`; "open" falls back to the default)

Rationale: Explicit demand-side signal lets the matcher pair complements instead of clones; an "open" option avoids forcing a false constraint.

### 3. Lane + idea flexibility

> **Where are you in the idea journey?**

Options:
- I have an idea and I'm committed to it
- I have an idea but I'd drop it for a better one
- I want to join someone else's idea
- Fully flexible — idea or joiner

Maps to: `lane` (`lane`) + `idea_flexibility` (`idea flexibility`)

Rationale: Idea-owner × joiner pairs avoid the two-visionaries collision; flexibility on the idea predicts whether a pair can converge (Entrepreneur First's edge/idea framing).

### 4. Climate areas (max 3) + top area

> **Which climate areas are you focused on? Pick up to 3, and star your top one.**

Options: energy, solar, wind, hydrogen, grid infrastructure, transport, EVs, buildings, food, agriculture, water, ocean, forestry, biodiversity, carbon removal, circular economy, sustainable materials, climate finance, policy

Maps to: `climate_areas` (`climate areas (all that apply)`) + `top_climate_area` (`top climate area`)

Rationale: Shared domain passion is where similarity helps — pairs need a problem they both care about, even when their skills differ.

### 5. Commitment

> **How committed are you to starting a company right now?**

Options:
- Full-time now — this is what I'm doing
- Full-time within 3 months if I find the right person
- Part-time / nights and weekends for now
- Exploring — here to learn and meet people

Maps to: `commitment` (`commitment`)

Rationale: Commitment asymmetry is the top predictor of cofounder breakups (Wasserman); the conditional tier separates genuinely-ready from browsing.

### 6. Runway

> **If you went full-time unpaid tomorrow, how long could you last?**

Options: Less than 3 months / 3–12 months / 12+ months / Prefer not to say

Maps to: `runway` (`runway`)

Rationale: Runway mismatch forces one founder to seek income while the other sprints — a hidden commitment mismatch (YC cofounder-matching guidance).

### 7. Working arrangement + city

> **How do you want to work with a cofounder, and where are you based?**

Options: In-person / co-located · Remote-friendly — plus a free-text city field

Maps to: `arrangement` (`working arrangement`) + `location` (`location`)

Rationale: Two colocated-only founders in different cities is a hard constraint, not a preference — better to filter it before the event.

### 8. Equity philosophy

> **Which best matches your view on splitting equity? (Pick one — no "it depends".)**

Options:
- Equal split, period
- Roughly equal, with vesting to protect everyone
- Split should reflect contribution (idea, capital, time)
- No strong view yet

Maps to: `equity_philosophy` (`equity philosophy`)

Rationale: Quick, unnegotiated splits correlate with team instability (Wasserman); surfacing philosophy early flags equal-vs-contribution clashes before they're personal.

### 9. Decision style

> **When my collaborator and I disagree on something important, I most want to…**

Options:
- Debate it out loud until one of us wins
- Write up both positions, then decide
- Defer to whoever owns that area
- Run a test and let the data decide

Maps to: `decision_style` (`decision style`)

Rationale: Conflict style predicts working-relationship durability more than surface personality traits (First Round founder-dating playbook).

### 10. Proof of work (two links + 15-word summaries)

> **Share two links that show your best work (repo, product, paper, deck, press). For each, add one line — max 15 words — on what *you specifically* did.**

Maps to: `proof_link_1`/`proof_link_2` (`proof link 1`/`proof link 2`) + `proof_summary_1`/`proof_summary_2` (`proof 1 summary` / `proof link 1 description`)

Rationale: Demonstrated output beats self-description; the "what you did" line separates builders from bystanders (EF selects on evidence of edge).

### 11. 90-day intention

> **What do you want to have shipped, tested, or decided in 90 days — and what's blocking it?**

Free text, 2–3 sentences.

Maps to: `intention_90_day` (`90-day intention`)

Rationale: Concrete near-term goals reveal pace and seriousness; the "what's blocking it" clause tells matches exactly how they could help.

### 12. Hardest thing

> **What's the hardest thing you've built or run, in one sentence?**

Free text, one sentence.

Maps to: `hardest_thing` (`hardest thing`)

Rationale: A single concrete peak-difficulty story is a fast, honest proxy for resilience and edge — and a ready-made conversation opener at the table.
