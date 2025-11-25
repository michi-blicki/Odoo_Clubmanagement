from odoo import models, fields

class Club(models.Model):
    _name = 'club.club'
    _description = 'Club'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    subclub_ids = fields.One2many('club.subclub', 'parent_club_id', string='Sub Club')
    board_ids = fields.One2many('club.board', 'club_id', string="Board")
    department_ids = fields.One2many('club.department', 'club_id', string='Departments')
    active = fields.Boolean(default=True)

class SubClub(models.Model):
    _name = 'club.subclub'
    _description = 'Sub Club / Sub-Association'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    parent_club_id = fields.Many2one('club.club', string="Parent Club / Association", required=True)
    board_ids = fields.One2many('club.board', 'subclub_id', string="Board")
    department_ids = fields.One2many('club.department', 'subclub_id', string="Departments")
    active = fields.Boolean(default=True)