# Model formulas — full transparency

Alle Formeln von enesys, in der Reihenfolge ihrer Anwendung.
Jede Formel mit Begründung, Beispielrechnung und Hinweis auf Quelle.

> **Hinweis zu den Beispielrechnungen:** Die Zahlenwerte in den
> `Beispielrechnung`-Blöcken sind illustrativ und entsprechen dem
> Modellstand **Mai 2026**. Bei Parameter-Updates (z. B. neue
> Quellen-Releases, BNEF-Refresh) bleiben die Formeln gültig, die
> konkreten Zahlen können sich aber leicht verschieben. Der Code in
> `enesys` ist die kanonische Wahrheit, die Beispiele dienen dem
> Nachvollzug der Mechanik.

## Lese-Konvention

- **Variablen** in `code-format`
- **Einheiten** in jedem Schritt mitgeführt
- **Beispiel** mit konkreten Werten am Ende jedes Abschnitts
- **Code-Referenz** auf die Top-Level-Funktion in `enesys`
  (`compute_path`, `baseline_all_paths`, `monte_carlo_all_paths` …)

---

## 1. Nachfrage-Schicht

### 1.1 Strombedarf Mobilität

**Formel:**

```
TWh_mobility = (PKW_Bestand · Jahresfahrleistung_km / 100
                · Verbrauch_kWh_100km · E-Anteil
                · (1 + Ladeverlust)) / 10⁹
              + Nutzfahrzeuge_Zusatz · Nutzfahrzeuge_E-Anteil
```

**Begründung:** Pro PKW: km/Jahr × kWh/100km = kWh/Jahr. Mit Anzahl PKW
und E-Anteil ergibt sich Energiemenge. Ladeverlust 10% deckt AC/DC-Konversion
und Standverluste ab.

**Beispielrechnung (Default 2045):**
- PKW-Bestand: 49 Mio.
- Fahrleistung: 13.500 km/a
- Verbrauch: 18 kWh/100 km
- E-Anteil: 80%
- Ladeverlust: 10%

```
kWh pro PKW pro Jahr = 13.500 km × 18 kWh/100 km = 2.430 kWh/PKW
PKW-Strom = 49 Mio × 2.430 kWh × 0,80 × 1,10
          = 49.000.000 × 2.430 × 0,88
          = 104,8 Mrd. kWh
          = 104,8 TWh
+ Nutzfahrzeuge: 25 TWh × 60 % = 15 TWh
TOTAL: 119,8 TWh ≈ 120 TWh
```

**Code:** `MobilityParams.electricity_consumption_twh()`

### 1.2 Wirkungsgrad-Faktor E-Auto vs. Verbrenner

**Formel:**

```
Wirkungsgrad-Faktor_Mob = (Verbrenner_l_100km · Benzin_kWh_l) / E-Auto_kWh_100km
```

**Begründung:** Beide Fahrzeuge fahren dieselbe Strecke. Der Faktor zeigt,
wieviel mehr Endenergie der Verbrenner braucht.

**Beispielrechnung:**

```
Verbrenner-Endenergie = 7 L/100km × 9,7 kWh/L = 67,9 kWh/100km
E-Auto-Endenergie = 18 kWh/100km
Faktor = 67,9 / 18 = 3,77x
```

**Physikalische Validierung:**
- Verbrennungsmotor: 25-30% thermischer Wirkungsgrad (Otto-Zyklus)
- E-Antrieb: 85-90% Wirkungsgrad (Akku zu Rad)
- Theoretischer Faktor: 0,87 / 0,28 ≈ 3,1
- Praktischer Faktor 3,77 plausibel (E-Auto besseres Drehmoment-Profil)

**Code:** `MobilityParams.efficiency_factor()`

### 1.3 Strombedarf Wärme

**Formel:**

```
TWh_wärme = (Heizungen_Bestand · Heizbedarf_kWh
             · (1 - Fernwärme-Anteil) · WP-Anteil
             / COP_Jahres) / 10⁹
           + Direkt-Strom-Anteil
```

**Begründung:** Wärmepumpe braucht Strom_input = Wärme_output / COP. COP 3,2
heißt: 1 kWh Strom liefert 3,2 kWh Wärme. Fernwärme ist nicht im Strommarkt.

**Beispielrechnung:**

