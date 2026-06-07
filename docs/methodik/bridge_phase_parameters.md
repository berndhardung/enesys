# Bridge-phase parameters — source documentation

**Purpose:** documents the central time-path parameters of the bridge
phase (coal phase-out, gas existing fleet, H2-ready capacity, H₂ fuel
availability) with source, date, source class, and camp range.
Complements `docs/SOURCES.md`.

The bridge phase in the model: 2026 to `BRIDGE_PHASE_BIS_JAHR = 2046`
(see `core/path_sensitivity.py`). The bridge phase ends in the
`neutral_default` camp at nuclear EPR IBN 2046; in the other camps
the de-facto bridge shifts accordingly (atom_opt to 2036, ee_opt to
2050).

---

## Parameter 1 — Coal existing fleet 2026

**Code:** `TimePathParams.kohle_bestand_capacity(year=2026)` = 33.0 GW

| Aspect | Value |
|---|---|
| **Default value** | 33 GW (16 hard coal + 17 lignite) |
| **Source** | BNetzA Monitoring 2024, tag `BNETZA-MONITORING-2024` |
| **URL** | https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Versorgungssicherheit/Erzeugungskapazitaeten/Kraftwerksliste/start.html |
| **Class** | **A** (official authority) |
| **Verification** | "around 56.5 GW of conventional plants remain" incl. natural gas; of which ~33 GW hard + brown coal |

**Camp spread:** none. The value is a legal stocktake.

---

## Parameter 2 — WEITER-SO coal exit year

**Code:** `weiterso_kohle_ausstieg_endjahr` (implicit in C.1 via knot points)

| Aspect | Value |
|---|---|
| **Default value** | 2038 |
| **Source (legal)** | Kohleverstromungsbeendigungsgesetz (KVBG) §4, BGBl. I 2020 p. 1818, tag `KVBG-2020` |
| **URL** | https://www.gesetze-im-internet.de/kvbg/ |
| **Class** | **A** (federal law) |
| **Verbatim evidence** | KVBG §4: "fully dismantled at the latest by 2038-12-31" |
| **Intermediate targets** | 30 GW (2022), 17 GW (2030: 8 hard + 9 lignite), 0 GW (2038) |

**Camp range:**

| Camp | Value | Rationale | Source |
|---|---|---|---|
| **EE-optimistic** | 2035 | KVBG §54 envisages review checkpoints 2026/2029/2032 — "to end as early as 2035 if possible" (federal-state agreement January 2020) | Wikipedia: coal-phase-out entry, note on Kohlekommission recommendation 2019 |
| **Neutral** | 2038 | KVBG end year | KVBG §4 |
| **Status-quo-pessimistic** | 2042+ | A softening is possible if the security-of-supply clause KVBG §54 takes effect; Datteln 4 came online in 2020 and is only set to close in 2038 → precedent for hardship-case extensions | energiezukunft.eu on the roadmap, Ersatzkraftwerkebereithaltungsgesetz 2022 as precedent for reactivations |

**Methodological friction point:** the value 2042 is *not* covered by
law — it would be a softening. Methodologically the cleanest framing
would be to label this in the model as a "sensitivity: KVBG softening"
rather than as an atom-camp position. The atom camp has no independent
position on coal (wants nuclear instead of coal anyway).

---

## Parameter 3 — Path coal exit year (all four non-WEITER-SO paths)

**Code:** `TimePathParams.kohle_bestand_capacity(year, weiterso=False)`
with knot points `{2026: 33, 2030: 0}`

| Aspect | Value |
|---|---|
| **Default value** | 2030 (linear phase-out 2026→2030) |
| **Source 1 (political)** | Coalition agreement SPD/Grüne/FDP 2021, point "climate, energy, transformation": "bring forward coal phase-out ideally to 2030" |
| **Source 2 (contractual)** | Agreement BMWK + NRW + RWE October 2022, brought-forward coal phase-out 2030 in Rhenish lignite region; by law 2022-12-01 (Bundestag printed paper 20/4300) |
| **URL** | https://www.bundestag.de/dokumente/textarchiv/2022/kw48-de-braunkohleausstieg-923096 |
| **Class** | **A** (federal law for Rhenish region) + **B** (political intent for other regions) |

