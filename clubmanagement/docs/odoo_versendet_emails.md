# E-Mail Versand aus Odoo

## Ist-Zustand
- Die Odoo Benutzer haben Benutzernamen wie `michi` oder `esther` und keine vollständigen E-Mail Adressen.
- Als Sender Adresse wird eine generische Adresse verwendet.
- Mailserver und DNS Server befinden sich beim Provider NetZone und sind unter der Kontrolle des Administrators.
- Odoo ist noch nicht für den Versand von E-Mails eingerichtet.

## Ziel
Mit dieser Anleitung richten wir Odoo für den Versand von E-Mails ein.

## Abgrenzung
Der Empfang von E-Mails ist aktuell keine Option

## Gültigkeit der Anleitung
- Odoo Version: **18**
- Edition: **Community Edition (CE)**
- Zielsysteme:
	- Produktion: `https://odoo-prod.fcthalwil.ch`
	- Test: `https://odoo-test.fcthalwil.ch`

---

## Ergebnis nach dieser Anleitung
Nach Durchführung dieser Schritte kann Odoo E-Mails zuverlässig über SMTP versenden (z. B. Benachrichtigungen, Angebote, Rechnungen), mit einer gültigen Absender-Domain und funktionierender Zustellbarkeit (SPF/DKIM/DMARC).

---

## Voraussetzungen
- Zugriff auf Odoo als Administrator.
- Zugriff auf DNS-Verwaltung bei NetZone für die Domain `fcthalwil.ch`.
- Zugriff auf den SMTP-Server bei NetZone (Host, Port, Verschlüsselung, Benutzer, Passwort).
- Dedizierte SMTP-Konten für Odoo:
	- Produktion: `no-reply@fcthalwil.ch`
	- Test: `no-reply-test@fcthalwil.ch`

---

## Entscheidungen (vor Start ausfüllen)

### Produktion (`odoo-prod.fcthalwil.ch`)

| Parameter | Wert |
|---|---|
| Odoo Basis-URL | `https://odoo-prod.fcthalwil.ch` |
| Absenderadresse (erzwingen) | `no-reply@fcthalwil.ch` |
| SMTP-Host | `mail.netzone.ch` |
| SMTP-Port | `587` (STARTTLS empfohlen) |
| SMTP-Verschlüsselung | `STARTTLS` |
| SMTP-Benutzer | `no-reply@fcthalwil.ch` |
| SMTP-Passwort | `<starkes-passwort>` |
| SPF-Policy aktuell | `v=spf1 include:spf.netzone.ch -all` |
| DMARC-Policy aktuell | `v=DMARC1; p=reject; pct=100; aspf=s; adkim=s` |

### Test (`odoo-test.fcthalwil.ch`)

| Parameter | Wert |
|---|---|
| Odoo Basis-URL | `https://odoo-test.fcthalwil.ch` |
| Absenderadresse (erzwingen) | `no-reply-test@fcthalwil.ch` |
| SMTP-Host | `mail.netzone.ch` |
| SMTP-Port | `587` (STARTTLS empfohlen) |
| SMTP-Verschlüsselung | `STARTTLS` |
| SMTP-Benutzer | `no-reply-test@fcthalwil.ch` |
| SMTP-Passwort | `<starkes-passwort>` |

Hinweis: Die aktuelle DMARC-Policy ist bereits strikt (`p=reject`). Änderungen nur geplant und kontrolliert durchführen.

---

## Schritt 1: SMTP-Konto bei NetZone erstellen
1. Im NetZone-Panel zwei SMTP-Logins anlegen:
	- `no-reply@fcthalwil.ch` (Produktion)
	- `no-reply-test@fcthalwil.ch` (Test)
2. Ein starkes, zufälliges Passwort setzen.
3. SMTP-Parameter dokumentieren:
	- Servername (z. B. `mail.fcthalwil.ch`)
	- Port (`587` für STARTTLS oder `465` für SSL/TLS)
	- Authentifizierung erforderlich: Ja