```
WP-Strom = 21,5 Mio × 18.000 kWh × (1-0,15) × 0,60 / 3,2 / 10⁹
         = 21.500.000 × 18.000 × 0,85 × 0,60 / 3,2 / 10⁹
         = 197.370.000.000 / 3,2 / 10⁹
         = 61,7 TWh
+ Direktheizung: 21,5 Mio × 18.000 × 0,85 × (1-0,60) × 0,05 / 10⁹
              = 6,5 TWh
TOTAL: 68,2 TWh ≈ 68 TWh ✓
```

**Code:** `HeatingParams.electricity_consumption_twh()`

### 1.4 Wirkungsgrad-Faktor WP vs. Gasheizung

**Formel:**

```
Wirkungsgrad-Faktor_Wärme = COP_Jahres · Gasheizung_Wirkungsgrad
```

**Beispielrechnung:**

```
Faktor = 3,2 × 0,95 = 3,04x
```

**Code:** `HeatingParams.efficiency_factor()`

### 1.5 Aggregierter Strombedarf

**Formel:**

```
TWh_total = Sockel_HH+Gewerbe + TWh_mobility + TWh_wärme + TWh_industry
```

**Beispielrechnung (Default 2045):**

```
220 (Sockel) + 120 (Mobilität) + 68 (Wärme) + 340 (Industrie) = 748 TWh
```

Vergleich zu Studien:
- Agora 2045: 750-900 TWh
- BMWK-Szenario: 1.000-1.300 TWh (mit mehr Industrie-H₂)
- Default-Modell: 748 TWh ✓ in der Mitte

**Code:** `Demand.total_twh()`

---

## 2. Erzeugungs-Schicht

### 2.1 Forward LCOE — Annuitätenmethode

**Formel:**

```
LCOE = (Annuitätsfaktor · CAPEX + OPEX_jährlich) / VLH_jährlich
       + Brennstoffkosten / Effizienz
```

mit

```
Annuitätsfaktor = WACC / (1 - (1 + WACC)^(-Lebensdauer))
```

**Begründung:** Forward-LCOE rechnet zukünftige Kapitalkosten als Jahresrate
(Annuität) und teilt durch die jährliche Stromproduktion. Ergibt EUR pro kWh.
**Sunk Costs (vergangene Investitionen) gehen NICHT ein.**

**Beispielrechnung PV:**

```
CAPEX: 700 €/kW
OPEX: 12 €/kW/a
WACC: 5%
Lebensdauer: 30 Jahre
VLH: 1.050 h/a

Annuitätsfaktor = 0,05 / (1 - 1,05^(-30))
                = 0,05 / (1 - 0,2314)
                = 0,05 / 0,7686
                = 0,0651 (6,51% p.a.)

Fixe Jahreskosten = 0,0651 × 700 + 12
                  = 45,55 + 12
                  = 57,55 €/kW/a

LCOE = 57,55 / 1.050 = 0,0548 €/kWh = 5,48 ct/kWh
```

Vergleich mit ISE-Studie: Bandbreite 4,1-6,9 ct → 5,48 liegt im realistischen Bereich.

**Beispielrechnung Kernkraft:**

```
CAPEX: 11.000 €/kW
OPEX: 130 €/kW/a
WACC: 8,5%
Lebensdauer: 60 Jahre
VLH: 6.500 h/a

Annuitätsfaktor = 0,085 / (1 - 1,085^(-60))
                = 0,085 / (1 - 0,00752)
                = 0,085 / 0,9925
                = 0,0856 (8,56% p.a.)

Fixe Jahreskosten = 0,0856 × 11.000 + 130
                  = 941,3 + 130
                  = 1.071 €/kW/a

LCOE = 1.071 / 6.500 = 0,1648 €/kWh = 16,48 ct/kWh
```

**Code:** `lcoe_forward()` und `annuity_factor()` in `path_inputs.py`

### 2.2 Effektive Kernkraft-LCOE bei reduzierten Volllaststunden

**Formel:**

```
LCOE_KKW_effektiv = LCOE_KKW_design · (VLH_design / VLH_real)
```

**Begründung:** KKW sind CAPEX-dominiert. Wenn VLH halbiert wird, verdoppelt
sich die LCOE annähernd, weil Fixkosten pro kWh skalieren.

**Beispielrechnung:**

