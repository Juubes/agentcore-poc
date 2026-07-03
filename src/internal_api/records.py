"""Mock records for the demo internal system. Every record is tagged with the
IdP group allowed to see it."""

DATA = {
    "documents": [
        {"id": "DOC-101", "title": "Service runbook: gateway", "group": "engineering"},
        {"id": "DOC-102", "title": "On-call escalation policy", "group": "engineering"},
        {"id": "DOC-201", "title": "FY25 budget model", "group": "finance"},
        {"id": "DOC-202", "title": "Vendor contract summary", "group": "finance"},
    ],
    "tickets": [
        {"id": "ENG-4412", "title": "p95 latency regression", "group": "engineering"},
        {"id": "ENG-4419", "title": "Rotate signing keys", "group": "engineering"},
        {"id": "FIN-88", "title": "Q3 invoice reconciliation", "group": "finance"},
    ],
    "employees": [
        {"id": "E-1", "name": "Ada (Staff Eng)", "group": "engineering"},
        {"id": "E-2", "name": "Grace (SRE)", "group": "engineering"},
        {"id": "E-9", "name": "Rao (Controller)", "group": "finance"},
    ],
    "customers": [
        {"id": "C-77", "name": "Acme Corp", "group": "finance"},
        {"id": "C-78", "name": "Globex", "group": "finance"},
    ],
}
