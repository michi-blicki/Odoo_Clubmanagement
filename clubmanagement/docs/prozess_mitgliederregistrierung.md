# Prozess Mitgliederregistrierung

## Ziel
Diese Phase fuehrt eine hierarchische Steuerung der Registrierung ein.
Jede Organisationseinheit kann die Registrierung auf ihrer Stufe als `open`, `restricted` oder `closed` steuern.

## Neue Felder
Die folgenden Modelle haben zwei Felder erhalten:

- `registration_mode`: manuelle Steuerung auf der jeweiligen Stufe
- `effective_registration_mode`: berechneter, wirksamer Modus (readonly)

Betroffene Modelle:

- `club.subclub`
- `club.department`
- `club.pool`
- `club.team`

## Werte und Bedeutung

- `open`: Registrierung ist zulaessig.
- `restricted`: Registrierung wird auf Warteliste gefuehrt.
- `closed`: Registrierung wird verhindert.
- `inherit`: nur fuer untergeordnete Stufen verfuegbar; uebernimmt und kombiniert den Modus der uebergeordneten Stufe.

## Hierarchie und Abhaengigkeit
Die Vererbung erfolgt von oben nach unten:

1. `club.subclub`
2. `club.department`
3. `club.pool`
4. `club.team`

Fuer die effektive Entscheidung gilt ein konservatives Prinzip:

- `closed` schlaegt alles
- `restricted` schlaegt `open`
- `open` gilt nur, wenn keine strengere Stufe aktiv ist

Damit kann eine untere Einheit eine strengere obere Vorgabe nicht aufweichen.

## Ablauf im Registrierungsprozess
Die API-Registrierung erfolgt ueber `/api/club/member/register`.

### Schritt 1: Eingabe und Validierung
Die Payload wird wie bisher geprueft und typkonvertiert.

### Schritt 2: Ermittlung des effektiven Registrierungsmodus
Vor dem `club.member.create()` wird aus den referenzierten Scope-Feldern (`subclub_ids`, `department_ids`, `pool_ids`, `team_ids`) der wirksame Modus berechnet.

### Schritt 3: Entscheidung

- Bei `closed`: Die API liefert `409` mit Fehlertext, es wird kein Mitglied erstellt.
- Bei `open` oder `restricted`: Erstellung wird fortgesetzt.

### Schritt 4: Statusinitialisierung und Steuerungsregel
Nach `create()` laeuft wie bisher die Initialisierung in `club.member.state.rule`.

Zusaetzlich gibt es nun eine einfache interne Steuerungsregel im Modell `club.member.state.rule`:

- effektiver Modus `restricted` -> Mitglied wird in Status `pending` verschoben (Warteliste)
- effektiver Modus `closed` -> Mitglied wird in Status `blocked` verschoben (falls State vorhanden)

Danach laufen weiterhin die konfigurierten Regeln mit `apply_on = registration`.

## Hinweise fuer den Betrieb

- Fuer produktive Prozesse sollte ein `pending`-State und ein `blocked`-State gepflegt sein.
- Die API-Antwort enthaelt jetzt zusaetzlich das Feld `registration_mode` zur Nachvollziehbarkeit.
- Die Felder sind in den Formularen und Listen der vier Organisationseinheiten sichtbar.

## Einfache Steuerungsregel im Modell
Die technische Basisregel ist direkt im Modell `club.member.state.rule` hinterlegt und arbeitet vor den benutzerdefinierten Registration-Regeln.
Sie dient als sichere Standardsteuerung fuer Warteliste und geschlossene Registrierung.
