from odoo import http
from odoo.http import request
from datetime import date

class ClubDashboardController(http.Controller):
    @http.route('/clubmanagement/dashboard/data', type='json', auth='user')
    def dashboard_data(self):
        # Hole den "single" Club
        club = request.env['club.club'].sudo().search([], limit=1)
        if not club:
            return {}

        # Member States
        member_ids_display = []
        for m in club.member_ids_display:
            member_ids_display.append({
                'id': m.id,
                'firstname': m.firstname,
                'lastname': m.lastname,
                'state_type': m.state_type,
                'birthdate': m.birthdate_date.isoformat() if m.birthdate_date else None,
            })

        # Departments/Teams/Pools
        department_ids = []
        for d in club.department_ids:
            department_ids.append({
                'id': d.id,
                'name': d.name,
                'team_ids': [t.id for t in getattr(d, 'team_ids', [])],
            })
        pool_ids = [p.id for p in club.pool_ids]

        # Birthdays
        birthdays_raw = club.get_upcoming_birthdays(days=30)
        upcoming_birthdays = [
            {
                'id': bd['id'],
                'firstname': bd['firstname'],
                'lastname': bd['lastname'],
                'birthdate': bd['birthdate'].isoformat() if bd['birthdate'] else None,
                'next_age': bd['next_age']
            }
            for bd in birthdays_raw
        ]

        # New Members This Month
        today = date.today()
        month_start = date(today.year, today.month, 1)
        new_members = request.env['club.member'].sudo().search([
            ('membership_date_start', '>=', month_start)
        ])
        new_members_data = [{
            'id': m.id,
            'firstname': m.firstname,
            'lastname': m.lastname,
            'age': m.age,
            'club_id': m.club_id.name if m.club_id else '',
            'department_ids': [d.name for d in m.department_ids],
            'current_state': m.current_state_id.state_type if m.current_state_id else '',
        } for m in new_members]

        return {
            'name': club.name,
            'company_id': {'id': club.company_id.id},
            'member_ids_display': member_ids_display,
            'department_ids': department_ids,
            'pool_ids': pool_ids,
            'upcoming_birthdays': upcoming_birthdays,
            'days': 30,
            'new_members': new_members_data,
        }
