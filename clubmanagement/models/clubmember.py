from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date

class ClubMember(models.Model):
    _name = 'club.member'
    _description = 'Club Member'
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', required=True, string='Contact')
    birthdate_date = fields.Date(related='partner_id.birthdate_date', store=True, string='Birthdate', readonly=False)
    gender = fields.Selection(related='partner_id.gender', store=True, string='Gender', readonly=False)
    nationality_id = fields.Many2one('res.country', related='partner_id.nationality_id', store=True, string='Nationality', readonly=False)
    department_ids = fields.Many2many('club.department', string='Departments')
    
    is_employee = fields.Boolean('Is Employee', default=False)
    employee_id = fields.Many2one('hr.employee', string='Employee')

    role_ids = fields.Many2many('club.role', string='Functions / Roles')

    membership_ids = fields.One2many('club.member.membership', 'member_id')

    state_ids = fields.One2many('club.member.state', 'member_id')

    active = fields.Boolean(default=True)

    year_of_birth = fields.Integer(string="Year of Birth", compute='_compute_year_of_birth', store=True)
    age = fields.Integer(string="Age", compute='_compute_age', store=True)
    years_in_club = fields.Float(string='Years in Club', compute='_compute_membership_duration', store=True)
    months_in_club = fields.Integer(string='Months in Club', compute='_compute_membership_duration', store=True)
    days_in_club = fields.Integer(string='Days in Club', compute='_compute_membership_duration', store=True)

    @api.depends('birthdate_date')
    def _compute_year_of_birth(self):
        for mem in self:
            mem.year_of_birth = mem.birthdate_date.year if mem.birthdate_date else False

    @api.depends('birthdate_date')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for mem in self:
            if mem.birthdate_date:
                mem.age = relativedelta(today, mem.birthdate_date).years
            else:
                mem.age = False

    @api.depends('membership_ids.start_date', 'membership_ids.end_date')
    def _compute_membership_duration(self):
        today = fields.Date.context_today(self)
        for mem in self:
            total_days = 0
            total_months = 0
            total_years = 0
            for ms in mem.membership_ids.filtered(lambda x: x.start_date and (x.end_date or x.start_date <= today)):
                start = ms.start_date
                end = ms.end_date if ms.end_date and ms.end_date <= today else today
                if end > start:
                    delta = relativedelta(end, start)
                    days = (end - start).days
                    total_days += days
                    total_months += delta.years * 12 + delta.months
                    total_years += delta.years + (delta.months / 12.0)
            mem.days_in_club = total_days
            mem.months_in_club = total_months
            mem.years_in_club = total_years