```
Design-LCOE bei 7.500 VLH: 14 ct/kWh
Effektiv bei 5.500 VLH: 14 × (7.500 / 5.500) = 19,1 ct/kWh
Effektiv bei 3.000 VLH: 14 × (7.500 / 3.000) = 35 ct/kWh
```

Das ist die methodische Brücke zur ISE-Studie, die 2.000-4.000 VLH für 2045
annimmt. Genau dieses Modell zeigt, wie die ISE auf die hohen LCOE-Werte kommt.

**Code:** Die VLH-Skalierung ist Teil der zentralen LCOE-Pipeline in
`compute_path()`; die VLH-Bandbreiten leben in `CAMP_RANGES`
(Parameter `nuclear_full_load_hours`).

---

## 3. Modell-Pfad-Berechnung

### 3.1 EE-H2 — EE + Speicher + H₂-Backup

**Erzeugungs-Mix-LCOE:**

```
LCOE_EE-H2_Erz = 0,40 · pv_LCOE
               + 0,30 · wind_onshore_LCOE
               + 0,15 · wind_offshore_LCOE
               + 0,04 · biomasse_LCOE
               + 0,03 · wasserkraft_LCOE
               + 0,08 · h2_backup_LCOE
```

**Begründung:** Die Anteile summieren auf 1,0 und reflektieren ein 100%-EE-System
mit H₂-Backup für Dunkelflauten. Die hohen PV/Wind-Anteile sind realistisch.

**Speicheranteil:**

```
Speicher_EE-H2 = 0,12 · battery_LCOS
```

12 % des Verbrauchs durch Batterie geführt — reflektiert hohe Volatilität in
EE-System.

**Endpreis-Formel:**

```
Endpreis_EE-H2 = LCOE_EE-H2_Erz + Speicher_EE-H2 + Netz + CO₂ + Steuern
                + Stabilitäts-Aufschlag (EE)
                - Flex-Rabatt (EE)
```

**Beispielrechnung mit Default-Werten:**

```
LCOE_EE-H2_Erz = 0,40 × 6,0 + 0,30 × 6,5 + 0,15 × 9,0
               + 0,04 × 14,0 + 0,03 × 6,0 + 0,08 × 32,0
               = 2,40 + 1,95 + 1,35 + 0,56 + 0,18 + 2,56
               = 9,00 ct/kWh

Speicher    = 0,12 × 7,0 = 0,84 ct/kWh
Netz        = 7,0 ct/kWh
CO₂         = 130 €/t × 30 g/kWh / 10.000 = 0,39 ct/kWh
Steuern     = 5,0 ct/kWh
Stabilität  = 0,11 ct/kWh (EE-Aufschlag)
Flex-Rabatt = 0,08 ct/kWh (EE)

Endpreis_EE-H2 = 9,00 + 0,84 + 7,0 + 0,36 + 5,0 + 0,11 - 0,08
               = 22,23 ct/kWh
```

Hinweis: Die Forward-Cost-Variante (ohne Steuern) liegt bei
0,40 × 6,0 + … + 0,08 × 32,0 + Speicher + Netz + CO₂ + Stabilität − Flex-Rabatt
= 17,23 ct/kWh in dieser Single-Year-Beispielrechnung. Im 30-Jahres-Mittel
ergibt das Modell für EE-H2 17,26 ct/kWh (neutral_default-Lager) — die
Differenz kommt von Lernkurven (PV-LCOE sinkt von 6,0 auf 4,0 ct,
H₂-LCOE von 45 auf 20 ct bis 2050) sowie Demand-gewichtetem Mittel.

**Code:** `compute_path()` in `path_model.py`

### 3.2 KKW-GAS — EE + Kernkraft + Gas-Bridge

**Erzeugungs-Mix mit zeitabhängiger KKW-Verfügbarkeit:**

```
falls Jahr ≥ KKW_Erstinbetriebnahme (lager-abhängig — siehe unten):
    LCOE_KKW-GAS_Erz = 0,25 · pv + 0,18 · won + 0,10 · woff
                     + 0,03 · bio + 0,03 · wasser
                     + KKW_Anteil · (KKW_LCOE_eff + Endlager + Stilllegung)
                     + Bridge_Gas_Anteil · gas_LCOE_fossil
                     + 0,06 · h2_backup_LCOE
sonst:
    LCOE_KKW-GAS_Erz = 0,25 · pv + 0,18 · won + 0,10 · woff
                     + 0,03 · bio + 0,03 · wasser
                     + 0,35 · gas_LCOE_fossil   (Bridge-Gas statt KKW)
                     + 0,06 · h2_backup_LCOE
```

