# LearnGPS — Knowledge Navigation Platform
## Architecture Design Document

**Role**: CPO + Chief Learning Scientist + Principal AI Architect
**Date**: August 2026
**Version**: 2.0 — "From Tutor to Navigator"

---

## The Core Insight

Google Maps works because the road network is fixed. Knowledge is different: the graph is *partially hidden* — connections between concepts only become visible when you learn both endpoints. Our map should reveal itself as the student learns. This is the mechanic that makes learning feel like exploration, not a checklist.

There's a second difference: Maps has one destination at a time. Knowledge has destinations the student doesn't know they want yet. The system must do discovery *for* them — surfacing "if you master this, you unlock that" to create pull.

---

## 1. Knowledge Graph Schema

### Node Types

**Concept** — the atomic unit (e.g., "Friction", "Pressure", "Gravity")
```
concept_id: string           # e.g., "friction"
name: string
domain: string               # "Physics", "Chemistry", "Math"
subject: string              # "Science", "Mathematics"
grade_range: [8, 10]
abstraction_level: int       # 1 (concrete) to 10 (abstract)
bloom_ceiling: string        # max assessable bloom level for this concept
estimated_hours: float       # average time to reach Apply level
decay_class: enum            # "stable" | "slow" | "fast"
misconceptions: string[]     # known common errors
keywords: string[]
curriculum_alignment: string[] # ["CBSE-8-Ch11", "NCERT-8-Science-Ch11"]
```

**SubConcept** — teachable unit within a Concept (what we have today)
```
subconcept_id: string        # e.g., "sc_friction"
name: string
parent_concept_id: string
chapter_id: string
sequence_order: int
content_summary: string      # 2-3 sentence teachable summary
```

**Chapter** — curriculum grouping
**Domain** — subject area (Physics, Chemistry...)
**Skill** — transferable competency (e.g., "Calculate ratios", "Read graphs")
**Career** — destination cluster (e.g., "Mechanical Engineer", "Data Scientist")
**Exam** — target assessment (JEE, NEET, CBSE Board, Olympiad)

### Relationship Types

```
(A)-[:RECOMMENDED_BEFORE]->(B)  # A is recommended before B — suggested order, NOT a hard gate
(A)-[:STRENGTHENS]->(B)         # mastering A makes B easier (purely optional)
(A)-[:APPLIES_IN {domain}]->(B) # friction applies in tribology (cross-domain)
(A)-[:CONFLICTS_WITH]->(B)      # common misconception pair
(A)-[:SIMILAR_TO {weight}]->(B) # for spaced repetition grouping
(A)-[:PART_OF]->(Chapter)
(A)-[:ASSESSED_IN {weight}]->(Exam)
(A)-[:LEADS_TO {relevance}]->(Career)
(Skill)-[:PRACTICED_BY]->(A)    # a skill is exercised by learning this concept
```

**No relationship type enforces a hard lock.** `RECOMMENDED_BEFORE` encodes pedagogically useful ordering; the student can always navigate to any concept. If a student jumps ahead, Gyaan adapts — see Adaptive Jump Behaviour in Section 6.

### The "Opacity" Property (not fog of war, not locks)

Every concept is **always visible** on the map. **No concept is ever hidden or locked.**

Hidden concepts kill motivation — students can't aim for what they can't see. Hard locks are even worse: they're paternalistic and wrong. A curious student who wants to jump ahead to Atmospheric Pressure should be able to. Gyaan will adapt.

Instead, concepts have an **opacity level** that acts as a *signal*, not a gate:

- **Full opacity** — prerequisites recommended before this are met (mastered/proficient), or actively learning
- **30% opacity (ghost)** — recommended prerequisites pending. Node is still **tappable and accessible** — the dim appearance says "there's context you haven't built yet" not "you are blocked"

The ghost state is a navigational signal: "here be prerequisites." Tapping a ghost node shows a small badge — "Complete SC06 first for best results" — and then opens Gyaan, who adapts by briefly covering the prerequisite gap before teaching the target concept.

This creates pull motivation ("I can see Friction is coming after Normal Force") and respects student agency. As recommended nodes are completed, the concept lights up — a satisfying reveal that rewards the recommended path without punishing the curious explorer.

### Cross-Subject Transfer Edges

