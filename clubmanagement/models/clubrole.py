from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ClubRole(models.Model):
    _name = 'club.role'
    _description = 'Team/Club Function or Role'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
    ]
    
    name = fields.Char(required=True, compute='_compute_name', store=True)
    name_extension = fields.Char(_('Name Extenseion'), required=False, tracking=True)
    code = fields.Char(required=True, tracking=True)
    description = fields.Text('Description', required=False)
    role_type = fields.Selection([
        ('lead', _('Leader')),
        ('assistant', _('Assistant')),
        ('special', _('Special')),
        ('admin', _('Administrator')),
        ('member', _('Member')),
        ('other', _('other'))
    ], default='member', tracking=True)

    scope_type = fields.Selection([
        ('club', _('Club')),
        ('board', _('Board')),
        ('subclub', _('Subclub')),
        ('department', _('Department')),
        ('pool', _('Pool')),
        ('team', _('Team'))
    ], required=True, readonly=True)

    club_id = fields.Many2one(comodel_name='club.club', string=_('Club'), tracking=True)
    board_id = fields.Many2one(comodel_name='club.board', string=_('Board'), tracking=True)
    subclub_id = fields.Many2one(comodel_name='club.subclub', string=_('Subclub'), tracking=True)
    department_id = fields.Many2one(comodel_name='club.department', string=_('Department'), tracking=True)
    pool_id = fields.Many2one(comodel_name='club.pool', string=_('Pool'), tracking=True)
    team_id = fields.Many2one(comodel_name='club.team', string=_('Team'), tracking=True)

    perm_read   = fields.Boolean(string=_('Read Permission'), required=True, default=False, tracking=True)
    perm_write  = fields.Boolean(string=_('Write Permission'), required=True, default=False, tracking=True)
    perm_create = fields.Boolean(string=_('Create Permission'), required=True, default=False, tracking=True)
    perm_unlink = fields.Boolean(string=_('Unlink Permission'), required=True, default=False, tracking=True)
    perm_mail   = fields.Boolean(string=_('Send Mail Permission'), required=True, default=False, tracking=True)

    member_id = fields.Many2one(string=_('Member'), comodel_name='club.member', required=False, tracking=True)

    active = fields.Boolean(default=True, tracking=True)

    @api.depends('role_type', 'scope_type', 'club_id', 'subclub_id', 'department_id', 'pool_id', 'team_id', 'board_id', 'name_extension')
    def _compute_name(self):
        for record in self:
            scope_obj = None
            if record.scope_type == 'club':
                scope_obj = record.club_id
            elif record.scope_type == 'board':
                scope_obj = record.board_id
            elif record.scope_type == 'subclub':
                scope_obj = record.subclub_id
            elif record.scope_type == 'department':
                scope_obj = record.department_id
            elif record.scope_type == 'pool':
                scope_obj = record.pool_id
            elif record.scope_type == 'team':
                scope_obj = record.team_id

            scope_name = scope_obj.name if scope_obj else '???'
            role_type = dict(self._fields['role_type'].selection).get(record.role_type, record.role_type)

            self.env['club.log'].log_event(
                scope_type='role',
                activity_type='update',
                model=self._name,
                res_id=record.id,
                res_name=record.name,
                description=_("Role Name changed: %s") % record.name
            )

    @api.constrains('scope_type')
    def _check_scope_assignment(self):
        for role in self:
            if role.scope_type == 'club' and not role.club_id:
                raise ValidationError(_('Club-Role needs to be assigned to a club'))
            if role.scope_type == 'board' and not role.board_id:
                raise ValidationError(_('Board-Role needs to be assigned to a board'))
            if role.scope_type == 'department' and not role.department_id:
                raise ValidationError(_('Department-Role needs to be assigned to a department'))
            if role.scope_type == 'pool' and not role.pool_id:
                raise ValidationError(_('Pool-Role needs to be assigned to a pool'))
            if role.scope_type == 'team' and not role.team_id:
                raise ValidationError(_('Team-Role needs to be assigned to a team'))

    @api.constrains('scope_type', 'role_type')
    def _check_role_types_for_scope(self):
        forbidden_types = ['member', 'other']
        forbidden_scopes = ['club', 'subclub', 'department', 'pool', 'team']
        for role in self:
            if role.scope_type in forbidden_scopes and role.role_type in forbidden_types:
                raise ValidationError(
                    _("Role of type '%s' is not allowed for scope '%s'") % (
                        dict(self._fields['role_type'].selection).get(role.role_type, role.role_type),
                        dict(self._fields['scope_type'].selection).get(role.scope_type, role.scope_type)
                    )
                )

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):
        
        # Create the role first
        roles = super(ClubRole, self).create(vals_list)

        for role in roles:

            # Create the log entry
            self.env['club.log'].log_event(
                scope_type='role',
                activity_type='create',
                model=self._name,
                res_id=role.id,
                res_name=role.name,
                description=_("Role created: %s") % role.name
            )

        return roles


    ########################
    # UNLINK HOOK
    ########################
    def unlink(self):
        for role in self:
            self.env['club.log'].log_event(
                scope_type='role',
                activity_type='unlink',
                model=self._name,
                res_id=role.id,
                res_name=role.name,
                description=_("Role deleted: %s") % role.name
            )

        return super(ClubRole, self).unlink()