# -*- coding: utf-8 -*-
from odoo import api, fields, SUPERUSER_ID
import logging
import random
from datetime import date

_logger = logging.getLogger(__name__)


def generate_club_members(env, team_config):
    """Generates club.members based on a configuration array."""
    MODULE = 'clubmanagement_democlub'
    ClubMember = env['club.member']
    MemberState = env['club.member.state']

    # Fix reference for Club - as there can't be more than one
    Club = env.ref(f'{MODULE}.manchester_nebula_fc_club')

    # List of names
    male_firstnames = [
        "Aaron", "Adam", "Adrian", "Aiden", "Alex", "Alfie", "Andrew", "Anthony", "Archie", "Arthur",
        "Benjamin", "Blake", "Bradley", "Brandon", "Callum", "Charlie", "Christopher", "Connor", "Daniel", "David",
        "Dylan", "Edward", "Elliot", "Ethan", "Finn", "Freddie", "George", "Harley", "Harry", "Harvey",
        "Henry", "Isaac", "Jack", "Jacob", "James", "Jamie", "Jayden", "Joshua", "Leo", "Liam",
        "Logan", "Louis", "Lucas", "Luke", "Matthew", "Max", "Michael", "Nathan", "Oliver", "Ryan"
    ]

    female_firstnames = [
        "Abigail", "Alice", "Amelia", "Anna", "Ava", "Beatrice", "Bethany", "Brooke", "Caitlin", "Charlotte",
        "Chloe", "Daisy", "Ella", "Ellie", "Emily", "Emma", "Erin", "Evie", "Faith", "Florence",
        "Freya", "Georgia", "Grace", "Hannah", "Harper", "Holly", "Isabelle", "Isla", "Jessica", "Katie",
        "Layla", "Leah", "Lilly", "Lily", "Lucy", "Megan", "Mia", "Millie", "Molly", "Nancy",
        "Olivia", "Phoebe", "Poppy", "Rosie", "Ruby", "Samantha", "Sophie", "Summer", "Zara", "Zoe"
    ]

    lastnames = [
        "Adams", "Alexander", "Allen", "Anderson", "Armstrong", "Atkinson", "Austin",
        "Bailey", "Baker", "Ball", "Barker", "Barnes", "Barrett", "Bates", "Bell", "Bennett", "Berry", "Black", "Booth",
        "Bowen", "Boyd", "Bradley", "Brady", "Brooks", "Brown", "Bryant", "Burgess", "Burke", "Burton",
        "Butler", "Campbell", "Carpenter", "Carr", "Carter", "Chamberlain", "Chapman", "Clark", "Clarke", "Cole",
        "Coleman", "Collins", "Cook", "Cooper", "Crawford", "Cox", "Craig", "Curtis", "Daniels", "Davidson",
        "Davies", "Davis", "Dawson", "Day", "Dean", "Dixon", "Douglas", "Doyle", "Duncan", "Edwards",
        "Elliott", "Evans", "Fisher", "Fletcher", "Ford", "Foster", "Fox", "Francis", "Fraser", "Gardner",
        "Gibson", "Gill", "Graham", "Grant", "Gray", "Green", "Griffin", "Hall", "Hamilton", "Hanson",
        "Hardy", "Harrison", "Hart", "Harvey", "Hawkins", "Hayes", "Henderson", "Hill", "Holland", "Holmes",
        "Howard", "Hudson", "Hughes", "Hunt", "Hunter", "Jackson", "James", "Jenkins", "Johnson", "Johnston",
        "Jones", "Kelly", "Kennedy", "Kerr", "King", "Knight", "Lawrence", "Lee", "Lewis", "Marshall",
        "Martin", "Mason", "Matthews", "Miller", "Mitchell", "Moore", "Morgan", "Morris", "Murphy", "Murray",
        "Nelson", "Nicholson", "Palmer", "Parker", "Paterson", "Pearson", "Porter", "Powell", "Price", "Reed",
        "Reid", "Reynolds", "Richards", "Richardson", "Roberts", "Robertson", "Robinson", "Ross", "Russell", "Spencer"
    ]

    nationality_id = env.ref('base.uk').id
    lang = 'en_GB'

    used_combinations = set()

    registered_state = MemberState.search([('state_type', '=', 'registered'), ('active', '=', True)], limit=1)
    if not registered_state:
        _logger.error("No Club Member State of type 'registered' found. This should not happen here")
        return

    for team in team_config:
        try:
            Team = env.ref(f"{MODULE}.{team['team_ref']}")
            MemberState = env.ref(f"{MODULE}.{team['state_ref']}")
            Membership = env.ref(f"{MODULE}.{team['membership_ref']}")
        except ValueError as e:
            _logger.error("Missing reference in team config: %s", e)
            continue

        gender = team.get('gender', 'male')
        firstnames = male_firstnames if gender == 'male' else female_firstnames

        for _ in range(team['count']):
            attempts = 0
            while True:
                fname = random.choice(firstnames)
                lname = random.choice(lastnames)
                combo = (fname, lname)
                if combo not in used_combinations:
                    used_combinations.add(combo)
                    break
                attempts += 1
                if attempts > 200:
                    _logger.warning("Could not find unique name after 200 attempts, search pool expention required!")
                    break

            yob = None
            if 'min_year' in team and 'max_year' in team:
                yob = random.randint(team['min_year'], team['max_year'])
            else:
                yob = date.today().year - random.randint(team['min_age'], team['max_age'])

            # unique mail generator: also uses loop index to guarantee uniqueness
            email_safe = f"{fname.lower()}.{lname.lower()}@nebulafc.co.uk"
            if any(m in email_safe for m in [' ', "'"]):
                email_safe = email_safe.replace(" ", "").replace("'", "")
            suffix = 1
            while ClubMember.search_count([('email', '=', email_safe)]) > 0:
                email_safe = f"{fname.lower()}.{lname.lower()}.{suffix}@nebulafc.co.uk"
                suffix += 1

            date_start = date(random.randint(2019, 2025), random.randint(1, 12), random.randint(1, 28))

            vals = {
                'firstname': fname,
                'lastname': lname,
                'birthdate_date': date(yob, random.randint(1, 12), random.randint(1, 28)),
                'gender': gender,
                'nationality_id': nationality_id,
                'lang': lang,
                'phone': f"+44 7{random.randint(1000, 9999)} {random.randint(100000, 999999)}",
                'company_id': team['company_id'],
                'club_id': Club.id,
                'team_ids': [(6, 0, [Team.id])],
                'membership_history_ids': [(0, 0, {
                    'membership_id': Membership.id,
                    'date_start': date_start,
                })],
                'state_history_ids': [
                    (0, 0, {'state_id': registered_state.id, 'start_date': date_start, 'end_date': date_start}),
                    (0, 0, {'state_id': MemberState.id, 'start_date': date_start, }),
                ],
                'is_club_member': True,
                'email': email_safe,
            }

            ClubMember.create(vals)

        _logger.info(
            "Demo: Generated %d %s members for team %s (%s–%s).",
            team['count'], gender, Team.display_name,
            team.get('min_year', team.get('min_age', '?')),
            team.get('max_year', team.get('max_age', '?')),
        )
    