**KKW-Inbetriebnahme nach Lager** (aus `KKW_EPR_APPROVAL_YEAR=2029` plus
sqrt-Streckung mit T_cap 21 a in
`core/inventories/tech_inventory.py`):

| Lager              | IBN-EPR | T_build |
|---|---:|---:|
| atom_optimistic    | 2036    | 7 a (Plan) |
| neutral_default    | 2046    | 17,5 a |
| bestand_optimistic | 2046    | 17,5 a |
| ee_optimistic      | 2050    | 21 a (Cap) |

**Wichtige Logik:** Bis zur Lager-IBN läuft KKW-GAS mit Gas-Backup statt
KKW. Erst danach übernimmt KKW schrittweise — und der Bridge-Gas-Anteil
geht zurück. Das ist die zentrale Bridge-Phase-Mechanik des Modells.

**Code:** `compute_path()` in `path_model.py`

### 3.3 KKW-H2 — EE + Kernkraft + H₂-Backup

Identisch zu KKW-GAS, aber mit `h2_backup_LCOE` statt `gas_LCOE_fossil` für
die Spitzendeckung. Bridge-Gas-Phase bleibt vor der Lager-IBN (technische
Realität: H₂ ist erst ab 2030+ in industriellem Maßstab verfügbar).

**Code:** `compute_path()` in `path_model.py`

### 3.4 EE-GAS — EE + Speicher + fossiles Gas-Backup

EE-GAS ist der Pfad mit Erneuerbarer Grundlast und fossilem
Erdgas-Backup. Im Modell wird »Gas« durchgängig als fossiles
Erdgas mit CO₂-Pönale modelliert — symmetrisch zu KKW-GAS und
WEITER-SO. Wer eine graduelle Beimischung von Bio-Methan oder
synthetischem Methan unterstellen möchte, kann die Backup-LCOE
selbst anpassen.

**Erzeugungs-Mix EE-GAS:**

```
LCOE_EE-GAS_Erz = 0,43 · pv + 0,32 · won + 0,15 · woff
                + 0,04 · bio + 0,03 · wasser
                + 0,08 · gas_LCOE_fossil
```

**Backup-LCOE (fossiles Erdgas, REINE Erzeugungskosten):**

```
gas_LCOE_fossil = 6,8 ct/kWh
```

Dieser Wert ist die REINE Stromgestehung von GuD-Kraftwerken bei
aktuellen Brennstoffkosten — OHNE CO₂-Pönale. Die Pönale wird global
über `co2_pricing_ct_kwh()` mit der pfadspezifischen CO₂-Intensität
und dem aktuellen CO₂-Preis-Welt-Belief (neutral 130 €/t, lager-spezifisch
100-160) erfasst. Die ISE-2024-Standardannahme »GuD inkl. CO₂« 11,2 ct/kWh
entspricht: 6,8 ct Erzeugung + 4,55 ct CO₂-Pönale (350 g/kWh × 130 €/t / 10.000).

**Code:** `compute_path()` in `path_model.py`

### 3.5 WEITER-SO — Status quo, Kohle bis Phaseout

**Erzeugungs-Mix mit zeitabhängigem Kohleausstieg und wachsendem Erdgas:**

```
kohle_anteil(Jahr) = max(0, kohle_initial · (1 − (Jahr − 2026)/(phaseout − 2026)))
gas_anteil(Jahr)   = gas_initial · (1 + erdgas_growth)^(Jahr − 2026)

LCOE_WEITER-SO_Erz = ee_anteil · LCOE_EE-Mix
                   + kohle_anteil(Jahr) · kohle_LCOE
                   + gas_anteil(Jahr)   · gas_LCOE_fossil
```

WEITER-SO modelliert die politische Untätigkeit: gebremster EE-Ausbau (60 % der
aktiven Pfade), Kohle bis 2038, Erdgas wächst parallel zum CO₂-Preis.

**Code:** `compute_path()` in `path_model.py`

---

