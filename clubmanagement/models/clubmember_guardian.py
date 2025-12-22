from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubMemberGuardian(models.Model):
    _name = 'club.member.guardian'
    _description = 'Club Member Guardian'

    member_id = fields.Many2one(string='Member', comodel_name='club.member', required=True, ondelete='cascade')
    guardian_id = fields.Many2one(string='Guardian', comodel_name='res.partner', required=True)
    relation = fields.Selection([
        ('parent', 'Parent'),
        ('legal_guardian', 'Legal Guardian'),
        ('other', 'Other'),
    ], string='Relation', required=True, default='parent')
    is_primary = fields.Boolean(string='is Primary Guardian', required=True, default=False)
    notes = fields.Text(string='Notes')
    