The most underused and highest-value addition. Example:
- `(friction)-[:APPLIES_IN {context:"inclined planes"}]->(trigonometry)`
- `(pressure)-[:APPLIES_IN {context:"blood pressure"}]->(biology_circulation)`
- `(resultant_force)-[:APPLIES_IN {context:"vector addition"}]->(mathematics_vectors)`

When Gyaan teaches friction in Class 8 Physics, it should plant a seed: "This same idea appears later in Math when you study inclined planes." That's the moment a student feels the universe is connected.

---

## 2. Mastery Engine

### Why Boolean Mastery Is Wrong

"Mastered = True" after 2 correct answers is a useful MVP hack, not a model of learning. Real mastery has three enemies: **decay**, **bloom gaps**, and **context-dependence**. A student who answers two MCQs correctly has demonstrated recall under one context at one point in time.

### The Mastery Vector

Replace the boolean with a MasteryProfile:

```python
MasteryProfile = {
    # Bloom dimension — scored 0.0-1.0 per level
    "bloom": {
        "Remember":  0.90,
        "Understand": 0.75,
        "Apply":     0.50,
        "Analyse":   0.20,
        "Evaluate":  0.05,
        "Create":    0.00,
    },
    
    # Retention — decays over time, resets on successful recall
    "retention": 0.88,          # current value (see decay model below)
    "last_accessed": "2026-08-20",
    "stability_coefficient": 14, # days until 50% retention without review
    
    # Quality signals
    "confidence": 0.72,         # inferred from response latency + certainty words
    "hint_dependency": 0.30,    # 0 = never needs hints, 1 = always needs hints
    "transfer_score": 0.40,     # performance on cross-domain questions
    
    # Misconception tracking
    "active_misconceptions": [
        {"text": "Friction always opposes motion", "severity": 0.6, "first_seen": "..."}
    ],
    "cleared_misconceptions": [],
    
    # Composite (computed, not stored)
    "mastery_score": 0.61       # weighted formula below
}
```

### Composite Formula

```
mastery_score = (
    0.35 × bloom_composite +
    0.25 × retention +
    0.20 × confidence +
    0.10 × transfer_score +
    0.10 × (1 - hint_dependency)
)

bloom_composite = weighted sum of bloom scores:
    Remember×0.05 + Understand×0.10 + Apply×0.25 + 
    Analyse×0.30 + Evaluate×0.20 + Create×0.10
```

A student who can only recall (Remember=1.0, rest=0) gets bloom_composite = 0.05. One who can apply (Apply=0.8) gets ~0.25. This correctly reflects that application is worth more than recall.

### Forgetting Curve (Retention Decay)

Adapted from SuperMemo SM-2, simplified for real-time use:

```
retention(t) = e^(-t / stability)

stability increases on each successful recall:
  new_stability = stability × 2.0   # if recalled correctly
  new_stability = stability × 0.5   # if failed
  
initial_stability = 1 day (after first correct answer)
```

In practice: if Dhwani mastered friction on Monday and it's Friday, retention = e^(-4/1) ≈ 0.02. The Retention Agent flags this for review. After she reviews it successfully on Friday, stability becomes 2 days. Then 4, 8, 16... This is why spaced repetition works.

### Mastery Thresholds

```
mastery_score < 0.30  → "Exploring"      (just started)
0.30 ≤ score < 0.55  → "Developing"     (can recall and understand)  
0.55 ≤ score < 0.75  → "Proficient"     (can apply reliably)
0.75 ≤ score < 0.90  → "Advanced"       (can analyse and evaluate)
score ≥ 0.90          → "Expert"         (can create/teach)
```

For GPS route purposes, `Proficient` (0.55+) unlocks the next node — equivalent to today's `mastered = true`.

---

## 3. Navigation Engine

The Navigation Engine answers: "What should this student learn next, and in what order, to reach their goal?"

### Route Calculation Algorithm

