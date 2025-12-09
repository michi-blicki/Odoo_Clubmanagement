from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta
import base64
from io import BytesIO
from datetime import date

from PIL import Image


class ClubMember(models.Model):
    _name = 'club.member'
    _description = 'Club Member'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    partner_id = fields.Many2one(comodel_name='res.partner', required=True, string=_('Contact'), readonly=True)
    firstname = fields.Char(related='partner_id.firstname', store=True, string=_('Firstname'), readonly=True)
    lastname = fields.Char(related='partner_id.lastname', store=True, string=_('Lastname'), readonly=True)
    birthdate_date = fields.Date(related='partner_id.birthdate_date', store=True, string=_('Birthdate'), readonly=False)
    gender = fields.Selection(related='partner_id.gender', store=True, string=_('Gender'), readonly=False)
    photo = fields.Binary(string=_("Photo"), attachment=True, help=_("Member photo of size 680x960 or 1360x1920"))
    nationality_id = fields.Many2one(comodel_name='res.country', related='partner_id.nationality_id', store=True, string=_('Nationality'), readonly=False)
    city = fields.Char(related='partner_id.city', store=True, string=_('City'), readonly=True)

    club_id = fields.Many2one(string=_('Club'), comodel_name='club.club', readonly=True)
    subclub_ids = fields.Many2many(string=_('Subclubs'), comodel_name='club.subclub', relation='club_subclub_member_rel', column1='member_id', column2='subclub_id')
    department_ids = fields.Many2many(string=_('Departments'), comodel_name='club.department', relation='club_department_member_rel', column1='member_id', column2='department_id')
    pool_ids = fields.Many2many(string=_('Pools'), comodel_name='club.pool', relation='club_pool_member_rel', column1='member_id', column2='pool_id')
    team_ids = fields.Many2many(string=_('Teams'), comodel_name='club.team', relation='club_team_member_rel', column1='member_id', column2='team_id')
    
    is_employee = fields.Boolean(string=_('Is Employee'), default=False)
    employee_id = fields.Many2one(comodel_name='hr.employee', string=_('Employee'), tracking=True)

    role_ids = fields.One2many(comodel_name='club.role', inverse_name='member_id', string=_('Roles / Functions'))

    current_membership_id  = fields.Many2one(string=_("Current Membership"), comodel_name="club.member.membership", compute="_compute_current_membership", store=True)
    membership_history_ids = fields.One2many(string=_("Membership History"), comodel_name="club.member.membership.history", inverse_name="member_id")
    membership_date_start  = fields.Date(string=_("Membership Start Date"), compute="_compute_current_membership", store=True)
    membership_date_end    = fields.Date(string=_("Membership End Date"), compute="_compute_current_membership", store=True)

    current_state_id = fields.Many2one(string=_("Current Member State"), comodel_name="club.member.state", compute="_compute_current_state", store=True)
    state_history_ids = fields.One2many(string=_("Member State History"), comodel_name="club.member.state.history", inverse_name="member_id")
    state_date_start = fields.Date(string=_("State Start Date"), compute="_compute_current_state", store=True)
    state_days_in_state = fields.Integer(string=_("Days in current state"), compute="_compute_state_days_since_start", store=False)
    state_header_color = fields.Char(string=_("Kanban Header Color"), compute="_compute_state_days_since_start", store=False)

    active = fields.Boolean(default=True, tracking=True)

    year_of_birth = fields.Integer(string=_("Year of Birth"), compute='_compute_year_of_birth', store=True)
    age = fields.Integer(string=_("Age"), compute='_compute_age', store=True)
    years_in_club = fields.Float(string=_('Years in Club'), compute='_compute_membership_duration', store=True)
    months_in_club = fields.Integer(string=_('Months in Club'), compute='_compute_membership_duration', store=True)
    days_in_club = fields.Integer(string=_('Days in Club'), compute='_compute_membership_duration', store=True)

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

    @api.depends('photo')
    def _check_photo_size(self):
        for member in self:
            if member.photo:
                try:
                    image_data = base64.b64decode(member.photo)
                    im = Image.open(BytesIO(image_data))
                    if(im.width, im.height) not in [(680,960), (1360,1920)]:
                        raise ValidationError(
                            _("The member photo must be exactly 680x960 or 1360x1920 pixels. Your photo is: %sx%s", im.width, im.height)
                        )
                except Exception:
                    raise ValidationError(
                        _("Could not verify the member photo. Please upload a valid image file")
                    )

    ###################################
    # MEMBER STATES - Functionalities
    ###################################
    @api.depends('state_history_ids.start_date', 'state_history_ids.end_date')
    def _compute_current_state(self):
        for member in self:
            current_state = self.env['club.member.state.history'].search([
                ('member_id', '=', member.id),
                ('start_date', '<=', fields.Datetime.now()),
                '|', ('end_date', '=', False), ('end_date', '>', fields.Datetime.now())
            ], order='date desc, id desc', limit=1)
            member.current_state_id = current_state.state_id if current_state else False
            member.state_date_start = current_state.start_date if current_state else False

    @api.depends('state_date_start')
    def _compute_state_days_since_start(self):
        for member in self:
            if member.state_date_start:
                member.state_days_in_state = (fields.Date.today() - member.state_date_start).days
                if member.state_days_in_state > 28:
                    member.state_header_color = "kanban-header-red"
                elif member.state_days_in_state >= 10:
                    member.state_header_color = "kanban-header-yellow"
                else:
                    member.state_header_color = ""
            else:
                member.state_days_in_state = 0

    def set_state(self, state_id, reason=None):
        self.ensure_one()
        current_state = self.state_history_ids.filtered(lambda r: not r.end_date)
        if current_state:
            current_state.write({'end_date': fields.Datetime.now()})

        self.env['club.member.state.history'].create({
            'member_id': self.id,
            'state_id': state_id,
            'reason': reason,
        })

    #######################################
    # MEMBER MEMBERSHIP - Functionalities
    #######################################
    @api.depends('membership_history_ids.date_start', 'membership_history_ids.date_end', 'membership_history_ids.active')
    def _compute_current_membership(self):
        today = fields.Date.context_today(self)
        for member in self:
            current_membership = self.env['club.member.membership.history'].search([
                ('member_id', '=', member.id),
                ('date_start', '<=', today),
                '|', ('date_end', '=', False), ('date_end', '>=', today),
                ('active', '=', True)
            ], order='date_start DESC, id DESC', limit=1)

            member.current_membership_id = current_membership.membership_id if current_membership else False
            member.membership_date_start = current_membership.date_start if current_membership else False
            member.membership_date_end   = current_membership.date_end if current_membership else False

    def set_membership(self, membership_id, date_start=None, date_end=None, note=None):
        self.ensure_one()
        if not date_start:
            date_start = fields.Date.context_today(self)

        current_active_membership = self.membership_history_ids.filtered(lambda r: r.active and r.date_start <= date_start and (not r.date_end or r.date_end >= date_start))
        if current_active_membership:
            current_active_membership.write({
                'active': False,
                'date_end': date_start,
            })

        self.env['club.member.membership.history'].create({
            'member_id': self.id,
            'membership_id': membership_id,
            'date_start': date_start,
            'date_end': date_end,
            'note': note,
        })

        self.env['club.log'].log_event(
            scope_type='member',
            activity_type='update',
            model=self._name,
            res_id=self.id,
            res_name=self.display_name,
            description=_("Membership changed to %s") % self.env['club.member.membership'].browse(membership_id).name,
            old_value=self.current_membership_id.name if self.current_membership_id else 'None',
            new_value=self.env['club.member.membership'].browse(membership_id).name
        )

        self._compute_current_membership()

    def end_current_membership(self, end_date=None, note=None):
        self.ensure_one()
        if not end_date:
            end_date = fields.Date.context_today(self)

        current_active_membership = self.membership_history_ids.filtered(lambda r: r.active and r.date_start <= end_date and (not r.date_end or r.date_end >= end_date))
        if current_active_membership:
            current_active_membership.write({
                'active': False,
                'date_end': end_date,
                'note': note,
            })

            self.env['club.log'].log_event(
                scope_type='member',
                activity_type='update',
                model=self._name,
                res_id=self.id,
                res_name=self.display_name,
                description=_("Membership Ended: %s") % current_active_membership.membership_id.name,
                old_value=current_active_membership.membership_id.name,
                new_value='None'
            )

        self._compute_current_membership()