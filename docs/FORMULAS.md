# Model formulas — full transparency

All formulas in enesys, in the order they are applied.
Each formula with rationale, worked example and a pointer to its source.

> **Note on worked examples:** The numbers in the `Worked example` blocks
> are illustrative and correspond to the model state **May 2026**. When
> parameters are updated (e.g. new source releases, BNEF refresh) the
> formulas remain valid; the concrete numbers may shift slightly. The
> code in `enesys` is the canonical truth — the examples are there to
> let you replay the mechanics.

## Reading convention

- **Variables** in `code-format`
- **Units** carried through every step
- **Example** with concrete values at the end of each section
- **Code reference** to the top-level function in `enesys`
  (`compute_path`, `baseline_all_paths`, `monte_carlo_all_paths` …)

---

## 1. Demand layer

### 1.1 Electricity demand from mobility

**Formula:**

```
TWh_mobility = (cars_stock · annual_km / 100
                · consumption_kWh_per_100km · ev_share
                · (1 + charging_loss)) / 10⁹
              + commercial_extra · commercial_ev_share
```

**Rationale:** Per car: km/year × kWh/100km = kWh/year. Times the number
of cars and the EV share gives the energy total. A 10 % charging loss
covers AC/DC conversion and standby losses.

**Worked example (default 2045):**
- Car stock: 49 million
- Mileage: 13,500 km/yr
- Consumption: 18 kWh/100 km
- EV share: 80 %
- Charging loss: 10 %

```
kWh per car per year = 13,500 km × 18 kWh/100 km = 2,430 kWh/car
Car electricity = 49 M × 2,430 kWh × 0.80 × 1.10
                = 49,000,000 × 2,430 × 0.88
                = 104.8 billion kWh
                = 104.8 TWh
+ Commercial vehicles: 25 TWh × 60 % = 15 TWh
TOTAL: 119.8 TWh ≈ 120 TWh
```

**Code:** `MobilityParams.electricity_consumption_twh()`

### 1.2 Efficiency factor: EV vs combustion engine

**Formula:**

```
efficiency_factor_mob = (ice_l_per_100km · gasoline_kWh_per_l) / ev_kWh_per_100km
```

**Rationale:** Both vehicles drive the same distance. The factor shows
how much more final energy the combustion engine needs.

**Worked example:**

```
ICE final energy = 7 L/100km × 9.7 kWh/L = 67.9 kWh/100km
EV final energy  = 18 kWh/100km
Factor = 67.9 / 18 = 3.77x
```

**Physical validation:**
- Combustion engine: 25-30 % thermal efficiency (Otto cycle)
- Electric drive: 85-90 % efficiency (battery to wheel)
- Theoretical factor: 0.87 / 0.28 ≈ 3.1
- Practical factor 3.77 is plausible (EV better torque profile)

**Code:** `MobilityParams.efficiency_factor()`

### 1.3 Electricity demand from heating

**Formula:**

```
TWh_heat = (heating_stock · heat_demand_kWh
            · (1 - district_heating_share) · heatpump_share
            / COP_annual) / 10⁹
          + direct_electric_share
```

**Rationale:** A heat pump needs `power_input = heat_output / COP`. A
COP of 3.2 means 1 kWh of electricity yields 3.2 kWh of heat. District
heating is outside the electricity market.

**Worked example:**

```
Heat-pump electricity = 21.5 M × 18,000 kWh × (1-0.15) × 0.60 / 3.2 / 10⁹
                      = 21,500,000 × 18,000 × 0.85 × 0.60 / 3.2 / 10⁹
                      = 197,370,000,000 / 3.2 / 10⁹
                      = 61.7 TWh
+ Direct electric:   21.5 M × 18,000 × 0.85 × (1-0.60) × 0.05 / 10⁹
                   = 6.5 TWh
TOTAL: 68.2 TWh ≈ 68 TWh ✓
```

**Code:** `HeatingParams.electricity_consumption_twh()`

### 1.4 Efficiency factor: heat pump vs gas boiler

**Formula:**

```
efficiency_factor_heat = COP_annual · gas_boiler_efficiency
```

**Worked example:**

```
Factor = 3.2 × 0.95 = 3.04x
```

