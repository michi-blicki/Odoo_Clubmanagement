from odoo import models, fields, _

class ClubMemberState(models.Model):
    _name = 'club.member.state'
    _description = 'Member Status'
    _order ='sequence, id'
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'State Code must be unique!')
    ]

    name = fields.Char(string=_("State Name"), required=True)
    code = fields.Char(string=_("Code"), required=True)
    sequence = fields.Integer(required=True, default=10)
    state_type = fields.Selection([
        ('pending', _('Pending')),
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('blocked', _('Blocked')),
        ('archived', _('Archived')),
        ('deleted', _('Deleted'))
    ], required=True, default='pending', string=_("State Type"))
    description = fields.Text(string=_("Description"))
    active = fields.Boolean(default=True)