**Decommissioning lead time:**
- **Minimum 30 months lead time** for an ordinance-based shutdown
  (BNetzA), plus a 12-month waiting period after the shutdown notice
- **Empirics**: since 2011, 41.73 GW of conventional capacity have
  been shut down — about 3 GW/year on average. The linear phase-out
  33→0 GW over 4 years = 8 GW/year is therefore **faster than the
  historical rate**, but not unrealistic (in crisis years like 2024,
  4.4 GW were shut down in one step).

**Camp range:**

| Camp | Value | Rationale |
|---|---|---|
| **EE-optimistic** | 2030 | Coalition agreement 2021, RWE contract 2022 |
| **Neutral** | 2032 | Realistic delay relative to the 2030 target |
| **Status-quo-pessimistic** | 2034 | Open-pit recultivation and personnel issues delay |

**Methodological friction point:** do we need the path value separate
from WEITER-SO? Yes: WEITER-SO is a definitionally passive path
(status-quo camp); the other four are active paths. EE/KKW paths *want*
coal gone — the atom camp just like the EE camp. Hence a shared value
for all four non-WEITER-SO paths.

---

## Parameter 4 — Natural-gas existing fleet 2026 and decommissioning path

**Code:** `TimePathParams.gas_bestand_capacity(year)` with knot points
`{2026: 31, 2030: 30, 2035: 28, 2040: 25, 2045: 22, 2050: 18}`

| Aspect | Value |
|---|---|
| **2026: 31 GW** | BNetzA Monitoring 2024, tag `BNETZA-MONITORING-2024` |
| **Class** | **A** (Federal Network Agency) |
| **Verification** | From 56.5 GW total conventional minus 33 GW coal = ~23.5 GW gas in the existing fleet. Plus reserve plants from Ersatzkraftwerkebereithaltungsgesetz 2022 (~7 GW reactivated) → 30-31 GW consistent |

**Decommissioning trajectory 2050: 18 GW**

Rationale for the linear phase-out assumption: the fleet is reduced
successively by age-related decommissioning. Mean service life of gas
plants ~30-40 years; the fleet is largely vintage 1990-2010. By 2050
the oldest plants are >50 years old and must be replaced. The phase-out
curve follows the empirical decommissioning logic of the BNetzA plant
list.

**Methodological friction point:** these numbers are **not from a
single source** but a plausible model assumption. They are flagged as
`[ASSUMPTION: model choice, derived from fleet age and mean service
life]`, not as a hard sourced figure. Class-B sources such as ISE
power-plant analyses or DLR system studies would qualitatively support
the linear phase-out; a study with exactly this 31→18 GW path is not
known.

**Camp range:** none — the existing fleet is a politically
uncontroversial quantity.

---

## Parameter 5 — H2-ready CCGT new-build

**Code:** `TimePathParams.h2ready_capacity(year)` with knot points
`{2026: 0, 2030: 6, 2035: 12, 2040: 16, 2045: 20, 2050: 22}`

| Aspect | Value |
|---|---|
| **2034: 12 GW** | Kraftwerksstrategie 2026, BMWE Eckpunktepapier January 2026, tag `BMWE-KWBG-2026` |
| **Class** | **A** (federal government) |
| **Verbatim evidence** | Kraftwerksstrategie 2026: 24 modern CCGT plants at 500 MW each, first IBN 2030, last 2034 |

**2030: 6 GW (realism discount)**

Rationale: from the plan of 12 GW over four years 2030-2034 a linear
ramp would mean 3 GW/year, i.e. 3 GW (2031), 6 GW (2032)… The 6 GW in
2030 is an **optimistic reading** — it assumes that the first 12
tender lots completed quickly. Realistically, 2030 could see only
3-4 GW.

**Camp range:**

| Camp | 2030 | 2035 | Rationale |
|---|---|---|---|
| **EE-optimistic** | 8 GW | 14 GW | KWBG fully and on-schedule |
| **Neutral** | 6 GW | 12 GW | plan value with moderate discount |
| **Sceptical** | 3 GW | 8 GW | permitting delays, supply chain, skills shortage |

