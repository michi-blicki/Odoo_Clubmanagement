from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ClubDepartment(models.Model):
    _name = 'club.department'
    _description = 'Department'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name = fields.Char(required=True, tracking=True)
    club_id = fields.Many2one(comodel_name='club.club', string=_('Club'), required=True, readonly=True)
    subclub_id = fields.Many2one(comodel_name='club.subclub', string=_('Sub Club'), tracking=True)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    board_ids = fields.One2many(comodel_name='club.board', inverse_name='department_id', string=_('Boards'), tracking=True)
    pool_ids = fields.One2many(comodel_name='club.pool', inverse_name='department_id', string=_('Pools'), tracking=True)
    team_ids = fields.One2many(comodel_name='club.team', inverse_name='department_id', string=_('Teams'), tracking=True)
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='department_id', string=_("Roles / Functions"), tracking=True)
    member_ids = fields.Many2many(string=_('Members'), comodel_name='club.member', relation='club_department_member_rel', column1='department_id', column2='member_id', tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids')
    member_count = fields.Integer(string=_("Member Count", comput="_compute_member_ids", store=True))
    active = fields.Boolean(default=True)

    @api.depends('member_ids', 'pool_ids.member_ids_display', 'team_ids.member_ids_display')
    def _compute_member_ids(self):
        for dept in self:
            direct = dept.member_ids
            team_members = dept.team_ids.mapped('member_ids_display')
            pool_members = dept.pool_ids.mapped('member_ids_display')
            all_members = direct | team_members | pool_members
            dept.member_ids_display = [(6, 0, all_members.ids)]
            member_count = len(dept.member_ids_display)

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals):
        subclub_exists = self.env['club.subclub'].search_count([('active', '=', True)]) > 0

        if subclub_exists:
            if not vals.get('subclub_id'):
                raise ValidationError(_('A subclub exists and must be assigned when creating a new department'))
        else:
            vals['subclub_id'] = False

        departments = super(ClubDepartment, self).create(vals)

        for department in departments:
            self.env['club.log'].log_event(
                scope_type='department',
                activity_type='create',
                model=self._name,
                res_id=department.id,
                res_name=department.name,
                description=_("Department created: %s") % department.name
            )

        return departments

    ########################
    # UNLINK HOOK
    ########################

    def unlink(self):
        for department in self:
            # 1. if pools under this department exists, do not delete this department
            if department.pool_ids:
                raise ValidationError(
                    _("Please remove or reassign all Pools linked to this Department before deletion.")
                )
            if department.team_ids:
                raise ValidationError(
                    _("Please remove or reassign all Teams linked to this Department before deletion.")
                )
            if department.board_ids:
                raise ValidationError(
                    _("Please remove or reassign all Boards linked to this Department before deletion.")
                )

            if department.role_ids:
                department.role_ids.unlink()

            self.env['club.log'].log_event(
                scope_type='department',
                activity_type='unlink',
                model=self._name,
                res_id=department.id,
                res_name=department.name,
                description=_("Department deleted: %s") % department.name
            )

        return super(ClubDepartment, self).unlink()