## 4. CO₂-Bilanz

### 4.1 CO₂-Intensität pro Pfad

**WEITER-SO:** dominanter Beitrag durch Kohle und Erdgas.
```
CO₂_intensität_WEITER-SO = kohle_anteil · 850 + gas_anteil · 350
                         + ee_anteil   · 25
```
Bei Default 2030 (Kohle 16 %, Gas wachsend): ca. 250 g/kWh.

**EE-H2:** ~30 g/kWh konstant (Lebenszyklus-CO₂ aus PV/Wind-Mix
plus Restbiomasse; H₂-Backup ist CO₂-frei).

**KKW-GAS:**
```
CO₂_intensität_KKW-GAS = 25 + Bridge_Gas_Anteil · 350
```
Bei vollständiger Bridge-Phase (2030): 25 + 0,35 × 350 = 147 g/kWh.
Bei voller KKW-Verfügbarkeit (2050): 25 g/kWh.

**KKW-H2:** ~25 g/kWh konstant (Lebenszyklus-CO₂ aus
Mix-Erzeugung; H₂-Backup ist CO₂-frei in Bridge-Phase und
darüber hinaus). Die kleine Differenz zu EE-H2 (5 g/kWh) ergibt
sich aus dem niedrigeren Lebenszyklus-CO₂-Anteil von Kernkraft
(IPCC AR6: ~12 g/kWh) im Vergleich zu PV (25-50 g/kWh) und
Biomasse (30-300 g/kWh). Diese Differenz liegt im Bereich der
Modellungenauigkeit; sie ist kein argumentativer Kern.

**EE-GAS:**
```
CO₂_intensität_EE-GAS = ee_gas_backup_anteil · 350
                       + (1 − ee_gas_backup_anteil) · 20
```
Mit 8 % Backup-Anteil: 0,08 × 350 + 0,92 × 20 = 46 g/kWh konstant
über die Pfadkurve (keine grüne Beimischung im Default-Modell).

### 4.2 Gesamt-CO₂ pro Jahr

```
CO₂_pro_Jahr = CO₂_intensität · Demand_TWh / 1.000
              + Nicht_elektrifizierte_Sektoren_Mt · (1 − Skalierung)
```

**Begründung:** Strom-CO₂ skaliert mit Verbrauch und Intensität.
Nicht-elektrifizierte Sektoren (Verkehr, Wärme) haben heutige 250 Mt, sinken
linear mit Elektrifizierungs-Skalierung.

### 4.3 Kumuliertes CO₂ — System-Boundary (Strom + extern)

Methodische Setzung: Der ehrliche Pfad-Vergleich aggregiert
**Strom-Sektor + externe Sektor-Kopplung**. Die aktiven Pfade
(EE-GAS, EE-H2, KKW-GAS, KKW-H2) ziehen Heizung und Mobility in den
Strom-Sektor und tragen deren CO₂-Last über den Strom-Mix; WEITER-SO
und BESTAND lassen Heizung+Mobility extern fossil weiterlaufen — diese
Emissionen erscheinen nicht in `r.co2_mt`, sondern in
`r.co2_external_mt_per_year`. Nur die Summe beider erlaubt einen
fairen Klima-Vergleich.

```
CO₂_kumuliert_total = Σ (r.co2_mt + r.co2_external_mt_per_year) über alle Jahre
```

**Kumulierte CO₂ 2026-2055 (30 Jahre, neutral_default-Lager, System-Boundary):**

| Pfad | Strom | Extern | Gesamt | vs BESTAND |
|---|---|---|---|---|
| EE-H2 | 1.677 | 1.012 | **2.689 Mt** | −2.181 Mt (−45 %) |
| EE-GAS | 1.926 | 1.012 | **2.937 Mt** | −1.933 Mt (−40 %) |
| KKW-H2 | 2.011 | 1.012 | **3.022 Mt** | −1.848 Mt |
| KKW-GAS | 2.300 | 1.012 | **3.312 Mt** | −1.558 Mt |
| WEITER-SO | 1.966 | 2.466 | **4.432 Mt** | −438 Mt (Reductio-Referenz) |
| BESTAND | 2.292 | 2.578 | **4.870 Mt** | baseline |

