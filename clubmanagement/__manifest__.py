# -*- coding: utf-8 -*-
{
    'name': "Club Management",

    'summary': "Multi-Company Club and Association Management",

    'description': """
Long description of module's purpose
    """,

    #
    # Issuer Specification
    'author': "Michael Blickenstorfer",
    'website': "https://www.blicki.ch",
    'license': "AGPL-3",
    #'price': 120.00,
    #'currency': "CHF",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Association',
    'version': '18.0.0.2.0',
    'application': True,
    'auto_install': False,
    'installable': True,

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'account',
        'contacts',
        'hr',
        'hr_contract',
        'mail',
        'mis_builder',
        'website',
        'website_payment',
        'partner_contact_birthdate',
        'partner_contact_gender',
        'partner_contact_nationality',
        'partner_multi_company',
        'partner_firstname',
        'payroll',
    ],

    # always loaded
    'data': [
        'security/clubmanagement_groups.xml',
        'security/ir.model.access.csv',
        'security/club_club.ir_rule.xml',
        'security/club_subclub.ir_rule.xml',
        'security/club_department.ir_rule.xml',
        'security/club_pool.ir_rule.xml',
        'security/club_team.ir_rule.xml',
        'security/club_role.ir_rule.xml',
        'security/club_api_config.ir_rule.xml',
        'security/res_partner.ir_rule.xml',
        'views/contacts_contacts.xml',
        'views/club_00_menu_root.xml',
        'views/club_20_menu_members.xml',
        'views/club_20_view_member_form.xml',
        'views/club_20_view_member_active.xml',
        'views/club_20_view_member_archived.xml',
        'views/club_20_view_member_blocked.xml',
        'views/club_20_view_member_deleted.xml',
        'views/club_20_view_member_waiting.xml',
        'views/club_20_view_member_all.xml',
        'views/club_30_menu_memberships.xml',
        'views/club_50_menu_organisation.xml',
        'views/club_50_view_department.xml',
        'views/club_50_view_pool.xml',
        'views/club_50_view_team.xml',
        'views/club_80_menu_administration.xml',
        'views/club_80_view_audit_log.xml',
        'views/club_80_view_boards.xml',
        'views/club_80_view_club.xml',
        'views/club_80_view_custom_field.xml',
        'views/club_80_view_memberships.xml',
        'views/club_80_view_memberstates.xml',
        'views/club_80_view_memberstate_rules.xml',
        'views/club_80_view_roles.xml',
        'views/club_80_view_subclub.xml',
        'views/club_80_view_apisettings.xml',
        'views/club_10_menu_dashboard.xml',
        'views/res_config_settings_view.xml',
    ],

    'translation_files': [
        'i18n/de_CH.po',
        'i18n/de_DE.po',
        'i18n/fr_FR.po',
        'i18n/it_IT.po',
    ],

    'assets': {
        'web.assets_backend': [
            'clubmanagement/static/src/scss/club_kanban.scss',
            'clubmanagement/static/src/js/club.dashboard.js',
            'clubmanagement/static/src/xml/club_dashboard_templates.xml'
        ],
    },

    # only loaded in demonstration mode
    'demo': [
        
    ],

    #
    # Hooks
    'pre_init_hook': '_pre_init_hook',
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',

}

