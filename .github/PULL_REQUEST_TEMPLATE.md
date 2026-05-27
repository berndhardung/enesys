<!--
Danke fürs Mitarbeiten. Bitte fülle die folgenden Felder aus, soweit
sie für Deine Änderung relevant sind. Felder, die nicht zutreffen,
darfst Du löschen.

Scope-Hinweis: siehe CONTRIBUTING.md — das Modell soll neutrales
Analyse-Werkzeug bleiben. Advocacy-PRs (Hardcode pro EE oder Atom,
einseitige Default-Verschiebungen) werden nicht akzeptiert.
-->

## Was diese PR macht

<!-- Ein, zwei Sätze: was ändert sich, und warum? -->

## Kategorie

- [ ] Bug-Fix (Formel-Fehler, Quellen-Mismatch, Test-Fehler)
- [ ] Quellen-Update (neue Studie / neue Datenversion → `docs/SOURCES.md` mit aktualisiert)
- [ ] Methodische Anpassung (Camp-Range, Parameter-Konvention, …)
- [ ] Regional-Adaption (anderes Land, konfigurierbar gemacht)
- [ ] Doku
- [ ] Tooling / CI / Abhängigkeiten
- [ ] Sonstiges:

## Was bewusst NICHT in der PR ist

<!-- Scope-Abgrenzung — vermeidet Erwartungs-Mismatch beim Review. -->

## Checklist

- [ ] Tests laufen lokal grün (`pytest`)
- [ ] Ruff ist sauber (`ruff check src/ tests/`)
- [ ] Bei geänderten Default-Parametern: `[SRC: ...]`-Tag in `docs/SOURCES.md` aktualisiert
- [ ] Bei methodischen Änderungen: `CHANGELOG.md` ([Unreleased]-Sektion) ergänzt
- [ ] PR-Titel folgt Conventional-Commits (`fix(scope):`, `feat(scope):`, `docs(scope):`, …)

## Quellen (bei Werte-Änderung)

<!--
- Studie / Report:
- Herausgeber + Datum:
- Link oder DOI:
- Konkrete Tabelle / Seite:
- Currency-Year + Einheiten geprüft? (LCOE-Snapshot vs. Forward-Cost, EUR vs. USD etc.)
- Misst die Quelle dasselbe wie das Modell-Feld? (System-Boundary-Check)
-->

## Erwartete Wirkung

<!-- Auf welche Pfade (EE-GAS, EE-H2, WEITER-SO, KKW-GAS, KKW-H2, BESTAND)
     wirkt die Änderung, und ungefähr in welcher Größenordnung? -->

## Hinweise für Review

<!-- Tradeoffs, Alternativen, offene Fragen. -->