**Code:** `HeatingParams.efficiency_factor()`

### 1.5 Aggregate electricity demand

**Formula:**

```
TWh_total = base_load_household+commercial + TWh_mobility + TWh_heat + TWh_industry
```

**Worked example (default 2045):**

```
220 (base) + 120 (mobility) + 68 (heat) + 340 (industry) = 748 TWh
```

Comparison with studies:
- Agora 2045: 750-900 TWh
- BMWK scenario: 1,000-1,300 TWh (with more industrial H₂)
- Default model: 748 TWh ✓ in the middle

**Code:** `Demand.total_twh()`

---

## 2. Generation layer

### 2.1 Forward LCOE — annuity method

**Formula:**

```
LCOE = (annuity_factor · CAPEX + OPEX_annual) / VLH_annual
       + fuel_cost / efficiency
```

with

```
annuity_factor = WACC / (1 - (1 + WACC)^(-lifetime))
```

**Rationale:** Forward LCOE expresses future capital costs as an annual
rate (annuity) and divides by annual electricity output. The result is
EUR per kWh. **Sunk costs (past investments) do NOT enter.**

**Worked example PV:**

```
CAPEX: 700 €/kW
OPEX: 12 €/kW/yr
WACC: 5 %
Lifetime: 30 years
VLH: 1,050 h/yr

annuity_factor = 0.05 / (1 - 1.05^(-30))
               = 0.05 / (1 - 0.2314)
               = 0.05 / 0.7686
               = 0.0651 (6.51 % p.a.)

Fixed annual cost = 0.0651 × 700 + 12
                  = 45.55 + 12
                  = 57.55 €/kW/yr

LCOE = 57.55 / 1,050 = 0.0548 €/kWh = 5.48 ct/kWh
```

Comparison with the ISE study: range 4.1-6.9 ct → 5.48 sits in the
realistic interval.

**Worked example nuclear:**

```
CAPEX: 11,000 €/kW
OPEX: 130 €/kW/yr
WACC: 8.5 %
Lifetime: 60 years
VLH: 6,500 h/yr

annuity_factor = 0.085 / (1 - 1.085^(-60))
               = 0.085 / (1 - 0.00752)
               = 0.085 / 0.9925
               = 0.0856 (8.56 % p.a.)

Fixed annual cost = 0.0856 × 11,000 + 130
                  = 941.3 + 130
                  = 1,071 €/kW/yr

LCOE = 1,071 / 6,500 = 0.1648 €/kWh = 16.48 ct/kWh
```

**Code:** `lcoe_forward()` and `annuity_factor()` in `path_inputs.py`

### 2.2 Effective nuclear LCOE at reduced full-load hours

**Formula:**

```
LCOE_nuclear_effective = LCOE_nuclear_design · (VLH_design / VLH_real)
```

**Rationale:** Nuclear is CAPEX-dominated. Halving VLH roughly doubles
LCOE because fixed costs scale per kWh.

**Worked example:**

```
Design LCOE at 7,500 VLH: 14 ct/kWh
Effective at 5,500 VLH: 14 × (7,500 / 5,500) = 19.1 ct/kWh
Effective at 3,000 VLH: 14 × (7,500 / 3,000) = 35 ct/kWh
```

This is the methodological bridge to the ISE study, which assumes
2,000-4,000 VLH for 2045. It is exactly this model that shows how the
ISE arrives at its high LCOE numbers.

**Code:** The VLH scaling is part of the central LCOE pipeline in
`compute_path()`; the VLH ranges live in `CAMP_RANGES` (parameter
`nuclear_full_load_hours`).

---

## 3. Model path computation

### 3.1 EE-H2 — RE + storage + H₂ backup

**Generation-mix LCOE:**

```
LCOE_EE-H2_gen = 0.40 · pv_LCOE
               + 0.30 · wind_onshore_LCOE
               + 0.15 · wind_offshore_LCOE
               + 0.04 · biomass_LCOE
               + 0.03 · hydro_LCOE
               + 0.08 · h2_backup_LCOE
```

**Rationale:** The shares sum to 1.0 and reflect a 100 %-renewable
system with H₂ backup for dark-doldrum periods. The high PV/wind shares
are realistic.

