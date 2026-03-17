# Copilot Instructions – clubmanagement (Odoo 18 CE)

## Zweck dieser Datei
Diese Datei ist der operative Wiedereinstieg für dieses Add-on.
Sie ist bewusst **kritisch, hinterfragend und faktenbasiert** aufgebaut.

## Arbeitsmodus (verbindlich)
1. **Keine Annahmen treffen.** Nur auf Basis von Code, Manifest, Security-Regeln und dokumentierten Anforderungen arbeiten.
2. **Bei Unklarheit immer Rückfragen stellen**, bevor Code geändert wird.
3. **Enterprise-Level Qualität** einhalten: Sicherheit, Nachvollziehbarkeit, saubere Migration, keine Quick-Fixes.
4. **Scope diszipliniert halten**: nur Standard-Odoo + OCA, keine zusätzlichen Fremdabhängigkeiten ohne explizite Freigabe.
5. Add-on ist **in Entwicklung / Pre-Alpha**: Änderungen immer mit Regression-Risiko einschätzen.
6. **Sprache Textbausteine**: Textelemente werden im Sourcode immer in Englisch formulert. Texte werden erst in der Übersetzungsphase in andere Sprachen übersetzt. Es gibt ausschliesslich englische Textelemente im Code.

## Faktenlage (Stand Codebasis)
- Modul: `clubmanagement`
- Odoo-Version: 18
- Edition-Ziel: Community Edition
- Manifest-Version: `18.0.0.4.0`
- Lizenz im Manifest: `AGPL-3`
- README-Status: „under heavy development / do not use yet"
- Zielgruppe laut README: grosse, enterprise-ähnliche Vereine

## Technischer Überblick (nur verifizierte Punkte)
### Kernbereiche
- Domänenmodell: Club, Subclub, Department, Pool, Team, Member, Role, Membership, Member-State(-History/-Rules), Custom Fields.
- Member-Modell nutzt `_inherits` mit `res.partner`.
- Sicherheit auf mehreren Ebenen:
  - Gruppen + ACL (`security/clubmanagement_groups.xml`, `security/ir.model.access.csv`)
  - Record Rules pro Organisationsobjekt
  - zusätzlicher Python-Sicherheitsmixin (`club.security.mixin`) für Create/Write/Unlink-Entscheidungen.
- API-Ebene vorhanden:
  - Registrierung: `/api/club/member/register`
  - Lookups: Companies/Countries/States/Languages/API-Fields
  - Security-Mixin für Rate-Limit, CORS, Response-Härtung.

### Wichtige Betriebslogik
- Mitgliedserstellung erzeugt bei Bedarf implizit `res.partner` und vergibt fortlaufende `member_id`.
- State-Regeln können bei Registrierung und periodisch per Cron greifen.
- API-Felder sind über `club.api.config` + `club.field.mixin` konfigurierbar.

## Datenmodell – Kern und Abhängigkeiten (verifiziert)
Dieser Abschnitt ist die zentrale Referenz für fachliche und technische Änderungen.

### 1) Organisationsstruktur (hierarchischer Kern)
- `club.club`
   - 1:n auf `club.subclub`, `club.department`, `club.pool`, `club.team`, `club.board`, `club.role`
   - m:n auf `club.member` über `club_club_member_rel`
- `club.subclub`
   - m:1 auf `club.club`
   - 1:n auf `club.department`, `club.board`, `club.role`
   - m:n auf `club.member` über `club_subclub_member_rel`
- `club.department`
   - m:1 auf `club.club`
   - m:1 optional auf `club.subclub`
   - 1:n auf `club.pool`, `club.team`, `club.board`, `club.role`
   - m:n auf `club.member` über `club_department_member_rel`
- `club.pool`
   - m:1 auf `club.department` (fachlich unterhalb Department)
   - 1:n auf `club.team`, `club.role`
   - m:n auf `club.member` über `club_pool_member_rel`
