"""Extensions: Verbraucher-Sicht, Flächen, Winter-Stress, Multikriterien.

Aufbauten auf core/, die das Hauptmodell um spezifische Perspektiven
erweitern. Jede Extension hat klare Abhängigkeiten zu core/, aber
nicht untereinander.

Module:
- consumers / consumer_bridge — Verbraucher-Sicht (BDEW-Komponenten,
  Steuern/Abgaben/Umlagen, Bridge zur Mengen-Bilanz).
- landuse                     — Pfad-Flächenbedarf (PV, Wind, KKW,
  Tagebau) als Aggregat-Vergleich.
- multicriteria               — Multikriterien-Ranking der vier
  klimaneutralen Pfade über vier Gewichtungs-Profile.
- profile_costs               — Profile-Cost-Aufschläge für volatile
  EE-Erzeugung (Hirth/Ueckerdt-Methodik).
- winter_stress               — Dunkelflauten-Stresstest mit
  LOLE-P95/P99-Härtung.
"""
