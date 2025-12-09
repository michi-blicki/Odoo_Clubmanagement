from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ClubPool(models.Model):
    _name = 'club.pool'
    _description = 'Pool'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name = fields.Char(required=True, tracking=True)
    club_id = fields.Many2one(string=_('Club'), comodel_name='club.club', related='department_id.club_id', store=True, readonly=True)
    department_id = fields.Many2one(string=_('Department'), comodel_name='club.department', required=True, tracking=True)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    team_ids = fields.One2many(comodel_name='club.team', inverse_name='pool_id', string='Teams')
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='pool_id', string=_("Roles / Functions"))
    member_ids = fields.Many2many(comodel_name='club.member', relation='club_pool_member_rel', column1='pool_id', column2='member_id', string=_('Members'), tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids')
    active = fields.Boolean(default=True, tracking=True)

    @api.depends('member_ids', 'team_ids.member_ids_display')
    def _compute_member_ids(self):
        for pool in self:
            direct = pool.member_ids
            team_member = pool.team_ids.mapped('member_ids_display')
            all_members = direct | team_member
            pool.member_ids_display = [(6, 0, all_members.ids)]

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals):
        pools = super(ClubPool, self).create(vals)

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
