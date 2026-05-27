# Quellen-Dokumentation der Eingangsparameter

Dieses Dokument belegt jeden Default-Parameter im Modell mit Quelle, Datum und
Lager-spezifischer Bandbreite. Es ist die Grundlage für die Belegbarkeit jeder
Default-Setzung im Modell.

> **Hinweis zur Code-Integration:** Die hier dokumentierten
> Lager-Bandbreiten sind im Code als zentrale Datenstruktur
> `CAMP_RANGES` aus `enesys` importierbar (siehe
> `from enesys import CAMP_RANGES, tornado_path_analysis,
> monte_carlo_all_paths`). Die Sensitivitäts-Funktionen lesen ihre
> Bandbreiten daraus ab — statt ad-hoc-±25 %. Wer einen Lager-Wert für
> unrealistisch hält, muss nur diese Tabelle ändern; alle Sensitivitäts-
> analysen aktualisieren sich automatisch.

> **Glaubwürdigkeit:** Die Modell-Aussagen stützen sich auf
> Klasse-A/B-Quellen (Behörden, peer-reviewte Wissenschaft). Die
> Tornado-kritischen Hebel sind in `docs/FORMULAS.md` mit ihrer
> Sensitivität dokumentiert; die volle Quellen-Tabelle steht weiter
> unten in diesem Dokument.

## Lese-Anleitung

Jeder Parameter folgt diesem Schema:

```
PARAMETER (Code-Variable)
├── Default (neutrale Mitte): WERT  [Quellen-Tag]
├── EE-Lager-Annahme: WERT-RANGE   [Quellen-Tag, Begründung]
├── Atom-Lager-Annahme: WERT-RANGE [Quellen-Tag, Begründung]
└── Methodischer Streitpunkt: ...
```

**Quellen-Tags** (verlinkt am Ende des Dokuments):
- `ISE-2024` Fraunhofer ISE Stromgestehungskosten 2024
- `BNEF-2025-LIB` BloombergNEF Lithium-Ion Battery Price Survey 2025 (Dez 2025)
- `BNEF-2025-LCOE` BloombergNEF LCOE Report 2026 (Feb 2026)
- `BNEF-2025-ESS` BloombergNEF Energy Storage Systems Cost Survey 2025
- `KENFO-2024` KENFO Geschäftsbericht 2024
- `EWI-2024` EWI Köln Wasserstoff-Studie
- `RUHNAU-2021` Ruhnau & Qvist, Hertie School
- `EDF-HPC` EDF Hinkley Point C Updates
- `NAO-HPC-2017` UK National Audit Office Hinkley Point C audit (staatlicher Rechnungshof)
- `COURDESCOMPTES-FLAM` Cour des Comptes Flamanville-Audit
- `BMWE-2026` BMWE Industriestrompreis-Richtlinie 2026
- `MODO-2025` Modo Energy Inertia-Studie
- `KERND-2024` KernD Bewertung der Fraunhofer-Studie (Pro-Atom-Position)
- `AGORA-2045` Agora Energiewende, Klimaneutrales DE 2045
- `BNETZA-VS-2025` Bundesnetzagentur Versorgungssicherheitsbericht 2025
- `DWA-2024` Deutsches Wetteramt / DWD Dunkelflauten-Analyse
- `EUKOM-2024` EU-Kommission, ETS-Reform-Bewertung 2024 (CO₂-Preispfade)
- `ENERGY-CHARTS-ISE` Fraunhofer ISE Energy-Charts — interaktive Datenplattform deutsche Stromerzeugung (2014-laufend); URL https://energy-charts.info
- `BATTERY-CHARTS-RWTH` RWTH Aachen ISEA Battery Charts — Bestandsauswertung deutsche Batteriespeicher (2022-laufend); URL https://battery-charts.de
- `FIGGENER-2022` Figgener et al.: peer-reviewte Methoden-Referenz Batteriespeicher-Marktentwicklung Deutschland
- `ELECTRICITYMAPS-TOMORROW` Tomorrow (Kopenhagen) — Live-CO₂-Intensitäts-Plattform mit Lifecycle-Faktoren, Flow-Tracing zwischen Netzen; URL https://electricitymaps.com
- `HIRTH-MARKETVALUE-2013` Lion Hirth, »The Market Value of Variable Renewables«, Energy Economics 38, 218–236 (2013). DOI 10.1016/j.eneco.2013.02.004. Cannibalization-Effekt für Wind/Solar
- `HIRTH-INTEGRATIONCOSTS-2015` Hirth, Ueckerdt & Edenhofer, »Integration Costs Revisited«, Renewable Energy 74, 925–939 (2015). DOI 10.1016/j.renene.2014.08.065. Profile-/Balancing-/Grid-Costs-Zerlegung
- `HIRTH-BALANCING-2015` Hirth & Ziegenhagen, »Balancing power and variable renewables«, Renewable & Sustainable Energy Reviews 50, 1035–1051 (2015). DOI 10.1016/j.rser.2015.04.180
- `RUHNAU-HIRTH-HEATPUMPS-2020` Ruhnau, Hirth & Praktiknjo, »Heating with wind: Economics of heat pumps and variable renewables«, Energy Economics 92, 104967 (2020). DOI 10.1016/j.eneco.2020.104967
- `CLOETE-HIRTH-H2-2021` Cloete, Ruhnau & Hirth, »On capital utilization in the hydrogen economy«, International Journal of Hydrogen Energy 46(1), 169–188 (2021). DOI 10.1016/j.ijhydene.2020.09.197
- `ZACHMANN-HIRTH-EUMARKET-2023` Zachmann, Hirth, Heussaff et al., ITRE-Studie zum EU-Strommarkt-Design (28.9.2023); URL https://www.europarl.europa.eu/RegData/etudes/STUD/2023/740094
- `HIRTH-DEMAND-2024` Hirth, Ruhnau & Khanna, »How aggregate electricity demand responds to hourly wholesale price fluctuations«, Energy Economics (2024)
- `STIEWE-HIRTH-CANNIBAL-2025` Stiewe & Hirth, »Cross-border cannibalization«, Applied Energy (2025). DOI 10.1016/j.apenergy.2025.125267
- `EHRHART-HIRTH-REDISPATCH-2025` Ehrhart, Eicke, Hirth et al., »Analysis of a capacity-based redispatch mechanism«, Energy Economics 149, 108751 (2025). DOI 10.1016/j.eneco.2025.108751
- `HIRTH-PREISSPITZEN-2025` Hirth, »Price spikes on the German electricity market« (50Hertz Scientific Advisory, 2025); URL https://neon.energy/Neon-Preisspitzen-EN.pdf
- `ISE-HENNING-2015` Henning & Palzer, »Was kostet die Energiewende?« (Fraunhofer ISE, November 2015). DOI 10.24406/publica-fhg-297710 — REMod-D-Sektor-Kopplungs-Modell
- `ISE-BAT4CPP-2022` Fraunhofer ISE, »Batteriespeicher an ehemaligen Kraftwerksstandorten« (Positionspapier 2022)
- `ISE-LCOE-FLEX-2025` Fraunhofer ISE, Kurzanalyse »Stromgestehungskosten flexible Kraftwerke« (Januar 2025) — Reserve-Tech-LCOE 12,9–132,7 ct/kWh je nach Volllaststunden

---

## A · ERZEUGUNGSKOSTEN (LCOE)

### `pv_lcoe` — PV-Freiflächen-LCOE

| | Wert | Quelle |
|---|---|---|
| Default | 6,0 ct/kWh | `ISE-2024` |
| Bandbreite ISE | 4,1 – 6,9 ct | `ISE-2024` (S.4) |
| EE-Lager | 4,5 ct | `ISE-2024` Untergrenze, optimistische Strahlung Süddeutschland |
| Atom-Lager | 8,0 ct | `KERND-2024` argumentiert für höhere Werte wegen Backup-Notwendigkeit |

**Methodischer Streitpunkt:** ISE rechnet PV als Solo-Anlage; Atom-Lager fordert
Aufschlag für Speicher/Backup ("Systemkosten"). Wir trennen das im Modell sauber:
LCOE ist *nur Erzeugung*, Speicher/Backup als eigene Schicht.

**Originalzitat ISE 2024:**
> "Die Kosten der Stromerzeugung von PV-Anlagen variieren laut Studie je nach
> Anlagentyp und Sonneneinstrahlung zwischen 4,1 und 14,4 €Cent/kWh"

PV-Freifläche (das was wir modellieren): 4,1–6,9 ct.

### `wind_onshore_lcoe`

| | Wert | Quelle |
|---|---|---|
| Default | 6,5 ct/kWh | `ISE-2024` |
| ISE-Bandbreite | 4,3 – 9,2 ct | `ISE-2024` (S.4) |
| Anlagenkosten | 1.300 – 1.900 €/kW | `ISE-2024` |
| EE-Lager | 5,0 ct | guter Standort + neue WEA-Generation |
| Atom-Lager | 8,5 ct | Bandbreite ISE Obergrenze + Realität DE-Genehmigungspraxis |

**Originalzitat ISE 2024:**
> "Die Stromgestehungskosten von Onshore-Windenergieanlagen liegen im Jahr 2024
> zwischen 4,3 und 9,2 €Cent/kWh, basierend auf spezifischen Anlagenkosten von
> 1300 bis 1900 Euro/kW."

### `wind_offshore_lcoe`

| | Wert | Quelle |
|---|---|---|
| Default | 9,0 ct/kWh | `ISE-2024` |
| ISE-Bandbreite | 5,5 – 10,3 ct | bei bis zu 4.500 Vollaststunden |
| BNEF 2026 global | ~10 ct ($100/MWh) | `BNEF-2025-LCOE` |
| EE-Lager | 7,5 ct | optimistisch, neue große Turbinen |
| Atom-Lager | 11,0 ct | inkl. Netzanbindung als Realität |

**Aktueller Kosten-Trend:** BNEF berichtet, dass Offshore-Wind-Kosten 2025
global um 12 % gestiegen sind, in UK sogar 69 % gegenüber dem Niveau von
vor fünf Jahren. Quelle: `BNEF-2025-LCOE`. Eine Aufwärts-Korrektur, die
in jeder methodisch sauberen Diskussion adressiert werden muss.

### `nuclear_lcoe` — Kernkraft-Neubau

| | Wert | Quelle |
|---|---|---|
| Default | 14,0 ct/kWh | Mittelwert real EU |
| ISE-Bandbreite | 13,6 – 49 ct | `ISE-2024` (Modellannahme mit niedrigen VLH) |
| Hinkley Point C real | ~15-16 ct | `EDF-HPC` Strike-Price 92,50 £/MWh in 2012-Preisen, inflationsindexiert auf £133/MWh Stand 2025 |
| Hinkley Point C UK-Audit | Strike Price £92,50/MWh (2012) → £133/MWh (2025); Top-up-Subvention von £6 Mrd. (2013) auf £30 Mrd. (2017) gestiegen | `NAO-HPC-2017` |
| Flamanville real | >20 ct | `COURDESCOMPTES-FLAM` 23,7 Mrd. € für 1,6 GW |
| EE-Lager | 18 ct | reale Hinkley/Flamanville-Erfahrung |
| Atom-Lager | 9 ct | optimistisch, Plan-LCOE neuer EPR-Generation |

**Streitpunkt — der wichtigste der ganzen Debatte:**
- Pro-Atom: rechnet mit *Plan*-LCOE basierend auf optimistischen Bauzeiten und VLH
- Pro-EE: rechnet mit *realisierten* LCOE aus Hinkley/Flamanville
- ISE rechnet mit reduzierten VLH (weil im 80%-EE-System KKW gedrosselt werden müsste)

**KernD-Kritik (`KERND-2024`):**
> "4.300 bis 6.300 Vollaststunden für Kernkraftwerke in 2024, die bis auf 2.000
> bis 4.000 Vollaststunden in 2045 absinken. Dies hat natürlich verheerende
> Folgen für die Kostenstruktur"

KernD argumentiert, dass deutsche KKW historisch 7.500-8.000 VLH erreichten — was
korrekt ist, aber für ein Grundlast-System gilt. In einem volatilen 80%-EE-System
müssten KKW wirtschaftlich abregeln, wenn EE-Strom billig ist. Diese Asymmetrie
ist methodisch unstrittig und wirkt direkt auf die Lager-Bandbreite.

### `nuclear_full_load_hours`

| | Wert | Quelle |
|---|---|---|
| Default | 6.500 h | Mittelwert |
| ISE-Annahme 2024 | 4.300 – 6.300 h | `ISE-2024` (kritisiert von KernD) |
| ISE-Annahme 2045 | 2.000 – 4.000 h | im Hochfluss-EE-System |
| KernD-Argument | 7.500 – 8.000 h | `KERND-2024`, historische DE-Werte |
| EE-Lager | 5.500 h | realistisch für 80%-EE-System |
| Atom-Lager | 7.800 h | wenn KKW Grundlast-Privileg hat |

**Modellbehandlung:** `effective_nuclear_lcoe()` skaliert die LCOE invers mit VLH,
weil CAPEX-dominiert. Das macht den Streit zwischen Plan-VLH und Realitäts-VLH
quantitativ sichtbar.

### `gas_ccgt_lcoe` — Gas-GuD, reine Erzeugungskosten (ohne CO₂-Pönale)

| | Wert | Quelle |
|---|---|---|
| Default (Modell) | 6,8 ct/kWh | `ISE-2024` minus CO₂-Anteil |
| ISE all-in (mit CO₂) | 11,0 ct/kWh | `ISE-2024` Default |
| ISE-Bandbreite all-in | 10,9 – 18,1 ct | abhängig von Gaspreis und CO₂-Preis |

Hinweis: Im Modell wird `gas_ccgt_lcoe` als REINE Erzeugungskosten
(6,8 ct/kWh) verwendet; die CO₂-Pönale wird separat über
`co2_pricing_ct_kwh()` mit der pfadspezifischen Intensität (350 g/kWh
für Gas-Backup-Anteil) und dem aktuellen CO₂-Preis erfasst. Das
vermeidet Doppelzählung der Pönale, wenn der CO₂-Preis-Welt-Belief
(neutral 130 €/t, lager-spezifisch 100-160) sich ändert. Der ISE-2024-Wert 11,2 ct/kWh entspricht der
Summe: 6,8 (Erzeugung) + 4,55 (350 g/kWh × 130 €/t / 10.000) = 11,35.

**Originalzitat ISE 2024:**
> "Die Stromgestehungskosten der flexiblen Technologien liegen deutlich über
> den Kosten der Erneuerbaren Energien, da CO2-Kosten und die Beschaffung von
> Wasserstoff zentrale Kostentreiber sind"

### `h2_gas_lcoe` — Wasserstoff-GuD-Backup

| | Wert | Quelle |
|---|---|---|
| Default | 32 ct/kWh | `EWI-2024` Mittelwert |
| ISE-Bandbreite | 23,6 – 43,3 ct | `ISE-2024` |
| EE-Lager | 25 ct | optimistisch, billiger H₂ aus Importen |
| Atom-Lager | 50 ct | skeptisch, H₂-Knappheit |

---

## B · CAPEX (Forward Costs)

### `pv_capex_eur_kw`

| | Wert | Quelle |
|---|---|---|
| Default | 700 €/kW | `ISE-2024`, BNEF |
| ISE-Bandbreite | 530 – 1.600 €/kW | `ISE-2024` Anlagengröße abhängig |

### `wind_onshore_capex_eur_kw`

| | Wert | Quelle |
|---|---|---|
| Default | 1.400 €/kW | `ISE-2024` |
| ISE-Bandbreite | 1.300 – 1.900 €/kW | `ISE-2024` |

### `nuclear_capex_eur_kw`

| | Wert | Quelle |
|---|---|---|
| Default | 14.000 €/kW | Mitte zwischen HPC-Realität (~18.000) und Sizewell-FOAK (~10.000); EU-EPR-Erfahrungs-Anker. Konservativer gewählt als Plan-EPR (~9.000), aber unter der Hinkley-Realität — die KKW-Pfade tragen damit nicht die volle Hinkley-Last, aber auch nicht den optimistischsten Plan-Wert |
| Hinkley Point C aktuell | £35 Mrd. in 2015-Preisen ≈ £49 Mrd. in 2026-Preisen für 3,2 GW = ~18.000 €/kW; Inbetriebnahme verschoben auf 2030 | `EDF-HPC` (EDF-Update Feb 2026), `NAO-HPC-2017` (UK-Audit) |
| Hinkley Point C historisch | 35-46 Mrd. £ (Stand Januar 2024) ≈ ~13.000 €/kW | `EDF-HPC` |
| Flamanville | 23,7 Mrd. € für 1,6 GW | `COURDESCOMPTES-FLAM` = ~14.800 €/kW |
| OL3 Finnland | 11 Mrd. € für 1,6 GW | ~6.900 €/kW |
| EE-Lager | 18.000 €/kW | HPC-Realität Stand Februar 2026 (EDF-Schätzung £35 Mrd. in 2015-Preisen ≈ £49 Mrd. in 2026-Preisen für 3,2 GW); EE-Lager-Argument: »reale EU-EPR-Bauerfahrung zeigt teure KKW« |
| Atom-Lager | 7.000 €/kW | optimistisch, "n-ter EPR" mit Skaleneffekten |

### `battery_capex_eur_kwh`

| | Wert | Quelle |
|---|---|---|
| Default | 110 €/kWh (~117 USD) | `BNEF-2025-ESS` |
| BNEF 2025 turnkey global | 117 USD/kWh | `BNEF-2025-ESS` (10. Dez. 2025) |
| BNEF 2025 stationäre Pack | 70 USD/kWh | `BNEF-2025-LIB` (9. Dez. 2025) |
| BNEF Forecast 2035 EU | 101 USD/kWh | `BNEF-2025-ESS` |
| EE-Lager | 90 €/kWh | China-bias-korrigiert |
| Atom-Lager | 165 €/kWh | konservativ, lokale Aufschläge |

**Wichtiger Hinweis:** BNEF unterscheidet:
- **Pack-Preis** (nur Batterie): 70 USD/kWh stationäre Storage (2025)
- **Turnkey-System** (komplette BESS-Anlage installiert): 117 USD/kWh
Das Modell rechnet mit Turnkey-System-Kosten, weil das die Forward Costs
für ein neues Speicher-Projekt sind.

**Originalzitat BNEF 2025:**
> "In 2025, the global average price of a turnkey battery energy storage system
> (BESS) is US$117/kWh"
> "By 2035, the firm has forecast US$41/kWh average prices for 4-hour turnkey
> systems in China, US$101/kWh in Europe"

---

## C · WACC (Risikoprämien)

### `wacc_pv` / `wacc_wind` / `wacc_nuclear` / `wacc_battery`

**Hergeleitete Default-Werte** mit expliziter Begründung gegen die
Frage »wurde der Wert so gewählt, dass die Pfad-LCOE bestimmte
Ziel-Werte treffen?«.

| Technologie | Default | Bandbreite extern (real WACC) | Herleitung Mittelwert |
|---|---|---|---|
| `wacc_pv` | **5,0 %** | IRENA-2024 EU 3,8 %; FEE-Frankreich 3 %; EY 5-8 % EU | DE = Premium-Markt (höhere Genehmigungs- und Netzanschlusskosten als FR/südliches EU). 5,0 % = oberes Drittel der EU-Bandbreite, konsistent mit dt. PV-Auctions 2023-2025. |
| `wacc_wind` | **6,0 %** | IRENA-2024 WEU 3,3 %; FEE-Frankreich 3 %; EY 5-8 % EU | Wind onshore DE: längere Genehmigungszeit als PV (NIMBY, Artenschutz, Abstandsregeln), höhere Risikoprämie. 6,0 % = obere Hälfte EU. |
| `wacc_nuclear` | **9,0 %** | HPC 9,0 % real terms equity (Helm-Oxford via CPI-indexiertes CfD, UK Parliament HPC0003); Sizewell-C-RAB 6,7 % real CPIH (UK GOV); Lazard 7,7 % (nominal); EIA-regulated 4,3 % real; EY 5-15 % global (gemischt) | DE-Reaktivierung/EPR ohne RAB-Modell: 9,0 % = HPC-Realität als Default, 7,0 % (Sizewell-RAB) als untere, 10 % (Privat-Investor) als obere Grenze. Alle drei Werte sind als Real-Terms verifiziert (vgl. interne Nominal-Real-Audit-Analyse). |
| `wacc_battery` | **7,0 %** | BNEF-2025-ESS impliziert ~6-9 % (LCOS-Reverse-Engineering); EY 5-8 % | Neuere Asset-Klasse mit weniger Track-Record als Wind, daher höher. 7,0 % = oberhalb Solar (5 %), unterhalb KKW (8,5 %). |

**WACC-Sensitivität pro Pfad:**

| WACC-Variation (±1 pp / 20 %) | Wirkung auf Pfad-LCOE |
|---|---|
| `wacc_pv` 5,0 → 6,0 % | EE-Pfade +0,20 ct, KKW-Pfade +0,13 ct |
| `wacc_wind` 6,0 → 6,6 % | EE-Pfade +0,13 ct, KKW-Pfade +0,08 ct |
| `wacc_nuclear` 8,5 → 10,0 % | nur KKW-Pfade +0,14 ct |
| `wacc_battery` 7,0 → 5,0 % | alle Pfade ±0,00 ct (LCOS dominiert) |

Die WACC-Sensitivität ist real, aber **kein einzelner WACC bewegt
einen Pfad-LCOE um mehr als 0,2 ct/kWh** bei plausibler Variation.

**Konservative Default-Wahl:** Innerhalb der plausiblen WACC-Bandbreiten
setzt das Modell jeden Parameter auf den Wert, der den jeweiligen Pfad
eher ungünstiger erscheinen lässt. Bei `wacc_pv` wäre 4,8 % im Korridor;
das Modell verwendet 5,0 %. Bei `wacc_nuclear` wäre 9,5 % im Korridor;
das Modell verwendet 9,0 %. Damit ist die Pfad-Reihenfolge robust
gegen WACC-Sensitivitätsläufe innerhalb der Quellenbandbreite (siehe
Camp-Symmetrie in README + methodology.md).

**Methodischer Streitpunkt:** Das Atom-Lager fordert oft 5 % WACC
mit Staatsgarantie (wie Frankreich vor der Cour-des-Comptes-Kritik
2024). Das EE-Lager argumentiert 9-10 % wegen historischer
Kostenüberläufe. Hinkley Point C: UK-Regierung hat de facto Risiko
durch CfD übernommen, was die WACC-Diskussion politisch verzerrt.
Sizewell C ab 2025 verwendet RAB-Modell (Regulated Asset Base) mit
Verbraucher-Risiko, was die nominalen WACCs senkt — wirtschaftlich
verschiebt das nur die Risikoträger, nicht die Kosten.

**Quellen:**

| Quelle | Bezug | Online |
|---|---|---|
| IRENA-2024-WACC | Renewable Power Generation Costs 2024, Figure S7: Europe-WACCs 3,8 % gewichtet | https://www.irena.org/Publications/2025/Jul/Renewable-power-generation-costs-in-2024 |
| EY-2025-Nuclear | Capital costs challenge — CESA nuclear newbuilds 5-15 %, Solar/Wind 5-8 % | https://www.ey.com/en_pl/insights/power-utilities/capital-costs-challenge-how-to-overcome-the-issue-in-cesa |
| Helm-Oxford-HPC | "Hinkley would have been half the cost at 2 % WACC, vs EDF's 9 %" | https://en.wikipedia.org/wiki/Hinkley_Point_C_nuclear_power_station (zitiert) |
| UK-Parliament-HPC0003 | HPC 9,04 % = real terms equity return; £79,7 Mrd Real-Cashflow (2016 prices); CfD CPI-indexiert. Belegt Real-Charakter des 9 %-WACC-Defaults. | https://committees.parliament.uk/writtenevidence/81140/pdf/ |
| Sizewell-C-RAB-GOV | UK GOV Sizewell-C-RAB-Lizenz: WACC 6,7 % real CPIH during construction (10,8 % real Allowed Return on Equity, 4,5 % real cost of debt, 65 % gearing). Belegt Real-Charakter des 7 %-Lower-Bounds. | https://www.gov.uk/government/publications/sizewell-c-regulated-asset-base-rab |
| World-Nuclear-2026 | Sizewell C RAB-Modell, Cost-of-Capital-Reduktion vs HPC | https://world-nuclear.org/information-library/economic-aspects/financing-nuclear-energy |
| BNEF-2025-ESS | Storage-Cost-Survey, WACCs implizit über LCOS-Komposition | (intern, nicht verlinkbar) |
| ISE-2024 | Stromgestehungskosten EE Deutschland, WACC-Methodik | https://www.ise.fraunhofer.de/de/veroeffentlichungen/studien/studie-stromgestehungskosten-erneuerbare-energien.html |

---

## D · SPEICHER

### `battery_lcos`

| | Wert | Quelle |
|---|---|---|
| Default | 7,0 ct/kWh entladen | BNEF 2026 LCOE |
| BNEF 2026 4h-System | <10 ct/kWh in 6 Märkten | `BNEF-2025-LCOE` |
| ISE 2024 (4 h) | 6,0 – 22,5 ct | `ISE-2024` |

**Originalzitat BNEF (Feb 2026):**
> "The levelized cost of electricity for a four-hour system is now below
> $100/MWh in six markets."

### `h2_storage_lcoe` — Wasserstoff-Backup-Vollkosten

| | Wert | Quelle |
|---|---|---|
| Default | 32 ct/kWh | EWI/ISE |
| Bandbreite | 20 – 55 ct | abhängig von Elektrolyseur-Skalen |
| H₂-Speicherbedarf DE 2045 | 43 – 84 TWh | `EWI-2024` |
| Atom-Lager-Skepsis | >100 TWh nötig | `RUHNAU-2021` Worst-Case-Annahme |

---

## E · CO₂

### `co2_price_eur_t` (Welt-Belief)

| | Wert | Quelle |
|---|---|---|
| Default 2026 | 90 €/t | EU-ETS aktuell |
| **Neutral-Welt 2045** | **130 €/t** | Konsens-Forecast, leicht über Pre-2026-Median |
| **EE-Lager-Welt** | **160 €/t** | Klimazielen-konsistente Internalisierung |
| **Atom-Lager-Welt** | **150 €/t** | Atom-Lager-Position mit CO₂-Preis-Konsistenz zur Klimaaktion |
| **Bestand-Lager-Welt** | **100 €/t** | ETS-Aufweichungs-Erwartung |
| EU-Modell 2030 | 90 – 150 €/t | EU-Kommission, CEPS |

### Lebenszyklus-CO₂-Intensitäten pro Technologie

Diese Werte sind im Modell-Code als Konstanten in der Pfad-CO₂-
Berechnung hinterlegt. Sie spiegeln Lebenszyklus-Werte
(LCA: Bau, Brennstoff, Betrieb, Rückbau) wider und sind Quelle
der kleinen CO₂-Differenz zwischen EE-H2 und KKW-H2.

| Technologie | Lebenszyklus-CO₂ | Quelle |
|---|---|---|
| Photovoltaik | 25 – 50 g/kWh | `IPCC-AR6-WG3` Annex III |
| Wind onshore | 7 – 15 g/kWh | `IPCC-AR6-WG3` Annex III |
| Wind offshore | 8 – 12 g/kWh | `IPCC-AR6-WG3` Annex III |
| Kernkraft (LWR) | ~12 g/kWh (Median) | `IPCC-AR6-WG3` Annex III |
| Biomasse | 30 – 300 g/kWh | `IPCC-AR6-WG3` Annex III, breite Spanne |
| Erdgas-GuD | ~350 g/kWh (Verbrennung) | EU-ETS-Methodik |
| Kohle-Kraftwerk | ~900 g/kWh (Verbrennung) | EU-ETS-Methodik |

**Methodischer Hinweis:** Lebenszyklus-Studien zu Kernkraft und
Photovoltaik haben breite Spannen, die je nach Standort,
Anlagentyp und Allokationsmethode variieren. Die im Modell
verwendeten gewichteten Pfad-Mittel (30 g/kWh für EE-H2,
25 g/kWh für KKW-H2) liegen innerhalb der konsensualen
Bandbreite, sind aber nicht die einzig vertretbare Wahl. Wer
Biomasse strenger oder PV-Lifecycle anders ansetzt, kann andere
Werte argumentieren. Die Differenz zwischen EE-H2 und KKW-H2
liegt deshalb im Bereich der Modellungenauigkeit.

---

## F · ENDLAGERUNG

### `endlager_per_kwh`

| | Wert | Quelle |
|---|---|---|
| Default | 0,3 ct/kWh | abgeleitet aus KENFO/Restmenge |
| KENFO-Fonds | 24,1 Mrd. € | `KENFO-2024` (3. Juli 2017 von Betreibern eingezahlt) |
| Bisherige Auszahlungen | 4,47 Mrd. € | `KENFO-2024` (Stand Ende 2024) |
| KENFO-Wertzuwachs 2024 | +9,4% | `KENFO-2024`, deutlich über Zielrendite 4,1% |
| BUND-Schätzung | 10,2 – 20,5 Mrd. € | für KKW-Müll allein, im KENFO enthalten |
| Endlager-Standort frühestens | 2046 | KENFO-Roadmap |
| Endlager-Betrieb möglich | 2050+ | Realität nach Bauzeit |

**Klarstellung zur Fonds-Höhe.** Die 24,1 Mrd. € sind das
**eingezahlte Fonds-Kapital** (KENFO-Einlage durch E.ON, RWE, EnBW,
Vattenfall 2017), nicht die erwartete Endlagerkosten-Summe. Aktuelle
Schätzungen zur Lebenszyklus-Endlagerung bewegen sich in einem
breiteren Korridor (BGE-/BUND-Bandbreiten 10-170 Mrd. €, je nach
Stilllegungs- und Konditionierungs-Annahmen).

Das KENFO-Modell verschiebt das Risiko: der Fonds rendiert über
einen 75-Jahres-Anlagehorizont (Wertzuwachs 9,4 % in 2024 deutlich
über Zielrendite 4,1 %), das Restrisiko (Kostenüberlauf, Inflation,
Bauzeit-Streckung) trägt der Bund. Vergleichende Analysen sollten
beide Dimensionen nennen — die belastbare Gegenfinanzierung des
Fonds und die staatliche Restrisiko-Übernahme als versteckte
Subvention.

**Originalzitat KENFO 2024:**
> "2024 war für den KENFO erneut ein erfolgreiches Jahr. Mit 9,4% Wertzuwachs
> haben wir unsere Zielrendite in 2024 von 4,1% deutlich übertroffen."

---

## G · NACHFRAGE-TREIBER

### `pkw_bestand_mio`

| | Wert | Quelle |
|---|---|---|
| Default | 49,0 Mio. | KBA 2024 (Kraftfahrt-Bundesamt) |

### `verbrauch_kwh_pro_100km`

| | Wert | Quelle |
|---|---|---|
| Default | 18 kWh/100km | Mix aus aktuellem E-Auto-Bestand |
| ADAC E-Auto-Tests | 14-25 kWh/100km | je Modellklasse |
| Vergleich Verbrenner | 7 L/100km × 9,7 kWh/L = 68 kWh/100km | physikalisch (Heizwert) |

**Wirkungsgrad-Faktor:** 68/18 = 3,8x. Gilt als physikalisch belegbar:
Verbrennungsmotor hat 25-30% Wirkungsgrad, E-Antrieb 85-90%.

### `heizungen_bestand_mio`

| | Wert | Quelle |
|---|---|---|
| Default | 21,5 Mio. | BDEW Heizungs-Statistik 2024 |

### `cop_jahres`

| | Wert | Quelle |
|---|---|---|
| Default | 3,2 | BWP-Branchenstudien (Bundesverband Wärmepumpe) |
| Realer DE-Mittel | 3,0-3,5 | Fraunhofer ISE WP-Monitoring |
| Winter-Worst-Case | 2,0-2,5 | bei -10°C |

### `nutzfahrzeuge_zusatz_twh`

| | Wert | Quelle |
|---|---|---|
| Default | 25 TWh | Nationale Plattform Mobilität (NPM) |

### `industry_h2_twh` und `h2_capacity_target_gw_2035`

| | Wert | Quelle |
|---|---|---|
| Default Industrie-H₂ | 80 TWh Strom-Equivalent | `BMWK-H2-STRATEGIE-2023` (Mittelwert 95-130 TWh inländisch) |
| H₂-Kraftwerks-Ziel 2035 | 20 GW | `BMWK-H2-STRATEGIE-2023` |
| Aufgliederung Stahl-DRI | 30 TWh Strom | Modellannahme nach BMWK |
| Aufgliederung Chemie | 25 TWh Strom | Modellannahme nach BMWK |
| Aufgliederung Restposten | 25 TWh Strom | Restanteil Industrie-H₂ |

**BMWK-H2-STRATEGIE-2023 (Fortschreibung Nationale Wasserstoffstrategie):**
Die Fortschreibung der Nationalen Wasserstoffstrategie (Juli 2023)
formuliert die zentralen quantitativen H₂-Ziele:
- Inländische Erzeugung 2030: 10 GW Elektrolysekapazität
- Inländischer H₂-Bedarf 2030: 95-130 TWh
- H₂-Importe 2030: 50-70 TWh
- H₂-Kraftwerks-Strategie als Backup-Säule, schrittweise bis 2035

Statusbericht 2024 (Dezember 2024) zeigt deutliche
Umsetzungs-Lücken: Stand Mitte 2025 etwa 0,3-0,5 GW installierte
Elektrolyse-Kapazität, also Faktor 20-33× unter dem 2030-Ziel.
Online: https://www.bmwk.de/Redaktion/DE/Publikationen/Energie/fortschreibung-nationale-wasserstoffstrategie.html

---

## H · ZEITACHSE

### KKW-Inbetriebnahme — `KKW_EPR_APPROVAL_YEAR` + sqrt-Streckung

Im aktuellen Modell wird die KKW-Inbetriebnahme aus drei Bausteinen
hergeleitet (siehe
`core/inventories/tech_inventory.py`):

```
IBN = KKW_EPR_APPROVAL_YEAR + min(KKW_EPR_PLAN_YEARS / Realgrad, KKW_EPR_T_CAP)
    = 2029 + min(7 / grad, 21)
```

- `KKW_EPR_APPROVAL_YEAR = 2029`: Politik-Beschluss 2026 + 3 Jahre
  FID-Vorlauf (konservativer FOAK-Mittelwert: HPC ~6 a, OL3 ~1 a,
  Flamanville ~3 a, Vogtle ~5 a). [SRC: UK NAO HPC-2017; TVO
  Pressemitteilungen OL-3; Cour-des-Comptes-Flamanville; Georgia-Power
  Vogtle-Reports.]
- `KKW_EPR_PLAN_YEARS = 7`: Areva-EPR2-Vendor-Spec (Spatenstich →
  IBN).
- `KKW_EPR_T_CAP = 21`: Bei niedrigem Realgrad würde die sqrt-
  Streckung über 21 a hinauslaufen, was gegen die Auslegungs-
  Lebensdauer spricht.

Lager-IBN-Jahre nach Realgrad:

| Lager              | KKW-Realgrad | T_build | IBN |
|---|---:|---:|---:|
| atom_optimistic    | 1,00 |  7 a | **2036** |
| neutral_default    | 0,40 | 17,5 a → 18 | **2046** (Default) |
| bestand_optimistic | 0,40 | 17,5 a → 18 | **2046** |
| ee_optimistic      | 0,20 | 35 a → Cap 21 | **2050** (Cap aktiv) |

SMR-Analoge mit `KKW_SMR_APPROVAL_YEAR = 2029`, `KKW_SMR_PLAN_YEARS = 5`,
`KKW_SMR_T_CAP = 17`: atom_opt 2034, neutral 2042, bestand_opt 2042,
ee_opt 2046.

**Empirische Verankerung — FOAK-Bauzeit Spatenstich → IBN:**

| Projekt | Land | Spatenstich | Real-IBN | Bauzeit |
|---|---|---:|---:|---:|
| Olkiluoto-3 | FI | 2005 | 2023 | 18 a |
| Flamanville-3 | FR | 2007 | 2024 | 17 a |
| Vogtle-3/4 | US | 2013 | 2024 | 11 a (Mittel) |
| Hinkley Point C | UK | 2018 | 2030+ | 12+ a (laufend) |

Modell-Empirie-Korridor: 13–17 a Bauzeit + 3–8 a FID-Vorlauf
→ Gesamt-Frist Politik-Beschluss → IBN 16–22 a. Siehe Chart in
`examples/nuclear_build_time_empirics.png`.

### `nuclear_target_gw_2050`

| | Wert | Quelle |
|---|---|---|
| Default | 24 GW | hypothetische DE-Renaissance |
| Atom-Lager | 30 GW | volle Renaissance, FR-Niveau pro Kopf |
| EE-Lager | 0 GW | kein Neubau |

### `pv_additions_gw_per_year`

| | Wert | Quelle |
|---|---|---|
| Default | 18 GW/a | Niveau 2024, BNetzA-Marktstammdatenregister |
| Brutto-Zubau 2024 | ~17,2 GW | `BNETZA-MASTR-2024` |
| EEG-Ausschreibungs-Ziel 2030 | 22 GW/a | `EEG-2023` |
| Modell verwendet 18 GW/a als realistisches Niveau zwischen aktuellem Zubau und EEG-Ziel. |

**BNETZA-MASTR-2024 (Marktstammdatenregister):**
Das Marktstammdatenregister der Bundesnetzagentur ist die laufend
aktualisierte Primärquelle für installierte PV-, Wind- und
Speicher-Kapazitäten in Deutschland. Stand der Daten variiert
quartalsweise; für PV-Zubau-Statistiken werden monatliche
Pressemitteilungen der BNetzA herangezogen (»PV-Zubau Januar bis
Dezember 2024 ca. 16,2 GW netto / 17,2 GW brutto«). Online:
https://www.marktstammdatenregister.de

---

## I · NETZSTABILITÄT

### `inertia_demand_gw_2030`

| | Wert | Quelle |
|---|---|---|
| Default | 50 GW | DE-TSO-Procurement |
| Aktuell DE 2027 | 30 GW BESS-Inertia | `MODO-2025` |
| Forecast 2037 | 72 GW | `MODO-2025` |
| GFM-BESS Erlös | 8-17 k€/MW/a | `MODO-2025` |

**Originalzitat Modo Energy 2025:**
> "Batteries need a grid-forming inverter to participate, which represents up
> to a 5% increase in CapEx, but receive a revenue uplift of €8-17k/MW/year.
> Germany's inertia requirement translates to roughly 30 GW of batteries in
> 2027... That figure climbs to 72 GW by 2037"

DE-TSOs (50Hertz, Amprion, Tennet, Transnet BW) haben am 22. Januar 2026
mit dem Inertia-Procurement begonnen.

---

## J · WINTER-STRESS-TEST

### `duration_hours` — Dunkelflaute-Dauer

| | Wert | Quelle |
|---|---|---|
| Default | 240 h (10 Tage) | Worst-Case |
| Dezember 2024 real | 11 Tage = 264 h | `BNETZA-VS-2025`, Amprion-Marktbericht |
| 2025 längste | 89 h | 1KOMMA5°-Analyse |
| Schnitt 2016-2025 | 3 pro Jahr | 1KOMMA5°-Analyse |
| Ruhnau & Qvist Worst | 61 Tage | `RUHNAU-2021` (Wettererfahrung 1996) |

**Originalzitat Amprion 2025:**
> "2024 historische Dunkelflaute, die elf Tage lang dauerte – die längste seit 1982"

### `pv_capacity_factor` (in Dunkelflaute)

| | Wert | Quelle |
|---|---|---|
| Default | 3% | typisch dichte Bewölkung |
| DWD-Definition | <10% mind. 48h | `DWA-2024` |

### `cop_winter`

| | Wert | Quelle |
|---|---|---|
| Default | 2,2 | bei -10°C Außentemperatur |
| Bandbreite | 1,8 - 2,8 | je nach Anlagengeneration |

---

## K · BACKUP-DIMENSIONIERUNG

### Backup-Anteil pro Pfad

Die Pfade haben unterschiedliche Backup-Anteile am Erzeugungsmix:

| Pfad | Backup-Anteil | Backup-Quelle |
|---|---|---|
| EE-GAS | 8 % (Default) | fossiles Erdgas |
| EE-H2 | 8 % | grüner Wasserstoff |
| KKW-GAS | bis zu 35 % in Bridge-Phase, dann nur Spitzen | fossiles Bridge-Gas, Spitzen-H₂ |
| KKW-H2 | bis zu 35 % in Bridge-Phase, dann nur Spitzen | Bridge-H₂, Spitzen-H₂ |

Der Default-Backup-Anteil von 8 % in EE-GAS ist abgeleitet aus
der absoluten Backup-Kapazität, die ein vollelektrifiziertes
deutsches Stromsystem 2045 für Dunkelflauten benötigt.

| | Wert | Quelle |
|---|---|---|
| Default Backup-Kapazität 2045 | ~50 GW | abgeleitet aus Spitzenlast-Bedarf |
| BNetzA-Bedarf 2035 | 22-35 GW gesicherte Leistung | `BNETZA-VS-2025` |
| Kraftwerksstrategie 2026 | 12 GW H₂-ready Gas | BMWE-Beschluss April 2026 |

**Methodischer Hinweis:** Die 50 GW sind eine Modell-Annahme für
2045 mit voller Elektrifizierung. Die BNetzA-Zahl (22-35 GW) gilt
für 2035 mit weniger Elektrifizierung. Beide Zahlen sind
konsistent miteinander, weil die Spitzenlast mit der
Sektorkopplung (Wärmepumpen, E-Auto-Laden) wächst.

---

## L · NETZ

### `grid_surcharge` — Netzschicht (Übertragung + Verteilung)

| | Wert | Quelle |
|---|---|---|
| Default | 7,0 ct/kWh | `BNETZA-VS-2025` Mittelwert deutsche Netzentgelte 2025/2026 |
| BNetzA Haushaltskunde 2026 | 7,1 – 7,4 ct/kWh | `BNETZA-VS-2025`; regional unterschiedlich (Spreizung Nord/Süd) |
| EE-Lager | 6,0 ct/kWh | smarte Netzführung, Digitalisierung, regionalisierter Ausbau |
| Atom-Lager | 9,0 ct/kWh | konservativ, hohe Trassenkosten, NEP-2037-Reserveanforderungen |

**Methodischer Hinweis:** Die Netzschicht ist im Modell als
*Pfad-konstant* angesetzt (Default 7,0 ct/kWh in allen sechs
Pfaden) — auf der Annahme, dass die Netz-Investitionsbedürfnisse
ähnlich groß sind, weil alle Pfade einen ähnlichen End-Energie-
Bedarf decken müssen. In der Sensitivitätsanalyse
wird die Netzschicht als unabhängiger Hebel variiert. Die
Bandbreite 6,0-9,0 ct deckt sowohl optimistische Smart-Grid-
Annahmen als auch konservative Trassenkosten-Annahmen ab.

---

## Quellenverzeichnis (vollständig)

| Tag | Vollzitat | URL/DOI | Datum |
|---|---|---|---|
| `ISE-2024` | Fraunhofer ISE: Studie Stromgestehungskosten Erneuerbare Energien Juli 2024 | https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/studies/DE2024_ISE_Studie_Stromgestehungskosten_Erneuerbare_Energien.pdf | Juli 2024 |
| `BNEF-2025-LIB` | BloombergNEF: 2025 Lithium-Ion Battery Price Survey | https://about.bnef.com/insights/clean-transport/lithium-ion-battery-pack-prices-fall-to-108-per-kilowatt-hour-despite-rising-metal-prices-bloombergnef/ | 9. Dez. 2025 |
| `BNEF-2025-ESS` | BloombergNEF: Energy Storage Systems Cost Survey 2025 | https://www.energy-storage.news/battery-storage-system-prices-continue-to-fall-sharply-bnef-and-ember-reports-find/ | 10. Dez. 2025 |
| `BNEF-2025-LCOE` | BloombergNEF: Levelized Cost of Electricity 2026 Report | https://about.bnef.com/insights/clean-energy/battery-storage-costs-hit-record-lows-as-costs-of-other-clean-power-technologies-increased-bloombergnef/ | 18. Feb. 2026 |
| `KENFO-2024` | KENFO: Geschäftsbericht 2024, Pressemitteilung Bilanz-Pressekonferenz | https://www.kenfo.de/en/press-media/press-information-speeches | 10. Juli 2025 |
| `EWI-2024` | EWI Köln: Wasserstoff-Studie | https://www.ewi.uni-koeln.de | 2024 |
| `RUHNAU-2021` | Ruhnau & Qvist: Storage requirements in a 100% renewable electricity system | Hertie School Working Paper | 2021/2022 |
| `EDF-HPC` | EDF: Hinkley Point C Construction Update | https://www.edfenergy.com/energy/nuclear-new-build-projects/hinkley-point-c | laufend |
| `NAO-HPC-2017` | UK National Audit Office: Hinkley Point C — value-for-money audit, finds the deal locked consumers into a risky and expensive project, top-up cost estimate increased from £6 Mrd. (2013) to £30 Mrd. (2017); LeighFisher-Berater hatte einen *potential conflict of interest* bei NNBG-Cost-Estimaten | https://www.nao.org.uk/reports/hinkley-point-c/ | 23. Juni 2017 |
| `COURDESCOMPTES-FLAM` | Cour des Comptes: Flamanville EPR audit | https://www.ccomptes.fr | 2024 |
| `BMWE-2026` | BMWE: Industriestrompreis-Richtlinie | https://www.bmwe.bund.de | April 2026 |
| `MODO-2025` | Modo Energy: Inertia in Europe — Market Analysis | https://modoenergy.com | 11/2025 |
| `KERND-2024` | KernD: Bewertung der Fraunhofer-ISE-Studie | https://kernd.de/wp-content/uploads/2024/08/KernD-Bewertung-Fraunhofer-ISE-Stromgestehungskosten-08-2024-1.pdf | 8/2024 |
| `AGORA-2045` | Agora Energiewende: Klimaneutrales Deutschland 2045 | https://www.agora-energiewende.de | laufend |
| `BNETZA-VS-2025` | Bundesnetzagentur: Versorgungssicherheitsbericht 2025 | https://www.bundesnetzagentur.de | 2025 |
| `DWA-2024` | Deutscher Wetterdienst: Dunkelflauten-Analyse | https://www.dwd.de | laufend |

---
| `KBA-2024` | Kraftfahrt-Bundesamt: Bestand Personenkraftwagen 2024 | https://www.kba.de/DE/Statistik/Fahrzeuge/Bestand/bestand_node.html | 1.1.2024 |
| `ADAC-2024` | ADAC: Reichweite und Stromverbrauch von Elektroautos im Test | https://www.adac.de/rund-ums-fahrzeug/elektromobilitaet/tests/stromverbrauch-elektroautos-adac-test/ | 2024 |
| `NPM-2023` | Nationale Plattform Zukunft der Mobilität: Stromnachfrage 2030/2045 | https://www.plattform-zukunft-mobilitaet.de | 2023 |
| `BDEW-2024` | BDEW: Wie heizt Deutschland 2023/24 — Heizungsbestand-Statistik | https://www.bdew.de/service/daten-und-grafiken/wie-heizt-deutschland/ | 2024 |
| `BWP-2024` | Bundesverband Wärmepumpe: Branchenstudie und Effizienzdaten | https://www.waermepumpe.de | 2024 |
| `AGEB-2024` | AG Energiebilanzen: Energieverbrauch in Deutschland | https://ag-energiebilanzen.de | 2024 |
| `IEA-2024` | International Energy Agency: Global Hydrogen Review 2024 | https://www.iea.org/reports/global-hydrogen-review-2024 | 2024 |
| `VDE-2023` | VDE: Studie zu H2-ready-Gaskraftwerken | https://www.vde.com | 2023 |
| `BMWi-2024` | BMWi/BMWE: Stromsteuer und Konzessionsabgaben | https://www.bmwk.de | 2024 |
| `BNetzA-2024` | Bundesnetzagentur: Netzentgelt-Statistik | https://www.bundesnetzagentur.de | 2024 |
| `BUND-2024` | Bund für Umwelt und Naturschutz: Studie Endlagerkosten | https://www.bund.net | 2024 |
| `BMWi-Wasserkraft` | BMWE: Wasserkraftanlagen in Deutschland | https://www.bmwk.de | laufend |
| `EU-ETS-2026` | EU-Kommission: ETS-Preisprognosen 2030 | https://climate.ec.europa.eu | 2026 |
| `EU-Kommission-2024` | EU-Kommission Stromsysteme 2050 / Konsens-Forecasts | https://commission.europa.eu | 2024 |
| `BNETZA-MASTR-2024` | Bundesnetzagentur: Marktstammdatenregister, PV-Zubau-Statistiken 2024 | https://www.marktstammdatenregister.de | 2024-2025 |
| `BMWK-H2-STRATEGIE-2023` | BMWK: Fortschreibung der Nationalen Wasserstoffstrategie + Statusbericht 2024 | https://www.bmwk.de/Redaktion/DE/Publikationen/Energie/fortschreibung-nationale-wasserstoffstrategie.html | Juli 2023 / Dez. 2024 |

### Klima- und Klimakosten-Studien

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `IPCC-AR6` | IPCC Sixth Assessment Report (AR6), Working Group I-III | https://www.ipcc.ch/assessment-report/ar6/ | 2021-2023 |
| `EDGAR-2024` | EDGAR Emissions Database for Global Atmospheric Research, JRC | https://edgar.jrc.ec.europa.eu | 2024 |
| `BDI-PROGNOS-2021` | BDI/Prognos: Klimapfade 2.0 — Wege zur Klimaneutralität 2045 | https://bdi.eu/publikation/news/klimapfade-2-0/ | Okt. 2021 |
| `RAHMSTORF-PIK` | Stefan Rahmstorf, Potsdam-Institut für Klimafolgenforschung | https://www.pik-potsdam.de/members/stefan | laufend |

### Frankreich EPR-Programm und Bauzeit-Belege

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `MACRON-EPR-2022` | Élysée: »Renaissance der Kernenergie« mit 6 EPR2-Reaktoren | https://www.elysee.fr | Februar 2022 |
| `EDF-PENLY-2025` | EDF: Penly EPR2 — Verschiebung auf 2038 | https://www.edf.fr | März 2025 |
| `SENAT-FR-EPR2` | Senat (FR): Gesetz für 14 EPR2-Reaktoren bis 2050 | https://www.senat.fr | Juli 2025 |
| `IWR-FR-2025` | IWR: Frankreichs Atomoffensive — erste Inbetriebnahme nicht vor 2038 | https://www.iwr.de | März 2025 |

### Uran und Lieferketten-Resilienz

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `EURATOM-2024` | Euratom Supply Agency: Annual Report 2024 (Uran-Importe EU) | https://euratom-supply.ec.europa.eu | August 2024 |
| `URANATLAS-2026` | Uranatlas 2026: NFFF, BUND, Rosa-Luxemburg-Stiftung u.a. | https://www.rosalux.de/dossiers/uranatlas | März 2026 |
| `WNA-2024` | World Nuclear Association: Uranium Production Figures | https://world-nuclear.org | 2024 |
| `BTAG-WD-URAN-2024` | Wissenschaftlicher Dienst Bundestag: Globaler Markt für Uran | https://www.bundestag.de/wissenschaftliche-dienste | Oktober 2024 |
| `OECD-NEA-2019` | OECD-NEA: *The Costs of Decarbonisation: System Costs with High Shares of Nuclear and Renewables*, NEA No. 7299, Paris 2019. Methoden-Referenz für System-Kosten in Mischsystemen mit hoher VRE-Penetration; verwendet in ANHANG_C als Beleg für die Aussage, dass dispatchable Kraftwerke unter ihre technischen Maxima fahren, sobald VRE-Anteile hoch sind. Class A — peer-reviewt, OECD-Publikation. | https://www.oecd-nea.org/jcms/pl_15000/the-costs-of-decarbonisation-system-costs-with-high-shares-of-nuclear-and-renewables | 2019 |
| `OECD-NEA-2024` | OECD-NEA / IAEA: Uranium 2024 — Resources, Production and Demand | https://www.oecd-nea.org | 2025 |

### Industrie-Kommunikations-Belege

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `STOECKER-2024` | Christian Stöcker: Männer, die die Welt verbrennen, S. Fischer Verlag | ISBN 978-3-10-397627-7 | 2024 |
| `EXXON-MEMOS-1977` | James Black (Exxon): Internal climate research memo | Inside Climate News | 1977/2015 |
| `ICN-EXXON` | Inside Climate News: Exxon — The Road Not Taken | https://insideclimatenews.org/project/exxon-the-road-not-taken | 2015 |
| `WVA-EPA-2022` | US Supreme Court: West Virginia vs. EPA | https://www.supremecourt.gov | Juni 2022 |
| `LOBBYCONTROL-2024` | LobbyControl: Energie-Lobbyismus in Deutschland | https://www.lobbycontrol.de | 2024 |
| `BTAG-LOBBYREGISTER` | Bundestag Lobbyregister | https://www.lobbyregister.bundestag.de | laufend |
| `KENFO-INVESTMENTS` | KENFO: Anlagestrategie und Portfolio-Berichte | https://www.kenfo.de | laufend |

### Politik und Gesetzgebung

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `KSG-2021` | Klimaschutzgesetz (KSG), Bundesgesetzblatt | https://www.gesetze-im-internet.de/ksg/ | 2021/2024 |
| `BVG-KLIMA-2021` | Bundesverfassungsgericht: Klimaschluss vom 24.3.2021 (1 BvR 2656/18) | https://www.bundesverfassungsgericht.de | März 2021 |
| `KRAFTW-STRATEGIE-2026` | BMWE: Kraftwerksstrategie 2026 | https://www.bmwk.de | Januar 2026 |
| `EEG-2023` | Erneuerbare-Energien-Gesetz, aktuelle Fassung | https://www.gesetze-im-internet.de/eeg_2023/ | 2023/2025 |
| `GEG-2024` | Gebäudeenergiegesetz | https://www.gesetze-im-internet.de/geg/ | 2024 |
| `EU-TAXONOMIE-2022` | EU-Taxonomieverordnung — Ergänzungsverordnung Atomkraft/Gas | https://eur-lex.europa.eu | März 2022 |

### Ergänzende Quellen-Referenzen

Quellen, die ergänzend zur Triangulation geführt werden. Wo sie
im Modell aktiv konsumiert werden, ist die Stelle in
`tech_inventory.py` / `fuel_inventory.py` / `path_model.py` markiert.

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `IEEFA-2024-SMR` | Institute for Energy Economics and Financial Analysis (IEEFA): SMR-Report — *Eyes Wide Shut: Investors should be wary of new nuclear reactors*. Referenz für SMR-CAPEX-Default (~11.500 €/kW Mitte Vendor-Plan/FOAK), gegen die Vendor-Versprechen von ~6.000 €/kW. | https://ieefa.org | 2024 |
| `NEA-OECD-SMR-DASHBOARD` | OECD Nuclear Energy Agency: Small Modular Reactor (SMR) Dashboard — Übersicht aller weltweit angekündigten und in Bau befindlichen SMR-Projekte. Class A — OECD-Datenbank, laufend aktualisiert. | https://www.oecd-nea.org | laufend |
| `MIT-SMR-CEEPR` | MIT Center for Energy and Environmental Policy Research (CEEPR): Working Papers zu SMR-Ökonomie und N-th-of-a-kind-Lernkurven. Referenz für die NOAK-Lernkurven-Diskussion. | https://ceepr.mit.edu | 2018 ff. |
| `DENA-NETZSTUDIE-III` | Deutsche Energie-Agentur: Netzstudie III — Integrierte Energiewende und Netzausbau-Bedarf bis 2045. Quellen-Triangulation für den Netz-EE-Aufschlag (~2,0 ct/kWh) neben NEP-2037/2045 V2025. Class B. | https://www.dena.de | 2024 ff. |
| `BNETZA-SES-2023` | Bundesnetzagentur: Smart Energy Showcases (SES) 2023 — Praxisberichte zu DSO-Ebene-Integration und Verteilnetzausbau. | https://www.bundesnetzagentur.de | 2023 |
| `PIK-ARIADNE-ETS-2024` | PIK / Ariadne-Kopernikus-Projekt: ETS-Trajektorie 2030-2050 — Modellierte CO₂-Preis-Pfade unter EU-Net-Zero-2050-Ziel. Referenz für CO₂-Preis-Welt-Konsistenz (neutral 130 EUR/t, lager-spezifisch 80-160). Class A. | https://ariadneprojekt.de | 2023-2024 |
| `BNETZA-MON-Q4-2025` | Bundesnetzagentur: Monitoring-Bericht Strom Q4-2025 — NEP-Realisierungsgrad-Empirie und Trassenausbau-Status. Quelle für den empirischen NEP-Realisierungsgrad-Anker im neutral_default-Lager (~0,65); die effektive Realisierung läuft im Modell durch den Min-Operator mit dem Lager-Welt-Belief. Class A. | https://www.bundesnetzagentur.de | Q4 2025 |
| `WNA-2025` | World Nuclear Association: Annual Report 2025 — Globale KKW-Bauzeit-Empirie und Realisierungsgrad-Statistiken. Quelle für den KKW-Default-Realisierungsgrad (0,40) und die Bauzeit-Bandbreite 13-17 a. Class A. | https://world-nuclear.org | 2025 |
| `ISE` | Fraunhofer ISE: Stromgestehungskosten Erneuerbare Energien — Kurz-Referenz für `ISE-2024`. Class A. | https://www.ise.fraunhofer.de | 2024 |
| `BSH` | Bundesamt für Seeschifffahrt und Hydrographie: Flächenentwicklungsplan Offshore-Wind. Class A. | https://www.bsh.de | laufend |
| `FfE` | Forschungsstelle für Energiewirtschaft e. V.: Discussion Paper Wind-Flächendichte — Mittelwert 23-29 MW/km² für Wind-onshore. Class A. | https://www.ffe.de | 2023 |
| `UBA-2024` | Umweltbundesamt: Tagebau-Bilanz und Folgenutzung in Deutschland 2024. Class A. | https://www.umweltbundesamt.de | 2024 |
| `STATISTIK-KOHLENWIRTSCHAFT` | Statistik der Kohlenwirtschaft e. V.: Tagebau-Jahresbericht — Historische Tagebau-Flächen 1885-2024 (Braunkohle), 179.402 ha kumuliert. Class A. | https://kohlenstatistik.de | jährlich |
| `KohleAusG` | Kohleausstiegsgesetz (KVBG): Bundesgesetz zur Beendigung der Kohleverstromung 2020 — Phaseout-Pfad bis 2038, Rekultivierungs-Verpflichtungen. Class A. | https://www.gesetze-im-internet.de/kvbg/ | 2020 |
| `EDF-EPR-Specifications` | EDF / Framatome: EPR2-Reaktor-Spezifikationen — Netto-Leistung 1.500-1.670 MW pro Block, Site-Größe ~30 ha pro Doppelblock. Class A. | https://www.edf.fr | laufend |
| `MODEL-DEFAULT` | Modell-Default: Verweis auf Konstanten und Trajektorien im Modell-Kern (`core/path_model.py`, `core/path_inputs.py`). Kein externer Beleg, sondern interner Kreuzverweis auf eine an anderer Stelle dokumentierte Modell-Setzung. | (intern) | laufend |

### Lager-Bücher und Positions-Belege

| Tag | Vollbeleg | URL/ISBN | Datum |
|---|---|---|---|
| `MEYER-2024` | Tim Meyer: Strom — Reportage zur Energiewende | ISBN 978-3-7766-2877-7 | 2024 |
| `SINN-ENW` | Hans-Werner Sinn: Energiewende ins Nichts | YouTube/Vorträge LMU | laufend |
| `QUASCHNING-2025` | Volker Quaschning: Energierevolution Jetzt! | ISBN 978-3-446-47763-1 | 2025 |
| `KEMFERT-2023` | Claudia Kemfert: Schockwellen — Letzte Chance Energiewende | ISBN 978-3-95890-579-5 | 2023 |
| `GATES-2021` | Bill Gates: How to Avoid a Climate Disaster, Penguin Random House | ISBN 978-0-385-54613-3 | 2021 |
| `LEVESON-2011` | Nancy Leveson: Engineering a Safer World, MIT Press | ISBN 978-0-262-01662-9 | 2011 |

### Fusion, KI, Disruption

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `LLNL-NIF-2022` | Lawrence Livermore National Laboratory: Net energy gain announcement | https://www.llnl.gov/news/national-ignition-facility | Dez. 2022 |
| `ITER-PROJECT` | ITER: Project status and milestones | https://www.iter.org | laufend |
| `CFS-COMMONWEALTH` | Commonwealth Fusion Systems: SPARC and ARC | https://cfs.energy | laufend |
| `HELION-MS-2023` | Microsoft-Helion Power Purchase Agreement | https://www.helionenergy.com | Mai 2023 |
| `IEA-ELECTRICITY-2024` | IEA: Electricity 2024 — Datacenter and AI demand projections | https://www.iea.org/reports/electricity-2024 | 2024 |

### Solar-Industrie historisch (Resilienz-Argument)

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `PVMAG-SOLAR-2023` | PV Magazine: Totales Desaster — Solar-Zölle und Niedergang | https://www.pv-magazine.de/2023/09/18/totales-desaster-wie-solar-zoelle-zehntausende-arbeitsplaetze-und-existenzen-in-deutschland-vernichteten/ | Sept. 2023 |
| `IGM-SOLAR-2022` | IG Metall: Solarindustrie — Auferstehen aus Ruinen | https://www.igmetall.de | 2022 |
| `MEYERBURGER-2021` | Meyer Burger: Wiederaufnahme PV-Produktion in Thalheim | https://www.meyerburger.com | 2021 |
| `SMA-2024` | SMA Solar Technology: Geschäftsbericht 2024 | https://www.sma.de | 2024 |

### Strompreise und Netzentgelte

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `BDEW-STROMPREISE` | BDEW: Strompreisanalyse 2024 (Haushalt, Industrie) | https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/ | 2024 |
| `BDEW-STROMPREISE-2025` | BDEW: Strompreisanalyse Oktober 2025 — Haushalt 39,7 ct/kWh brutto (Beschaffung+Vertrieb 16,1 / Netz 10,9 / Steuern+Abgaben+Umlagen 12,7), Industrie Mittelverbrauch 15,9 ct/kWh netto, Großindustrie 14,4 ct/kWh netto | https://www.bdew.de/media/documents/BDEW_Strompreisanalyse_102025.pdf | Oktober 2025 |
| `BDEW-STROMPREISE-2026` | BDEW: Strompreisanalyse Mai 2026 — Haushalt 37,0 ct/kWh brutto (Beschaffung+Vertrieb 15,2 / Netz 9,3 / Steuern+Abgaben+Umlagen 12,6 inkl. MwSt-Anteil), Industrie GHD ~23,5 ct/kWh netto, kleine bis mittlere 16,7, mittelgroße 15,9, große 14,4. Industrie-Komponenten-Aufschlüsselung in `consumers.py::BDEW_2026_INDUSTRY`: Beschaffung+Vertrieb 9-13 ct, Netzentgelte 3,7-7,5 ct (mit §19-StromNEV-Reduktion bei großen Verbrauchern), TCL 1,5-3,2 ct (mit StromStG §9b und BesAR-Privilegien). Basis: 3.500 kWh/Jahr Haushalt; Mittelspannung Industrie, gewichteter Durchschnitt aller Tarifprodukte und Grundversorgungstarife inkl. Neukundentarife | https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/ | Mai 2026 |
| `BNETZA-INDUSTRIE-2024` | Bundesnetzagentur: Monitoringbericht 2024 — Industriestrompreise nach Verbrauchsklassen, Mittelspannung. Verwendet zur Komponenten-Aufschlüsselung von `BDEW_2026_INDUSTRY` (Beschaffung/Netz/TCL pro GHD/KMI/MG/GR-Klasse). Methodischer Vorbehalt: Industriepreise sind individualvertraglich und durch BesAR-Befreiungen heterogen — die im Modell ausgewiesenen Komponenten sind konsolidierte Mittelwerte, keine vertraglichen Einzelwerte | https://www.bundesnetzagentur.de/SharedDocs/Mediathek/Monitoringberichte/ | 2024 |
| `STROMSTG-9B-2026` | Stromsteuergesetz §9b Abs. 1: »Nach Abs. 2 Nr. 4 des Stromsteuergesetzes wird die Stromsteuer für das produzierende Gewerbe und die Land- und Forstwirtschaft auf 0,05 Cent je Kilowattstunde reduziert (statt regulär 2,05 Cent).« Verwendet im Industrie-Privilegien-Block `INDUSTRIE_PRIVILEGIEN_2026`. Ohne dieses Privileg liegt der Industrie-Strompreis ~2 ct/kWh höher. | https://www.gesetze-im-internet.de/stromstg/__9b.html | aktuell 2026 |
| `STROMNEV-19-2026` | StromNEV §19 Abs. 2: individuelle Netzentgelte für atypische und intensive Letztverbraucher. Reduktion typisch 30-60 % gegenüber Standard-Netzentgelten, abhängig von Lastprofil und Vollbenutzungsstunden. Verwendet im Industrie-Privilegien-Block. | https://www.gesetze-im-internet.de/stromnev/__19.html | aktuell 2026 |
| `EEG-BESAR-2026` | EEG §63 ff. (Besondere Ausgleichsregelung BesAR): Begrenzung der Umlagen (KWKG, Offshore) für stromkostenintensive Unternehmen mit Stromkostenintensität ≥ 14 % bzw. ≥ 17 % der Bruttowertschöpfung. Reduktion bis zu ~80 %. Verwendet im Industrie-Privilegien-Block. | https://www.bafa.de/DE/Energie/Energieeffizienz/Besondere_Ausgleichsregelung/ | aktuell 2026 |
| `DESTATIS-MZ-2024` | Statistisches Bundesamt: Mikrozensus 2024 — Haushalte und Familien. 41,0 Millionen private Hauptwohnsitzhaushalte in Deutschland (Pressemitteilung 21. Juli 2025); mittlere Haushaltsgröße 2,0 Personen | https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Haushalte-Familien/_inhalt.html | Juli 2025 |
| `DESTATIS-INFLATION` | Destatis: Verbraucherpreisindex und Inflationsrate | https://www.destatis.de | laufend |
| `BAFA-STROMPREIS-KOMP` | BAFA: Strompreiskompensation für stromintensive Industrie | https://www.bafa.de | laufend |
| `NETZENT-ZUSCHUSS-2026` | Bundesregierung: Bundeszuschuss zu Übertragungsnetzentgelten 6,5 Mrd. €, Gesetz in Kraft 12.12.2025 | https://www.bundesregierung.de/breg-de/aktuelles/niedrigere-netzentgelte-2382396 | Dezember 2025 |
| `VZBV-NETZENT-2026` | Verbraucherzentrale Bundesverband: Wirkungsanalyse Netzentgelt-Zuschuss 2026 (regionale Spreizung 18-100 €/Haushalt, Mittelwert ~56 €) | https://www.vzbv.de | April 2026 |
| `BNETZA-AGNES-2026` | Bundesnetzagentur: Festlegungsverfahren AgNes (Allgemeine Netzentgeltsystematik Strom), NEST-Prozess | https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Netzentgelte/ | laufend 2025-2027 |
| `BNETZA-KANU-2024` | Bundesnetzagentur: KANU 2.0 — Kapitalkosten-Anpassungs-Festlegung Gasnetze, vorgezogene Abschreibungen mit Blick auf 2045 | https://www.bundesnetzagentur.de | 2024 |
| `BNETZA-EE-NETZKOSTEN-2025` | Bundesnetzagentur Festlegung BK8-24-001-A: bundesweite Verteilung der Mehrkosten aus EE-Integration ab 2025 | https://www.bundesnetzagentur.de | 2024-2025 |

### Wasserstoff-Hochlauf

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `BNETZA-H2-KERNNETZ-2024` | Bundesnetzagentur: Wasserstoff-Kernnetz, Genehmigung 22.10.2024 — 9.040 km Leitung, 18,9 Mrd. € Investitionsvolumen, Zieljahr 2032 | https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Wasserstoff/Kernnetz/ | Oktober 2024 |
| `BNETZA-H2-VERSTROMUNG-VERSCHOBEN` | Bundesnetzagentur: Im Zuge der Kraftwerksstrategie wurden die Annahmen zur Wasserstoffverstromung deutlich reduziert und auf einen Zeitraum nach 2032 verschoben (Begründung Wasserstoff-Kernnetz-Modellierung) | https://www.bundesnetzagentur.de | 2024 |
| `H2-KAPRES-2026` | Wasserstoff-Kernnetzbetreiber (OGE, Gasunie, GASCADE, Thyssengas, GTG Nord u.a.): Eckpunkte zur Kapazitätsreservierung ab 2026, veröffentlicht 16. Oktober 2025 | https://oge.net/de/pressemitteilungen/2025/wasserstoff-kernnetzbetreiber-veroeffentlichen-grundlagen-zur-kapazitaetsreservierung-ab-2026 | Oktober 2025 |
| `BNETZA-WAKANDA-WASABI` | Bundesnetzagentur: Festlegungsverfahren WaKandA (Kapazitäten/Netzzugang) und WasABi (Ausgleich/Bilanzierung) für H₂-Kernnetz, geplanter Abschluss vor Reservierungs-Start 2026 | https://www.bundesnetzagentur.de | 2025-2026 |
| `H2-BESCHLG-2025` | Bundeskabinett: Wasserstoffbeschleunigungsgesetz (Entwurf Oktober 2025, Bundestagsbehandlung November 2025) — Vereinfachung von Genehmigungsverfahren | https://www.bmwe.de | Oktober 2025 |
| `DIW-H2-2026` | Wolf-Peter Schill (DIW): Diagnose 2026 — H₂-Hochlauf »schleppend in praktisch allen Bereichen« (Elektrolyse, Nachfrage, Speicher, Netz, Importe) | dpa-Meldung Januar 2026 | Januar 2026 |
| `BDEW-H2-2026-ANDREAE` | Kerstin Andreae, Vorsitzende BDEW: Kritik an Kürzungen der Wasserstoffförderung im Haushaltsentwurf 2026 als »völlig falsches Signal« | BDEW-Pressemeldung | Januar 2026 |
| `THYSSENKRUPP-H2-DUISBURG` | Thyssenkrupp Steel: Direktreduktionsanlage Duisburg, Vollbetrieb-Wasserstoffbedarf 143.000 t/Jahr (~390 t/Tag) | https://www.thyssenkrupp-steel.com | 2024-2026 |

### Dunkelflaute und Versorgungssicherheit

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `AMPRION-2024-DEZ` | Amprion: Marktbericht Dezember 2024 (11-tägige Dunkelflaute) | https://www.amprion.net | Januar 2025 |
| `ENTSO-E` | ENTSO-E: Transparency Platform (Strom-Echtzeit-Daten) | https://transparency.entsoe.eu | laufend |
| `DWD-DUNKELFLAUTEN` | DWD: Witterungsanalysen 2024 — kalte Dunkelflauten | https://www.dwd.de | 2024-2025 |

### NIMBY-Konflikte und Reformhebel

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `UBA-10H-2021` | Umweltbundesamt: Forschungsvorhaben zur Auswirkung der 10H-Abstandsregelung in Bayern (85-97% Flächenreduktion) | https://www.umweltbundesamt.de | September 2021 |
| `BAYBO-10H-2014` | Bayerische Bauordnung Art. 82 (»10H-Regel«), eingeführt 2014, Lockerung 16.11.2022 | https://www.gesetze-bayern.de | 2014/2022 |
| `IKND-EMBER-2023` | IKND und Ember: Auswirkungen der 10H-Regel nach der Lockerung 2022 (max. 5,2 GW vs. 15+ GW) | https://www.iknd.de | Dezember 2023 |
| `BAY-LANDTAG-WIND` | Bayerischer Landtag: Antworten zu Wind-Genehmigungsanträgen 2013-2024 (400 → 3) | https://www.bayern.landtag.de | 2022-2024 |
| `IWR-NETZAUSBAU-2025` | IWR: Genehmigung der drei Nord-Süd-Stromverbindungen (5 Jahre Verzögerung, 6,5 Mrd. Euro Bundeszuschuss) | https://www.iwr.de/news/stromleitungen-bundesnetzagentur-genehmigt-letzte-der-drei-grossen-nord-sued-stromverbindungen-vollstaendig-news39403 | November 2025 |
| `BMWi-ERDKABEL-2015` | BMWi: Schätzung Mehrkosten Erdkabel-Vorrang (3-8 Mrd. Euro) | https://www.bmwk.de | 2015 |
| `SUEDLINK-WIKI` | SuedLink: Trassenverlauf, Bauzeit, Inbetriebnahme 2028 statt 2022 | https://de.wikipedia.org/wiki/Suedlink | laufend |
| `BNETZA-NEP` | Bundesnetzagentur: Netzentwicklungsplan Strom 2037/2045 | https://www.netzausbau.de | 2024 |
| `BGE-ENDLAGER-2022` | Bundesgesellschaft für Endlagerung (BGE): Diskussionspapier zum Projektablauf — Standortentscheidung 2046-2068 | https://www.bge.de | Oktober 2022 |
| `BASE-ENDLAGER-2022` | Bundesamt für die Sicherheit der nuklearen Entsorgung (BASE): Stellungnahme zum BGE-Zeitplan | https://www.base.bund.de/shareddocs/kurzmeldungen/de/2022/zeitplan-endlagersuche.html | November 2022 |
| `STANDAG-2017` | Standortauswahlgesetz (StandAG), Bundesgesetzblatt 2017 | https://www.gesetze-im-internet.de/standag_2017/ | 2017 |
| `BGE-OPT-2025` | BGE: Diskussionsvorschlag zur zeitlichen Optimierung des Standortauswahlverfahrens | https://www.bge.de | Januar 2025 |
| `GEG-NOVELLE-2024` | Gebäudeenergiegesetz 2024 (»Heizungsgesetz«), GBl. I 2023 S. 1184 | https://www.gesetze-im-internet.de/geg/ | 1.1.2024 |
| `GMG-ECKPUNKTE-2026` | Bundesregierung: Eckpunkte für Gebäudemodernisierungsgesetz (GMG), Ablösung GEG zum 1.7.2026 | https://www.bmwsb.bund.de | Februar 2026 |
| `BVG-GEG-STOPP-2023` | Bundesverfassungsgericht: einstweilige Anordnung Sommer 2023 (GEG-Verabschiedung gestoppt) | https://www.bundesverfassungsgericht.de | Juli 2023 |
| `WPG-2023` | Wärmeplanungsgesetz vom 20.12.2023 (Pflicht zur kommunalen Wärmeplanung bis 2026/2028) | https://www.gesetze-im-internet.de/wpg/ | Januar 2024 |
| `WIND-LAND-2022` | Wind-an-Land-Gesetz vom 20.7.2022 (BGBl. I S. 1353), 2-Prozent-Flächenziel | https://www.gesetze-im-internet.de | Juli 2022 |

### EU-Politik

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `EU-NZIA-2024` | EU Net-Zero Industry Act, Verordnung (EU) 2024/1735 vom 13. Juni 2024 | https://eur-lex.europa.eu/eli/reg/2024/1735 | Juni 2024 |
| `EU-CRMA-2024` | EU Critical Raw Materials Act, Verordnung (EU) 2024/1252 vom 11. April 2024 | https://eur-lex.europa.eu/eli/reg/2024/1252 | April 2024 |
| `EU-ETS-DIR` | EU Emissions Trading System (EU-ETS), Richtlinie 2003/87/EG idF 2023 | https://climate.ec.europa.eu/eu-action/eu-emissions-trading-system-eu-ets_en | laufend |
| `EU-COMM-FITFOR55` | EU-Kommission: Fit for 55 Package, Strategiebericht | https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/european-green-deal/delivering-european-green-deal_en | 2021-2024 |
| `KVBG` | Kohleverstromungsbeendigungsgesetz vom 8. August 2020 (BGBl. I S. 1818); § 2 Abs. 2 legt Kohleausstieg spätestens 31.12.2038 fest | https://www.gesetze-im-internet.de/kvbg/ | August 2020 |

### CO₂-Kosten und Klimakosten-Studien

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `AGORA-MEHRKOSTEN-2021` | Agora Energiewende: Klimaneutrales DE 2045 — 940 Mrd. Euro Mehrkosten als Vergleichs-Größe zur Investitions-Bandbreite | https://www.agora-energiewende.de/veroeffentlichungen/klimaneutrales-deutschland-2045 | 2021 |
| `IPCC-AR6-WG3` | IPCC AR6 Working Group III: Mitigation of Climate Change | https://www.ipcc.ch/report/ar6/wg3/ | 2022 |

### Klimadynamik und Großwetterlagen

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `HEREON-2024` | Helmholtz-Zentrum Geesthacht (Hereon) und Max-Planck-Institut für Meteorologie: *Klimawandel und Großwetterlagen über Mitteleuropa — Trends 1980-2023 und Projektionen 2050*. Tendenz: leichte Zunahme winterlicher Hochdrucklagen über Mitteleuropa (+5-10 % Häufigkeit) bei gleichzeitiger Verlängerung einzelner Episoden um 10-20 %. Verwendet zur Begründung der Stresstest-Klima-Robustheit (Tiefdruckpause-Annahme). | https://www.hereon.de | 2024 |

### Lieferketten und Industrie-Kapazität

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `WOODMAC-TRAFO-2024` | Wood Mackenzie: *Power Transformer Supply Outlook*, 2024. Lieferzeiten 100-120 Wochen für große Leistungstransformatoren, Preissteigerung 60-80 % seit 2021. Verwendet im Stresstest (Trafo-Engpass-Argument) und in der Lieferketten-Resilienz-Diskussion. | https://www.woodmac.com/ | 2024 |
| `WOODMAC-FUSION-2025` | Wood Mackenzie / Prakash Sharma: Branchenanalyse zur kommerziellen Fusions-Reife. Zitiert in Fortune, Oktober 2025. Verwendet zur Einordnung der Fusions-Zeitlinie. | https://www.woodmac.com/ | 2025 |
| `ENERGY-CHARTS-ISE` | Fraunhofer ISE / Prof. Bruno Burger: *Energy-Charts* — interaktive Datenplattform zur Stromerzeugung in Deutschland und 42 europäischen Ländern, online seit 2014. Bereitet Stundendaten zu Erzeugung, Last, Börsenpreisen, Emissionen und Klimadaten aus mehreren neutralen Quellen auf (ENTSO-E, BNetzA, AGEB, DWD). Verwendet als historische Faktendatenbank für Erzeugungsmix-Validierung, Stresstest-Kalibrierung gegen Dezember 2024, und als Cross-Check zu BDEW-Daten. Class A — eine der umfangreichsten öffentlich verfügbaren Energiedatenplattformen Europas. | https://www.energy-charts.info | 2014-laufend |
| `BATTERY-CHARTS-RWTH` | RWTH Aachen ISEA / PGS, Figgener et al.: *Battery Charts* — monatliche Auswertung des deutschen Batteriespeicher-Bestands aus dem Marktstammdatenregister der Bundesnetzagentur, gegliedert nach Heim- (≤30 kWh), Gewerbe- (30-1.000 kWh) und Großspeichern. Verwendet zur Validierung der Speicher-Bestandsdaten 2024-2026 und als empirischer Anker für die im Modell unterstellte Lernkurve. Class A — primäre öffentliche Marktbeobachtung mit institutionellem Backing (RWTH Aachen, ISEA). | https://battery-charts.de | 2022-laufend |
| `FIGGENER-2022` | Figgener, J. et al.: *The development of battery storage systems in Germany — A market review*, RWTH Aachen ISEA, arXiv:2203.06762 (Update 2023). Peer-reviewte Methoden-Referenz für die deutsche Batteriespeicher-Marktentwicklung 2013-2023. Quelle für Lernkurven-Annahmen Lithium-Ionen und für die Mix-Annahme Heim-/Gewerbe-/Großspeicher im Modell. Class A — peer-reviewed, akademisch. | https://arxiv.org/abs/2203.06762 | 2022-2023 |

### BESTAND-Pfad (Bestands-Lager-Pure-Play)

Quellen für den BESTAND-Pfad (aktive fossile Kontinuität) und den
Versorgungs-Schwelle-Lager-Parameter.

| Tag | Vollbeleg | URL | Datum |
|---|---|---|---|
| `BDI-2024` | Bundesverband der Deutschen Industrie: *Energiewende — Realismus und Wettbewerbsfähigkeit*, Positionspapier 2024. Bestands-Lager-Position zur Erdgas-Brücke und H2-ready-Skepsis; Begründung der Erdgas-Anteils-Annahmen (~45-50 % im BESTAND-Pfad), Kapazitäts-Trajektorie (Bestand 35 GW + Neubau 15 GW = 50 GW bis 2055), und gedämpfte EE-Ausbau-Annahme. Class C/D — Wirtschaftsverband-Lobby, dokumentiert das Lager-Programm aus erster Hand. | https://bdi.eu | 2024 |
| `ERAA` | ENTSO-E: *European Resource Adequacy Assessment* (jährlich). Methodischer Standard für die LOLE-Bewertung (Loss of Load Expectation) gemäß § 51 EnWG; Grundlage der "neutralen Mitte"-Position für die Versorgungs-Schwelle (10-15 GW akzeptables Restdefizit im Stresstest mit DSM-Reserve). | https://www.entsoe.eu/outlooks/eraa/ | jährlich seit 2021 |
| `EIA-USA-2025` | U.S. Energy Information Administration: *Electricity in the U.S.* — annual energy outlook reference data. Beleg für USA-Strommix als BESTAND-Realitätsanker (Erdgas 43 %, EE 24-25 %, Atom 18 %, Kohle 15 %); zeigt, dass das Bestands-Lager-Programm empirisch existiert, ohne 1:1-Übertragbarkeit zu unterstellen (DE: 5 % Erdgas-Eigenproduktion vs. USA 95 %). | https://www.eia.gov/energyexplained/electricity/electricity-in-the-us.php | 2025 |
| `AGORA-STRANDED-2024` | Agora Energiewende: *Stranded-Assets-Risiken in der Bridge-Phase der Energiewende*. Beleg für die Caveat-Begründung gegen BESTAND: Erdgas-Neubau ohne H2-ready wird bei späterer EU-ETS-Eskalation oder KSchG-Verschärfung ökonomisch entwertet. | https://www.agora-energiewende.de | 2024 |
| `TECH-FOR-FUTURE-2025` | Tech for Future: *Backup-Kraftwerke: Wasserstoff vs Carbon Capture vs Kernkraft*, Mai 2025. Beleg für KKW-Lager-Position "KKW + Erdgas mit CCS als Alternative zu H₂-Monokultur"; Quelle für die Klarstellung, dass das KKW-Lager keine eindeutige Backup-Präferenz hat. | https://techforfuture.de | Mai 2025 |
| `BPB-WAGNER-2025` | Bundeszentrale für politische Bildung, Anna Veronika Wagner: *Kernenergie gehört zu einer guten Klimastrategie*. Beleg für KKW-Lager-Programm "40 % Atom + EE-Komplement" (Maximalprogramm), das im Modell explizit als nicht-modellierte Variante ausgewiesen wird. | https://www.bpb.de | Februar 2025 |
| `FRAUNHOFER-ISE-LCOE-2024` | Fraunhofer ISE: *Stromgestehungskosten Erneuerbare Energien*, Auflage 2024 — KKW-LCOE-Bandbreite 13,6-49,0 ct/kWh und Methoden-Hinweis "KKW-Regelbarkeit technisch nur bedingt umsetzbar". Cross-Reference zur ISE-2024-Studie (PV/Wind), spezifisch für die KKW-Bandbreiten-Diskussion. | https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/studies/DE2024_ISE_Studie_Stromgestehungskosten_Erneuerbare_Energien.pdf | Juli 2024 |
| `AGORA-DEMAND-FLEX-2024` | Agora Energiewende: *Demand-Side-Flexibilität im klimaneutralen Stromsystem*, 2024. Qualitative Bandbreite für DSM-Grenznutzen in volatilen EE-Systemen (~0,3-0,6 ct/kWh Einsparung über System-Mittel). Belegt die DSM-Asymmetrie EE-vs-KKW-Pfade (höherer Grenznutzen bei höherer Preisvolatilität). Class B — Agora-Branchen-Analyse, qualitativ. | https://www.agora-energiewende.de | 2024 |
| `ARIADNE-FLEX-2024` | PIK / Ariadne-Kopernikus-Projekt: *Flexibilität im deutschen Energiesystem bis 2045*, Szenarienreport 2024. Qualitative Stützung der EE-DSM-Asymmetrie (Lastflexibilität in volatilen Systemen wertvoller) und der Misch-Pfad-Werte. Class A — Projekt-Verbund mit BMWK-Förderung. | https://ariadneprojekt.de | 2024 |
| `IFW-REAKTIV-2025` | IfW Kiel: *Kurzanalyse zur ETS-Reform unter passiver Klimapolitik*, 2025. Belegt die WEITER-SO-Position »passive Trägheit akzeptiert EU-ETS-Korridor-Unterkante«; Grundlage für `co2_price_eur_t.weiterso_optimistic = 80` (symmetrisch zu BESTAND). Class B — Wirtschaftsforschungs-Institut, Politik-Analyse. | https://www.ifw-kiel.de | 2025 |
| `NEA-PROJECTED-COSTS-2020` | OECD-NEA / IEA: *Projected Costs of Generating Electricity*, 2020-Ausgabe. Liefert den 0,1-2,4 ct/kWh-Korridor für Nuclear-Liability-Externalisierung; verwendet als Cross-Validation für die HPC-CfD-Decommissioning- + Endlager-Beitrags-Anker im Modell. Class A — peer-reviewt, OECD/IEA-Publikation. | https://www.oecd-nea.org/jcms/pl_15725/projected-costs-of-generating-electricity-2020-edition | 2020 |
| `EDF-HPC-CFD` | Hinkley Point C Contract for Difference (UK ONR / HM Treasury Government Support Package, 2016) plus *Funded Decommissioning Programme* + *Waste Transfer Price* Vertragsdokumente. Belegt die Mid-Range-Anker für KKW-Neubau-Rückstellungen (Decommissioning-Fund £2-3/MWh + Waste-Transfer £1-2/MWh) — vertraglich fixierte Werte als empirischer Anker statt theoretischer Schätzungen. Class A — öffentlicher CfD-Vertrag. | https://assets.publishing.service.gov.uk (HPC Funded Decommissioning Programme) | 2016 |

## Methodische Anmerkungen

**Erstens — die Lager-Spreizung ist real, aber begrenzt.**
Die Bandbreiten zwischen EE-Lager und Atom-Lager sind selten Faktor 2 oder mehr.
Sie sind meist 30-80 %. Das heißt: Beide Lager arbeiten in der Regel mit den
selben Studien, aber wählen daraus *unterschiedliche Punkte der Bandbreite*.
Niemand erfindet Zahlen — aber alle wählen selektiv.

**Zweitens — Quellen-Priorität.**
Die belastbarste Quelle ist `ISE-2024` (peer-reviewed-äquivalent, methodisch
transparent). `KERND-2024` ist als Branchenverbands-Position einzuordnen
und methodisch ernst zu nehmen. Beide Positionen werden in der Lager-
Bandbreite transparent nebeneinandergestellt.

**Drittens — Dynamik der Quellen.**
BNEF aktualisiert jährlich, BNEF Februar 2026 zeigt: Offshore-Wind ist deutlich
teurer geworden. Reproduzierbarkeit braucht klare Versions-Stempel und einen
transparenten Umgang mit der Update-Frequenz.

**Viertens — was ist NICHT modelliert.**
Das Modell deckt nicht ab: geopolitische Risiken (China-Solarpanel-Abhängigkeit,
Erdgas-Importrouten), technologische Disruption (Natrium-Ionen, SMRs vor 2050),
Verhaltensänderungen (Konsumreduktion, Suffizienz). Diese Themen gehören in
eine begleitende Diskussion, nicht ins Modell.
