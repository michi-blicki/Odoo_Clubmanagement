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
    'version': '18.0.1.0.0',
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
        'website',
        'partner_contact_birthdate',
        'partner_contact_gender',
        'partner_contact_nationality',
        'partner_multi_company'
    ],

    # always loaded
    'data': [
        'security/clubmanagement_groups.xml',
        'security/ir.model.access.csv',
        'views/clubmanagement_main_menu.xml',
        'views/club_config_club.xml',
#        'views/club_config_department.xml',
#        'views/club_config_pool.xml',
#        'views/club_config_subclub.xml',
#        'views/club_config_team.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    #
    # Hooks
    'pre_init_hook': '_pre_init_hook',
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',

}