**Methodological friction point:** the KWBG cornerstones are a
political intent statement, not the state of the law. Tenders are
only now starting. Delays are realistically likely.

---

## Parameter 6 — H2 fuel availability

**Code:** `TimePathParams.h2_brennstoff_capacity(year)` with knot
points `{2026: 0.5, 2030: 3, 2035: 10, 2040: 20, 2045: 30, 2050: 40}`

| Aspect | Value |
|---|---|
| **2030: 3 GW backup-capable** | Nationale Wasserstoff-Strategie Update 2023, tag `NWS-2023` |
| **Class** | **B** (research institutes with federal mandate) — BMWK is class A, but the NWS is a strategy paper, not law |
| **Verbatim evidence NWS-2023** | "Electrolysis 5 GW by 2030, 10 GW by 2035" |

**Calculation logic 2030: 3 GW from 5 GW electrolysis**

Per 1 GW H2 plant operated at full load for 240 h (10 days) at
55-58 % efficiency: ~0.4 TWh H2 reserve. 5 GW electrolysis produce
~30 TWh H2 per year — of which industry competition (steel, chemicals,
mobility consume preferentially). Backup-capable share ~60 % of total
→ 18 TWh / year → enough for ~3 GW backup capacity over 240 h.

**Camp range:**

| Camp | 2030 | 2035 | 2045 | Rationale |
|---|---|---|---|---|
| **EE-optimistic** | 5 GW | 15 GW | 40 GW | NWS-2023 plan ambitious, imports quick |
| **Neutral** | 3 GW | 10 GW | 30 GW | NWS minus industry competition |
| **Atom-/status-quo-sceptical** | 1 GW | 5 GW | 15 GW | Imports delayed, caverns absent, industry takes everything |

**Source for the scepticism (atom camp):** "We're betting on a
hydrogen monoculture instead of a technology mix" — Tech for Future,
pro-CCS position; heise.de on the SMC survey 2023 with Ruprecht/Thess
scepticism. Class **D** (camp-adjacent voices), but argumentatively
consistent.

---

## Parameter 7 — H2 fuel split EE-H2 / KKW-H2

**Code:** `H2_FUEL_SHARE = {"EE-H2": 0.5, "KKW-H2": 0.5}`

| Aspect | Value |
|---|---|
| **Default** | 0.5 / 0.5 (half-half split) |
| **Class** | methodological model choice (`[ASSUMPTION]` tag) |

**Rationale:** both paths share an identical bridge architecture and
an identical H2 demand in the bridge phase. Through 2042 the values
are identical (both compute 0.65 EE + 0.35 backup); afterwards KKW-H2
structurally needs less H2 because nuclear takes over part of the
backup load. The half-half setting is exact through 2042 and
afterwards slightly biased toward KKW-H2 visibility — neutral, and
irrelevant in range terms across the 30-year balance.

---

## Source-class overview

| Parameter | Class | Source tag in [`SOURCES.md`](../SOURCES.md) |
|---|---|---|
| Coal existing fleet 2026 | A (statutory/regulatory) | `KVBG-2020`, `BNETZA-MONITORING-2024` |
| WEITER-SO exit | A (statutory) | `KVBG-2020`, `RWE-VERTRAG-2022` |
| Path exit | A+B (path logic) | `BMWE-KWBG-2026` |
| Gas-fleet trajectory | B (`[ASSUMPTION]`) | fleet age and service life; modeled conservatively-linearly |
| H2-ready KWBG | A (statutory) | `BMWE-KWBG-2026` |
| H2 fuel availability | B (`[ASSUMPTION]`) | `NWS-2023`, `H2-IMPORT-2024`, `WASSERSTOFF-KERNNETZ-2024` |
| H2 split 50/50 | `[ASSUMPTION]` (methodological) | half-half neutral setting in the bridge phase |

Three parameters (gas phase-out curve, H2 availability, 50/50 H2
split) are methodological model choices and carry the `[ASSUMPTION]`
tag — they rest on consistent bridge logic, not a specific
peer-reviewed study — the choices are surfaced openly here so they
remain traceable.