4. Falls möglich: Versand-Limit und Rate-Limits prüfen (pro Stunde/Tag).

---

## Schritt 2: DNS korrekt setzen (SPF, DKIM, DMARC)

### 2.1 SPF setzen
1. DNS-Zone von `fcthalwil.ch` öffnen.
2. TXT-Record für Root-Domain setzen/prüfen:

```txt
Name: @
Typ: TXT
Wert: v=spf1 include:spf.netzone.ch -all
```

Wichtig:
- Es darf nur **ein** SPF-Record pro Domain existieren.
- Wenn bereits ein SPF-Eintrag vorhanden ist, diesen erweitern statt einen zweiten anzulegen.

### 2.2 DKIM aktivieren
1. DKIM im Mail-Provider (NetZone) aktivieren.
2. Den von NetZone gelieferten DKIM-Selector und TXT-Wert in DNS eintragen.
3. Beispiel (Platzhalter):

```txt
Name: selector1._domainkey
Typ: TXT
Wert: v=DKIM1; k=rsa; p=<public-key>
```

### 2.3 DMARC setzen
1. DMARC-Record anlegen:

```txt
Name: _dmarc
Typ: TXT
Wert: v=DMARC1; p=reject; pct=100; aspf=s; adkim=s
```

2. Optional: Falls Zustellprobleme analysiert werden müssen, Policy temporär entschärfen (`p=quarantine` oder `p=none`) und danach wieder auf `p=reject` zurückstellen.

### 2.4 DNS prüfen
Nach dem Speichern 15–120 Minuten Replikation abwarten und mit Tools prüfen:
- MXToolbox (SPF/DKIM/DMARC Lookup)
- `dig TXT fcthalwil.ch`
- `dig TXT _dmarc.fcthalwil.ch`
- `dig TXT selector1._domainkey.fcthalwil.ch`

---

## Schritt 3: Odoo für ausgehende E-Mails konfigurieren

Hinweis für Odoo 18 CE: Die folgenden Menüpunkte sind im Entwicklermodus verfügbar und gelten für die Community Edition.

### 3.1 Entwicklermodus aktivieren
1. Odoo öffnen.
2. **Einstellungen** → Entwicklermodus aktivieren.

### 3.2 Outgoing Mail Server anlegen
1. **Einstellungen** → **Technisch** → **E-Mail** → **Ausgehende Mail-Server**.
2. Für **Produktion** Server mit folgenden Werten:
	- Beschreibung: `NetZone SMTP`
	- SMTP-Server: `mail.netzone.ch`
	- Port: `587`
	- Verbindungssicherheit: `STARTTLS`
	- Benutzername: `no-reply@fcthalwil.ch`
	- Passwort: `<smtp-passwort>`
	- Priorität: `1`
3. Auf **Verbindung testen** klicken.
4. Speichern.

Für **Test** identisch, aber mit Benutzername `no-reply-test@fcthalwil.ch`.

Wichtig bei NetZone (Sender Ownership):
- Wenn der Provider nur Absender akzeptiert, die dem SMTP-Login gehören, muss die effektive Absenderadresse zu diesem Login passen.
- Für den Verbindungstest in Odoo 18 CE wird häufig die E-Mail des aktuell angemeldeten Benutzers als Absender verwendet.
- Deshalb kann der Test fehlschlagen, obwohl SMTP-Host/Port/Passwort korrekt sind.

Praktische Lösung für den Test:
1. Temporär die Benutzer-E-Mail des Admin-Users auf den SMTP-Login der jeweiligen Umgebung setzen.
2. Erneut auf **Verbindung testen** klicken.
3. Danach die Benutzer-E-Mail wieder zurücksetzen.

Dauerhafte Lösung für den Betrieb:
- Sender zentral erzwingen (siehe Schritt 3.4), damit Mails immer mit der festen Umgebungsadresse versendet werden.

