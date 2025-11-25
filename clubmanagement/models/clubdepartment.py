from odoo import models, fields

class ClubDepartment(models.Model):
    _name = 'club.department'
    _description = 'Department'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True)
    club_id = fields.Many2one('club.club', string=Club)
    subclub_id = fields.Many2one('club.subclub', string='Sub Club')
    hr_department_id = fields.Manx2one('hr.department', string="HR Department", help="Optional HR department mapping for HR processes")
    pool_ids = fields.One2many('club.pool', 'department_id', string='Pools')
    active = fields.Boolean(default=True)