Vergleichs-Anker BESTAND (statt WEITER-SO), weil BESTAND der politisch
ernsthaft verteidigte Status-quo-Pfad ist; WEITER-SO ist der Reductio-
Maßstab — was passiert, wenn niemand entscheidet — und kein Programm.

Differenz KKW-GAS − EE-GAS (Strom-Sektor): +374 Mt zulasten KKW-GAS,
davon ~265 Mt in der Bridge-Phase 2026–2046 (Bridge-Anteil ~71 %).
Siehe `BRIDGE_MEHREMISSIONEN_KKW_VS_EE_MT` und
`TOTAL_MEHREMISSIONEN_KKW_VS_EE_MT` in `core/path_sensitivity.py`.
Die Bridge-Phase trägt strukturell den größten Teil der KKW-CO₂-
Asymmetrie: KKW-Inbetriebnahme liegt im neutral_default-Lager bei
2046, bis dahin deckt fossiles Gas die KKW-Pfad-Versorgung.

**Steady-State 2055-2085 (30 Jahre Reife-Phase, System-Boundary):**
In der Reife-Phase ist die Sektor-Kopplung in EE/KKW-Pfaden
abgeschlossen → Extern-CO₂ ≈ 0; in WEITER-SO/BESTAND bleibt
Heizung+Mobility fossil. Pfad-Spannweite öffnet sich: EE-H2 1.076 /
KKW-H2 1.089 / KKW-GAS 1.146 / EE-GAS 1.393 vs. WEITER-SO 3.211 /
BESTAND 3.788 Mt. **EE-GAS spart 2.395 Mt (63 %) gegenüber BESTAND**
im Steady-State — gegen den ernsthaften politischen Gegen-Pfad öffnet
sich die Klima-Story mit der Zeit, sie wird nicht schwächer.
Methodische Caveat: Die Steady-State-Tabelle hält die Sektor-Kopplungs-
Tiefe auf dem 2055er-Stand konstant; jede weitere Sektor-Kopplungs-
Vertiefung post-2055 vergrößert den Abstand weiter, weil aktive Pfade
zusätzliche Demand klimaneutral aufnehmen, während BESTAND/WEITER-SO
weiterhin fossile Sektoren tragen.

**Code:** Aggregation aus `co2_lockin_metric()` in `path_model.py`;
returns `kumuliert_total_mt` (Strom + extern), `kumuliert_strom_mt`
(nur Strom-Sektor, alt-API-Pendant), `kumuliert_extern_mt`,
`kumuliert_lockin_mt` (Total ab `lockin_threshold_year`).

---

## 5. Sensitivitätsanalysen

### 5.1 Tornado-Diagramm

**Formel pro Parameter:**

```
Swing_p = |LCOE_total(p · 1,25) - LCOE_total(p · 0,75)|
```

**Sortierung absteigend nach Swing.** Größter Swing = wichtigster Parameter.

**Code:** `tornado_path_analysis()` in `path_sensitivity.py`

### 5.2 Monte-Carlo-Simulation

**Verteilungen:**

| Parameter | Verteilung | Parameter |
|---|---|---|
| pv_lcoe | Normal | μ=6,0, σ=1,0, clip [3, 12] |
| wind_onshore | Normal | μ=6,5, σ=1,0, clip [4, 11] |
| wind_offshore | Normal | μ=9,0, σ=1,5, clip [7, 13] |
| battery_lcos | Lognormal | log(μ)=log(7), σ=0,30, clip [3, 18] |
| nuclear_lcoe | Lognormal | log(μ)=log(14), σ=0,25, clip [7, 25] |
| nuclear_vlh | Normal | μ=6500, σ=800, clip [3500, 8000] |
| h2_lcoe | Normal | μ=32, σ=6, clip [20, 55] |
| co2_price | Normal | μ=120, σ=30, clip [50, 200] |
| grid_surcharge | Normal | μ=7, σ=1,5, clip [4, 12] |

**Begründung Lognormal für KKW und Batterien:** Reale Kostenüberläufe sind
asymmetrisch (sehr hohe Werte sind möglich, sehr niedrige nicht), daher
Lognormal statt Normal.

**Output-Metriken:**

```
P(EE-H2 < KKW-GAS) = Anteil der Läufe, in denen EE-H2 günstiger als KKW-GAS
P(EE-GAS < KKW-GAS) = Anteil der Läufe, in denen EE-GAS günstiger als KKW-GAS
```