**Storage share:**

```
storage_EE-H2 = 0.12 · battery_LCOS
```

12 % of consumption routed through batteries — reflecting the high
volatility of an RE system.

**End-price formula:**

```
end_price_EE-H2 = LCOE_EE-H2_gen + storage_EE-H2 + grid + CO₂ + taxes
                + stability_surcharge (RE)
                - flex_discount (RE)
```

**Worked example with default values:**

```
LCOE_EE-H2_gen = 0.40 × 6.0 + 0.30 × 6.5 + 0.15 × 9.0
               + 0.04 × 14.0 + 0.03 × 6.0 + 0.08 × 32.0
               = 2.40 + 1.95 + 1.35 + 0.56 + 0.18 + 2.56
               = 9.00 ct/kWh

Storage    = 0.12 × 7.0 = 0.84 ct/kWh
Grid       = 7.0 ct/kWh
CO₂        = 130 €/t × 30 g/kWh / 10,000 = 0.39 ct/kWh
Taxes      = 5.0 ct/kWh
Stability  = 0.11 ct/kWh (RE surcharge)
Flex disc. = 0.08 ct/kWh (RE)

End price EE-H2 = 9.00 + 0.84 + 7.0 + 0.36 + 5.0 + 0.11 - 0.08
                = 22.23 ct/kWh
```

Note: The Forward-Cost variant (without taxes) sits at
0.40 × 6.0 + … + 0.08 × 32.0 + storage + grid + CO₂ + stability − flex_discount
= 17.23 ct/kWh in this single-year example. Over the 30-year mean the
model yields 17.26 ct/kWh for EE-H2 (`neutral_default` camp) — the
difference comes from learning curves (PV LCOE drops from 6.0 to 4.0 ct,
H₂ LCOE from 45 to 20 ct by 2050) and from the demand-weighted average.

**Code:** `compute_path()` in `path_model.py`

### 3.2 KKW-GAS — RE + nuclear + bridge gas

**Generation mix with time-dependent nuclear availability:**

```
if year ≥ nuclear_first_IBN (camp-dependent — see below):
    LCOE_KKW-GAS_gen = 0.25 · pv + 0.18 · won + 0.10 · woff
                     + 0.03 · bio + 0.03 · hydro
                     + nuclear_share · (KKW_LCOE_eff + repository + decommissioning)
                     + bridge_gas_share · gas_LCOE_fossil
                     + 0.06 · h2_backup_LCOE
else:
    LCOE_KKW-GAS_gen = 0.25 · pv + 0.18 · won + 0.10 · woff
                     + 0.03 · bio + 0.03 · hydro
                     + 0.35 · gas_LCOE_fossil   (bridge gas instead of nuclear)
                     + 0.06 · h2_backup_LCOE
```

**Nuclear IBN per camp** (derived from `KKW_EPR_APPROVAL_YEAR=2029`
plus sqrt-stretching with T_cap 21 yr in
`core/inventories/tech_inventory.py`):

| Camp                | IBN-EPR | T_build |
|---|---:|---:|
| atom_optimistic    | 2036    | 7 yr (plan) |
| neutral_default    | 2046    | 17.5 yr |
| bestand_optimistic | 2046    | 17.5 yr |
| ee_optimistic      | 2050    | 21 yr (cap) |

**Key logic:** Until camp IBN, KKW-GAS runs on gas backup instead of
nuclear. Only afterwards does nuclear take over step by step — and the
bridge-gas share recedes. This is the model's central bridge-phase
mechanic.

**Code:** `compute_path()` in `path_model.py`

### 3.3 KKW-H2 — RE + nuclear + H₂ backup

Identical to KKW-GAS, but with `h2_backup_LCOE` instead of
`gas_LCOE_fossil` for peak coverage. The bridge-gas phase remains in
place before camp IBN (technical reality: H₂ is only available at
industrial scale from 2030+).

**Code:** `compute_path()` in `path_model.py`

### 3.4 EE-GAS — RE + storage + fossil gas backup