def create_demo_user_members(env):
    """Erzeugt club.member-Einträge für alle bestehenden Benutzer (res.users),
    sofern sie noch nicht existieren. Jeder Benutzer wird mit seinem Partner
    verknüpft und erhält alle Subclubs basierend auf seinen company_ids.
    Da es nur einen club.club gibt, wird dieser global gesetzt.
    """
    ClubMember = env['club.member'].sudo()
    SubClub = env['club.subclub'].sudo()
    Club = env['club.club'].sudo()

    # Es gibt nur genau einen Club – den holen wir einmalig
    main_club = Club.search([], limit=1)
    if not main_club:
        raise ValueError("Es existiert kein club.club-Datensatz – bitte zuerst den Verein anlegen.")

    # Mapping: Company-ID → zugehörige Subclubs
    subclubs_by_company = {}
    for subclub in SubClub.search([]):
        subclubs_by_company.setdefault(subclub.company_id.id, []).append(subclub.id)

    # Alle Benutzer laden
    users = env['res.users'].sudo().search([])

    for user in users:
        if not user.partner_id:
            continue

        # Überspringe, wenn bereits ein ClubMember mit diesem Partner existiert
        if ClubMember.search_count([('partner_id', '=', user.partner_id.id)]):
            continue

        # Sammle alle Firmen, in denen der Benutzer Mitglied ist
        company_ids = set(user.company_ids.ids)
        company_ids.add(user.company_id.id)

        # Finde alle Subclubs, die zu diesen Firmen gehören
        subclub_ids = []
        for cid in company_ids:
            subclub_ids.extend(subclubs_by_company.get(cid, []))

        vals = {
            'partner_id': user.partner_id.id,
            'club_id': main_club.id,
        }

        if subclub_ids:
            vals['subclub_ids'] = [(6, 0, list(set(subclub_ids)))]

        ClubMember.create(vals)
