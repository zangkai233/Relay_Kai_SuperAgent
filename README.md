# Relay Kai SuperAgent

**One executive agent. Learned specialists in every vertical domain. A supervisor that checks real outcomes.**

## The thesis

Our thesis is that **the only viable engineering path to practical AGI** is a hierarchy: one Super Agent coordinates domain Boss Agents, while each vertical domain develops its own machine learning capability. The Super Agent turns a human goal into a dependency-aware plan, chooses specialists, passes results between them, and replans when evidence shows a gap.

A domain Boss is more than an API wrapper. Travel should learn from route reliability and arrival outcomes; scheduling from conflicts and user preferences; shopping from availability and substitutions. Each specialist needs its own data, models, memory, tools, and measurable feedback. The Super Agent learns how to compose these capabilities into work that crosses domains.

```text
User goal → Super Agent → Domain Bosses → Worker Agents / tools
                 ↑                 ↓
                 └── Supervisor ← observable outcomes
```

**Relay, not a static tree:** a calendar result can change a travel plan; a missing grocery item can change dinner and study timing. The workflow is a dynamic dependency graph. The Supervisor checks concrete signals such as user confirmations, checklist completion, deadlines, and external state. If the goal is incomplete, it sends the missing work back to the right Boss. Successful and failed outcomes become training data for the corresponding domain.

## What this repository demonstrates

The current FastAPI + vanilla HTML/CSS/JavaScript demo streams two scripted workflows with Server-Sent Events:

- A visa appointment: schedule, route, documents, battery, departure, arrival, and on-site checklist.
- An evening plan: groceries, an out-of-stock substitution, cooking, ML Chapter 10 review, and sleep before a 9:00 lecture.

The phone view simulates user taps. Supervisor decisions are computed from those checklist states, including a failed check followed by a successful recheck. **This demo uses fixed data; it does not call an AI model or a live external API.** It illustrates the control loop, not AGI itself.

## Next steps

1. Connect real calendar, routing, device, and order signals with explicit user permission.
2. Record task state, handoffs, user corrections, and verified outcomes as structured data.
3. Train and evaluate domain-specific models against those outcomes.
4. Train the Super Agent to delegate, reconcile conflicting results, and stop only when the Supervisor has sufficient evidence.

## Run the demo

```bash
python3 -m pip install fastapi uvicorn
python3 main.py
```

Open `http://127.0.0.1:8000`.
