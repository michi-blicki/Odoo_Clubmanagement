from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta

import logging
_logger = logging.getLogger(__name__)

class Club(models.Model):
    _name = 'club.club'
    _description = 'Club'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
        'club.custom.field.mixin',
        'club.security.mixin',
    ]

    name                        = fields.Char(string="Name", required=True, tracking=True)
    company_id                  = fields.Many2one(string="Company", comodel_name='res.company', required=True, default=lambda self: self.env.company)
    logo                        = fields.Binary(string="Logo", related='company_id.logo', readonly=True, store=False)
    account_analytic_account_id = fields.Many2one(string="Account Analytic Account", comodel_name="account.analytic.account")
    subclub_ids                 = fields.One2many(string="Subclubs", comodel_name='club.subclub', inverse_name='club_id')
    board_ids                   = fields.One2many(string="Boards", comodel_name='club.board', inverse_name='club_id')
    department_ids              = fields.One2many(string="Departments", comodel_name='club.department', inverse_name='club_id')
    pool_ids                    = fields.One2many(string="Pools", comodel_name='club.pool', inverse_name='club_id')
    team_ids                    = fields.One2many(string="Teams", comodel_name='club.team', inverse_name='club_id')
    role_ids                    = fields.One2many(string="Roles / Functions", comodel_name='club.role', inverse_name='club_id')
    member_ids                  = fields.Many2many(string="Members", comodel_name='club.member', relation='club_club_member_rel', column1='club_id', column2='member_id')
    member_ids_display          = fields.Many2many(string="All Members", comodel_name='club.member', compute='_compute_member_ids', store=False)

    custom_field_lines          = fields.Json(string="Custom Fields", compute="_compute_custom_fields")
    
    active                      = fields.Boolean(default=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.depends('member_ids', 'subclub_ids.member_ids_display', 'department_ids.member_ids_display')
    def _compute_member_ids(self):
        for club in self:
            direct = club.member_ids
            subclub_members = club.subclub_ids.mapped('member_ids_display')
            dept_members = club.department_ids.mapped('member_ids_display')
            all_members = direct | subclub_members | dept_members
            club.member_ids_display = [(6, 0, all_members.ids)]
            

    def view_config_roles_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Roles'),
            'res_model': 'club.role',
            'view_mode': 'list,form',
            'domain': [('club_id', '=', self.id)],
            'context': {
                'default_club_id': self.id,
                'search_default_club_id': self.id,
            }
        }

    def get_upcoming_birthdays(self, days=7):
        today = date.today()
        birthdays = []
        for member in self.member_ids_display:
            bd = member.birthdate_date
            if not bd:
                continue
            try:
                this_year_bday = date(today.year, bd.month, bd.day)
            except ValueError:
                continue
            if this_year_bday < today:
                next_bday = date(today.year + 1, bd.month, bd.day)
                next_age = today.year + 1 - bd.year
            else:
                next_bday = this_year_bday
                next_age = today.year - bd.year
            delta = (next_bday - today).days
            if 0 <= delta <= days:
                birthdays.append({
                    'id': member.id,
                    'firstname': member.firstname,
                    'lastname': member.lastname,
                    'birthdate': member.birthdate_date,
                    'next_age': next_age
                })
        birthdays.sort(key=lambda rec: (rec['birthdate'].month, rec['birthdate'].day))
        return birthdays

    #######################
    # GET CLUB HELPER
    #######################
    def get_club(self):
        club = self.search([], limit=1)
        if not club:
            raise ValidationError(_("No club has been created yes."))
        
        return club

    ########################
    # CREATE HOOK
    ########################

    @api.model_create_multi
    def create(self, vals_list):
        if self.search_count([]) >= 1:
            raise ValidationError(_('Only one club can be created in this system.'))
            
        clubs = super(Club, self).create(vals_list)
        self.env.cr.flush()
        self.env.cr.commit()

        for club in clubs:
            self.env['club.log'].log_event(
                scope_type='club',
                activity_type='create',
                model=self._name,
                res_id=club.id,
                res_name=club.name,
                description=_("Club created: %s") % club.name
            )

        return clubs

    def action_create_default_roles_and_boards(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('club_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant', 'admin']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'scope_type': 'club',
                    'club_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'CLUB_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        if not self.board_ids:
            board = self.env['club.board'].create({
                'name': _("%s - Executive Board") % self.name,
                'group_type': 'board',
                'scope_type': 'club',
                'club_id': self.id,
            })

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
        for club in self:
            if club.subclub_ids:
                raise ValidationError(
                    _("Subclubs associated to club. Club cannot be deleted!")
                )
            if club.board_ids:
                raise ValidationError(
                    _("Boards associated to club. Club cannot be deleted!")
                )
            if club.department_ids:
                raise ValidationError(
                    _("Departments associated to club. Club cannot be deleted! Deactivate Club instead.")
                )
            
            if club.role_ids:
                club.role_ids.unlink()

            self.env['club.log'].log_event(
                scope_type='club',
                activity_type='unlink',
                model=self._name,
                res_id=club.id,
                res_name=club.name,
                description=_("Club deleted: %s") % club.name
            )

        return super(Club, self).unlink()

    ########################
    # SECURITY MIXIN
    ########################
    def search(self, args, **kwargs):
        user = self.env.user
        if not user.has_group('clubmanagement.group_clubmanagement_administrator'):
            scopes = self._get_user_scope_entities(user)
            args = [('id', 'in', scopes['club_ids'].ids)] + list(args)
        return super().search(args, **kwargs)