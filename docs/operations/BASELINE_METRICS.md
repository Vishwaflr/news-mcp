# Baseline Metrics - Sprint 1 Day 1

**Datum:** 2025-10-01
**Zweck:** Ist-Zustand vor Sprint 1 Optimierungen

---

## 📊 Feed-Lag Baseline

**Top 10 Feeds mit höchstem Lag:**

| Feed ID | Title | Lag (Minutes) | Items (24h) |
|---------|-------|---------------|-------------|
| 12 | ABC News Top Stories TEST | 47.96 | 20 |
| 65 | FIXED | 34.74 | 4 |
| 13 | TechCrunch TEST | 33.48 | 48 |
| 24 | Financial Times World Economy | 25.65 | 20 |
| 32 | Sky News World | 25.58 | 24 |
| 30 | Wired | 10.26 | 25 |
| 68 | coindesk | 10.22 | 41 |
| 22 | CNBC World | 10.18 | 42 |
| 67 | cointelegraph | 10.15 | 640 |
| 40 | AI News | 10.10 | 5 |

**Durchschnittlicher Lag:** ~22 Minuten
**p95 Lag (geschätzt):** ~40 Minuten

---

## 🎯 Gesamt-Übersicht

| Metric | Wert |
|--------|------|
| **Active Feeds** | 35 |
| **Total Items** | 16,053 |
| **Analyzed Items** | 5,551 (34.6%) |
| **Active Runs** | 0 |

---

## 📈 Analyse-Durchsatz

**Letzte 24 Stunden:**
- Keine neuen Analysen in letzten 24h (System idle)
- Historical: ~30 Items/min (basierend auf vorherigen Messungen)

---

## ⚠️ Fehlerrate

**Analysis Run Items Status:**
- Schema verwendet `state` Spalte mit Werten: `queued`, `processing`, `completed`, `failed`, `skipped`
- Aktuelle Daten: Noch nicht gemessen (keine aktiven Runs)

---

## 🔍 DB Query Performance (Baseline)

**Nicht optimierte Queries (vor Indizes):**
- Item-Liste Query: Nicht gemessen
- Queue-Batch Query: Nicht gemessen
- Feed-Health Query: Nicht gemessen

**Wird nach Index-Optimierung gemessen**

---

## 📋 Beobachtungen

### Positiv
1. ✅ 35 aktive Feeds laufen stabil
2. ✅ 16k Items erfolgreich ingested
3. ✅ 34.6% der Items bereits analysiert

### Verbesserungspotential
1. 🟡 Feed-Lag teilweise >30 Minuten (Ziel: ≤5 min)
2. 🟡 Keine aktiven Analysen derzeit
3. 🔴 Keine Idempotenz → Potentielle Duplikate
4. 🔴 Keine Backpressure-Kontrolle
5. 🔴 Keine Metriken/Monitoring

---

## 🎯 Sprint 1 Ziele (Verbesserung)

| KPI | Baseline | Ziel Sprint 1 | Status |
|-----|----------|---------------|--------|
| **Feed-Lag p95** | ~40 min | Messbar via Grafana | ⏳ TBD |
| **Durchsatz** | ~30/min | ≥20/min maintained | ⏳ TBD |
| **Fehlerrate** | Unbekannt | Messbar, <5% | ⏳ TBD |
| **Duplikate** | Möglich | 0% (Idempotenz) | ⏳ TBD |
| **Queue Concurrent** | Unbegrenzt | Max 50 | ⏳ TBD |
| **DB Query p95** | Unbekannt | <150ms | ⏳ TBD |

---

## 📝 Nächste Schritte

1. ✅ Baseline dokumentiert
2. ⏳ Idempotenz implementieren (Tag 1-2)
3. ⏳ Backpressure implementieren (Tag 3-4)
4. ⏳ Prometheus Metrics (Tag 5-6)
5. ⏳ DB-Indizes optimieren (Tag 7)

---

**Erstellt:** 2025-10-01
**Nächste Messung:** Nach Sprint 1 (Tag 7)