- `club.team`
   - m:1 auf `club.department`
   - m:1 optional auf `club.pool`
   - 1:n auf `club.role`
   - m:n auf `club.member` über `club_team_member_rel`

### 2) Mitglied, Rollen, Status, Mitgliedschaft
- `club.member`
   - `_inherits = {'res.partner': 'partner_id'}` (Contact ist technischer Primäranker)
   - m:1 auf `club.club`
   - m:n auf `club.subclub`, `club.department`, `club.pool`, `club.team`
   - 1:n auf `club.role`, `club.member.guardian`, `club.member.membership.history`, `club.member.state.history`
   - m:1 berechnet auf `club.member.membership` (`current_membership_id`)
   - m:1 berechnet auf `club.member.state` (`current_state_id`)
- `club.role`
   - optional m:1 auf Scope-Objekte (`club`, `board`, `subclub`, `department`, `pool`, `team`)
   - optional m:1 auf `club.member` (Rolle einem Mitglied zuweisen)
   - enthält die fachlichen Berechtigungsflags (`perm_read/write/create/unlink/mail`)
- `club.member.membership`
   - 1:n auf `club.member.membership.history`
   - 1:n auf `club.member.membership.additional.product`
   - erzeugt dynamische Menüs/Aktionen (Modell `club.member.membership.menu`)
- `club.member.membership.history`
   - m:1 auf `club.member`
   - m:1 auf `club.member.membership`
- `club.member.state`
   - Stammdatenmodell für Member-Status (registered/pending/active/...)
- `club.member.state.history`
   - m:1 auf `club.member`
   - m:1 auf `club.member.state`
- `club.member.state.rule`
   - m:1 auf Zielstatus `club.member.state`
   - erzeugt optional `ir.cron` und schreibt `club.member.state.history`

### 3) Dynamische Felder und API-Feldfreigaben
- `club.custom.field`
   - m:1 auf `club.club`
   - m:n auf `res.company`
   - definiert zusätzliche Felder für Modelle (`club.member`, `club.team`, `club.pool`, `club.department`, `club.subclub`, `club.club`)
- `club.custom.field.value`
   - m:1 auf `club.custom.field`
   - Werte je Datensatz über (`model`, `res_id`) gespeichert
- `club.field.mixin`
   - vereinheitlicht Systemfelder (`ir.model.fields`) und Custom Fields (`club.custom.field`)
   - zentrale Quelle für API-Feldselektion
- `club.api.config`
   - m:1 auf `club.club`, m:n auf `res.company`, m:1 auf `res.users` (API-User)
   - m:n auf `club.field.mixin` über `allowed_fields`

### 4) Externe Modellabhängigkeiten (fachlich relevant)
- Kontakt/Identity: `res.partner`, `res.users`, `res.company`, `res.country`, `res.country.state`, `res.lang`
- HR: `hr.employee`, `hr.department`, `hr.contract`, `payroll`
- Accounting/Analytic: `account.*`, `account.analytic.account`, `mis_builder`
- Membership Pricing: `product.product`, `res.currency`
- Framework/Infra: `mail.thread`, `mail.activity.mixin`, `ir.cron`, `ir.actions.act_window`, `ir.ui.menu`

### 5) Abhängigkeitsregeln für Änderungen (arbeitspraktisch)
Wenn eines der folgenden Modelle geändert wird, müssen die genannten Nachbarbereiche mitgeprüft werden:
- Änderung an `club.member` -> prüfen: `res.partner`, `club.role`, Membership-History, State-History, API `register_member`.
- Änderung an `club.role` oder Berechtigungsflags -> prüfen: `club.security.mixin`, Record Rules, ACL-Matrix, API-User-Flows.
- Änderung an `club.department`/`club.pool`/`club.team` -> prüfen: Aggregationen `member_ids_display`, Rollenvererbung, Such-Scopes im Security-Mixin.
- Änderung an Membership-Modellen -> prüfen: dynamische Menüs/Aktionen (`club.member.membership.menu`) und Historienkonsistenz.
- Änderung an `club.custom.field*` oder `club.field.mixin` -> prüfen: API-Allowed-Fields, Typvalidierung, Unique-Constraints.

