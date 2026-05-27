# Bridge-Phase-Parameter — Quellen-Dokumentation

**Zweck:** Belegt die zentralen Time-Path-Parameter der Bridge-Phase
(Kohle-Auslauf, Erdgas-Bestand, h2-ready-Capacity, H₂-Brennstoff-
Verfügbarkeit) mit Quelle, Datum, Klassen-Einordnung und
Lager-Bandbreite. Ergänzt `docs/SOURCES.md`.

Bridge-Phase im Modell: 2026 bis `BRIDGE_PHASE_BIS_JAHR = 2046`
(siehe `core/path_sensitivity.py`). Die Bridge-Phase endet im
neutral_default-Lager mit der KKW-EPR-IBN 2046; in den anderen
Lagern verschiebt sich die De-facto-Bridge entsprechend (atom_opt
bis 2036, ee_opt bis 2050).

---

## Parameter 1 — Kohle-Bestand 2026

**Code:** `TimePathParams.kohle_bestand_capacity(year=2026)` = 33,0 GW

| Aspekt | Wert |
|---|---|
| **Default-Wert** | 33 GW (16 Steinkohle + 17 Braunkohle) |
| **Quelle** | BNetzA-Monitoring 2024, Tag `BNETZA-MONITORING-2024` |
| **URL** | https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Versorgungssicherheit/Erzeugungskapazitaeten/Kraftwerksliste/start.html |
| **Klasse** | **A** (offizielle Behörde) |
| **Verifikation** | "rund 56,5 Gigawatt an konventionellen Kraftwerken übrig" inkl. Erdgas; davon ~33 GW Stein-+Braunkohle |

**Lager-Spannung:** Keine. Wert ist gesetzliche Bestandsfestschreibung.

---

## Parameter 2 — WEITER-SO Kohle-Ausstiegsjahr

**Code:** `weiterso_kohle_ausstieg_endjahr` (in C.1 implizit über Stützstellen)

| Aspekt | Wert |
|---|---|
| **Default-Wert** | 2038 |
| **Quelle (juristisch)** | Kohleverstromungsbeendigungsgesetz (KVBG) §4, BGBl. I 2020 S. 1818, Tag `KVBG-2020` |
| **URL** | https://www.gesetze-im-internet.de/kvbg/ |
| **Klasse** | **A** (Bundesgesetz) |
| **Verbatim-Beleg** | KVBG §4: "spätestens bis zum 31.12.2038 vollständig abgebaut" |
| **Zwischenziele** | 30 GW (2022), 17 GW (2030: 8 Steinkohle + 9 Braunkohle), 0 GW (2038) |

**Lager-Bandbreite:**

| Lager | Wert | Begründung | Quelle |
|---|---|---|---|
| **EE-optimistisch** | 2035 | KVBG §54 sieht Revisions-Prüfungen 2026/2029/2032 vor — "wenn möglich schon 2035 zu beenden" (Bund-Länder-Einigung Januar 2020) | Wikipedia: Kohleausstiegs-Eintrag, Hinweis auf Kohlekommission-Empfehlung 2019 |
| **Neutral** | 2038 | KVBG-Endjahr | KVBG §4 |
| **Status-quo-pessimistisch** | 2042+ | Aufweichung möglich, wenn Versorgungssicherheits-Klausel KVBG §54 greift; Datteln 4 ging 2020 ans Netz und soll erst 2038 schließen → Präzedenz für Härtefall-Verlängerungen | energiezukunft.eu zum Fahrplan, Ersatzkraftwerkebereithaltungsgesetz 2022 als Präzedenz für Reaktivierungen |

**Methodischer Streitpunkt:** Der Wert 2042 ist *nicht* gesetzlich abgedeckt — er wäre eine Aufweichung. Methodisch sauber wäre, das im Modell als "Sensitivität: KVBG-Aufweichung" zu kennzeichnen, nicht als Atom-Lager-Position. Atom-Lager hat bei Kohle keine eigenständige Position (will sowieso KKW statt Kohle).

