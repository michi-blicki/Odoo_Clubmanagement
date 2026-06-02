## Business Case: Mitgliedschaft und effektiver Mitgliederbeitrag

### Ziel
Dieses Dokument beschreibt die fachliche Logik zur Ermittlung der effektiven Mitgliedschaft und des effektiven Mitgliederbeitrags je Mitglied.

Es gilt:
- Jedes Mitglied hat eine generelle Basis-Mitgliedschaft.
- Zusätzlich können auf Organisationsebenen spezifische Mitgliedschaften definiert werden.
- Die effektiv gültige Mitgliedschaft wird über eine klare Prioritätsregel ermittelt.

### Begriffe
- Basis-Mitgliedschaft: Die generelle Mitgliedschaft des Mitglieds (z. B. Aktivmitglied, Juniorenmitglied).
- Ebenen-Mitgliedschaft: Eine Mitgliedschaft, die auf einer Organisationseinheit hinterlegt ist.
- Effektive Mitgliedschaft: Die für Beitrag/Billing tatsächlich verwendete Mitgliedschaft.

### Datenquelle
- Basis-Mitgliedschaft: club.member.current_membership_id
- Ebenen-Mitgliedschaften:
	- club.subclub.effective_membership_id
	- club.department.effective_membership_id
	- club.pool.effective_membership_id
	- club.team.effective_membership_id

Hinweis: Auf den Ebenen wird effective_membership_id bereits per Vererbung/Fallback berechnet.

### Entscheidungslogik

#### 1) Priorität der Ebenen
Die Ermittlung der effektiven Mitgliedschaft erfolgt in folgender Reihenfolge:

1. Team
2. Pool
3. Department
4. Subclub
5. Basis-Mitgliedschaft

Sobald auf einer höheren Prioritätsstufe ein gültiger Treffer existiert, werden tiefere Prioritäten nicht mehr berücksichtigt.

#### 2) Mehrere Treffer auf derselben Ebene
Falls ein Mitglied auf derselben Prioritätsstufe mehreren Einheiten zugeordnet ist und diese unterschiedliche Mitgliedschaften liefern:

- Die Mitgliedschaft mit dem höheren Preis gewinnt.

Technisch/fachlich konkret:
- Verglichen wird membership.price (bzw. der daraus abgeleitete effektive Beitrag).
- Bei nur einem Treffer auf derselben Ebene wird dieser direkt verwendet.

#### 3) Gleichstand auf derselben Ebene
Falls mehrere Mitgliedschaften auf derselben Ebene denselben Preis haben:

- Es wird die Mitgliedschaft mit der kleinsten sequence gewählt.
- Bei weiterem Gleichstand wird die kleinste id gewählt.

Diese Tie-Breaker-Regel stellt deterministisches Verhalten sicher.

### Berechnungsablauf (fachlich)
1. Relevante Mitgliedschaften aus Team-Zuordnungen des Mitglieds sammeln.
2. Falls vorhanden: beste Team-Mitgliedschaft ermitteln (höherer Preis gewinnt; sonst sequence/id).
3. Falls kein Team-Treffer: Pool-Treffer gleich auswerten.
4. Falls kein Pool-Treffer: Department-Treffer gleich auswerten.
5. Falls kein Department-Treffer: Subclub-Treffer gleich auswerten.
6. Falls kein Subclub-Treffer: Basis-Mitgliedschaft verwenden.

Ergebnis:
- Genau eine effektive Mitgliedschaft pro Mitglied und Stichtag.
- Genau ein effektiver Mitgliederbeitrag pro Mitglied und Stichtag.

### Beispiele

#### Beispiel A: Team überschreibt Basis
- Basis-Mitgliedschaft: Aktivmitglied (120)
- Team-Mitgliedschaft: Leistungsteam (180)

Ergebnis: Leistungsteam (180), da Team die höchste Priorität hat.

#### Beispiel B: Zwei Teams mit verschiedenen Preisen
- Team 1: Mitgliedschaft A (150)
- Team 2: Mitgliedschaft B (190)

Ergebnis: Mitgliedschaft B (190), da auf gleicher Ebene der höhere Preis gewinnt.

#### Beispiel C: Kein Team/Pool/Department/Subclub-Treffer
- Basis-Mitgliedschaft: Juniorenmitglied (90)

Ergebnis: Juniorenmitglied (90).

### Auswirkungen auf Billing
- Billing verwendet die effektive Mitgliedschaft als Beitragsgrundlage.
- Die Herkunft der effektiven Mitgliedschaft (Ebene + Quelle) muss im Run nachvollziehbar protokolliert werden.
- Dadurch ist transparent, ob ein Beitrag aus Team-, Pool-, Department-, Subclub- oder Basis-Logik resultiert.

### Nicht-Ziele
- Dieses Dokument regelt nicht die Frage, ob mehrere Rechnungspositionen pro Mitglied zulässig sind.
- Dieses Dokument regelt nicht die Debitorbestimmung (invoice partner).

### Akzeptanzkriterien
1. Die Priorität Team > Pool > Department > Subclub > Basis wird immer eingehalten.
2. Bei mehreren Treffern auf derselben Ebene gewinnt immer der höhere Preis.
3. Bei Preisgleichheit ist die Auswahl deterministisch (sequence, dann id).
4. Für jedes Mitglied wird genau eine effektive Mitgliedschaft ermittelt.
5. Die effektive Mitgliedschaft ist für Anwender und im Billing-Run nachvollziehbar.

### Entscheidungsstatus
- Status: beschlossen
- Datum: 2026-05-19
- Beschluss:
	- Eindeutige Priorität der Ebenen: Team > Pool > Department > Subclub > Basis-Mitgliedschaft
	- Bei mehreren Treffern auf derselben Ebene: höherer Preis gewinnt
