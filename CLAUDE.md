Sudo Passowrd: Aug2012#

# CLAUDE.md – Arbeitsregeln für News-MCP

## Kontextquellen
- **ENDPOINTS.md** = API-Gedächtnis (150+ Endpunkte, strukturiert nach Kategorien).
- **NAVIGATOR.md** = Systemübersicht (3-Spalten-Tabelle, Hotspots, Worksets, Roadmap).
- **INDEX.md** (optional) = Datei-Map.

Diese Dokumente gelten als **Quelle der Wahrheit**. Keine Annahmen außerhalb davon.

## Arbeitsprinzipien
1. **Plan vor Code**
   - Erstelle zuerst einen kurzen Plan oder Update der 3-Spalten-Übersicht.
   - Warte auf Freigabe, bevor du Änderungen vornimmst.

2. **Scope-Begrenzung**
   - Änderungen nur in den freigegebenen **Worksets** (max. 8 Dateien pro Hotspot).
   - Keine Streuänderungen in anderen Modulen.

3. **Output-Regeln**
   - Code nur als **unified diff (patch)** ausgeben.
   - Pläne, Reviews oder Analysen nur als Tabellen oder Bullet-Listen.

4. **Roadmap-Treue**
   - Folge der Phase-2-Roadmap in NAVIGATOR.md Schritt für Schritt.
   - Keine parallelen Änderungen an nicht freigegebenen Roadmap-Teilen.

5. **Test- & Stabilitätsregeln**
   - Beziehe dich immer auf die definierten 5 Contract Tests.
   - Brechen bestehende Tests → Änderung zurückstellen, Tests zuerst anpassen.

6. **Kommunikation**
   - Kompakt & präzise antworten.
   - Rückfragen stellen, wenn Unsicherheit besteht.
   - Niemals stillschweigend Annahmen treffen.

## Do / Don’t
✅ Nutze ENDPOINTS.md für API-Referenzen  
✅ Halte dich an NAVIGATOR.md für Hotspots, Worksets, Roadmap  
✅ Erstelle kleine, nachvollziehbare Diffs  
❌ Keine neuen Dependencies ohne Freigabe  
❌ Keine Änderungen außerhalb genehmigter Dateien  
❌ Keine Vermischung von Code und Freitext im selben Output