Analog für jeden Paarvergleich der sechs Pfade. Die Pair-Probabilities
zeigen, wie robust die Pfad-Reihenfolge gegenüber Parameter-Unsicherheit
ist; ein Violin-Plot je Pfad lässt sich aus `monte_carlo_all_paths()` mit
`viz/charts/montecarlo.py` rendern.

**Code:** `monte_carlo_all_paths()` — Top-Level-Import via `from enesys import monte_carlo_all_paths`.

---

## 6. Winter-Stress-Test

### 6.1 Spitzenlast bei kalter Dunkelflaute

**Formel:**

```
Peak_GW = Sockel_avg · 1,3 · Winter_Faktor
        + Heizung_avg · Heiz_Faktor · (COP_Jahr / COP_Winter)
        + Mobilität_avg · 1,4 · (1 + E-Auto_Winter_Aufschlag)
        + Industrie_avg · 1,0
```

**Begründung der Faktoren:**

- Sockel × 1,3: Winter-Abendspitze über Jahresmittel (Beleuchtung, Geräte)
- Heizung-Faktor 1,8: kalter Tag = 80% mehr Heizleistung als Mittel
- COP-Verschlechterung: 3,2 / 2,2 = 1,45 mehr Strom pro kWh Wärme
- Mobilität × 1,4: 60% laden in Spitzenstunde × 25% Winter-Aufschlag

**Beispielrechnung 2045 Default:**

```
Sockel_avg = 220 / 8760 × 1000 = 25,1 GW × 1,3 × 1,1 = 35,9 GW
Heizung_avg = 68 / 8760 × 1000 = 7,8 GW × 1,8 × 1,45 = 20,3 GW
Mobilität_avg = 120 / 8760 × 1000 = 13,7 GW × 1,4 × 1,25 = 24,0 GW
Industrie = 340 / 8760 × 1000 = 38,8 GW

Peak = 35,9 + 20,3 + 24,0 + 38,8 = 119,0 GW
```

Validierung gegen ÜNB-Szenarien für 2045: 110-160 GW. Modell-Output 119 GW
liegt im unteren Bereich → mit Default-Werten konservativ angenommen
(80% E-Mob, 60% WP). Bei voller Elektrifizierung würde der Peak Richtung 145 GW
gehen.

**Code:** `WinterStressParams.winter_demand_gw()` in `extensions/winter_stress.py`

### 6.2 EE-Erzeugung während Dunkelflaute

```
EE_supply_GW = PV_Kapazität · 0,03 + Wind_onshore · 0,10
              + Wind_offshore · 0,15 + 8 (firm: Bio + Wasser)
```

3% PV, 10% Wind onshore, 15% Wind offshore (offshore besser bei Dunkelflaute,
weil andere Wettersysteme).

### 6.3 Defizit-Berechnung

```
Residual_GW = Peak_GW - EE_supply_GW
Backup_total = Σ Backup-Quellen
Defizit = max(0, Residual_GW - Backup_total)
```

Wenn `Defizit > 0`: Versorgungslücke, Strompreise explodieren oder Lastabwurf nötig.

**Code:** `winter_stress_test()` in `extensions/winter_stress.py`

---

## 7. Annahmen, die nicht im Modell stehen

Was außerhalb des Modells liegt:

1. **Geopolitische Risiken** — Solarpanel-Importabhängigkeit von China,
   Erdgas-Importrouten, Uran-Versorgung
2. **Nicht-deployte Technologien** — Natrium-Ionen-Akkus, Festkörper-
   Akkus (kein kommerzieller Deployment-Stand). SMRs sind im Modell
   explizit mit `KKW_SMR_APPROVAL_YEAR = 2029` und IBN 2034–2046
   parametrisiert.
3. **Verhalten** — Suffizienz, Konsumreduktion, Wärmesanierung
4. **Politische Stabilität** — Regierungswechsel, EU-Politik-Änderungen
5. **Stranded Assets** — was mit bestehenden Gaskraftwerken passiert,
   wenn sie früher als geplant ausgemustert werden

Diese Faktoren sind teils nicht modellierbar, teils nur qualitativ
behandelbar. Eine sachgerechte Diskussion sollte sie benennen, ohne sie
zu pseudo-quantifizieren.