### 3.4 Verbindliche Sender-Policy erzwingen (für alle Mails)

Ziel:
- Produktion sendet **immer** mit `no-reply@fcthalwil.ch`.
- Test sendet **immer** mit `no-reply-test@fcthalwil.ch`.
- Unabhängig von Benutzer-E-Mail, Partner-E-Mail oder Ursprung der Nachricht.

Umsetzung in Odoo 18 CE (ohne Custom-Code):
Voraussetzung:
- Das Modul `Automated Actions` (technischer Name: `base_automation`) muss installiert sein.
- Du musst im richtigen Menü arbeiten: **Technisch → Automatisierung → Automatisierte Aktionen**.
- In **Geplante Aktionen** (`ir.cron`) gibt es nur Zeitintervalle; dort ist kein Trigger „Bei Erstellung“ verfügbar.

Wenn nur ein Zeit-Trigger sichtbar ist:
1. Prüfen, ob du versehentlich in **Geplante Aktionen** bist.
2. In **Apps** nach `base_automation` suchen (Filter „Apps“ entfernen, Entwickler-Modus aktiv).
3. `base_automation` installieren und Seite neu laden.

Dann erst die folgende Regel anlegen:
1. **Einstellungen** → **Technisch** → **Automatisierung** → **Automatisierte Aktionen**.
2. Neue Aktion erstellen:
   - Name: `Force Outgoing Sender (mail.mail)`
   - Modell: `E-Mail` (`mail.mail`)
	- Trigger: `On save` (robuster als `After creation`)
   - Aktion ausführen: `Python-Code`
3. Python-Code (Produktion):

```python
user_email = (env.user.partner_id.email or '').strip().lower()
reply_to_value = user_email if user_email.endswith('@fcthalwil.ch') else 'info@fcthalwil.ch'

target_records = records or record
for rec in target_records:
	rec.write({
		'email_from': 'FCT Halwil <no-reply@fcthalwil.ch>',
		'reply_to': reply_to_value,
	})
```

4. Python-Code (Test):

```python
user_email = (env.user.partner_id.email or '').strip().lower()
reply_to_value = user_email if user_email.endswith('@fcthalwil.ch') else 'info@fcthalwil.ch'

target_records = records or record
for rec in target_records:
	rec.write({
		'email_from': 'FCT Halwil Test <no-reply-test@fcthalwil.ch>',
		'reply_to': reply_to_value,
	})
```

5. Aktion speichern und aktivieren.
6. Testmail erzeugen und in **Technisch → E-Mail → E-Mails** prüfen, dass `Von` immer der erzwungenen Adresse entspricht.

Hinweis:
- Falls bereits andere Automatisierungen auf `mail.mail` existieren, Reihenfolge prüfen.
- Diese Policy ist absichtlich strikt, damit SMTP-`Sender not owned` Fehler ausgeschlossen werden.
- `reply_to` wird dynamisch gesetzt: interne Adresse `@fcthalwil.ch` verwenden, sonst Fallback `info@fcthalwil.ch`.
- `On save` ist die empfohlene Einstellung, wenn `email_from` im Prozess später nochmals verändert wird.

### 3.4.1 Wenn die Sender-Erzwingung nicht greift
Prüfen in dieser Reihenfolge:
1. Automatisierte Aktion ist **aktiv**.
2. Modell ist exakt `mail.mail` (nicht `mail.message`).
3. Trigger ist `On save`.
4. Es gibt keine einschränkende Bedingung/Domain, die Testmails ausschliesst.
5. E-Mail nach Änderung neu erzeugen und unter **Technisch → E-Mail → E-Mails** prüfen, ob `Von` überschrieben wurde.
6. Falls weiterhin nicht überschrieben: zweite Aktion mit höherer Reihenfolge deaktivieren bzw. Konflikte mit anderen Automationen prüfen.

