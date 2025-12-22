=================================
Club Management
=================================

**Actually under heavy development - do not use it yet!**

The Club Management Addon allows you to manage your club or association with Odoo – flexible and fully customizable, designed for large, enterprise-like organizations.

This module is fully developped to be compliant with Odoo Community Edition.

Key Features
============

- Highly flexible multi-level club structure
- Custom fields for nearly all entities
- Automated membership tracking with product integration
- Granular access rights and club roles
- Centralized member state and history tracking
- Integration with Odoo contacts, HR, and mail
- Backend, Website interface and External API

Table of Contents
=================

.. contents:: 
   :local:

Usage
=====

1. Meet the requirements: Pillow
2. Setup Companies in **Settings** => **User & Companies** => **Companies**
    * Also setup Subcompanies, if required by your association.
3. Install the **clubmanagement** module. It depends on many CE mdules:
    * 'base',
    * 'account',
    * 'contacts',
    * 'hr',
    * 'hr_contract',
    * 'mail',
    * 'mis_builder',
    * 'website',
    * 'website_payment',
    * 'partner_contact_birthdate',
    * 'partner_contact_gender',
    * 'partner_contact_nationality',
    * 'partner_multi_company',
    * 'partner_firstname'

4. Setup **HR Departments** in Employees => Departments, if you would like to use them for payed employees and contracting
5. Create your **Club/Association** in **Clubmanagement** => **Administration**
    * do not forget to push the "Create Default Roles and Boards" button
6. If your organization has multiple Subclubs, like within a group company, create these now and associate them with the according companies
7. Create the **Departments** and associate them with **HR Departments** if in use
8. Create the **Roles** required by your association.

more to follow... It will be a long list once finished ;)


Screenshots
===========

.. image:: https://raw.githubusercontent.com/DEIN-USER/DEIN-REPO/BRANCH/docs/img/configuration.png
   :width: 600px

.. image:: https://raw.githubusercontent.com/DEIN-USER/DEIN-REPO/BRANCH/docs/img/membership.png
   :width: 600px

Documentation
=============

- Full documentation: See the `/docs` folder in this repository.
- API reference: [Link to /docs/api.rst or your docs site]

Known Issues / Roadmap
======================

- Actually in Pre-Alpha-Phase and under heavy development.
- Automations support coming soon
- Member import/export improvements planned

Languages
=========

- English: development language
- German: automatically translated and manually checked
- French: automatically translated
- Italian: automatically translated

Bug Tracker & Support
=====================

If you encounter problems, please use the [issues tracker]https://github.com/michi-blicki/Odoo_Clubmanagement/) on GitHub.

**For enterprise support:** There is currently no enterprise support.

Maintainer
==========

This module is maintained by **Michael Blickenstorfer**

contact: michi@blicki.ch

GitHub: https://github.com/michi-blicki/Odoo_Clubmanagement.git

License
=======

LGPL-3.0; see the `LICENSE` file.