---

## Parameter 3 — Pfad-Kohle-Ausstiegsjahr (alle vier Nicht-WEITER-SO-Pfade)

**Code:** `TimePathParams.kohle_bestand_capacity(year, weiterso=False)` mit Stützstellen `{2026: 33, 2030: 0}`

| Aspekt | Wert |
|---|---|
| **Default-Wert** | 2030 (linear ausgelaufen 2026→2030) |
| **Quelle 1 (politisch)** | Koalitionsvertrag SPD/Grüne/FDP 2021, Pkt. "Klima, Energie, Transformation": "Kohleausstieg idealerweise auf 2030 vorziehen" |
| **Quelle 2 (vertraglich)** | Verständigung BMWK + NRW + RWE Oktober 2022, vorgezogener Kohleausstieg 2030 im Rheinischen Revier; per Gesetz 1.12.2022 (Bundestag-Drucksache 20/4300) |
| **URL** | https://www.bundestag.de/dokumente/textarchiv/2022/kw48-de-braunkohleausstieg-923096 |
| **Klasse** | **A** (Bundesgesetz für Rheinisches Revier) + **B** (politische Absicht für andere Reviere) |

**Stilllegungs-Vorlauf:**
- **Mindest-Vorlauf 30 Monate** für ordnungsrechtliche Anordnung (BNetzA), plus 12 Monate Wartefrist nach Stilllegungsanzeige
- **Empirie**: Seit 2011 wurden 41,73 GW konventionelle Kapazität stillgelegt — durchschnittlich 3 GW/Jahr. Der lineare Auslauf 33→0 GW über 4 Jahre = 8 GW/Jahr ist also **schneller als die historische Rate**, aber nicht unrealistisch (in Krisenjahren wie 2024 wurden 4,4 GW in einem Schritt stillgelegt).

**Lager-Bandbreite:**

| Lager | Wert | Begründung |
|---|---|---|
| **EE-optimistisch** | 2030 | Koalitionsvertrag 2021, RWE-Vertrag 2022 |
| **Neutral** | 2032 | Realistische Verzögerung gegenüber Ziel 2030 |
| **Status-quo-pessimistisch** | 2034 | Tagebau-Rekultivierung und Personalfragen verzögern |

**Methodischer Streitpunkt:** Brauchen wir den Pfad-Wert getrennt von WEITER-SO? Begründung ja: WEITER-SO ist ein definitorisch passiver Pfad (Status-quo-Lager), die anderen vier sind aktive Pfade. EE/KKW-Pfade *wollen* Kohle weghaben — Atom-Lager genauso wie EE-Lager. Daher gemeinsamer Wert für alle vier Nicht-WEITER-SO-Pfade.

---

## Parameter 4 — Erdgas-Bestand 2026 und Stilllegungs-Pfad

**Code:** `TimePathParams.gas_bestand_capacity(year)` mit Stützstellen `{2026: 31, 2030: 30, 2035: 28, 2040: 25, 2045: 22, 2050: 18}`

| Aspekt | Wert |
|---|---|
| **2026: 31 GW** | BNetzA-Monitoring 2024, Tag `BNETZA-MONITORING-2024` |
| **Klasse** | **A** (Bundesnetzagentur) |
| **Verifikation** | Aus 56,5 GW Gesamtkonventionell minus 33 GW Kohle = ~23,5 GW Erdgas im Bestand. Plus Reserve-Kraftwerke aus Ersatzkraftwerkebereithaltungsgesetz 2022 (~7 GW reaktiviert) → 30-31 GW konsistent |

**Stilllegungs-Trajektorie 2050: 18 GW**

