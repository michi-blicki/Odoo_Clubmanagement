# Prozess: Mitgliederrechnung (Jahresrechnung)

## Ziel
Enterprise-fähiger Prozess für die jährliche Rechnungsstellung im Add-on `clubmanagement`, inklusive Minderjährige, Guardians und Familien mit mehreren Kindern.

## Verifizierter Ist-Stand (Codebasis)
- `club.member` ist über `_inherits` an `res.partner` gebunden.
- Guardians sind über `club.member.guardian` modelliert (`member_id`, `guardian_id`, `relation`, `is_primary`).
- Es existiert aktuell **keine** fachliche Trennung zwischen „Mitglied“ und „Rechnungsempfänger“.
- Im Modul gibt es derzeit keine produktive `account.move`-Erzeugungslogik für Mitgliedsrechnungen.
- Hinweis im UI vorhanden: Mitglieder werden nicht final entfernt, da Rechnungsbezug auf Mitglieder bestehen kann.

## Bereits abgestimmte Leitentscheide (25.03.2026)
1. Rechnungseinheit: **konfigurierbar pro Club**
	- Option A: pro Mitglied
	- Option B: pro Zahler/Familie (konsolidiert)
2. Volljährige: **immer Selbstzahler** (Mitgliedspartner als Debitor)
3. Migration: **keine Bestandsmigration erforderlich** (noch keine relevanten Daten im System)

## Kernproblem
Für Minderjährige reicht `primary_guardian_id` als reine Kontaktinformation nicht aus.
Benötigt wird eine robuste Debitor-Logik für:
- Rechnungsstellung an Erziehungsberechtigte
- optional konsolidierte Familienrechnung über mehrere Kinder
- revisionssichere Nachvollziehbarkeit, wer warum Debitor war

## Architekturvarianten Debitorsteuerung

### Variante 1: Ableitung rein aus Guardian (z. B. `primary_guardian_id`)
Vorteile:
- Wenig zusätzliche Felder
- Schneller initialer Setup

Risiken:
- Schwache Nachvollziehbarkeit bei Sonderfällen (abweichender Zahler)
- Schwer erweiterbar für Familien- oder Split-Szenarien
- Hohe Kopplung an `is_primary`, das fachlich nicht automatisch „Rechnungspflicht“ bedeutet

### Variante 2: Explizites Feld `invoice_partner_id` am Mitglied (mit Fallback)
Vorteile:
- Klare fachliche Semantik: „Wer ist Debitor für dieses Mitglied?“
- Bessere Auditierbarkeit und Governance
- Entkoppelt Guardian-Rolle von Debitor-Rolle
- Fundament für konsolidierte Familienrechnung

Risiken / Aufwand:
- Zusätzliche Felder, Constraints, Views und Security-Prüfungen
- Saubere Default-/Fallback-Logik erforderlich

## Vorläufige fachliche Empfehlung
Variante 2 als Zielbild:
- Neues Debitor-Feld am Mitglied (`invoice_partner_id`)
- Ergänzend ein `billing_mode` pro Mitglied oder pro Club (z. B. `self`, `guardian_primary`, `guardian_specific`)
- Für Volljährige automatische Default-Setzung auf `partner_id`
- Für Minderjährige Default aus Primary Guardian, aber explizit überschreibbar

## Offene Designfragen (vor Implementierung zu klären)
1. Muss `invoice_partner_id` zwingend einer der hinterlegten Guardians sein (bei Minderjährigen)?
    Aus meiner Sicht ist das nicht zwingend. Siehe hierzu auch meine Szenarien aus Punkt 2.