### 6) ASCII-ER-Übersicht (Schnellzugriff)
Hinweis: Fokus auf fachlich zentrale Beziehungen; technische Mixins/Tracking-Modelle sind bewusst nicht vollständig ausgeschrieben.

#### 6.1) ASCII-ER ultrakompakt (15 Zeilen, Prompt-Start)

```text
[club.club] -> [club.subclub] -> [club.department] -> [club.pool] -> [club.team]
[club.club] -> [club.board], [club.role]
[club.subclub] -> [club.board], [club.role]
[club.department] -> [club.board], [club.role], [club.team]
[club.pool] -> [club.role], [club.team]
[club.team] -> [club.role]
[res.partner] ==_inherits== [club.member]
[club.member] -> [club.role] (member_id optional)
[club.member] -> [club.member.membership.history] -> [club.member.membership]
[club.member] -> [club.member.state.history] -> [club.member.state]
[club.member] -> [club.member.guardian] -> [res.partner]
[club.member] <-> [club.club|subclub|department|pool|team] (M:N rel tables)
[club.custom.field] -> [club.custom.field.value] by (model,res_id)
[club.api.config] <-> [club.field.mixin] ; [club.api.config] -> [club.club|res.company|res.users]
[club.member.state.rule] -> [club.member.state] ; writes [club.member.state.history] ; optional [ir.cron]
```

#### 6.2) ASCII Security-Scope ultrakompakt (Prompt-Start)

```text
SECURITY LAYERS
1) ACL: security/ir.model.access.csv
2) Record Rules: security/*.ir_rule.xml
3) Python Scope: club.security.mixin (search/create/write/unlink gatekeeping)

USER -> MEMBER -> ROLES -> SCOPES
[res.users.partner_id] -> [club.member] -> [club.role]
[club.role.scope_type] in {club, subclub, department, pool, team, board}
[club.role perms] = {perm_read, perm_write, perm_create, perm_unlink, perm_mail}

SCOPE EXPANSION LOGIC
club scope      => all linked org units under club
subclub scope   => departments/pools/teams under subclub
department scope=> pools/teams in department
pool scope      => teams in pool
team scope      => direct team members

HIGH-RISK CHECKPOINTS
sudo/with_user/direct SQL can bypass intended scope
API user must be constrained to group_clubmanagement_api_user
changes in role flags must be validated against ACL + record rules
```

#### 6.3) ASCII-ER detailliert (komplett, Prompt-Ende)
```text
ORGANISATIONSKERN

[club.club] 1---n [club.subclub] 1---n [club.department] 1---n [club.pool] 1---n [club.team]
     |                  |                    |                    |                 |
     |                  |                    |                    |                 +---n [club.role]
     |                  |                    |                    +---n [club.role]
     |                  |                    +---n [club.team]
     |                  |                    +---n [club.board]
     |                  |                    +---n [club.role]
     |                  +---n [club.board]
     |                  +---n [club.role]
     +---n [club.board]
     +---n [club.role]

MITGLIEDER & ROLLEN

[res.partner] 1---1 [club.member]   (_inherits via partner_id)
   ^                |   \ \
   |                |    \ +---n [club.member.state.history] n---1 [club.member.state]
   |                |     +---n [club.member.membership.history] n---1 [club.member.membership]
   |                |     +---n [club.member.guardian] n---1 [res.partner] (guardian)
   |                +---n [club.role] (member_id optional)
   |
   +--- [res.users] -> verknüpft indirekt über user.partner_id (Security-Scope)

M:N-ZUORDNUNGEN MEMBER <-> ORG-EINHEITEN

[club.member] n---m [club.club]       (club_club_member_rel)
[club.member] n---m [club.subclub]    (club_subclub_member_rel)
[club.member] n---m [club.department] (club_department_member_rel)
[club.member] n---m [club.pool]       (club_pool_member_rel)
[club.member] n---m [club.team]       (club_team_member_rel)

CUSTOM FIELDS & API

[club.custom.field] 1---n [club.custom.field.value] (pro model + res_id)
    |  
    n---m [res.company]
    |
    +--> über [club.field.mixin] (system/custom vereinheitlicht)

[club.api.config] n---m [club.field.mixin] (allowed_fields)
[club.api.config] n---1 [club.club]
[club.api.config] n---m [res.company]
[club.api.config] n---1 [res.users] (api user)

STATE-AUTOMATION

[club.member.state.rule] n---1 [club.member.state] (new_state_id)
[club.member.state.rule] 1---0..1 [ir.cron]
[club.member.state.rule] --(writes)--> [club.member.state.history]
```

