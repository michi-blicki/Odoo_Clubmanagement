# Club Management for Odoo

A flexible Odoo module for club and association management with granular role assignment and dynamic permissions.

==THIS ADDON IS CURRENTLY UNDER DEVELOPMENT - DO NOT USE YET==

| Author | Michael Blickenstorfer |
| Version | 18.0.1.0.0 alpha |
| Created | 2025-11-24 |
| Last Update | 2025-11-25 |

## Features

- **Member Management**: Comprehensive member records with complete membership history.
- **Analytical Fields**: Age, year of birth, and days/years in the club, correctly calculated even with multiple memberships or break periods.
- **OCA Integration**: Fields for birthdate, gender, and nationality directly integrated using [partner_contact_birthdate](https://github.com/OCA/partner-contact), [partner_contact_gender](https://github.com/OCA/partner-contact), and [partner_contact_nationality](https://github.com/OCA/partner-contact).
- **Flexible Organization Structure**: Support for Boards, Departments, Pools, and Teams.
- **Advanced Role Model**: Create and assign leadership, assistant, administrative, and special roles per organizational unit.
- **Granular Backend/Web Permissions**: Access control down to exact units and roles; clubs may define custom permission schemes to match their structure.
- **Maximum Flexibility**: Each club can define its own organizational structure, roles, and permissions in the backend.

## Architecture

### Club Member

The `club.member` model represents a club member and includes:
- Link to Odoo contact (`res.partner`)
- Membership roles (`role_ids`)
- Pointers to organizational units (`department_id`, `pool_id`, `team_id`, etc.)

**Analytical Fields:**
- Year of birth and age (calculated from birthdate)
- Club affiliation in days/years (summed across all periods of active membership)

### Role Model (`club.role`)

**Generic & Extensible**:
- Each function or role is defined with the `club.role` model, including a type (`Leader`, `Assistant`, `Admin`, etc.) and its scope (`Board`, `Department`, `Pool`, `Team`)
- Roles are assigned to members via a `Many2many` relation (`role_ids`)
- Organizations are free to configure any role structure in the backend, without code changes

## Permission & Access Control
- Rights are managed dynamically via roles and their corresponding organizational units
- E.g.: A Department Leader can only see and edit members of their department; a Pool Leader only those of their pool, etc.
- Record rules and domains are generated based on role assignments—no hardcoded groups required!
- All customizable: easy read-only access for partners, full control for designated admin users, and fine-grained per-unit rights

### Sample dynamic domain
```python
domain = [
    ('role_ids.scope_type', '=', 'department'),
    ('role_ids.department_id', '=', current_department_id),
    ('role_ids.role_type', '=', 'lead')
]
```

## OCA Integration
This module leverages:
- [partner_contact_birthdate](https://github.com/OCA/partner-contact)
- [partner_contact_gender](https://github.com/OCA/partner-contact)
- [partner_contact_nationality](https://github.com/OCA/partner-contact)

## Installation
* Clone full repository to some download area
* Copy addons to custom addons folder (see addon_path in odoo.conf)
* Clone all required OCA addons
* Restart Odoo Server
* Install either via Odoo frontend or with `odoo-bin -d <database> -c <odoo.conf> -i clubmanagement`
* Start customizing