from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ClubPool(models.Model):
    _name = 'club.pool'
    _description = 'Pool'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True)
    department_id = fields.Many2one('club.department', required=True)
    hr_department_id = fields.Many2one('hr.department', string="HR Department", help="Optional HR department mapping for HR processes")
    team_ids = fields.One2many('club.team', 'pool_id', string='Teams')
    active = fields.Boolean(default=True)

    def unlink(self):
        for pool in self:
            if pool.team_ids:
                raise ValidationError(
                    "Teams associated with pool. Pool cannot be deleted!"
                )
        return super(ClubPool, self).unlink()