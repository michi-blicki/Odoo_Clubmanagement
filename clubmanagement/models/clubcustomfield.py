from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)

class ClubCustomField(models.Model):
    _name = 'club.custom.field'
    _description = 'Configurable additional fields for clubs'
    _order = 'sequence, label'

    _sql_constraints = [
        (
            'unique_club_model_techname',
            'unique(club_id, model, technical_name)',
            'Technical name of custom field must be unique within clubs'
        )
    ]

    club_id             = fields.Many2one(string='Club', comodel_name='club.club', required=True, ondelete='cascade')

    model               = fields.Selection([
                            ('club.member', 'Club Member'),
                            ('club.team', 'Team'),
                            ('club.pool', 'Pool'),
                            ('club.department', 'Department'),
                            ('club.subclub', 'Subclub'),
                            ('club.club', 'Club')
                        ], string='Model', required=True)

    technical_name      = fields.Char(string='Technical Field Name', required=True)
    label               = fields.Char(string='Label', required=True)
    field_type          = fields.Selection([
                            ('char', 'Textline'),
                            ('text', 'Textarea'),
                            ('integer', 'Integer'),
                            ('float', 'Float'),
                            ('date', 'Date'),
                            ('datetime', 'Date/Time'),
                            ('selection', 'Selection'),
                            ('boolean', 'Checkbox')
                        ], string='Field Type', required=True)

    required            = fields.Boolean(string='Required', default=False)
    sequence            = fields.Integer(string='Sequence', default=10)
    selection_values    = fields.Char(string='For Selection Lists only, as comma-separated list')



    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()