Empfehlung zur Verschlüsselung (Odoo 18 CE):
- Primär: `587` + `STARTTLS` (Submission-Standard, bei NetZone typischerweise die beste Wahl).
- Fallback: `465` + `SSL/TLS` (falls `587`/STARTTLS nicht verfügbar oder vom Provider anders vorgegeben).
- Nicht verwenden: unverschlüsseltes SMTP ohne TLS.

### 3.2.1 Entscheidungsmatrix und Porttests (NetZone)

| Kriterium | `587` + STARTTLS | `465` + SSL/TLS |
|---|---|---|
| Standard für Mail Submission | Ja (bevorzugt) | Eher Legacy/Fallback |
| Upgrade auf TLS | Nach Verbindungsaufbau | Sofort beim Verbindungsaufbau |
| Odoo 18 CE Kompatibilität | Sehr gut | Sehr gut |
| Empfehlung für FCT Halwil | **1. Wahl** | 2. Wahl |

Porttests vom Odoo-Host aus (Shell):

```bash
openssl s_client -starttls smtp -connect mail.netzone.ch:587 -servername mail.netzone.ch
```

Erwartung:
- Zertifikat wird angezeigt.
- Handshake erfolgreich.
- SMTP-Antwort enthält `250 STARTTLS`.

```bash
openssl s_client -connect mail.netzone.ch:465 -servername mail.netzone.ch
```

Erwartung:
- Zertifikat wird angezeigt.
- TLS-Verbindung kommt direkt zustande.

Verbindliche Betriebsentscheidung:
1. Wenn `587`-Test erfolgreich und Odoo-`Verbindung testen` erfolgreich: Betrieb mit `587` + `STARTTLS`.
2. Wenn `587` fehlschlägt, aber `465` erfolgreich: Betrieb mit `465` + `SSL/TLS`.
3. Entscheidung (Datum, Tester, Ergebnis) unten dokumentieren.

| Datum | Getestet von | Ergebnis Port 587 | Ergebnis Port 465 | Gewählte Konfiguration |
|---|---|---|---|---|
| `<YYYY-MM-DD>` | `<Name>` | `<ok/fehler>` | `<ok/fehler>` | `<587 STARTTLS / 465 SSL/TLS>` |

### 3.3 Systemparameter prüfen (optional, empfohlen)
Unter **Einstellungen** → **Technisch** → **Systemparameter**:
- `web.base.url` = `https://odoo-prod.fcthalwil.ch`

Optional (nur wenn URL automatisch überschrieben wird):
- `web.base.url.freeze` = `True`

Hinweis: Für reinen Versand ohne eingehende Verarbeitung sind Catchall/Bounce-Aliase nicht zwingend erforderlich.

---

## Schritt 4: Absenderdaten in Odoo korrekt setzen

### 4.1 Unternehmensadresse
1. **Einstellungen** → **Unternehmen** → Firmendaten.
2. E-Mail setzen:
	- Produktion: `no-reply@fcthalwil.ch`
	- Test: `no-reply-test@fcthalwil.ch`

### 4.2 Benutzeradressen
1. **Einstellungen** → **Benutzer & Unternehmen** → **Benutzer**.
2. Für jeden relevanten Benutzer im Feld E-Mail eine gültige Adresse hinterlegen.

Wichtig:
- Der **Loginname** darf weiterhin kurz sein (`michi`, `esther`).
- Entscheidend für den Mailversand ist das **E-Mail-Feld** am Benutzer/Partner.

### 4.3 Optional: Einheitliche Absenderadresse erzwingen
Die verbindliche Erzwingung erfolgt bereits in Schritt 3.4. Mail-Templates werden zusätzlich auf Konsistenz geprüft (Schritt 5).

---

