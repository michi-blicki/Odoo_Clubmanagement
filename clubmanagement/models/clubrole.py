from odoo import models, fields

class ClubRole(models.Model):
    _name = 'club.role'
    _description = 'Team/Club Function or Role'
    
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Text('Description', required=False)
    role_type = fields.Selection([
        ('lead', 'Leader'),
        ('assistant', 'Assistant'),
        ('special', 'Special'),
        ('admin', 'Administration'),
        ('member', 'Member'),
        ('other', 'other')
    ], default='other')

    scope_type = fields.Selection([
        ('board', 'Board'),
        ('department', 'Department'),
        ('pool', 'Pool'),
        ('team', 'Team')
    ], required=True)

    board_id = fields.Many2one('club.board', string='Board')
    department_id = fields.Many2one('club.department', string='Department')
    pool_id = fields.Many2one('club.pool', string='Pool')
    team_id = fields.Many2one('club.team', string='Team')

    active = fields.Boolean(default=True)

    @api.constrains('scope_type')
    def _check_scope_assignment(self):
        for role in self:
            if role.scope_type == 'board' and not role.board_id:
                raise ValidationError('Board-Role needs to be assigned to a board')
            if role.scope_type == 'department' and not role.department_id:
                raise ValidationError('Department-Role needs to be assigned to a department')
            if role.scope_type == 'pool' and not role.pool_id:
                raise ValidationError('Pool-Role needs to be assigned to a pool')
            if role.scope_type == 'team' and not role.team_id:
                raise ValidationError('Team-Role needs to be assigned to a team')