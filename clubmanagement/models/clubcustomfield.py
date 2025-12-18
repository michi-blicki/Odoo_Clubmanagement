from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)

class ClubCustomField(models.Model):
    _name = 'club.custom.field'
    _description = 'Configurable additional fields for clubs'
    _order = 'sequence, label'

    club_id = fields.Many2one(string=_("Club"), comodel_name='club.club', required=True, ondelete='cascade')

    model = fields.Selection([
        ('club.member', _('Club Member')),
        ('club.team', _('Team')),
        ('club.pool', _('Pool')),
        ('club.department', _('Department')),
        ('club.subclub', _('Subclub')),
        ('club.club', _('Club'))
    ], string=_('Model'), required=True)

    technical_name = fields.Char(string=_('Technical field name'), required=True)
    label = fields.Char(string=_('Label'), required=True)
    field_type = fields.Selection([
        ('char', _('Textline')),
        ('text', _('Textarea')),
        ('integer', _('Integer')),
        ('float', _('Float')),
        ('date', _('Date')),
        ('datetime', _('Date/Time')),
        ('selection', _('Selection')),
        ('boolean', _('Checkbox'))
    ], string=_('Field Type'), required=True)

    required = fields.Boolean(string=_("Required"), default=False)
    sequence = fields.Integer(string=_("Sequence"), default=10)
    selection_values = fields.Char(string=_('For Selection Lists only, as comma-separated list'))

    _sql_constraints = [
        (
            'unique_club_model_techname',
            'unique(club_id, model, technical_name)',
            'Technical name of custom field must be unique within clubs'
        )
    ]

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()