## Schritt 5: Mail-Templates prüfen
1. **Einstellungen** → **Technisch** → **E-Mail** → **Vorlagen**.
2. Relevante Vorlagen öffnen (z. B. Angebote, Rechnungen, Portal-Mails).
3. Feld **Von (E-Mail)** prüfen und bei Bedarf setzen, z. B.:

```txt
FCT Halwil <no-replay@fcthalwil.ch>
```

Im Testsystem entsprechend:

```txt
FCT Halwil Test <no-replay-test@fcthalwil.ch>
```

4. Platzhalter nur verwenden, wenn die resultierende Adresse sicher gültig ist.

### 5.1 OCA Addons: Wirkung und Grenzen
Installierte Addons:
- `mail_composer_cc_bcc`
- `mail_debrand`
- `mail_layout_preview`

Was sie typischerweise ändern:
- `mail_composer_cc_bcc`: erweitert den Composer um `Cc`/`Bcc` Felder.
- `mail_debrand`: reduziert Odoo-Branding in E-Mail-Inhalten/Links.
- `mail_layout_preview`: verbessert Vorschau/Prüfung von Mail-Layouts.

Was sie **nicht** ändern:
- Kein Wechsel der Odoo-Core-Empfängerlogik von Chatter **Send message** (Follower-/Thread-basiert).
- Keine automatische Korrektur von SMTP-Fehlern wie `Sender not owned`.
- Keine Ersetzung der in Schritt 3.4 definierten Sender-Policy.

Konsequenz für diese Anleitung:
- Für gezielte externe Tests weiter den Weg **Kontakte (Listenansicht) → Aktion → Send email** verwenden.
- Chatter **Send message** weiterhin nicht als zuverlässigen SMTP-End-to-End-Test verwenden.

---

## Schritt 6: Funktionstest durchführen
### 6.1 Testmail mit eigenem Inhalt senden
`Verbindung testen` in den SMTP-Einstellungen sendet **keine** frei editierbare Testmail mit Inhalt.

Wichtig:
- **Technisch → E-Mail → E-Mails** (`mail.mail`) ist primär eine technische Versand-Queue.
- Das Feld `body_content` ist ein berechnetes Feld und in dieser Maske nicht als normaler Composer gedacht.

Für eine echte Testmail mit frei editierbarem Inhalt stattdessen:
1. **Kontakte** öffnen.
2. In die **Listenansicht** wechseln und den Testkontakt markieren.
3. **Aktion** → **Send email** ausführen (dies ist in Odoo 18 CE standardmässig als Listenaktion auf `res.partner` gebunden).
4. Im Composer `Betreff` und Nachrichtentext erfassen und senden.
5. Danach unter **Einstellungen** → **Technisch** → **E-Mail** → **E-Mails** die erzeugte Mail prüfen:
	- `Von` = erzwungene Adresse der Umgebung
	- `Antwort an` = `@fcthalwil.ch`-Adresse des Users oder `info@fcthalwil.ch`

Wichtig für den Empfänger:
- Nicht den Chatter-Modus **Send Message** verwenden, wenn eine externe Testmail erwartet wird.
- Für SMTP-Tests immer explizit einen externen Empfänger im Composer setzen.
- Sicherstellen, dass keine Platzhalteradresse wie `admin@example.com` als Empfänger/Follower verwendet wird.

Warum das so ist (Odoo 18 CE Standardverhalten):
- Chatter **Send message** arbeitet im Kommentar-Modus (`comment`) und ruft intern `message_post` auf; adressiert werden primär Thread-/Follower-Empfänger.
- Für `res.partner` ist **Send email** als Listen-Aktion gebunden und öffnet den Mail-Composer für gezielten E-Mail-Versand.
- Deshalb kann **Send message** im Kontaktformular an Follower (z. B. Administrator) gehen statt an die erwartete Kontakt-E-Mail.

### 6.2 Wenn stattdessen `admin@example.com` angeschrieben wird
Symptom:
- Im Log erscheint z. B. `SMTPRecipientsRefused ... 'admin@example.com' ... Recipient address rejected`.

