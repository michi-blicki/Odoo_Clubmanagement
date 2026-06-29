# Technische Spezifikation: club.member.state.rule

## Ziel
Dieses Dokument beschreibt die technische Zielarchitektur fuer das Rule Framework auf dem Modell club.member.state.rule.

Das Framework soll:
- Regeln periodisch oder bei Registrierung ausfuehren.
- Pro Regel eine Bedingung auswerten.
- Bei wahrer Bedingung einen frei definierbaren Python-Action-Code ausfuehren.
- Optional die weitere Rule-Verarbeitung pro Mitglied stoppen.

Das Dokument ist so formuliert, dass danach direkt die Implementierung im Python-Modell und in den Views erfolgen kann.

## Scope
In Scope:
- Erweiterung des Modells club.member.state.rule.
- Anpassung der Rule-Ausfuehrungslogik.
- Anpassung der Form- und Listen-Views fuer Rule-Konfiguration.
- Logging und Fehlerverhalten waehrend Rule-Ausfuehrung.

Nicht in Scope:
- Migrationsschritte.
- Erweiterung externer Module ausserhalb clubmanagement.

## Ist-Zustand (Kurz)
Der aktuelle Stand stellt bereits Folgendes bereit:
- apply_on mit registration und periodic.
- Cron-Erstellung fuer periodic-Regeln.
- condition wird mit eval ausgewertet.
- Bei Treffer wird new_state_id ueber _change_member_state gesetzt.
- Registrierung ruft _apply_registratoin_rules fuer neue Mitglieder auf.

Aktuelle Einschraenkung:
- Es gibt keinen separaten Action-Code fuer beliebige Aktionen.
- Es gibt kein Stop-Flag fuer Short-Circuit-Verhalten.
- Die Ausfuehrung nutzt eval statt safe_eval.

## Zielmodell: Datenfelder
Folgende Felder sollen auf club.member.state.rule vorhanden sein.

### Bestehende Felder (bleiben erhalten)
- name: Char, Pflicht
- sequence: Integer, Pflicht
- active: Boolean
- apply_on: Selection (registration, periodic)
- cron_id: Many2one auf ir.cron, readonly
- condition: Text

### Neue Felder
1. action_code
- Typ: Text
- Pflicht: Ja
- Zweck: Wird nur ausgefuehrt, wenn die Bedingung true ist.
- Hinweis: Action-Code wird per safe_eval im exec-Modus ausgefuehrt.

2. stop_processing_on_match
- Typ: Boolean
- Default: False
- Zweck: Stoppt weitere Regeln fuer dasselbe Mitglied, wenn diese Regel matcht und erfolgreich ausgefuehrt wurde.

3. continue_on_error
- Typ: Boolean
- Default: True
- Zweck: Definiert, ob bei Fehler in condition/action fuer dieses Mitglied mit der naechsten Regel weitergearbeitet wird.

4. member_domain
- Typ: Char oder Text
- Default: []
- Zweck: Optionaler Odoo-Domain-Filter fuer Zielmitglieder.
- Anwendung:
  - periodic: Domain wird auf Gesamtmenge angewandt.
  - registration: Domain wird auf uebergebene neue Mitglieder angewandt.

5. execution_note
- Typ: Text, readonly
- Zweck: Letztes kompaktes Ausfuehrungsresultat fuer Admin-Transparenz (z. B. letzte Ausfuehrung, Trefferzahl, Fehlerzahl).

6. error_notify_member_id
- Typ: Many2one auf club.member
- Pflicht: Nein
- Zweck: Optionaler Empfaenger fuer Fehlerbenachrichtigungen, wenn continue_on_error=False und eine Regel fuer ein Mitglied fehlschlaegt.

## Ausfuehrungskontext fuer safe_eval
Fuer condition und action wird ein definierter Kontext bereitgestellt.

Pflichtvariablen:
- env: Odoo Environment
- member: club.member Datensatz (single record)
- rule: aktuelle club.member.state.rule
- datetime: datetime Modul
- date: date Klasse
- time: time Modul
- log: Helper-Funktion fuer strukturierte Rule-Logs

Optional:
- result: dict fuer Werte, die condition fuer action vorbereiten kann

Nicht erlaubt:
- Direkter Zugriff auf builtins ausser Whitelist.
- Kein unkontrollierter globaler Namespace.

## Zielmethoden im Modell

### 1) _get_safe_eval_context
Signatur:
- def _get_safe_eval_context(self, member):