EE-GAS is the path with renewable base generation and a fossil
natural-gas backup. The model treats »gas« throughout as fossil natural
gas with a CO₂ penalty — symmetric to KKW-GAS and WEITER-SO. Anyone
who wants to assume a gradual admixture of bio-methane or synthetic
methane can adjust the backup LCOE themselves.

**EE-GAS generation mix:**

```
LCOE_EE-GAS_gen = 0.43 · pv + 0.32 · won + 0.15 · woff
                + 0.04 · bio + 0.03 · hydro
                + 0.08 · gas_LCOE_fossil
```

**Backup LCOE (fossil natural gas, PURE generation cost):**

```
gas_LCOE_fossil = 6.8 ct/kWh
```

This value is the pure generation cost of CCGT plants at current fuel
prices — WITHOUT a CO₂ penalty. The penalty is applied globally via
`co2_pricing_ct_kwh()` with the path-specific CO₂ intensity and the
current world CO₂ price assumption (neutral 130 €/t, camp-specific
100-160). The ISE 2024 standard assumption »CCGT incl. CO₂« of
11.2 ct/kWh decomposes as: 6.8 ct generation + 4.55 ct CO₂ penalty
(350 g/kWh × 130 €/t / 10,000).

**Code:** `compute_path()` in `path_model.py`

### 3.5 WEITER-SO — status quo, coal until phase-out

**Generation mix with time-dependent coal phase-out and rising gas:**

```
coal_share(year) = max(0, coal_initial · (1 − (year − 2026)/(phaseout − 2026)))
gas_share(year)  = gas_initial · (1 + gas_growth)^(year − 2026)

LCOE_WEITER-SO_gen = re_share · LCOE_RE-mix
                   + coal_share(year) · coal_LCOE
                   + gas_share(year)  · gas_LCOE_fossil
```

WEITER-SO models political inaction: dampened RE expansion (60 % of the
active paths), coal until 2038, gas growing in step with the CO₂ price.

**Code:** `compute_path()` in `path_model.py`

---

## 4. CO₂ accounting

### 4.1 CO₂ intensity per path

**WEITER-SO:** dominant contribution from coal and natural gas.
```
CO₂_intensity_WEITER-SO = coal_share · 850 + gas_share · 350
                        + re_share   · 25
```
With defaults for 2030 (coal 16 %, gas rising): about 250 g/kWh.

**EE-H2:** ~30 g/kWh, constant (lifecycle CO₂ from the PV/wind mix
plus residual biomass; the H₂ backup is CO₂-free).

**KKW-GAS:**
```
CO₂_intensity_KKW-GAS = 25 + bridge_gas_share · 350
```
Full bridge phase (2030): 25 + 0.35 × 350 = 147 g/kWh.
Full nuclear availability (2050): 25 g/kWh.

**KKW-H2:** ~25 g/kWh, constant (lifecycle CO₂ from the mix
generation; the H₂ backup is CO₂-free in the bridge phase and beyond).
The small difference vs EE-H2 (5 g/kWh) comes from the lower lifecycle
CO₂ share of nuclear (IPCC AR6: ~12 g/kWh) compared to PV (25-50 g/kWh)
and biomass (30-300 g/kWh). This difference lies within the model
uncertainty; it is not a core argument.

**EE-GAS:**
```
CO₂_intensity_EE-GAS = ee_gas_backup_share · 350
                     + (1 − ee_gas_backup_share) · 20
```
With an 8 % backup share: 0.08 × 350 + 0.92 × 20 = 46 g/kWh, constant
along the path curve (no green admixture in the default model).

### 4.2 Total CO₂ per year

```
CO₂_per_year = CO₂_intensity · demand_TWh / 1,000
              + non_electrified_sectors_Mt · (1 − scaling)
```

**Rationale:** Electricity CO₂ scales with consumption and intensity.
Non-electrified sectors (transport, heating) emit 250 Mt today and
decline linearly with electrification scaling.

### 4.3 Cumulative CO₂ — system boundary (electricity + external)

Methodological choice: the honest path comparison aggregates **the
electricity sector + external sector coupling**. The active paths
(EE-GAS, EE-H2, KKW-GAS, KKW-H2) pull heating and mobility into the
electricity sector and carry their CO₂ load through the electricity
mix; WEITER-SO and BESTAND leave heating and mobility running on fossil
fuels externally — those emissions do not appear in `r.co2_mt` but in
`r.co2_external_mt_per_year`. Only the sum of both allows a fair climate
comparison.