```
Input: student_id, destination (career/exam/chapter)
Output: ordered list of ConceptNodes to traverse

1. EXPAND DESTINATION
   → Find all Concepts in the destination cluster
   → Score each by relevance_to_goal (edge weight)

2. ASSESS READINESS
   → For each Concept, check:
     a. Recommended prerequisites met (mastery_score ≥ 0.55 on RECOMMENDED_BEFORE nodes)?
     b. Student can always navigate to any concept regardless — prerequisites are advisory only
   → Build "frontier" = concepts where recommended prereqs are met (for default route suggestion)

3. SCORE FRONTIER CONCEPTS
   priority_score = (
       prerequisite_coverage × 0.40 +   # how many prereqs are met
       goal_relevance × 0.35 +           # how important for destination
       consolidation_value × 0.25        # strengthens weak prereqs
   ) / estimated_hours

4. PLAN ROUTE
   → Rank frontier by priority_score
   → Interleave revision items from RetentionAgent
   → Return: [current, next_3, later_10, ghost_N]
   # ghost_N = concepts where prereqs are pending (shown at 30% opacity, still tappable)
```

### Route Modes (like Google Maps alternatives)

**Focused Route** — minimum concepts to reach proficiency. "Highway mode." For students with a specific exam deadline.

**Deep Understanding Route** — full bloom traversal of each concept before advancing. "Scenic route." For students who want to truly master, not just pass.

**Revision Route** — when retention is low across many concepts. "Fix what's fading before building higher."

**Discovery Route** — intentionally explores cross-domain connections. Shows the student how Physics connects to Biology or Math. Builds intuition.

### Learning ETA

```python
def estimate_eta(student, destination_concepts):
    # Student's recent learning velocity
    xp_per_hour = student.total_xp / student.total_study_hours
    
    # For each concept not yet proficient
    remaining_xp = sum(
        concept.estimated_hours * XP_PER_HOUR * (1 - student.mastery(concept))
        for concept in destination_concepts
        if student.mastery(concept) < 0.55
    )
    
    return remaining_xp / xp_per_hour  # hours
    # Display as: "~47 study sessions at your current pace"
```

The ETA updates every session. When Dhwani has a great session, she sees her ETA drop. This is deeply motivating — like a maps ETA updating as you drive faster.

---

## 4. UI Redesign

### Design Principle: The Map is the Product

Today the Map is one of four tabs. In V2, **the map is the home screen**. Everything else radiates from it.

### Screen Architecture

**Map Screen (new home)**
- Full-screen zoomable knowledge graph
- Pan/zoom gestures: zoom out to see all of Physics, zoom in to see subconcepts of Friction
- Node states with visual encoding:
  - 🟢 Green filled = Expert/Advanced (≥0.75)
  - 🟡 Yellow filled = Proficient (0.55-0.75)
  - 🔵 Blue pulsing = Currently learning
  - ⚪ Gray outlined = Visible, ready to learn (recommended prerequisites met)
  - 👻 30% opacity (ghost) = Accessible but prereqs recommended first — tappable with advisory badge
- Tap **any** node (including ghost) → "Quick Info" card with concept summary + "Start Here" button
- Long-press → full concept detail with Bloom progress bar, retention score, ETA
- Filter chips at top: [All] [Needs Review] [Ready to Learn] [Mastered]

**Gyaan Screen (chat)**
- Same Socratic tutor, but now has a "Map Context" header
- Shows: "Currently at: Friction → Apply level"
- "Jump to concept" button top-right → opens map zoomed to current concept
- Each concept Gyaan mentions is tappable → opens that concept on the map

**Journey Screen (was Progress)**
- Timeline of mastery growth, not just XP
- Shows Bloom dimension per concept: a radial chart for each concept (radar-style)
- "Retention risk" section: 3 concepts fading, due for review
- Chapter-level mastery rollup (real data, not hardcoded)

**Destination Screen (new)**
- Student sets a goal: "I want to crack JEE" or "I'm interested in Medicine"
- System shows: the full route, estimated sessions, concepts already covered (green), gaps (red)
- "Recalculate route" button — like rerouting in Maps

**Parent/Teacher View (new, separate)**
- Weekly digest: time spent, concepts mastered, retention at-risk concepts
- Bloom-level heatmap per subject
- No access to chat history (privacy)

---

## 5. Data Model — What Lives Where

### Neo4j (Knowledge Graph)

Everything about the *structure of knowledge*, not the student:
- All Concept and SubConcept nodes
- All relationship types (REQUIRES, STRENGTHENS, APPLIES_IN, etc.)
- Curriculum alignment (which CBSE chapter covers what)
- Career/Exam concept clusters
- Concept metadata (bloom_ceiling, decay_class, misconceptions)

**Why Neo4j**: Graph traversal for route calculation is O(concepts) in Neo4j vs. O(concepts²) in SQL. As we expand to all subjects (500+ concepts), this matters.

