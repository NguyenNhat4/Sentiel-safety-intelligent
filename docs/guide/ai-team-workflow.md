Here is the synthesized article in English, ready to be shared with your team:

---

# 🚀 [INTERNAL SHARING] HOW TO OPERATE A SOFTWARE ENGINEERING TEAM IN THE AI ERA

*(Key takeaways from the presentation by Nguyen Tri Dung - CTO Builder)*

Team,

As AI tools and Coding Agents (like Claude Code, Codex, and Cursor) become commonplace, every engineer now effectively has their own "personal AI army". While this skyrockets individual productivity, it raises a critical question: how do we operate and build products together as a team without causing chaos?

Here are the core principles we need to align on to successfully build products alongside AI.

### 1. The Reality of AI: High Speed but Lacks "Context"

* Building a small project is like building a hut: one person and AI are enough. But building real, scaled products is like building a skyscraper; it strictly requires architectural design, clear assignments, standards, and monitoring.


* AI acts like a blazing-fast construction robot. However, it lacks the overall context of the system and only optimizes for local tasks.


* If we lack processes and architecture, AI will not help us build faster—it will simply help us break things faster.



### 2. The Four Pillars of Software Development

AI accelerates individuals, but it does not replace the system. We must maintain four essential pillars:

* **Method:** Our mindset and work organization, such as Agile, Scrum, and dividing work into Sprints.


* **People:** In the AI era, members might wear multiple hats, but responsibilities (who does what and who is accountable) must remain clearly defined.


* **Workspace & Tools:** Centralized storage for documents, source code (Git), and task management (Jira, Linear, etc.).


* **Workflow & Rules:** A consistent flow (Idea -> Spec -> Dev -> Test -> Release) guided by shared standards like coding conventions, PR rules, and Definition of Done (DoD).



### 3. The Git Repo as Our "Single Source of Truth"

To ensure both the team and the AI agents are moving in the exact same direction, all project context must live in one shared workspace.

* **`/specs`**: Business rules, features, user roles, and API contracts.


* **`/adrs`**: Architecture Decision Records detailing our tech stack, folder structure, and conventions.


* **`/planning` & `/tasks**`: Sprint plans, backlogs, and user stories.


* **`/src`**: The project codebase.


* **`/docs`**: Runbooks, guidelines, and an `AGENTS.md` file establishing the rules for our AI tools.



### 4. 6 Golden Rules for Team + AI Execution

1. **Spec-Driven (Do Not Code First):** Clarify "what", "why", and "how" before any code is written. The spec is the shared source of truth; a good spec prevents costly pivots later.


2. **ADR is the Foundation:** Every architectural and technical decision must be documented. This prevents different AI agents from writing code in conflicting styles.


3. **Assign Large Tasks:** The team should manage tasks at the feature level. Give the AI space to plan and break these larger items down into subtasks itself.


4. **Work via Contracts:** Services and domains must communicate strictly through defined contracts (API/gRPC/Events). The team only needs to know the "commitment," not the internal implementation, allowing parallel work.


5. **AI Must Always Read the Context:** Before writing a single line of code, the AI agent must read the specs, ADRs, and contracts. Clearer context equals fewer loops and better alignment.


6. **Git Workflow Discipline:** Utilize clear branches, mandate Pull Requests and reviews (by humans or AI), and only merge when the DoD is fully met.



### 5. Bonus: Structuring Tasks for AI Success

If the AI produces incorrect results, it is almost always because the provided context was insufficient or outdated. Follow this logic chain for smooth parallel execution:

* **Clear Boundaries:** Split the system by domains (Microservices or Modular Monolith) so members can work concurrently with minimal code conflicts.


* **Clear Contracts:** Scale the team using explicit API contracts, not implicit understandings.


* **Clear Tests:** Prioritize writing tests or Acceptance Criteria upfront. Tests act as a clear "destination," allowing the agent to code, run tests, and self-correct.


* **Clear Conventions:** Enforce strict folder structures and coding styles so the AI does not multiply chaos. Remember: "Done" does not mean the code simply runs; it means it passes tests, docs are updated, and it is ready to merge.