```
CO₂_cumulative_total = Σ (r.co2_mt + r.co2_external_mt_per_year) over all years
```

**Cumulative CO₂ 2026-2055 (30 years, `neutral_default` camp, system boundary):**

| Path | Electricity | External | Total | vs BESTAND |
|---|---|---|---|---|
| EE-H2 | 1,677 | 1,012 | **2,689 Mt** | −2,181 Mt (−45 %) |
| EE-GAS | 1,926 | 1,012 | **2,937 Mt** | −1,933 Mt (−40 %) |
| KKW-H2 | 2,011 | 1,012 | **3,022 Mt** | −1,848 Mt |
| KKW-GAS | 2,300 | 1,012 | **3,312 Mt** | −1,558 Mt |
| WEITER-SO | 1,966 | 2,466 | **4,432 Mt** | −438 Mt (status quo without a decision) |
| BESTAND | 2,292 | 2,578 | **4,870 Mt** | baseline |

The comparison anchor is BESTAND because BESTAND is the politically
seriously-defended status-quo path; WEITER-SO is the status-quo
extrapolation without a decision — what happens if nothing is chosen
— and not a program.

KKW-GAS − EE-GAS difference (electricity sector): +374 Mt to the
disadvantage of KKW-GAS, of which ~265 Mt arise in the bridge phase
2026–2046 (bridge share ~71 %). See
`BRIDGE_MEHREMISSIONEN_KKW_VS_EE_MT` and
`TOTAL_MEHREMISSIONEN_KKW_VS_EE_MT` in `core/path_sensitivity.py`. The
bridge phase structurally carries most of the KKW CO₂ asymmetry: nuclear
IBN sits at 2046 in the `neutral_default` camp, and until then fossil
gas supplies the KKW path.

**Steady state 2055-2085 (30 years of maturity, system boundary):**
In the maturity phase the sector coupling in the EE/KKW paths is
complete → external CO₂ ≈ 0; in WEITER-SO/BESTAND heating and mobility
stay fossil. The path spread opens up: EE-H2 1,076 / KKW-H2 1,089 /
KKW-GAS 1,146 / EE-GAS 1,393 vs WEITER-SO 3,211 / BESTAND 3,788 Mt.
**EE-GAS saves 2,395 Mt (63 %) vs BESTAND** in steady state — against
the serious political counter-path the climate story opens up with
time, it does not weaken. Methodological caveat: the steady-state table
holds sector-coupling depth constant at the 2055 level; any further
sector-coupling deepening post-2055 widens the gap further, because the
active paths absorb additional demand carbon-free, while BESTAND/
WEITER-SO keep carrying fossil sectors.

**Code:** Aggregation in `co2_lockin_metric()` in `path_model.py`;
returns `kumuliert_total_mt` (electricity + external),
`kumuliert_strom_mt` (electricity sector only, old-API counterpart),
`kumuliert_extern_mt`, `kumuliert_lockin_mt` (total from
`lockin_threshold_year` onward).

---

## 5. Sensitivity analyses

### 5.1 Tornado chart

**Formula per parameter:**

```
swing_p = |LCOE_total(p · 1.25) - LCOE_total(p · 0.75)|
```

**Sort descending by swing.** Largest swing = most important parameter.

**Code:** `tornado_path_analysis()` in `path_sensitivity.py`

### 5.2 Monte-Carlo simulation

**Distributions:**

| Parameter | Distribution | Parameters |
|---|---|---|
| pv_lcoe | Normal | μ=6.0, σ=1.0, clip [3, 12] |
| wind_onshore | Normal | μ=6.5, σ=1.0, clip [4, 11] |
| wind_offshore | Normal | μ=9.0, σ=1.5, clip [7, 13] |
| battery_lcos | Lognormal | log(μ)=log(7), σ=0.30, clip [3, 18] |
| nuclear_lcoe | Lognormal | log(μ)=log(14), σ=0.25, clip [7, 25] |
| nuclear_vlh | Normal | μ=6500, σ=800, clip [3500, 8000] |
| h2_lcoe | Normal | μ=32, σ=6, clip [20, 55] |
| co2_price | Normal | μ=120, σ=30, clip [50, 200] |
| grid_surcharge | Normal | μ=7, σ=1.5, clip [4, 12] |

