# -*- coding: utf-8 -*-

from . import controllers
from . import models

from datetime import date

import logging
_logger = logging.getLogger(__name__)


from .models.club_member_postinit import generate_club_members

def _pre_init_hook(env):
    _logger.info(f"_pre_init_hook(): Start")
    _logger.info(f"_pre_init_hook(): End")

def _post_init_hook(env):
    _logger.info(f"_post_init_hook(): Start")

    """
        Club Member Generation
        ----------------------------------------------
        As we need a whole lot of members, there is no
        way to use data files. Therefore, we implement
        a function to models/club_member_postinit.py,
        that will generate club.member and res.partner
        for us based on random names and birthdates.

        Still, we need to specify the teams, these
        members belong to. This will be done here.

        We actually support a range of
        - 50 male prenames
        - 50 female prenames
        - 120 lastnames
        This makes a unique range of:
        - 6000 male players
        - 6000 female players
        which is far enough to generate a large pool of
        demo players, isn't it? :)

        We will actually create 716 members. You can
        modify the following list. Adding new teams
        you need to add also to the according team
        data xml files.
    """
    today = date.today()
    team_config = [

        #
        # Nebula FC - Main FC
        {
            'team_ref': 'team_championship',
            'company_id': 'manchester_nebula_fc_main_club',
            'membership_ref': 'membership_manchester_main_fc_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_year': today.year - 25,
            'max_year': today.year - 18,
            'count': 25,
        },
        {
            'team_ref': 'team_league_two',
            'company_id': 'manchester_nebula_fc_main_club',
            'membership_ref': 'membership_manchester_main_fc_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_year': today.year - 26,
            'max_year': today.year - 17,
            'count': 28,
        },
        {
            'team_ref': 'team_national_north',
            'company_id': 'manchester_nebula_fc_main_club',
            'membership_ref': 'membership_manchester_main_fc_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_year': today.year - 26,
            'max_year': today.year - 17,
            'count': 23,
        },
        {
            'team_ref': 'team_northern_premier',
            'company_id': 'manchester_nebula_fc_main_club',
            'membership_ref': 'membership_manchester_main_fc_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_year': today.year - 24,
            'max_year': today.year - 17,
            'count': 30,
        },
        {
            'team_ref': 'team_womens_super_league',
            'company_id': 'manchester_nebula_fc_main_club',
            'membership_ref': 'membership_manchester_main_fc_active',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_year': today.year - 26,
            'max_year': today.year - 17,
            'count': 24,
        },
        {
            'team_ref': 'team_womens_national_league_div_one',
            'company_id': 'manchester_nebula_fc_main_club',
            'membership_ref': 'membership_manchester_main_fc_active',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_year': today.year - 28,
            'max_year': today.year - 17,
            'count': 26,
        },

        #
        # Nebula FC - Youth Division - Boys
        {
            'team_ref': 'team_boys_u18',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_youth_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 16,
            'max_age': 18,
            'count': 27,
        },
        {
            'team_ref': 'team_boys_u16',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_youth_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 15,
            'max_age': 16,
            'count': 25,
        },
        {
            'team_ref': 'team_boys_u14a',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 13,
            'max_age': 14,
            'count': 15,
        },
        {
            'team_ref': 'team_boys_u14b',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 13,
            'max_age': 14,
            'count': 18,
        },
        {
            'team_ref': 'team_boys_u12a',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 11,
            'max_age': 12,
            'count': 15,
        },
        {
            'team_ref': 'team_boys_u12b',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 11,
            'max_age': 12,
            'count': 16,
        },
        {
            'team_ref': 'team_boys_u12c',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 11,
            'max_age': 12,
            'count': 18,
        },
        {
            'team_ref': 'team_boys_u10a',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 9,
            'max_age': 10,
            'count': 14,
        },
        {
            'team_ref': 'team_boys_u10b',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 9,
            'max_age': 10,
            'count': 12,
        },
        {
            'team_ref': 'team_boys_u10c',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 9,
            'max_age': 10,
            'count': 15,
        },
        {
            'team_ref': 'team_boys_u10d',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 9,
            'max_age': 10,
            'count': 13,
        },
        {
            'team_ref': 'team_boys_u10e',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_boys',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 9,
            'max_age': 10,
            'count': 16,
        },

        #
        # Nebula FC - Youth Division - Girls
        {
            'team_ref': 'team_girls_u18',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_youth_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 16,
            'max_age': 18,
            'count': 29,
        },
        {
            'team_ref': 'team_girls_u16',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_youth_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 15,
            'max_age': 16,
            'count': 23,
        },
        {
            'team_ref': 'team_girls_u13',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 12,
            'max_age': 13,
            'count': 15,
        },
        {
            'team_ref': 'team_girls_u12a',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 10,
            'max_age': 12,
            'count': 18,
        },
        {
            'team_ref': 'team_girls_u12b',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 10,
            'max_age': 12,
            'count': 18,
        },
        {
            'team_ref': 'team_girls_u10a',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 10,
            'max_age': 10,
            'count': 14,
        },
        {
            'team_ref': 'team_girls_u10b',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 9,
            'max_age': 10,
            'count': 16,
        },
        {
            'team_ref': 'team_girls_u10c',
            'company_id': 'manchester_nebula_fc_junior',
            'membership_ref': 'membership_manchester_junior_division_kids_girls',
            'state_ref': 'member_state_active',
            'gender': 'female',
            'min_age': 8,
            'max_age': 10,
            'count': 15,
        },

        #
        # Nebula FC - Chapter Lucerne
        {
            'team_ref': 'team_lucerne_2liga',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 17,
            'max_age': 28,
            'count': 31,
        },
        {
            'team_ref': 'team_lucerne_3liga',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 21,
            'max_age': 28,
            'count': 26,
        },
        {
            'team_ref': 'team_lucerne_4liga',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_active',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 24,
            'max_age': 33,
            'count': 29,
        },
        {
            'team_ref': 'team_lucerne_bjunioren',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 16,
            'max_age': 17,
            'count': 25,
        },
        {
            'team_ref': 'team_lucerne_cjunioren',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 13,
            'max_age': 15,
            'count': 25,
        },
        {
            'team_ref': 'team_lucerne_d9a',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 10,
            'max_age': 13,
            'count': 16,
        },
        {
            'team_ref': 'team_lucerne_d9b',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 10,
            'max_age': 13,
            'count': 19,
        },
        {
            'team_ref': 'team_lucerne_ea',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 8,
            'max_age': 10,
            'count': 12,
        },
        {
            'team_ref': 'team_lucerne_eb',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 8,
            'max_age': 10,
            'count': 14,
        },
        {
            'team_ref': 'team_lucerne_ec',
            'company_id': 'nebula_fc_lucerne',
            'membership_ref': 'membership_lucerne_junior',
            'state_ref': 'member_state_active',
            'gender': 'male',
            'min_age': 8,
            'max_age': 10,
            'count': 11,
        },
        
    ]
    generate_club_members(env, team_config)

    create_demo_user_members(env)

    _logger.info(f"_post_init_hook(): End")

def _uninstall_hook(env):
    _logger.info(f"_uninstall_hook(): Start")

    _logger.info(f"_uninstall_hook(): End")