### Supabase / PostgreSQL (Student State)

Everything about *individual student progress*:

```sql
-- Core mastery store (replaces current student_progress)
CREATE TABLE concept_mastery (
    student_id        uuid REFERENCES auth.users,
    concept_id        text,                    -- Neo4j concept_id
    subconcept_id     text,                    -- Neo4j subconcept_id
    
    -- Bloom dimension
    bloom_remember    float DEFAULT 0,
    bloom_understand  float DEFAULT 0,
    bloom_apply       float DEFAULT 0,
    bloom_analyse     float DEFAULT 0,
    bloom_evaluate    float DEFAULT 0,
    bloom_create      float DEFAULT 0,
    
    -- Retention
    stability_days    float DEFAULT 1,
    last_accessed     timestamptz,
    
    -- Quality signals
    confidence_score  float DEFAULT 0,
    hint_dependency   float DEFAULT 0,
    transfer_score    float DEFAULT 0,
    
    -- Computed
    mastery_score     float DEFAULT 0,        -- updated by trigger
    mastery_level     text DEFAULT 'Exploring', -- Exploring/Developing/Proficient/Advanced/Expert
    
    -- Legacy bridge (keep for backward compat)
    consecutive_correct int DEFAULT 0,
    mastered          boolean DEFAULT false,   -- mastery_score >= 0.55
    
    PRIMARY KEY (student_id, subconcept_id)
);

-- Assessment history (every question-answer pair)
CREATE TABLE assessment_events (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id        uuid REFERENCES auth.users,
    subconcept_id     text,
    bloom_level       text,
    question_type     text,
    correct           boolean,
    response_latency_ms int,
    hints_used        int,
    session_id        uuid,
    created_at        timestamptz DEFAULT now()
);

-- Misconception tracking
CREATE TABLE misconception_instances (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id        uuid REFERENCES auth.users,
    concept_id        text,
    misconception_text text,
    severity          float,
    first_seen        timestamptz DEFAULT now(),
    last_seen         timestamptz DEFAULT now(),
    cleared_at        timestamptz,
    evidence_count    int DEFAULT 1
);

-- SRS revision schedule (from Retention Agent)
CREATE TABLE revision_schedule (
    student_id        uuid REFERENCES auth.users,
    subconcept_id     text,
    due_date          date,
    priority          float,
    PRIMARY KEY (student_id, subconcept_id)
);
```

### ChromaDB (Semantic)

- NCERT content chunks (254 already indexed)
- Question bank embeddings (for semantic deduplication)
- Student explanation history (to detect misconceptions via similarity)
- Concept description embeddings (for "related concepts" discovery)

**New addition**: Student's own past explanations, embedded and stored. When a student explains something wrong, we embed their explanation and compare it against the known-misconception vectors. High similarity → misconception detected.

### Redis / Edge Cache

- Active session state (current subconcept, bloom level, hint count)
- Navigation route for current session (cached, invalidated on mastery update)
- Real-time mastery score (avoids DB read on every chat turn)

---

## 6. Agent Architecture

The current system has one agent: Gyaan the tutor. The V2 system has five specialized agents coordinated by a Navigator.

### Navigator Agent (NEW — the orchestrator)

The "dispatch center" of the system. Runs before and after every interaction.

**Responsibilities**:
- Determines what concept to teach next (calls Neo4j route engine)
- Decides the *mode* for each turn: explain → question → revise → simulate → celebrate
- Reads outputs from all other agents to make decisions
- Updates the GPS map state

**Decision tree per session**:
```
1. Check RetentionAgent → any urgent reviews due? → insert revision turn
2. Check MisconceivedAgent → active misconceptions? → address before advancing
3. Check MasteryEngine → current concept at Proficient? → advance to next node
4. Else → continue current concept at appropriate bloom level
```

### Gyaan — Socratic Agent (current tutor, refined)

Today Gyaan does everything. In V2, Gyaan focuses only on the Socratic dialogue:
- Teaches via guided questions (not lectures)
- Produces structured output: `{reply, xp_earned, bloom_advance, misconception_detected, confidence_signal}`
- No longer decides what to teach — that's Navigator's job
- Receives system prompt enriched with: current concept, bloom target, known misconceptions to address, prerequisite context from Neo4j

