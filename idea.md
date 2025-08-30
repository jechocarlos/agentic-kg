Imagine you have tons of internal documents (policies, meeting notes, contracts, Jira tickets). You want a knowledge graph so people (or bots) can query: “Who approved the new leave policy and when?”

🔄 Agent Flow

Ingestion Agent

Pulls docs from SharePoint, Confluence, Jira, emails.

Normalizes them into text + metadata.

Extraction Agent

Uses an LLM (fine-tuned or prompted) to do NER (named entity recognition) + relation extraction.

Example:

Entity: “Leave Policy 2025”

Entity: “HR Director – Maria Santos”

Relation: “approved by”

Date: “July 12, 2025”

Schema Agent

Decides how to slot new info into the ontology.

If “Policy” class already exists → add “Leave Policy 2025” there.

If it encounters a new type (“Sustainability Program”), it proposes adding a new class.

Validation Agent

Checks for duplicates, conflicting facts.

Example: Doc A says “Approved by Maria Santos”, Doc B says “Approved by John Cruz.”

The agent either:
a) Keeps both but adds provenance (who said it, when).
b) Flags for human review.

Graph Construction Agent

Writes nodes/edges into Neo4j (or similar graph DB).

Handles versioning and provenance (so you can trace facts back).

Maintenance Agent

Periodically scans new docs.

Detects if entities changed roles (e.g., Maria Santos → now “VP of HR”).

Updates graph accordingly.

Query Agent (for RAG)

When user asks: “Who approved the leave policy?”

It doesn’t just keyword search, it queries the KG: