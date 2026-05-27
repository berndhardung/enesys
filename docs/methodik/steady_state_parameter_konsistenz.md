# Steady-State-Modell — Parameter-Konsistenz mit Hauptmodell

Diese Tabelle dokumentiert jeden Parameter im Steady-State-Modell
(deckt den Zeitraum 2055–2085 ab) gegenüber dem entsprechenden
Hauptmodell-Wert (`path_model.py ForwardCostParams`). Sie ist die
Grundlage für die Aussage „das Steady-State-Modell ist methodisch
konsistent zum Hauptmodell".

## Konvention der Quellen-Tags

- `[SRC: TAG]` — externe Quelle aus `docs/SOURCES.md`
- `[CALIBRATED: ]` — aus Quellen hergeleitet, mit Begründung
- `[ASSUMPTION: ]` — Schätzung ohne harte Quelle, mit Begründung
- `[MODEL: ]` — Modell-interne Konstante, z. B. aus `ForwardCostParams`

## CAPEX (€/kW)

Die CAPEX-Werte sinken deutlich von 2026 auf 2050 — das ist die
zentrale Lernkurven-Annahme aus C.2.

| Parameter | Hauptmodell 2026 | Steady-State 2055 | Faktor | Quelle |
|---|---|---|---|---|
| PV | 700 | **350** | ÷2 | BNEF-NEO-2024 Net-Zero-Median |
| Wind onshore | 1.400 | **1.100** | ÷1,3 | IEA-WEO-2024 |
| Wind offshore | 3.000 | **1.800** | ÷1,7 | IEA-WEO-2024 |
| KKW | 11.000 | **6.000** | ÷1,8 | C.2-Mittelwert SMR-optim/EPR-pessim |
| Batterie €/kWh | 110 | **50** | ÷2,2 | BNEF-2025-LIB Lernrate |
| Biomasse | — | 3.000 | — | Ausgereift, ähnlich heute |

## OPEX (€/kW/Jahr) — absolut, nicht prozentual

OPEX-Werte sind technologie-strukturell und sinken nur leicht
gegenüber 2026 (Wartungs-Lernkurven). Keine drastische Reduktion.

| Parameter | Hauptmodell 2026 | Steady-State 2055 | Differenz | Begründung |
|---|---|---|---|---|
| PV | 12 | **10** | -17 % | Standardisierte Wartung |
| Wind onshore | 35 | **28** | -20 % | Predictive Maintenance |
| Wind offshore | 90 | **70** | -22 % | Standardisierte See-Logistik |
| KKW | 130 | **150** | +15 % | Konservative Brennelement-Annahme |
| Biomasse | — | 180 | — | Brennstoffkosten dominieren |

**Methodische Konvention:** OPEX werden als absolute €/kW/Jahr
modelliert, nicht als Prozentsatz der CAPEX. Das ist die
Hauptmodell-Konvention und entspricht der Realität: Wartung,
Versicherung und Brennstoffkosten skalieren nicht 1:1 mit der
CAPEX, sondern sind anlagengrößen- und technologie-spezifisch
weitgehend stabil.

## Lebensdauer (Jahre) — strukturell, identisch zu Hauptmodell

| Parameter | Hauptmodell | Steady-State | Quelle |
|---|---|---|---|
| PV | 30 | **30** | ISE-2024 |
| Wind | 25 | **25** | ISE-2024 |
| KKW | 60 | **60** | EPR-Design-Spec |
| Batterie | 6.000 Zyklen | 15 Jahre | äquivalent bei 365/Jahr |
| Biomasse | — | 25 | Annahme analog Wind |

## Volllaststunden (h/a) — identisch zu Hauptmodell

| Parameter | Hauptmodell | Steady-State | Quelle |
|---|---|---|---|
| PV | 1.050 | **1.050** | ISE-2024 DE-Mittel |
| Wind onshore | 2.200 | **2.200** | ISE-2024 DE-Mittel |
| Wind offshore | 4.200 | **4.200** | ISE-2024 |
| KKW | 6.500 | **6.500** | ISE-2024, EE-Mix-Realität |
| Biomasse | — | 4.500 | Bandlast-Annahme |

**Hinweis zu KKW-VLH:** KernD argumentiert historisch 7.500-8.000
Stunden. Die niedrigeren 6.500 spiegeln, dass im 80-%-EE-System
2055 die KKW-Auslastung durch EE-Vorrang und Lastfolge-Begrenzungen
gedrückt wird — siehe TAB-2017 zur Lastfolgefähigkeit und
OECD-NEA-2019 zu Systemkosten.

## WACC pro Technologie

WACC ist die zentrale Stellschraube. Hauptmodell setzt Werte für
2026 mit Risikoprämien. Für 2055 sind die Werte für reife
Technologien moderat reduziert — das ist konsistent zur
Lernkurven-Logik.

| Technologie | Hauptmodell 2026 | Steady-State 2055 | Differenz | Begründung |
|---|---|---|---|---|
| PV | 5,0 % | **4,0 %** | -1 pp | 30 Jahre etablierte Industrie |
| Wind | 6,0 % | **5,0 %** | -1 pp | Reife Genehmigungsprozesse |
| KKW | **8,5 %** | **8,5 %** | 0 pp | Bauzeit-Risiko bleibt strukturell |
| Batterie | 7,0 % | **5,0 %** | -2 pp | Reife Asset-Klasse 2055 |

**KKW-WACC unverändert.** Eine "Lernkurven-Reduktion" für KKW würde
voraussetzen, dass die Industrie Lieferzeit- und Budget-Treue empirisch
nachweist; die EU-Referenzen Hinkley Point C, Flamanville und Olkiluoto
stützen das bislang nicht. Die Sensitivitäts-Tabelle deckt eine implizite
WACC-Reduktion über das Szenario "KKW-CAPEX 4.500 €/kW" mit ab — ein
KKW zu 4.500 €/kW mit 5 % WACC entspricht etwa demselben LCOE wie
KKW zu 6.000 €/kW mit 8,5 % WACC.

## Mix-Anteile

Mix-Anteile spiegeln den Steady-State 2055. Sie sind nicht direkt
aus dem Hauptmodell übernommen (das modelliert die Trajektorie),
sondern aus dessen 2050+-Steady-State abgeleitet.

| Pfad | PV | Wind on | Wind off | Bio | Wasser | KKW | Backup |
|---|---|---|---|---|---|---|---|
| EE-GAS | 43 % | 32 % | 15 % | 4 % | 3 % | — | 8 % |
| EE-H2 | 43 % | 32 % | 15 % | 4 % | 3 % | — | 8 % H₂ |
| KKW-GAS | 28 % | 21 % | 10 % | 3 % | 2 % | 30 % | 6 % |
| KKW-H2 | 28 % | 21 % | 10 % | 3 % | 2 % | 30 % | 6 % H₂ |
| WEITER-SO | 30 % | 20 % | 8 % | 5 % | 3 % | — | 30 % Gas |

## Speicher-Anteile (Stromdurchsatz durch Tages-Speicher)

Methodische Logik: Speicherbedarf skaliert mit der **variablen
Komponente** im Pfad, nicht mit der Pfad-Familie pauschal.
Saison-Speicher (H₂) ist nicht in dieser Schicht — fließt über die
Backup-Erzeugung in die Erzeugungs-Schicht ein.

| Pfad | Anteil | Begründung |
|---|---|---|
| EE-GAS | 10 % | Schill-DIW-2024 für 100%-EE-Systeme |
| EE-H2 | 12 % | Tag-Ausgleich + H₂-Saison kombiniert |
| KKW-GAS | 7 % | 70 % variable Komponente × Skalierung + KKW-Überschuss-Pufferung |
| KKW-H2 | 10 % | KKW + H₂-Saison |
| WEITER-SO | 3 % | Wenig Speicher-Ausbau, Erdgas als Flexibilität |

Die Skalierung 10 % × 70/92 ≈ 7,5 % spiegelt, dass im KKW-Pfad
zwar weniger variable EE-Erzeugung vorhanden ist (70 % statt 92 %),
aber die KKW-Bandlast in Schwachlast-Stunden (Sommernächte)
zusätzlich gepuffert werden muss.

## Netz und Stabilität

| Schicht | Wert | Quelle |
|---|---|---|
| Netz aktiv | 7,0 ct/kWh | BNETZA-VS-2025 (Mittellage 5-8) |
| Netz WEITER-SO | 7,5 ct/kWh | + 0,5 für weniger Modernisierung |
| Stab EE | 1,1 ct/kWh | MODO-2025 + ENTSO-E-Modelle |
| Stab KKW | 0,4 ct/kWh | rotierende Massen liefern Inertia passiv |
| Stab WEITER-SO | 0,6 ct/kWh | zwischen EE und KKW |

## CO₂-Pönale

Wird über `co2_pricing_ct_kwh()` aus `path_model.py` berechnet —
**dieselbe Funktion** wie das Hauptmodell. CO₂-Intensitäten der
Mix-Komponenten sind Lebenszyklus-Werte (IPCC AR6 Median):

| Technologie | CO₂-Intensität |
|---|---|
| PV | 30 g/kWh |
| Wind | 10 g/kWh |
| Biomasse | 50 g/kWh |
| Wasser | 5 g/kWh |
| KKW | 12 g/kWh |
| Erdgas (Verbrennung) | 350 g/kWh |
| H₂ (grün) | 0 g/kWh |

| Pfad | CO₂-Preis-Welt | Begründung |
|---|---|---|
| Aktive Pfade (neutral) | 130 €/t | Hauptmodell-Default 2030+, lager-spezifisch 100-160 (ee_opt 160 / atom_opt 150 / bestand_opt 100) |
| WEITER-SO | 100 €/t | Hauptmodell-WEITER-SO-spezifisch (ETS-Aufweichungs-Annahme) |

## Resultate (Steady-State 2055-2085, neutral_default-Lager)

30-Jahres-Mittel aus `compute_path()`:

| Pfad      | LCOE 2055-2085 |
|---|---:|
| EE-GAS    | 15,54 ct |
| WEITER-SO | 15,77 ct |
| EE-H2     | 16,32 ct |
| BESTAND   | 16,92 ct |
| KKW-GAS   | 17,37 ct |
| KKW-H2    | 18,15 ct |

**EE-GAS bleibt im Default-Szenario günstigster Pfad** mit knappem
Vorsprung vor WEITER-SO (~0,23 ct) und deutlichem Abstand zu KKW-GAS
(+1,83 ct) und KKW-H2 (+2,61 ct). Der Steady-State unterscheidet sich
von der 2045-Snapshot-Reihenfolge: KKW-GAS und KKW-H2 fallen im
30-Jahres-Mittel-2055-2085 auf die hinteren Plätze, weil die hohen
Bridge-Phase-CO₂-Lasten und Bauzeit-Verzögerungen aus den 2040ern
heraus sind und der reine Steady-State-Betrieb sich amortisiert.

## Camp-Symmetrie

Die EE-GAS-Empfehlung im Steady-State 2055-2085 hält im `neutral_default`-,
`ee_optimistic`- und `bestand_optimistic`-Lager; im `atom_optimistic`-Lager
kippt sie zugunsten KKW-GAS (höherer KKW-Realgrad, Plan-Bauzeit voll
genutzt). Das ist die strukturelle Lager-Asymmetrie: jedes Lager liefert
seinen bevorzugten Pfad im Punkt-Schätzwert. Die Modell-Empfehlung
folgt aus Min-Max-Regret über die vier Lager, nicht aus einem
lager-übergreifenden Punkt-Schätzwert (siehe README, methodology.md).

## Drift-Sicherung

Konsistenz zwischen Hauptmodell und Steady-State-Modell wird durch
Tests in `tests/consistency/` abgesichert; bei Parameter-Änderungen
im Hauptmodell schlagen diese Tests an und erzwingen die explizite
Nachführung des Steady-State-Modells.