Begründung der linearen Auslauf-Annahme: Bestand wird durch Alters-Stilllegung sukzessive reduziert. Mittlere Lebensdauer Gaskraftwerke ~30-40 Jahre, Bestand größtenteils Baujahre 1990-2010. Bis 2050 sind die ältesten Anlagen >50 Jahre alt, müssen ersetzt werden. Auslaufkurve folgt empirischer Stilllegungs-Logik der BNetzA-Kraftwerksliste.

**Methodischer Streitpunkt:** Diese Zahlen sind **nicht aus einer
einzelnen Quelle**, sondern eine plausible Modell-Annahme. Sie sind als
`[ASSUMPTION: Modell-Setzung, abgeleitet aus Bestands-Alter und
mittlerer Lebensdauer]` markiert, nicht als hartes Quellen-Datum.
Klasse-B-Quellen wie ISE-Kraftwerksanalyse oder DLR-System-Studien
würden den linearen Auslauf qualitativ stützen; eine Studie mit genau
diesem 31→18-GW-Pfad ist nicht bekannt.

**Lager-Bandbreite:** Keine — Bestand ist eine politisch unkontroverse Größe.

---

## Parameter 5 — H2-ready GuD-Neubau

**Code:** `TimePathParams.h2ready_capacity(year)` mit Stützstellen `{2026: 0, 2030: 6, 2035: 12, 2040: 16, 2045: 20, 2050: 22}`

| Aspekt | Wert |
|---|---|
| **2034: 12 GW** | Kraftwerksstrategie 2026, BMWE Eckpunktepapier Januar 2026, Tag `BMWE-KWBG-2026` |
| **Klasse** | **A** (Bundesregierung) |
| **Verbatim-Beleg** | Kraftwerksstrategie 2026: 24 moderne GuD-Kraftwerke à 500 MW, erste Inbetriebnahme 2030, letzte 2034 |

**2030: 6 GW (Realismus-Abschlag)**

Begründung: Vom Plan 12 GW über vier Jahre 2030-2034 würde linear 3 GW/Jahr bedeuten, also 3 GW (2031), 6 GW (2032)... Die 6 GW in 2030 sind eine **optimistische Lesart** — sie unterstellen, dass die ersten 12 Ausschreibungs-Lose schnell zugelaufen sind. Realistisch könnte 2030 auch erst 3-4 GW stehen.

**Lager-Bandbreite:**

| Lager | 2030 | 2035 | Begründung |
|---|---|---|---|
| **EE-optimistisch** | 8 GW | 14 GW | KWBG voll und planmäßig zugelaufen |
| **Neutral** | 6 GW | 12 GW | Plan-Wert mit moderatem Abschlag |
| **Skeptisch** | 3 GW | 8 GW | Genehmigungs-Verzögerungen, Lieferkette, Fachkräftemangel |

**Methodischer Streitpunkt:** Die KWBG-Eckpunkte sind politische Absichtserklärung, kein Rechtsstand. Ausschreibungen laufen erst an. Realistisch ist Verzögerung wahrscheinlich.

---

## Parameter 6 — H2-Brennstoff-Verfügbarkeit

**Code:** `TimePathParams.h2_brennstoff_capacity(year)` mit Stützstellen `{2026: 0,5, 2030: 3, 2035: 10, 2040: 20, 2045: 30, 2050: 40}`

| Aspekt | Wert |
|---|---|
| **2030: 3 GW backup-fähig** | Nationale Wasserstoff-Strategie Update 2023, Tag `NWS-2023` |
| **Klasse** | **B** (Forschungsinstitute mit Bundesregierung-Auftrag) — BMWK ist Klasse A, aber NWS ist Strategie-Papier, nicht Gesetz |
| **Verbatim-Beleg NWS-2023** | "Elektrolyse 5 GW bis 2030, 10 GW bis 2035" |

**Berechnungs-Logik 2030: 3 GW von 5 GW Elektrolyse**

