from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubRole(models.Model):
    _name = 'club.role'
    _description = 'Team/Club Function or Role'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
    ]
    
    name            = fields.Char(string='Name', required=True, store=True)
    auto_name       = fields.Boolean(string='Auto-generate Name', required=True, default=True, help="If checked, the name will be automatically generated.")
    name_extension  = fields.Char('Name Extenseion', required=False, tracking=True)
    code            = fields.Char(string='Code', required=True, tracking=True)
    company_id      = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)
    description     = fields.Text(string='Description', required=False)
    role_type       = fields.Selection([
                        ('lead', 'Leader'),
                        ('assistant', 'Assistant'),
                        ('special', 'Special'),
                        ('admin', 'Administrator'),
                        ('member', 'Member'),
                        ('other', 'other')
                    ], string='Role Type', default='member', tracking=True)

    scope_type      = fields.Selection([
                        ('club', 'Club'),
                        ('board', 'Board'),
                        ('subclub', 'Subclub'),
                        ('department', 'Department'),
                        ('pool', 'Pool'),
                        ('team', 'Team')
                    ], string='Scope Type', required=True, readonly=True)

    club_id         = fields.Many2one(string='Club', comodel_name='club.club', tracking=True)
    board_id        = fields.Many2one(string='Board', comodel_name='club.board', tracking=True)
    subclub_id      = fields.Many2one(string='Subclub', comodel_name='club.subclub', tracking=True)
    department_id   = fields.Many2one(string='Department', comodel_name='club.department', tracking=True)
    pool_id         = fields.Many2one(string='Pool', comodel_name='club.pool', tracking=True)
    team_id         = fields.Many2one(string='Team', comodel_name='club.team', tracking=True)

    perm_read       = fields.Boolean(string='Read Permission', required=True, default=False, tracking=True)
    perm_write      = fields.Boolean(string='Write Permission', required=True, default=False, tracking=True)
    perm_create     = fields.Boolean(string='Create Permission', required=True, default=False, tracking=True)
    perm_unlink     = fields.Boolean(string='Unlink Permission', required=True, default=False, tracking=True)
    perm_mail       = fields.Boolean(string='Send Mail Permission', required=True, default=False, tracking=True)

    member_id       = fields.Many2one(string='Member', comodel_name='club.member', required=False, tracking=True)

    active          = fields.Boolean(default=True, tracking=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.model
    def _generate_name(self, vals):
        #
        # This procedure generates the name based on given values
        scope_type = vals.get('scope_type')
        role_type = dict(self._fields['role_type'].selection).get(vals.get('role_type'), '')
        name_extension = vals.get('name_extension', '')

        scope_name = ''
        if scope_type == 'club' and vals.get('club_id'):
            club = self.env['club.club'].browse(vals.get('club_id'))
            scope_name = f"{club.name} (Club)"
        elif scope_type == 'board' and vals.get('board_id'):
            board = self.env['club.board'].browse(vals.get('board_id'))
            scope_name = f"{board.name} ({_("Board")})"
        elif scope_type == 'subclub' and vals.get('subclub_id'):
            subclub = self.env['club.subclub'].browse(vals.get('subclub_id'))
            scope_name = f"{subclub.name} ({_("Subclub")})"
        elif scope_type == 'department' and vals.get('department_id'):
            dep = self.env['club.department'].browse(vals.get('department_id'))
            scope_name = f"{dep.name} ({_("Department")})"
        elif scope_type == 'pool' and vals.get('pool_id'):
            pool = self.env['club.pool'].browse(vals.get('pool_id'))
            scope_name = f"{pool.department_id.name} - {pool.name} ({_("Pool")})"
        elif scope_type == 'team' and vals.get('team_id'):
            team = self.env['club.team'].browse(vals.get('team_id'))
            scope_name = f"{team.department_id.name} - {team.name} ({_("Team")})"

        generated_name = scope_name
        if name_extension:
            generated_name += f": {name_extension}"

        return generated_name

    @api.depends('auto_name', 'role_type', 'scope_type', 'club_id', 'subclub_id', 'department_id', 'pool_id', 'team_id', 'board_id', 'name_extension')
    def _on_change_name_fields(self):

        if self.auto_name:
            self.name = self._generate_name(self._convert_to_write(self.read(['scope_type', 'role_type', 'club_id', 'board_id', 'subclub_id', 'department_id', 'pool_id', 'team_id', 'name_extension'])[0]))

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

        for vals in vals_list:
            if vals.get('auto_name', True):
                vals['name'] = self._generate_name(vals)
        
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
    # WRITE HOOK
    ########################
    def write(self, vals):
        if 'auto_name' in vals or (vals.get('auto_name', True) and any(field in vals for field in ['scope_type', 'role_type', 'club_id', 'team_id', 'name_extension'])):
            for record in self:
                if record.auto_name:
                    new_vals = record.copy_data()[0]
                    new_vals.update(vals)
                    vals['name'] = self._generate_name(new_vals)
        
        return super(ClubRole, self).write(vals)

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