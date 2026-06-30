# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubTeam(models.Model):
    _name = 'club.team'
    _description = 'Team'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
        'club.custom.field.mixin',
        'club.security.mixin',
    ]
    _group_by_full = {
        'department_id': lambda self, departments, domain, order: self._read_group_department_id(departments, domain, order),
    }

    name                        = fields.Char(required=True, tracking=True)
    shortname                   = fields.Char(string='Short Name', required=False, size=8, help='Short code, max 5 characters', tracking=True)
    company_id                  = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id                     = fields.Many2one(string='Club', comodel_name='club.club', store=True, readonly=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    department_id               = fields.Many2one(string='Department', comodel_name='club.department', required=True, tracking=True)
    pool_id                     = fields.Many2one(string='Pool', comodel_name='club.pool', required=False, tracking=True)
    hr_department_id            = fields.Many2one(string='HR Department', comodel_name='hr.department', help='Optional HR department mapping for HR processes', tracking=True)
    account_analytic_account_id = fields.Many2one(string="Account Analytic Account", comodel_name="account.analytic.account")
    sequence                    = fields.Integer(string='Sequence', required=True, default=10)
    gender                      = fields.Selection([
                                    ('male', 'Male'),
                                    ('female', 'Female'),
                                    ('mixed', 'Mixed'),
                                    ('divers', 'Divers')
                                ], string="Team Gender", compute="_compute_team_gender")
    role_ids                    = fields.One2many(string='Roles / Functions', comodel_name='club.role', inverse_name='team_id')
    member_ids                  = fields.Many2many(string='Members', comodel_name='club.member', relation='club_team_member_rel', column1='team_id', column2='member_id', tracking=True)
    member_ids_display          = fields.Many2many(string='All Members', comodel_name='club.member', compute='_compute_member_ids', store=True)
    members_count               = fields.Integer(string='Member Cound', compute="_compute_member_ids", store=True)
    active                      = fields.Boolean(default=True, tracking=True)

    price                       = fields.Monetary(string="Price", compute="_compute_price", store=True, currency_field='currency_id', readonly=True)
    currency_id                 = fields.Many2one(string="Currency", compute="_compute_price", comodel_name='res.currency', related='company_id.currency_id', readonly=True)
    membership_id               = fields.Many2one(string="Membership", comodel_name="club.member.membership", store=True)
    effective_membership_id     = fields.Many2one(string="Effective Membership", comodel_name="club.member.membership", compute="_compute_effective_membership_id", store=True, readonly=True)
    registration_mode           = fields.Selection([
                                    ('inherit', 'Inherit'),
                                    ('open', 'Open'),
                                    ('restricted', 'Restricted (Waitlist)'),
                                    ('closed', 'Closed')
                                ], string='Registration Mode', required=True, default='inherit', tracking=True)
    effective_registration_mode = fields.Selection([
                                    ('open', 'Open'),
                                    ('restricted', 'Restricted (Waitlist)'),
                                    ('closed', 'Closed')
                                ], string='Effective Registration Mode', compute='_compute_effective_registration_mode', store=True, readonly=True)

    custom_field_lines          = fields.Json(string="Custom Fields", compute="_compute_custom_fields")

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.model
    def _read_group_department_id(self, departments, domain, order):
        return self.env['club.department'].search([('company_id', '=', self.env.company.id)], order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'department_id' in groupby:
            departments = self.env['club.department'].search([('company_id', '=', self.env.company.id)])
            result = [{
                '__domain': [('department_id', '=', department.id), ('company_id', '=', self.env.company.id)],
                'department_id': (department.id, department.name),
                'department_id_count': self.search_count([('department_id', '=', department.id), ('company_id', '=', self.env.company.id)]),
                '__count': self.search_count([('department_id', '=', department.id), ('company_id', '=', self.env.company.id)])
            } for department in departments]
            return result
        return super(ClubTeam, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


    @api.depends('shortname')
    def _check_shortname_length(self):
        for record in self:
            if record.shortname and len(record.shortname) > 5:
                raise ValidationError(_("Short Name must be at most 5 characters"))


    @api.depends('member_ids')
    def _compute_member_ids(self):
        for team in self:
            team.member_ids_display = [(6, 0, team.member_ids.ids)]
            team.members_count = len(team.member_ids)

    @api.depends('member_ids')
    def _compute_team_gender(self):
        for team in self:
            # Evaluate team members
            has_gender_male = any(member.gender == 'male' for member in team.member_ids)
            has_gender_female = any(member.gender == 'female' for member in team.member_ids)
            has_gender_other = any(member.gender == 'other' for member in team.member_ids)

            # Calculate team gender
            if has_gender_other:
                team.gender = 'divers'
            elif has_gender_male and has_gender_female:
                team.gender = 'mixed'
            elif has_gender_male:
                team.gender = 'male'
            elif has_gender_female:
                team.gender = 'female'
            else:
                # No member within this team
                team.gender = False

    @api.depends('membership_id', 'pool_id', 'pool_id.effective_membership_id', 'department_id', 'department_id.effective_membership_id')
    def _compute_effective_membership_id(self):
        for team in self:
            team.effective_membership_id = (
                team.membership_id
                or team.pool_id.effective_membership_id
                or team.department_id.effective_membership_id
            )

    @api.model
    def _merge_registration_modes(self, modes):
        rank = {
            'open': 1,
            'restricted': 2,
            'closed': 3,
        }
        valid_modes = [m for m in modes if m in rank]
        if not valid_modes:
            return 'open'
        return sorted(valid_modes, key=lambda m: rank[m], reverse=True)[0]

    @api.depends('registration_mode', 'pool_id.effective_registration_mode', 'department_id.effective_registration_mode')
    def _compute_effective_registration_mode(self):
        for team in self:
            modes = [team.department_id.effective_registration_mode or 'open']
            if team.pool_id:
                modes.append(team.pool_id.effective_registration_mode or 'open')
            if team.registration_mode != 'inherit':
                modes.append(team.registration_mode)
            team.effective_registration_mode = self._merge_registration_modes(modes)

    @api.depends('effective_membership_id')
    def _compute_price(self):
        for team in self:
            price = 0.0
            if team.effective_membership_id:
                price = team.effective_membership_id.price
                currency = team.effective_membership_id.currency_id
            team.price = price
            team.currency_id = currency.id if price else False



    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):

        club = self.env['club.club'].search([('company_id', '=', self.env.company.id)], limit=1)
        if not club:
            club = self.env['club.club'].search([], limit=1)

        for vals in vals_list:
            if not vals.get('club_id'):
                if not club:
                    raise ValidationError(_("Club must be created first"))
                vals['club_id'] = club.id

        self._check_user_action_permissions('create', record=self.env['club.team'])
        teams = super(ClubTeam, self).create(vals_list)

        for team in teams:

            self.env['club.log'].log_event(
                scope_type='team',
                activity_type='create',
                model=self._name,
                res_id=team.id,
                res_name=team.name,
                description=_("Team created: %s") % team.name,
            )

        return teams

    def action_create_default_roles(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('team_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'club_id': self.club_id.id,
                    'scope_type': 'team',
                    'team_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'TEAM_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        return {
            'type': "ir.actions.client",
            'tag': 'reload',
        }

    #######################################
    # WRITE HOOK
    #######################################
    def write(self, vals):
        for rec in self:
            rec._check_user_action_permissions('write', record=rec)

        res = super().write(vals)

        # Update custom fields, if available and required
        if 'custom_field_lines' in vals:
            for rec in self:
                rec.write_custom_fields(vals['custom_field_lines'])

        return res

    ########################
    # UNLINK HOOK
    ########################
    def unlink(self):
        for team in self:
            # 1. Check for assigned members
            if team.member_ids:
                raise ValidationError(
                    _("Team members assigned. Team cannot be deleted! Deactivate team instead.")
                )

            # 2. Perform Security Check
            self._check_user_action_permissions('unlink', record=team)

            # 3. Unlink assigned roles
            if team.role_ids:
                team.role_ids.unlink()

            self.env['club.log'].log_event(
                scope_type='team',
                activity_type='unlink',
                model=self._name,
                res_id=team.id,
                res_name=team.name,
                description=_("Team deleted: %s") % team.name
            )
        return super(ClubTeam, self).unlink()

    ########################
    # CLUB SECURITY MIXIN
    ########################
    @api.model
    def search(self, args, **kwargs):
        if self.env.su or self._context.get('club_security_internal'):
            return super().search(args, **kwargs)

        user = self.env.user
        if not user.has_group('clubmanagement.group_clubmanagement_administrator'):
            visible_teams = self._get_visible_team_ids(user)
            args = [('id', 'in', visible_teams.ids)] + list(args)
        return super().search(args, **kwargs)