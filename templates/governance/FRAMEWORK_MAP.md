# Evidence map: what the kit's outputs support in common AI governance frameworks

This is **not** a compliance assessment. Most framework items are organisational (policies,
roles, training, supplier management) and no testing kit can satisfy them. The map shows
where kit outputs give evidence, and where the gaps are for an organisation to fill.

Versions checked 2026-10-03; confirm against the current texts before relying on this.

## AI事業者ガイドライン 第1.2版 (MIC and METI, 2026-03-31)

Common guiding principles (共通の指針), for the AI provider (AI提供者) role an app operator
usually holds.

| Principle | Kit evidence | Gap |
|---|---|---|
| 人間中心 (human-centric) | `child.safety`: replies point people to a trusted adult or emergency help | Human oversight in operation |
| 安全性 (safety) | `child.safety`, `child.conversation`; risk register; safety case | Incident response in operation |
| 公平性 (fairness) | Same cases in Japanese, English and Vietnamese | No bias or fairness pack yet |
| プライバシー保護 (privacy) | `no_pii_request`; `agent.unauthorized_action` (cross-user data) | Data retention, consent, APPI duties |
| セキュリティ確保 (security) | Red-team packs with attack success rates; `platform.session_lock` | Infrastructure security, vulnerability handling |
| 透明性 (transparency) | System card; full report with scope and limitations | User-facing AI disclosure |
| アカウンタビリティ (accountability) | Logs per run, decision log, reports dated per configuration | Named owners, sign-off |
| 教育・リテラシー (education and literacy) | – | Organisational |
| 公正競争確保 (fair competition) | – | Organisational |
| イノベーション (innovation) | – | Organisational |

## NIST AI Risk Management Framework 1.0 (AI 100-1) and Generative AI Profile (AI 600-1)

| Function | Kit evidence | Gap |
|---|---|---|
| GOVERN | Decision log, change rule: re-run packs after every model or prompt change | Policies, roles, accountability structures |
| MAP | Target capabilities and audience in `target.yaml`; risk register | Business context, stakeholder impacts |
| MEASURE | Packs and metrics: pass rates, pass^k, attack success rate; judge calibration against human labels (kappa) | Production monitoring, fairness, environmental impact |
| MANAGE | Before/after guardrail measurements; safety case blocks release on unsupported claims | Incident response, decommissioning |

## ISO/IEC 42001:2023, Annex A (38 controls, objectives A.2 to A.10)

| Objective | Kit evidence | Gap |
|---|---|---|
| A.2 Policies related to AI | – | Organisational |
| A.3 Internal organisation | – | Organisational |
| A.4 Resources for AI systems | Target configuration recorded per report (model, adapter, prompt) | Resource inventory |
| A.5 Assessing impacts of AI systems | Risk register, safety case | Societal impact assessment |
| A.6 AI system life cycle | Verification and validation: packs, repeat runs, regression tests, before/after measurements | Requirements, deployment, operation and monitoring records |
| A.7 Data for AI systems | Synthetic, versioned test data (JSONL), human labels | Training-data provenance and quality |
| A.8 Information for interested parties | System card, reports with limitations | User documentation, incident reporting channel |
| A.9 Use of AI systems | Scope and intended use stated in system card and safety case | Usage monitoring |
| A.10 Third-party and customer relationships | Black-box testing of third-party models through adapters | Supplier agreements |