2. Darf ein Debitor mehrere Mitglieder auf einer Rechnung bündeln (Familienmodus)?
    Ich stelle mir gerade eine Familie vor, wo der Vater im Senioren-Team aktiv ist und die Kinder bei den Junioren spielen. Das gibt in der aktuellen Realität folgende Möglichkeiten:
        Vater und Kinder sind im selben Haushalt: eine Rechnung für alle drei
        Vater und Kinder leben getrennt: allenfalls unterschiedliche Rechnungsempfänger
        Vater und Kinder leben getrennt, aber Rechnungsempfänger ist der Vater
    Ein zweites Szenario: Vater und Mutter leben getrennt, die Kinder bei der Mutter. Aber ein Kind bezahlt der Vater, ein Kind bezahlt die Mutter.
    Ein drittes Szenario: das Kind lebt im Kinderheim, getrennt von den Eltern. Das Kinderheim hat vier Kinder, die im Verein sind. Es braucht also vier Rechnungen, obschon der Rechnungsempfänger bei den vier Kindern identisch ist.

    Wir müssen das im Szenario abdecken können.

3. Wie wird periodisch fakturiert: eigener Billing-Run im Modul oder Anbindung an bestehende Odoo-Subscription-/Accounting-Prozesse?
    Wenn es bereits ein Odoo Community Modul für Subscription gibt, welches sauber in Odoo integriert ist, wäre das natürlich deutlich sinnvoller, als den Billing-Run zusätzlich abzubilden.

4. Welche Benutzergruppen dürfen Debitorlogik pflegen/ändern (inkl. Freigabeprozess)?
    Das muss auf jeden Fall jemand sein, welcher die Gruppe `account.group_account_invoice` hat.

5. Welche Historisierung ist erforderlich (Debitorwechsel mit Gültigkeitszeitraum)?
    Aus meiner Sicht ausreichend ist die Markierung neuer Felder mit `tracking=True` ausreichend. Für die Nachvollziehbarkeit gegenüber dem Finanzamt sind die Rechnungen ausschlaggebend. Zudem könnte man zur Not auch über die `account_move_line`-Tabelle die Rechnungshistorie herausfinden, wenn es denn notwendig wäre.

## Security-/Compliance-Checkpoints
- Kein `sudo`/Bypass der Record Rules in operativer Logik.
- Multi-Company sauber erzwingen (`company_id`-Grenzen auch für Debitorpartner).
- Vermeidung von Dubletten und Inkonsistenzen zwischen `club.member`, `res.partner` und Guardian-Beziehungen.
- Kein Änderungsprotokoll im Club-Log bei Debitorwechsel notwendig.

## Verfügbarkeit Subscription in Odoo CE (Stand Workspace)
- In der aktuellen Odoo-CE-Codebasis im Workspace ist kein direkt nutzbares Membership-Subscription-Modul für diesen Prozess vorhanden.
- Schlussfolgerung: Für den MVP ist ein eigener, schlanker Billing-Run im Add-on realistischer als eine Abhängigkeit auf nicht vorhandene Subscription-Funktionalität.

## Offene Punkte
1. Abgrenzung Doppelverrechnung: Wie verhindern wir Kollisionen zwischen Jahreslauf und Single Billing im selben Jahr (gleiche Mitglieder)?
    Können wir überhaupt davon ausgehen, dass die Mitgliedschaft immer jährlich bezahlt wird? Ich denke nicht. Entsprechend müssen wir Kollisionen grundsätzlich zulassen und in einer späteren Dokumentation entsprechend ausweisen, dass diese generell möglich sind.

2. Rerun-Scope: Welche Entwürfe werden genau ersetzt (nur vom gleichen Run-Typ, Journal, Jahr, Company)?
    Bei einem Rerun werden diejenigen Rechnungen ersetzt, welche vom gleichen Debitor sind und noch im Entwurf stehen.

3. Rollenmodell: Darf clubmanagement.group_clubmanagement_key_user nur Debitorfelder pflegen oder auch Billing-Läufe starten?
    `clubmanagement.group_clubmanagement_key_user` darf nur Debitorenfelder pflegen, keine Billing-Läufe starten. Hierfür braucht es, neben `clubmanagement.group_clubmanagement_key_user` auch die Rolle `account.group_account_invoice`.