Bedeutung:
- Odoo versucht an einen Chatter-/Follower-Empfänger zu senden (häufig Default-Admin mit Platzhalteradresse), nicht an den gewünschten Testkontakt.

Prüfschritte:
1. Benutzer **Administrator** öffnen und E-Mail von `admin@example.com` auf eine gültige Adresse ändern.
2. Testkontakt öffnen und prüfen, dass Feld `E-Mail` korrekt gesetzt ist.
3. Beim Verfassen den Listen-Aktionsweg **Aktion → Send email** nutzen und Empfänger explizit kontrollieren.
4. Falls Chatter genutzt wurde: bestehende fehlerhafte Queue-Mails auf `Cancelled` setzen, dann neu testen.
5. In **Technisch → E-Mail → E-Mails** prüfen, dass `An` die gewünschte Zieladresse enthält.

Hinweis zum Logtext `SMTP server 'None'`:
- Dieser Text kann trotz verwendetem Server auftreten.
- Maßgeblich ist die Queue-Info `Sent batch ... via mail server ID #<id>` und die Mailserver-Konfiguration.

Hinweis zur UI:
- Ein separates Feld `Body (HTML)` ist in Odoo 18 bei `mail.mail` nicht als Composer-Feld vorgesehen.
- Für Inhaltstests immer den normalen E-Mail-Composer verwenden, nicht die technische Queue-Maske.

Abschlussprüfung nach Versand:
1. Unter **Einstellungen** → **Technisch** → **E-Mail** prüfen:
	- **E-Mails** (Status `Gesendet`)
	- **Mail Queue** (keine hängen gebliebenen Einträge)
2. Im Empfängerpostfach prüfen:
	- Mail angekommen?
	- Nicht im Spam?
	- Header enthält SPF/DKIM = `pass`?
	- Return-Path/Envelope-From gehört zur Domain `fcthalwil.ch`?

---

## Schritt 7: Betrieb und Monitoring

### 7.1 Geplante Aktion prüfen
1. **Einstellungen** → **Technisch** → **Automatisierung** → **Geplante Aktionen**.
2. Job für Mailversand (`Mail: Email Queue Manager` oder ähnlich) muss aktiv sein.
3. Intervall sinnvoll setzen (z. B. jede Minute), damit Mails zeitnah versendet werden.

### 7.2 Regelmässige Kontrollen
- Wöchentlich Queue prüfen (hängende Mails/Fehlertexte).
- DMARC-Reports auswerten.
- SMTP-Passwort sicher verwalten und periodisch rotieren.

---

## Troubleshooting

| Problem | Typische Ursache | Lösung |
|---|---|---|
| `Authentication failed` | Falscher SMTP-User/Passwort | Zugangsdaten prüfen, Passwort neu setzen |
| `Connection refused` | Host/Port falsch oder Firewall | SMTP-Host, Port und Netzfreigaben prüfen |
| `SMTPRecipientsRefused ... admin@example.com ... Access denied` | Falscher Empfänger (Placeholder/Follower aus Chatter) | Statt Chatter-Nachricht den E-Mail-Composer nutzen, Empfänger explizit setzen, `admin@example.com` durch gültige Adresse ersetzen |
| `5.7.1 Sender address rejected: not owned by user` | SMTP-Provider erlaubt nur Absender des authentifizierten SMTP-Users | Benutzer-E-Mail für den Test auf SMTP-Login setzen; produktiv Templates auf erlaubte Absenderadresse festlegen |
| `STARTTLS extension not supported` | Falscher Port/Sicherheitsmodus | Port/Security-Kombination korrigieren (`587` + STARTTLS oder `465` + SSL/TLS) |
| Mails landen im Spam | SPF/DKIM/DMARC fehlen oder inkonsistent | DNS korrigieren, Domain-Alignment sicherstellen |
| `Sender not allowed` | Provider erlaubt From-Adresse nicht | From-Adresse auf autorisierte Domain setzen |
| Queue bleibt hängen | Cronjob inaktiv | Geplante Aktion aktivieren und neu ausführen |