Verhalten:
- Baut den eval/exec-Kontext fuer genau ein Mitglied.
- Enthaltet log-Callback fuer standardisierte Eintraege in _logger und optional club.log.

### 2) _eval_condition
Signatur:
- def _eval_condition(self, member):

Rueckgabe:
- dict mit:
  - matched: bool
  - aux: dict

Verhalten:
- condition muss bool liefern.
- Bei Typfehlern: ValidationError mit klarer Rule-Meldung.

### 3) _execute_action_code
Signatur:
- def _execute_action_code(self, member, eval_result):

Verhalten:
- action_code ist Pflichtfeld und wird bei Match immer ausgefuehrt.
- Sonst safe_eval im exec-Modus.
- Kontext enthaelt eval_result und ggf. result-dict.

### 4) _execute_match_effects
Signatur:
- def _execute_match_effects(self, member, eval_result):

Verhalten:
- Fuehrt ausschliesslich _execute_action_code aus.
- State-Aenderungen erfolgen nur explizit ueber action_code.

### 5) _process_rule_for_member
Signatur:
- def _process_rule_for_member(self, member):

Rueckgabe:
- dict mit:
  - matched: bool
  - stopped: bool
  - error: str oder False

Verhalten:
- Evaluiert condition.
- Bei Match: fuehrt Match-Effekte aus.
- Setzt stopped gemaess stop_processing_on_match.
- Fehlerbehandlung gemaess continue_on_error.
- Wenn continue_on_error=False und error_notify_member_id gesetzt ist:
  - Versand einer Fehlerbenachrichtigung per wiederverwendbarem mail.template an die Kontakt-E-Mail des referenzierten Mitglieds.
  - Mindestinhalt der Mail: rule name und member.
  - Vollstaendiger Traceback wird im Log persistiert.

### 6) _apply_rule
Signatur:
- def _apply_rule(self, members):

Verhalten:
- Erwartet Recordset von club.member.
- Wendet optional member_domain an.
- Iteriert Mitglieder und ruft _process_rule_for_member auf.
- Liefert aggregierte Statistik.

### 7) _run_rule
Signatur:
- def _run_rule(self, rule_id):

Verhalten:
- Fuer cron-Run.
- Laedt Regel, prueft active.
- Kandidatenmenge ist nicht auf active=True eingeschraenkt.
- Ruft _apply_rule auf.
- Schreibt execution_note.

### 8) _apply_registration_rules
Signatur bleibt:
- def _apply_registration_rules(self, members):

Verhalten:
- Bestehende Initialisierung registered-State bleibt.
- Bestehendes Registration-Mode-Steering bleibt.
- Regeln mit apply_on=registration werden in sequence-Reihenfolge verarbeitet.
- Neu: Verarbeitung pro Mitglied mit Short-Circuit:
  - Fuer jedes member alle Regeln nacheinander.
  - Wenn eine Regel matched und stop_processing_on_match=True, keine weiteren Regeln fuer dieses member.

Hinweis:
- Der Tippfehler im Methodennamen wird in dieser Iteration korrigiert.
- Zielname: _apply_registration_rules.
- Fuer Rueckwaertskompatibilitaet bleibt temporaer ein delegierender Alias _apply_registratoin_rules bestehen.

## Rule-Verarbeitung: Soll-Ablauf
1. Input-Menge members bestimmen.
2. Regeln laden:
- active=True
- apply_on passend zu Trigger
- sortiert nach sequence, id
3. Pro Mitglied:
- Pro Regel:
  - condition auswerten
  - falls matched:
    - Action-Code
    - bei stop_processing_on_match: break fuer dieses Mitglied
  - bei Fehlern:
    - wenn continue_on_error=True: weiter
    - sonst: Abbruch nur fuer dieses Mitglied
    - zusaetzlich klare Fehlermeldung in Log und optional Mail an error_notify_member_id
4. Laufstatistik und execution_note aktualisieren.

## Sicherheitsanforderungen
- Nutzung von odoo.tools.safe_eval statt eval.
- Fuer condition:
  - safe_eval im eval-Modus.
- Fuer action_code:
  - safe_eval im exec-Modus.
- Strikte Kontextkontrolle und kein Durchreichen unkontrollierter Objekte.
- Fehlernachrichten duerfen keine sensiblen Daten enthalten.
- Keine zusaetzlichen Guardrails auf Model/Methoden-Ebene (fachlicher Entscheid).