4. Multi-Company-Quelle: Da club.member kein eigenes company_id hat, welche Company ist bei Mitgliedern verbindlich (über club_id, membership, oder Run-Company)?
    Verbindlich für Mitglieder ist die Zuordnung des Mitglieds zu `club.subclub`, da `club.subclub` eine eindeutige Referenz auf `res.company` besitzt.

5. Buchhaltungs-Fallbacks: Was passiert bei fehlendem Produkt-Ertragskonto/Steuern/Fiscal Position (harter Block vs. Fehlerliste)?
    Dies ergibt einen harten Block mit Fehlermeldung.

6. Rechnungsdatum-Regel: Fixes Rechnungsdatum im Lauf (z. B. Stichtag) oder Laufdatum?
    Das Laufdatum ergibt das Rechnungsdatum.

## Review-Update (26.03.2026, kritisch)
Folgende Punkte sind nun final geklärt:
- Rerun: ersetzt vollständig Entwürfe des gleichen Run-Typs, Jahres, Company und Journals.
- Kollisionen Jahreslauf vs. Single Billing: werden zugelassen, aber als Warnung im Run-Protokoll ausgewiesen.
- Billing-Startberechtigung: `account.group_account_invoice` und `account.group_account_manager`.

Ein Punkt ist bewusst noch offen und muss vor Coding final entschieden werden:
- **Cross-Company & Beitragsregel**
    - Falls ein Mitglied in mehreren Strukturen mit unterschiedlichen Membership-Kontexten vorkommt,
        soll dann nur der höchste Beitrag fakturiert werden, oder sollen mehrere Positionen zulässig sein?
    - Diese Regel beeinflusst direkt Company-Zuordnung, Gruppenbildung und Preisermittlung.

Finaler Entscheid für MVP:
- Billing-Run bleibt strikt company-gebunden.
- Pro Mitglied wird genau eine Position aus `current_membership_id` verarbeitet.
- Mehrfachkontexte werden als Datenqualitätsfehler protokolliert und nicht automatisch aufgelöst.

## Zielarchitektur v1 (MVP, enterprise-fähig)

### 1) Trennung von Fachkonzepten
Wir trennen strikt:
- **Debitorbestimmung**: Wer zahlt für ein Mitglied?
- **Rechnungsbündelung**: Welche Positionen landen gemeinsam auf einer Rechnung?

Diese Trennung ist notwendig, um alle genannten Szenarien abzubilden:
- gleiche Familie, eine Sammelrechnung
- getrennte Haushalte, unterschiedliche Debitoren
- gleicher Debitor, aber trotzdem mehrere Einzelrechnungen (Kinderheim-Szenario)

### 2) Debitorlogik (pro Mitglied)
Vorgeschlagene Felder auf `club.member`:
- `invoice_partner_id` (`Many2one` auf `res.partner`, `tracking=True`)
- `invoice_partner_source` (`Selection`, z. B. `self`, `primary_guardian`, `manual`)

Regelwerk:
1. Volljährige: `invoice_partner_id = partner_id` (Self-Payer)
2. Minderjährige:
    - Default: Primary Guardian, wenn vorhanden
    - Sonst manuell setzbar (auch Nicht-Guardian erlaubt)
3. Validierung:
    - `invoice_partner_id` muss gesetzt sein, bevor fakturiert wird
    - `invoice_partner_id.company_id` darf nicht im Konflikt zur fakturierenden Company stehen

### 3) Bündelungslogik (pro Mitglied, unabhängig vom Debitor)
Vorgeschlagenes Feld auf `club.member`:
- `invoice_grouping_mode` (`Selection`)
  - `single`: immer Einzelrechnung für dieses Mitglied
  - `by_payer`: konsolidierbar mit anderen Mitgliedern mit gleichem Debitor