**Rationale for Lognormal on nuclear and batteries:** Real-world cost
overruns are asymmetric (very high values are possible, very low ones
are not), hence Lognormal instead of Normal.

**Output metrics:**

```
P(EE-H2 < KKW-GAS) = share of runs in which EE-H2 is cheaper than KKW-GAS
P(EE-GAS < KKW-GAS) = share of runs in which EE-GAS is cheaper than KKW-GAS
```

Analogous for every pair-comparison of the six paths. The pair
probabilities show how robust the path ordering is against parameter
uncertainty; a violin plot per path can be rendered from
`monte_carlo_all_paths()` via `viz/charts/montecarlo.py`.

**Code:** `monte_carlo_all_paths()` — top-level import via `from enesys import monte_carlo_all_paths`.

---

## 6. Winter stress test

### 6.1 Peak load during a cold dark-doldrum period

**Formula:**

```
peak_GW = base_avg · 1.3 · winter_factor
        + heating_avg · heat_factor · (COP_year / COP_winter)
        + mobility_avg · 1.4 · (1 + ev_winter_surcharge)
        + industry_avg · 1.0
```

**Rationale for the factors:**

- Base × 1.3: winter evening peak over the annual mean (lighting, appliances)
- Heating factor 1.8: cold day = 80 % more heating output than average
- COP degradation: 3.2 / 2.2 = 1.45 more electricity per kWh of heat
- Mobility × 1.4: 60 % charge during the peak hour × 25 % winter surcharge

**Worked example 2045 default:**

```
base_avg = 220 / 8760 × 1000 = 25.1 GW × 1.3 × 1.1 = 35.9 GW
heating_avg = 68 / 8760 × 1000 = 7.8 GW × 1.8 × 1.45 = 20.3 GW
mobility_avg = 120 / 8760 × 1000 = 13.7 GW × 1.4 × 1.25 = 24.0 GW
industry = 340 / 8760 × 1000 = 38.8 GW

Peak = 35.9 + 20.3 + 24.0 + 38.8 = 119.0 GW
```

Validation against ÜNB scenarios for 2045: 110-160 GW. Model output 119
GW sits in the lower range → with default values, this is a conservative
assumption (80 % EV, 60 % heat pump). At full electrification the peak
would push toward 145 GW.

**Code:** `WinterStressParams.winter_demand_gw()` in `extensions/winter_stress.py`

### 6.2 RE generation during a dark-doldrum period

```
RE_supply_GW = PV_capacity · 0.03 + wind_onshore · 0.10
             + wind_offshore · 0.15 + 8 (firm: bio + hydro)
```

3 % PV, 10 % wind onshore, 15 % wind offshore (offshore is better
during dark-doldrum periods because of different weather systems).

### 6.3 Deficit calculation

```
residual_GW = peak_GW - RE_supply_GW
backup_total = Σ backup sources
deficit = max(0, residual_GW - backup_total)
```

If `deficit > 0`: supply gap, prices explode or load-shedding is needed.

**Code:** `winter_stress_test()` in `extensions/winter_stress.py`

---

## 7. Assumptions not in the model

What sits outside the model:

1. **Geopolitical risks** — solar-panel import dependency on China,
   natural-gas import routes, uranium supply.
2. **Non-deployed technologies** — sodium-ion batteries, solid-state
   batteries (no commercial deployment status). SMRs are explicitly
   parameterized in the model with `KKW_SMR_APPROVAL_YEAR = 2029` and
   IBN 2034–2046.
3. **Behavior** — sufficiency, consumption reduction, building retrofits.
4. **Political stability** — government changes, EU policy shifts.
5. **Stranded assets** — what happens to existing gas plants if they
   are retired earlier than planned.

Some of these factors are not modelable, others only qualitatively
treatable. A sober discussion should name them without
pseudo-quantifying them.