## Logging und Transparenz
Minimales Logging pro Lauf:
- rule id/name
- trigger (periodic oder registration)
- anzahl gepruefter Mitglieder
- anzahl matches
- anzahl action executes
- anzahl errors

Speicherung:
- execution_note enthaelt letzte kompakte Zusammenfassung.
- Ausfuehrliche Details in _logger.
- Fehlerfaelle enthalten den vollstaendigen Traceback im Log.

## Dry-Run/Testmodus
- Der Dry-Run wird ueber einen Wizard im Backend aufgerufen.
- Der Wizard zeigt pro Mitglied, welche Regeln matchen und welche Action ausgefuehrt wuerde.
- Im Dry-Run sind write/create/unlink-Seiteneffekte zu unterdruecken.
- Ausgabe als Ergebnisliste im Wizard (keine persistente Aenderung).

## View-Anpassungen (Soll)

### Form-View fuer club.member.state.rule
Neue/angepasste Bereiche:
1. Bereich Trigger
- apply_on
- active
- sequence
- cron_id readonly

2. Bereich Condition
- condition (Code-Editor-Widget, Monospace, volle Breite)
- member_domain

3. Bereich Effects
- action_code (Code-Editor-Widget)

4. Bereich Flow Control
- stop_processing_on_match
- continue_on_error

5. Bereich Monitoring
- execution_note readonly
- error_notify_member_id

Usability:
- Kontext-Hinweis ueber verfuegbare Variablen im Condition/Action-Code.
- Placeholder-Beispiele fuer boolesche Bedingungen.

### List-View fuer club.member.state.rule
Spalten:
- sequence
- name
- active
- apply_on
- stop_processing_on_match
- continue_on_error
- error_notify_member_id

Optional:
- Farbliche Kennzeichnung inaktive Regeln.

## Beispiele fuer Rule-Konfigurationen

### Beispiel A: Nur Statuswechsel bei weiblich
- condition:
  - member.gender == 'female'
- action_code:
  - env['club.member.state.rule']._change_member_state(member, env['club.member.state'].search([('state_type', '=', 'pending')], limit=1), 'Auto state by rule')
- stop_processing_on_match: False

### Beispiel B: Männlich bis 14 und Mail-Action
- condition:
  - member.gender == 'male' and member.age is not False and member.age <= 14
- action_code:
  - env['mail.mail'].sudo().create({...}).send()
  - oder Aufruf eines kapselnden Helper-Services im Addon
- stop_processing_on_match: True

### Beispiel C: Dry-Run/Testmodus
- Ausfuehrung in einem expliziten Testmodus ohne write/create.
- Rueckgabe je Mitglied mit Liste der Regeln, die matchen wuerden.
- Keine persistenten Aenderungen, nur Simulationsergebnis.

### Beispiel D: Jede Registrierung, Mail an fixe Adresse
- apply_on:
  - registration
- condition:
  - True
- action_code:
  - template = env.ref('clubmanagement.mail_template_club_member_state_rule_error', raise_if_not_found=False)
  - if template:
      template.with_context(
        club_rule_error_member_name=member.display_name,
        club_rule_error_member_id=member.id,
        club_rule_error_message='Neue Registrierung',
        club_rule_error_trace='',
      ).send_mail(
        rule.id,
        force_send=False,
        email_values={'email_to': 'finanzen@fcthalwil.ch'},
      )
- stop_processing_on_match:
  - False

## Akzeptanzkriterien
1. Regeln mit apply_on=periodic laufen ueber cron.
2. Regeln mit apply_on=registration laufen bei Registrierung.
3. condition kann sicher ausgewertet werden.
4. action_code kann sicher ausgefuehrt werden.
5. stop_processing_on_match beendet die Rule-Kette pro Mitglied.
6. continue_on_error steuert Fehlerfortsetzung.
7. Views erlauben vollstaendige Konfiguration ohne Codeaenderung im Python-File.
8. condition liefert ausschliesslich bool und wird einheitlich ausgewertet.
9. Action-Ausfuehrungen werden als strukturierte Events in club.log persistiert.
10. Es gibt einen Dry-Run/Testmodus mit Ergebnis pro Mitglied.
11. Tippfehler in _apply_registratoin_rules wird korrigiert (neuer Zielname: _apply_registration_rules).
12. Feld reason wird aus club.member.state.rule entfernt.

## Offene Fragen
Aktuell keine offenen Fragen.