Damit wird das Kinderheim-Szenario sauber möglich:
- Vier Kinder, gleicher Debitor, aber `single` => vier Rechnungen.

### 4) Clubweite Defaults (Governance)
Vorgeschlagene Felder auf `club.club` oder `res.config.settings`:
- `default_invoice_grouping_mode` (`single` | `by_payer`)
- `default_minor_invoice_source` (`primary_guardian` | `manual`)

Wirkung:
- Neue Mitglieder erhalten Default-Werte.
- Fachliche Ausnahmen bleiben pro Mitglied möglich.

### 5) Jahres-Billing-Run (eigener Prozess im Add-on)
Neues Prozessmodell (technisch): `club.member.billing.run`

Minimaler Ablauf:
1. Stichtag/Jahr und Ziel-Company wählen
2. Fakturierbare Mitglieder selektieren (aktive Membership-Historie zum Stichtag)
3. Für jedes Mitglied Debitor auflösen (`invoice_partner_id`)
4. Rechnungsgruppen bilden:
    - `single` => eigene Gruppe je Mitglied
    - `by_payer` => Gruppe nach Debitor
5. Entwürfe in `account.move` (out_invoice) erzeugen
6. Pro Rechnung Referenz auf Mitglieder transparent machen (über `account.move.line`)

Wichtig: die Rechnungen dürfen nicht bestätigt werden. Die Finanzadministration muss im Nachgang des Billing-Run noch die Möglichkeit haben, Anpassungen an der Rechnung vorzunehmen.

### 6) Single Billing (eigener Prozess im Add-On)

Minimaler Ablauf:
1. Button-gesteuerter Rechnungslauf für ein Mitglied, ein Team oder ein Pool
2. Erstellt eine Rechnung nur für die selektierten Mitgliedern ohne Rücksicht auf weitere Mitglieder
3. Rechnungsgruppen bilden, wo möglich:
    - `single` => eigene Gruppe je Mitglied
    - `by_payer` => Gruppe nach Debitor
4. Entwürfe in `account.move` (out_invoice) erzeugen
5. Pro Rechnung Referenz auf Mitglied transparent machen (über `account.move.line`)

### 7) Nachvollziehbarkeit ohne separate Historientabelle
Gemäss Entscheid reicht vorerst:
- `tracking=True` auf Debitor- und Gruppierungsfeldern
- zusätzlich eine Billing-Run-Line-Tabelle mit Snapshotwerten je erzeugter Position:
  - Mitglied
  - Debitor zum Laufzeitpunkt
  - Membership/Produkte
  - Zielrechnung (`account.move`)

Damit ist die Historie über Rechnungen und Run-Lines nachvollziehbar, ohne komplexe SCD-Historisierung.

### 8) Berechtigungen
Pflege Debitorlogik nur für Nutzer mit:
- `account.group_account_invoice`
- plus bestehende Club-Scope-Regeln (kein Rechte-Bypass)

Vorschlag:
- UI-Felder readonly für User ohne Rechnungsgruppe
- serverseitige `write`-Validierung zusätzlich erzwingen (defence in depth)

## Architecture Freeze v1 (entscheidet, 26.03.2026)

### A) Debitor und Gruppierung
- `invoice_partner_id` auf `club.member` wird eingeführt.
- Minderjährige: Default über `primary_guardian_id`, aber Debitor darf bewusst auch ein anderer Partner sein.
- Volljährige: Default Selbstzahler (`partner_id`).
- `invoice_grouping_mode` wird pro Mitglied geführt und per `res.config.settings` defaultet.

### B) Produkt- und Positionslogik
- Positionen werden je Mitglied/Produkt transparent ausgewiesen, auch bei Sammelrechnung.
- `once_per_invoice` ist fachlich aktiv und wird so interpretiert:
    - bei `by_payer`: einmal pro Sammelrechnung (Debitor-Gruppe)
    - bei `single`: einmal pro Mitgliedsrechnung
