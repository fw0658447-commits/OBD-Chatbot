# Regulatory Graph Review

Checked: 2026-11-27T15:10:55.523814+00:00

- 21 regulation/standard nodes; 17 relationships; 40 catalog sources
- 5 source-text-marked links; 12 inference/review links
- 0 graph-integrity findings
- 0 directly affected nodes, 0 impacted within two hops
- 0 potential engineering relation cycles (NOT legal contradictions)

## Findings
- None

## Source-change impact
- None observed; requires source monitor snapshots

## Human-review queue
- L005: UN_GTR22 -> EU_2026_1764 (shared_technical_subject) — Battery durability, SOCE; not an asserted incorporation of GTR directly
- L007: CARB_1968_2 -> SAE_J1979_2 (explicit_reference) — 13 CCR 1968.2(d)(9.2.2), subject to applicability
- L008: UN_R155 -> ISO_21434 (related_technical_standard) — CSMS and cybersecurity engineering may be aligned; ISO not automatically required
- L009: UN_R156 -> ISO_24089 (related_technical_standard) — SUMS and software-update engineering may be aligned; ISO not automatically required
- L010: UN_GTR22 -> UN_R156 (shared_system_chain) — BMS algorithm OTA change can affect reported SOCE; impact analysis needed
- L011: EU_2018_858 -> ISO_17978_1 (shared_service_chain) — RMI access vs technical SOVD diagnostics, not legal incorporation
- L012: DE_STVZO_VIIIA -> EU_2018_858 (jurisdictional_intersection) — German PTI/ePTI vs EU type approval/service data; obligations not equivalent
- L013: JAPAN_OBD_KENSA -> DE_STVZO_VIIIA (similar_inspection_topic) — Both inspect vehicles but must never transpose national DTC lists
- L014: CN_GBT46991_1 -> UN_GTR22 (shared_technical_subject) — Battery durability standards; legal status in China independent of UN GTR
- L015: CN_GB18352_6 -> US_86_1806_27 (similar_obd_topic) — OBD demo/calibration traceability; no equivalent regulatory thresholds assumed
- L016: GTR20 -> UN_GTR22 (shared_vehicle_function) — BMS/HV safety vs battery durability; different acceptance criteria
- L017: GTR20 -> ISO_26262 (shared_safety_topic) — Battery safety vs functional safety; no blanket incorporation

**Limitation:** This is a structured, traceable plausibility check; it does not prove substantive legal accuracy. Review exact legal text, amendments, effective dates, national adoption and clauses before certification.