Pro 1 GW H2-Kraftwerk in 240 h Volllast (10 Tage) bei 55-58 % Wirkungsgrad: ~0,4 TWh H2-Reserve. 5 GW Elektrolyse erzeugen jährlich ~30 TWh H2 — davon Industrie-Konkurrenz (Stahl, Chemie, Mobilität ziehen prioritär). Backup-fähiger Anteil ~60 % der Gesamtmenge → 18 TWh / Jahr → reicht für ~3 GW Backup-Leistung in 240 h.

**Lager-Bandbreite:**

| Lager | 2030 | 2035 | 2045 | Begründung |
|---|---|---|---|---|
| **EE-optimistisch** | 5 GW | 15 GW | 40 GW | NWS-2023-Plan ehrgeizig, Importe schnell |
| **Neutral** | 3 GW | 10 GW | 30 GW | NWS abzgl. Industrie-Konkurrenz |
| **Atom-/Status-quo-skeptisch** | 1 GW | 5 GW | 15 GW | Importe verzögern, Kavernen nicht da, Industrie zieht alles |

**Quelle für Skepsis (Atom-Lager):** "Wir setzen auf eine Wasserstoff-Monokultur statt auf einen Technologie-Mix" — Tech for Future, Pro-CCS-Position; Heise/heise.de zur SMC-Befragung 2023 mit Ruprecht/Thess-Skepsis. Klasse **D** (Lager-nahe Stimmen), aber argumentationskonsistent.

---

## Parameter 7 — H2-Brennstoff-Aufteilung EE-H2 / KKW-H2

**Code:** `H2_FUEL_SHARE = {"EE-H2": 0.5, "KKW-H2": 0.5}`

| Aspekt | Wert |
|---|---|
| **Default** | 0,5 / 0,5 (hälftige Aufteilung) |
| **Klasse** | methodische Modell-Setzung (`[ASSUMPTION]`-Tag) |

**Begründung:** Beide Pfade haben identische Bridge-Architektur und in
der Bridge-Phase identischen H2-Bedarf. Bis 2042 sind die Werte
identisch (beide rechnen mit 0,65 EE + 0,35 Backup); danach hat KKW-H2
strukturell weniger H2-Bedarf, weil KKW Teile der Backup-Last übernimmt.
Die hälftige Setzung ist bis 2042 exakt und danach leicht zugunsten
KKW-H2-Sichtbarkeit verzerrt — neutral, in der 30-Jahres-Bilanz
spannweiten-irrelevant.

---

## Quellen-Klassen-Übersicht

| Parameter | Klasse | Quellen-Tag in [`SOURCES.md`](../SOURCES.md) |
|---|---|---|
| Kohle-Bestand 2026 | A (gesetzlich/behördlich) | `KVBG-2020`, `BNETZA-MONITORING-2024` |
| WEITER-SO-Ausstieg | A (gesetzlich) | `KVBG-2020`, `RWE-VERTRAG-2022` |
| Pfad-Ausstieg | A+B (Pfad-Logik) | `BMWE-KWBG-2026` |
| Erdgas-Bestand-Trajektorie | B (`[ASSUMPTION]`) | Bestands-Alter und Lebensdauer; konservativ-linear ausmodelliert |
| H2-ready KWBG | A (gesetzlich) | `BMWE-KWBG-2026` |
| H2-Brennstoff-Verfügbarkeit | B (`[ASSUMPTION]`) | `NWS-2023`, `H2-IMPORT-2024`, `WASSERSTOFF-KERNNETZ-2024` |
| H2-Aufteilung 50/50 | `[ASSUMPTION]` (methodisch) | hälftige Neutral-Setzung in der Bridge-Phase |

Drei Parameter (Erdgas-Auslaufkurve, H2-Verfügbarkeit, H2-Aufteilung
50/50) sind methodische Modell-Setzungen und tragen den
`[ASSUMPTION]`-Tag — sie stützen sich auf konsistente Bridge-Logik, nicht
auf eine spezifische peer-reviewte Studie — die Setzungen sind hier
offen ausgewiesen, damit sie nachvollziehbar bleiben.
