from odoo import models, fields

#
# For Club Boards and Working Groups
#
class ClubBoard(models.Model):
    _name = 'club.board'
    _description = 'Club Board / Working Group'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True)
    club_id = fields.Many2one('club.club', string='Club')
    subclub_id = fields.Many2one('club.subclub', string='Sub Club')
    member_ids = fields.Many2many('res.partner', string='Board Members')
    group_type = fields.Selection([
        ('board', 'Board'),
        ('working', 'Working Group')
    ], default='board')
    active = fields.Boolean(default=True)