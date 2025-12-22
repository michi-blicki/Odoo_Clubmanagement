from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubPool(models.Model):
    _name = 'club.pool'
    _description = 'Pool'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name                = fields.Char(string='Name', required=True, tracking=True)
    club_id             = fields.Many2one(string='Club', comodel_name='club.club', store=True, readonly=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    company_id          = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)
    department_id       = fields.Many2one(string='Department', comodel_name='club.department', required=True, tracking=True)
    hr_department_id    = fields.Many2one(string='HR Department', comodel_name='hr.department', help='Optional HR department mapping for HR processes', tracking=True)
    sequence            = fields.Integer(string='Sequence', required=True, default=10)
    team_ids            = fields.One2many(string='Teams', comodel_name='club.team', inverse_name='pool_id')
    team_count          = fields.Integer(string='Team Count', compute="_compute_team_count", store=True)
    role_ids            = fields.One2many(string='Roles / Functions', comodel_name='club.role', inverse_name='pool_id')
    member_ids          = fields.Many2many(string='Members', comodel_name='club.member', relation='club_pool_member_rel', column1='pool_id', column2='member_id', tracking=True)
    member_ids_display  = fields.Many2many(string='All Members', comodel_name='club.member', compute='_compute_member_ids', store=True)
    member_count        = fields.Integer(string='Member Count', compute="_compute_member_ids", store=True)
    active              = fields.Boolean(default=True, tracking=True)

    _group_by_full      = {'department_id': lambda self, *args, **kwargs: self._read_group_department_id(*args, **kwargs), }

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.depends('team_ids')
    def _compute_team_count(self):
        for pool in self:
            pool.team_count = len(pool.team_ids)

    @api.depends('member_ids', 'team_ids.member_ids_display')
    def _compute_member_ids(self):
        for pool in self:
            direct = pool.member_ids
            team_member = pool.team_ids.mapped('member_ids_display')
            all_members = direct | team_member
            pool.member_ids_display = [(6, 0, all_members.ids)]
            pool.member_count = len(pool.member_ids_display)

    @api.model
    def _read_group_department_id(self, departments, domain, order):
        return self.env['club.department'].search([])


    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):

        club = self.env['club.club'].search([], limit=1)
        if not club:
            raise ValidationError(_("Club must be created first"))

        pools = super(ClubPool, self).create(vals_list)

        for pool in pools:

            self.env['club.log'].log_event(
                scope_type='pool',
                activity_type='create',
                model=self._name,
                res_id=pool.id,
                res_name=pool.name,
                description=_("Pool created: %s") % pool.name
            )

        return pools

    def action_create_default_roles(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('pool_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'club_id': self.club_id.id,
                    'scope_type': 'pool',
                    'pool_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'POOL_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        return {
            'type': "ir.actions.client",
            'tag': 'reload',
        }

    ########################
    # UNLINK HOOK
    ########################

    def unlink(self):
        for pool in self:
            if pool.team_ids:
                raise ValidationError(
                    "Teams associated with pool. Pool cannot be deleted!"
                )

            if pool.role_ids:
                pool.role_ids.unlink()
                
            self.env['club.log'].log_event(
                scope_type='pool',
                activity_type='unlink',
                model=self._name,
                res_id=pool.id,
                res_name=pool.name,
                description=_("Pool deleted: %s") % pool.name
            )
        return super(ClubPool, self).unlink()

    ########################
    # ACTION HOOKS
    ########################
    def action_view_teams(self):
        self.ensure_one()
        return {
            'name': _('Pool Teams'),
            'type': 'ir.actions.act_window',
            'res_model': 'club.team',
            'view_mode': 'kanban,list,form',
            'domain': [('pool_id', '=', self.id)]
        }

    def action_view_members(self):
        self.ensure_one()
        return {
            'name': _('Pool Members'),
            'type': 'ir.actions.act_window',
            'res_model': 'club.member',
            'view_mode': 'list,form',
            'domain': [('pool_id', '=', self.member_ids_display.ids)]
        }