**New input from Neo4j**: prerequisite chain context. Before teaching Pressure, Gyaan knows the student's Force mastery is at 0.65. The system prompt says: "Student understands Force (Apply level). Build on this — use force examples they already know."

### Gyaan's Adaptive Jump Behaviour (when student navigates ahead)

A student can tap any ghost node and Gyaan opens. Gyaan receives a flag: `jumped_ahead: true` with the list of pending recommended prerequisites and the student's current mastery on each. Gyaan's response strategy:

| Gap size | Situation | Gyaan's approach |
|---|---|---|
| 1 node behind | Missing 1 recommended prereq | One-sentence bridge: "For this we need Normal Force — here's the key idea in brief." Then teaches target. |
| 2-3 nodes behind | Skipped a short chain | 2-3 question warm-up on the gap concepts, framed as "let me give you quick context first." |
| 4+ nodes behind | Jumped to a late concept | Starts at **Remember** bloom regardless of prior performance. Progressively builds: Define → Explain → Example → Apply. |
| Student already knows it | High prior knowledge signal | Gyaan assesses first with 2 calibration questions. If correct → advances to Apply bloom immediately. Avoids wasting a curious student's time. |

**Key principle**: Gyaan never says "you can't do this yet." It says "let me give you a bit of context first" — and then teaches. The student who jumped ahead always leaves having learned something, whether it's the target concept or the missing bridge.

### Assessment Agent (extracted from current logic)

Currently, assessment happens inside Gyaan's response. In V2, it's a dedicated step.

**Responsibilities**:
- Selects questions calibrated to student's current theta (ability estimate)
- Uses Item Response Theory: chooses questions with difficulty matching ability ± 0.5 SD
- Produces: `{bloom_delta, confidence_delta, misconception_flag, correct}`
- Feeds into MasteryEngine on every answer

**IRT in practice**: we don't need full IRT modeling initially. Simpler approach: tag each question in the bank with `difficulty: float (0.0-1.0)`. If student mastery_score = 0.55, target questions with difficulty 0.50-0.65. Too easy = no information gain. Too hard = demotivation.

### Retention Agent (NEW)

Runs asynchronously, not in the critical path of chat.

**Responsibilities**:
- Nightly: compute current retention for every mastered concept across all students
- Flag concepts where retention < 0.50 (fading fast)
- Generate revision schedule (due_date per concept)
- In-session: tell Navigator "this student hasn't touched Muscular Force in 12 days, retention = 0.22 — insert one recall question before advancing"

**Implementation**: a scheduled Railway cron job calling a Python function that:
1. Reads all concept_mastery rows where mastered=true and last_accessed < now - 3 days
2. Computes retention = e^(-days_since_access / stability_days)
3. Updates retention score and upserts revision_schedule

### Misconception Agent (NEW)

**Responsibilities**:
- Analyzes student explanations for known misconception patterns
- Pattern: embed the student's explanation, compare cosine similarity to misconception embeddings
- If similarity > 0.85 → flag misconception, pass to Gyaan to address it
- Tracks misconception lifecycle: first_seen, severity, cleared_at

**Why this matters**: The most common learning failures aren't "didn't learn it" — they're "learned it wrong and it calcified." Friction misconception example: many students believe "friction always opposes motion." This is subtly wrong — friction opposes *relative motion*, and can actually drive a wheel forward. If this isn't caught, the student will fail application-level questions for years.

### Parent/Teacher Digest Agent (NEW, async)

**Responsibilities**:
- Weekly: compile a digest for each parent/teacher linked to a student
- Format: "This week Dhwani spent 3 sessions on Friction. She reached Apply level. Her retention of Contact Force is fading — a review session this weekend would help."
- Delivered via: email / WhatsApp (future) / in-app notification

---

## 7. One-Year Roadmap

### Phase 1: Foundation Hardening (Now → Month 3)
*Current MVP is in production. These are stability fixes, not features.*

- Day streak counter (daily login tracker, increment streak_days)
- Wire Neo4j prerequisite context into Gyaan's system prompt (highest-value, 2 days work)
- Fix Map: show correct "current" node based on actual mastery (not just first subconcept)
- Progress screen: real bloom level from student_progress (remove "Apply level" hardcode)
- Expand to 2 more chapters (Light, Motion) to validate cross-chapter GPS routing
- Deploy Retention Agent as a nightly Railway cron job