## Kritische Prüfpunkte vor jeder Änderung
1. **Sicherheitsauswirkung**
   - Welche Gruppen/Record-Rules sind betroffen?
   - Hebelt Code ACL/Rules aus (z. B. `sudo`, `with_user`, direkte SQL)?
2. **Mehrfirmen-/Mandantenfähigkeit**
   - Ist `company_id` korrekt gesetzt/gefiltert?
   - Leaken Daten über Company-Grenzen?
3. **Datenkonsistenz**
   - Entstehen Dubletten bei Member/Partner?
   - Bleiben Historien (State/Membership/Log) konsistent?
4. **API-Härtung**
   - Input validiert? Feldtyp korrekt? Fehlercodes konsistent?
   - Rate-Limit/CORS/HTTPS-Konfiguration berücksichtigt?
5. **Upgrade-/Migrationsfähigkeit**
   - Feldänderung kompatibel? Hook-/Init-Verhalten stabil?

## Verpflichtende Rückfragen (wenn unklar)
Bei fehlendem Kontext **immer zuerst fragen**, z. B.:
- Soll Verhalten für bestehende Daten migriert oder nur für Neudaten gelten?
- Welche Benutzergruppen/Companies müssen explizit Zugriff behalten oder verlieren?
- Ist die Änderung API-kompatibel (Backward Compatibility) erforderlich?
- Gibt es OCA-Standardmuster, die zwingend einzuhalten sind?
- Ist eine temporäre Lösung erlaubt oder nur produktionsreife Umsetzung?

## Aktuell sichtbare Inkonsistenzen / offene Risiken
Diese Punkte sind im aktuellen Stand erkennbar und sollten vor grösseren Änderungen geklärt werden:
1. **State-Rule Engine**: Regel-`condition` wird per `eval` ausgeführt (hohes Sicherheits-/Stabilitätsrisiko).

## Arbeitsreihenfolge für künftige Tasks
1. Anforderung präzisieren (Rückfragen, Akzeptanzkriterien, betroffene Rollen/Companies).
2. Betroffene Modelle/Views/Security/API lokalisieren.
3. Risikoanalyse (Security, Multi-Company, Datenhistorie).
4. Minimal-invasive Änderung umsetzen.
5. Validieren (Install/Update, Rechte, API-Pfade, relevante Flows).
6. Ergebnis + offene Punkte dokumentieren.

## Dateien für schnellen Wiedereinstieg
- `__manifest__.py`
- `__init__.py`
- `models/clubmember.py`
- `models/club_security_mixin.py`
- `models/clubmember_state_rule.py`
- `models/clubapiconfig.py`
- `models/res_config_settings.py`
- `controllers/club_member_api.py`
- `controllers/club_lookup_api.py`
- `controllers/club_api_security_mixin.py`
- `security/clubmanagement_groups.xml`
- `security/ir.model.access.csv`

## Qualitätsstandard für Copilot in diesem Add-on
- Keine stillen Architekturänderungen.
- Keine implizite Rechteausweitung.
- Keine neuen Abhängigkeiten ohne Begründung.
- Keine Annahmen über Vereinsprozesse ohne Rückfrage.
- Immer transparent markieren: Fakt, Risiko, offene Frage, Entscheidung.
