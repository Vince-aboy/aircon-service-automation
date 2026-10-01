# Phases 0–9 Roadmap

```mermaid
flowchart TD
    P0[Phase 0<br/>Plan the synthetic MVP] --> P1[Phase 1<br/>Python, tests, PostgreSQL foundation]
    P1 --> P2[Phase 2<br/>Controlled booking database]
    P2 --> P3[Phase 3<br/>Local service-request form]
    P3 --> P4[Phase 4<br/>Staff review and team dispatch]
    P4 --> P5[Phase 5<br/>Job lifecycle and audit trail]
    P5 --> P6[Phase 6<br/>Protected synthetic n8n webhook]
    P6 --> P7[Phase 7<br/>Local app to n8n connection]
    P7 --> P8[Phase 8<br/>Dispatcher notice and completion shortcut]
    P8 --> P9[Phase 9<br/>Duplicate, failure, and retry protection]
```

## Completed outcomes

| Phase | Outcome |
| --- | --- |
| 0 | Defined a bounded synthetic-only MVP. |
| 1 | Created local Python, Pytest, and PostgreSQL foundation. |
| 2 | Added controlled relational booking schema. |
| 3 | Built local request form and receipt. |
| 4 | Added staff approval and two-team scheduling. |
| 5 | Added job lifecycle, history, cancellation, and completion shortcut. |
| 6 | Built protected unpublished n8n synthetic webhook workflow. |
| 7 | Connected local synthetic outbox to n8n test webhook. |
| 8 | Stored/displayed dispatcher notice after completed jobs. |
| 9 | Added duplicate prevention, visible failed delivery, and retry evidence. |