- Technischer Hinweis: `additional_product_ids` ist korrekt als `One2many` auf `club.member.membership.additional.product` modelliert.

### C) Billing-Run Verhalten
- Eigener Billing-Run im Add-on (`club.member.billing.run`), keine Abhängigkeit auf nicht vorhandene CE-Subscription.
- Erzeugte Rechnungen bleiben Entwürfe (`account.move`, `out_invoice`), keine automatische Bestätigung.
- Rerun im selben Jahr ersetzt vorhandene Entwürfe des vorherigen Laufs vollständig und erzeugt neu.

### D) Preise, Steuern, Fälligkeit, Journal
- Preis-/Steuerbasis: aktuelle Produktpreise + Partner-Steuern/Fiscal Position am Run-Datum.
- Fälligkeit: Payment Term vom Debitorpartner.
- Journal: Standard in `res.config.settings`, mit Fallback-Auswahl im Billing-Run.

### E) Datenqualität und Berechtigungen
- Billing blockiert bei fehlender Debitoradresse; Pflichtfelder: `name`, `street`, `zip`, `city`.
- `country_id` und `street2` bleiben optional.
- Debitorfelder dürfen geändert werden durch:
    - `account.group_account_invoice`
    - `account.group_account_manager`
    - `clubmanagement.group_clubmanagement_key_user`

## Nächster Schritt (Umsetzungsstart)
Technische Spezifikation in umsetzbare Arbeitspakete:
- Modellfelder + Constraints
- Views + ACL/Record-Rule-Anpassung
- Billing-Run + `account.move`-Erzeugung
- Tests für Familien-/Minderjährigen-Szenarien und Rerun-Idempotenz

## Umsetzungspakete v1 (Ready for Coding)

### Paket 1: Datenmodell und Regeln
Umfang:
- `club.member`: `invoice_partner_id`, `invoice_partner_source`, `invoice_grouping_mode` (mit `tracking=True`)
- `res.config.settings`: `default_invoice_grouping_mode`, Standard-Journal für Membership Billing
- serverseitige Validierungen für Debitorqualität (`name`, `street`, `zip`, `city`)

Akzeptanzkriterien:
- Minderjährige erhalten sinnvolle Defaults, Volljährige defaulten auf Selbstzahler.
- Billing-relevante Felder sind ohne berechtigte Gruppen nicht änderbar.

### Paket 2: Billing-Run Modelle
Umfang:
- `club.member.billing.run` (Kopf)
- `club.member.billing.run.line` (Snapshot je Mitglied/Produkt)
- Statusmodell für Lauf (`draft`, `done`, `cancelled`)

Akzeptanzkriterien:
- Lauf speichert alle relevanten Snapshotdaten reproduzierbar.
- Rerun ersetzt Draft-Rechnungen aus vorherigem Lauf vollständig.

### Paket 3: Rechnungserzeugung
Umfang:
- Gruppenbildung `single` vs. `by_payer`
- Mapping Membership -> `main_product_id` + `additional_product_ids`
- Logik für `once_per_invoice`
- Erstellung von `account.move` im Draft inklusive sauberer Referenzen

Akzeptanzkriterien:
- Sammelrechnung enthält getrennte Positionen pro Mitglied/Produkt.
- `once_per_invoice` wird korrekt je Gruppenmodus angewandt.
- Fälligkeit wird aus Payment Term des Debitors bestimmt.

### Paket 4: UI, Security, Tests
Umfang:
- Form-/List-Views für Debitorfelder und Billing-Run
- ACL/Record-Rule-Erweiterungen gemäss Freeze
- Testfälle für Familien, getrennte Debitoren, Kinderheim-Szenario, Rerun

Akzeptanzkriterien:
- Unberechtigte Nutzer können Debitorfelder nicht ändern.
- Alle definierten Schlüsselszenarien laufen deterministisch durch.