---

## Go-Live Checkliste
- [ ] SMTP-Konto `no-replay@fcthalwil.ch` (Prod) existiert und Login getestet.
- [ ] SMTP-Konto `no-replay-test@fcthalwil.ch` (Test) existiert und Login getestet.
- [ ] SPF, DKIM und DMARC sind gesetzt und per Lookup verifiziert.
- [ ] Odoo Outgoing Mail Server ist aktiv und Verbindungstest erfolgreich.
- [ ] Automatisierte Aktion `Force Outgoing Sender (mail.mail)` ist aktiv.
- [ ] Unternehmens- und Benutzer-E-Mails in Odoo sind gepflegt.
- [ ] Relevante Mail-Vorlagen haben korrekte From-Adresse.
- [ ] Externer End-to-End-Test erfolgreich (inkl. Header-Prüfung).
- [ ] Mail Queue ist leer/stabil und geplanter Mail-Job aktiv.

---

## Wartungsempfehlung
- DMARC-Policy `p=reject` beibehalten; nur für kontrollierte Analysefenster temporär entschärfen und anschliessend wieder härten.
- Änderungen an DNS und SMTP immer in dieser Datei nachführen.
- Nach jeder Odoo-Aktualisierung einen erneuten End-to-End-Mailtest ausführen.

---

## Betroffene Odoo-Tabellen (durch diese Anpassungen)

### Konfiguration und Stammdaten

| Modell | Datenbanktabelle | Zweck in dieser Anleitung | Typische betroffene Felder |
|---|---|---|---|
| `ir.mail_server` | `ir_mail_server` | Outgoing SMTP Server konfigurieren | `smtp_host`, `smtp_port`, `smtp_encryption`, `smtp_user`, `smtp_pass`, `sequence`, `active` |
| `ir.config_parameter` | `ir_config_parameter` | Systemparameter setzen | `key`, `value` (z. B. `web.base.url`, `web.base.url.freeze`) |
| `base.automation` | `base_automation` | Trigger-Regel für Sender-Policy | `name`, `model_id`, `trigger`, `active`, `action_server_id` |
| `ir.actions.server` | `ir_act_server` | Python-Code der Automatisierung | `name`, `state`, `code`, `model_id` |
| `mail.template` | `mail_template` | Absender in Templates konsistent setzen | `email_from`, `reply_to`, `body_html` |
| `res.users` | `res_users` | Benutzerdaten für Reply-To-Logik | `partner_id`, `notification_type` |
| `res.partner` | `res_partner` | Kontakt-E-Mails und Empfängerqualität | `email`, `name`, `active` |

### Laufzeit, Versand und Kontrolle

| Modell | Datenbanktabelle | Zweck in dieser Anleitung | Typische betroffene Felder |
|---|---|---|---|
| `mail.mail` | `mail_mail` | Queue und tatsächlicher ausgehender Versand | `email_from`, `reply_to`, `email_to`, `state`, `failure_reason`, `mail_server_id` |
| `mail.message` | `mail_message` | Chatter-/Composer-Nachrichten als Ausgangsbasis | `message_type`, `author_id`, `subtype_id`, `body` |
| `mail.followers` | `mail_followers` | Empfängerauflösung bei Chatter `Send message` | `res_model`, `res_id`, `partner_id`, `subtype_ids` |
| `ir.cron` | `ir_cron` | Queue-Job für Mailversand | `name`, `active`, `interval_number`, `interval_type` |

Hinweis:
- Diese Tabellenübersicht dient der Nachvollziehbarkeit, welche Odoo-Bereiche durch die beschriebenen Konfigurations- und Testschritte berührt werden.