### Phase 2: Mastery Engine (Month 3-6)
*Replace boolean mastery with the multi-dimensional model.*

- Migrate student_progress → concept_mastery table (additive schema change, no breaking)
- Implement bloom dimension scoring (6 floats per subconcept)
- Add confidence inference from response latency (frontend measures time-to-answer)
- Add hint_dependency tracking (already have hint_count, normalize it)
- Implement retention decay calculation (simple formula, run nightly)
- Update GPS map visuals to show mastery gradient (not just done/not-done)
- Mastery score visible to student: "You're at Apply level (61% mastery)"

### Phase 3: Navigation Engine + Map V2 (Month 6-9)
*The map becomes the product.*

- Build Destination Screen: student picks a goal (JEE / NEET / Doctor / Engineer)
- Load career → concept cluster mapping into Neo4j
- Implement route calculation algorithm (Dijkstra on knowledge graph)
- Learning ETA calculation and display
- Map V2: zoomable concept graph, fog-of-war for hidden concepts
- Cross-subject concept links (Physics ↔ Math connections appear on map)
- Misconception Agent: detect top 20 known misconceptions per chapter

### Phase 4: Multi-Agent Orchestration (Month 9-12)
*Extract specialized agents from Gyaan.*

- Navigator Agent: separate service, orchestrates all others
- Assessment Agent: IRT-calibrated question selection
- Retention Agent: in-session revision inserts (not just async)
- Parent Digest Agent: weekly email report
- Expand to all Class 8 Science chapters
- Teacher dashboard: class-level mastery heatmap
- Misconception tracking dashboard

### Phase 5: Social + Scale (Month 12+)
*The product becomes a platform.*

- Peer ambient awareness: "2 students are also mastering Friction this week" (anonymized)
- School/teacher onboarding: class roster, bulk progress reports
- Content expansion: Class 9 and 10
- API for third-party content integration
- Mobile app (PWA → React Native)

---

## What We're NOT Building (Deliberate Choices)

**Leaderboards and competitive XP**: Research consistently shows leaderboards help high performers and demotivate everyone else. We use XP as personal progress fuel, not social currency.

**Video-first content**: We have DIKSHA integration for videos, but they're a supplement not the core. The evidence for learning through dialogue (Socratic method) far exceeds passive video watching for deep understanding.

**AI-generated explanations as lectures**: Gyaan asks questions, doesn't lecture. This is a non-negotiable pedagogical choice. When Gyaan does explain, it's to correct a misconception after the student has tried — not as the first move.

**Weekly/monthly subscriptions with paywalls mid-chapter**: A student who starts a chapter should be able to finish it. Monetization gates happen at chapter/grade boundaries, not mid-concept.

---

## The Hardest Problem: Transfer Learning

The biggest unsolved problem in education technology — and in human learning generally — is *transfer*: the ability to apply knowledge in a new context. A student who has "mastered" friction in a physics context still can't apply it to understand why car brakes work differently in rain.

Our transfer_score in the mastery vector is an early gesture toward measuring this. The full solution requires:
1. Cross-domain questions that deliberately present a concept in an unfamiliar domain
2. A cross-subject knowledge graph with APPLIES_IN edges
3. A transfer task library: problems where the student must recognize that a known concept applies

This is Year 2 work. But the schema is designed for it now.

---

## Current State vs. Target State

| Component | Today (MVP) | V2 Target |
|---|---|---|
| Mastery | Boolean (2 correct) | 6-dim Bloom × Retention × Confidence |
| Navigation | Linear subconcept order | Graph-based with career destinations |
| Knowledge graph | Force & Pressure only | All Class 8-10 Science + cross-subject |
| Map UI | Vertical path with nodes | Zoomable opacity-based knowledge map (no fog, no locks) |
| Agents | Gyaan (monolith) | 5 specialized agents + Navigator orchestrator |
| Forgetting | No model | SM-2 inspired decay + revision scheduling |
| Misconceptions | Not tracked | Detected, tracked, cleared |
| Parent visibility | None | Weekly digest + in-app dashboard |
| Destinations | None | JEE, NEET, career clusters with ETA |

---

*The architecture is designed so each phase delivers standalone value — no phase depends on completing the next. Phase 1 makes today's product stable. Phase 2 makes mastery meaningful. Phase 3 makes navigation real. Phase 4 makes the system truly intelligent. Each is independently deployable.*
