# -*- coding: utf-8 -*-
{
    'name': "Club Management Demo: Manchester Nebula FC",

    'summary': "Creates Manchester Nebula FC, a large, fictitious football club for demo and testing purposes",

    'description': """
Club Management Demo - Manchester Nebula FC
===========================================

This module creates a comprehensive demo setup for Manchester Nebula FC, a large, 
fictitious football club based in Manchester, England. It showcases all functionalities 
of the main "clubmanagement" addon and is designed for demonstration and testing purposes.

Club Details:
-------------
* Name: Manchester Nebula FC
* Nickname: The Nebulans
* Stadium: Cosmic Park
* Motto: "Beyond the Visible"

Features:
---------
* Generates a complete football club structure for Manchester Nebula FC
* Populates the club with sample data (players, staff, teams, etc.)
* Demonstrates all features of the main clubmanagement addon
* Ideal for testing and showcasing the full capabilities of club management

This demo setup allows users to explore and test all aspects of club management 
without affecting real data, making it perfect for training, demonstrations, 
and system testing. Experience the future of football management with Manchester Nebula FC!
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
    'category': 'Sports/Football',
    'version': '18.0.1.0.1',
    'application': False,
    'auto_install': False,
    'installable': True,

    'depends': [
        'clubmanagement'
    ],

    'data': [
        'data/000_res_company.xml',
        'data/010_hr_department.xml',
        'data/020_product_product.xml',
        'data/100_club_club.xml',
        'data/110_club_subclub.xml',
        'data/120_club_department.xml',
        'data/130_club_pool.xml',
        'data/200_club_team_manchester.xml',
        'data/200_club_team_manchester_boys.xml',
        'data/200_club_team_manchester_girls.xml',
        'data/220_club_team_lucerne.xml',
        'data/300_club_club_board.xml',
        'data/310_club_subclub_board.xml',
        'data/320_club_department_board.xml',
        'data/400_club_club_role.xml',
        'data/410_club_subclub_role.xml',
        'data/420_club_department_role.xml',
        'data/430_club_pool_role.xml',
        'data/440_club_team_manchester_role.xml',
        'data/440_club_team_manchester_boys_role.xml',
        'data/440_club_team_manchester_girls_role.xml'
        'data/440_club_team_lucerne_role.xml',
        'data/500_club_member_states.xml',
        'res_users.xml',
    ],

    'demo': [

    ],

    #
    # Hooks
    'pre_init_hook': '_pre_init_hook',
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',

}

