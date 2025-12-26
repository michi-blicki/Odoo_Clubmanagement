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
    company_ids         = fields.Many2many(string='Companies', comodel_name='res.company', required=True, ondelete='cascade')

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

    #######################################
    # CREATE HOOK
    #######################################
    @api.model_create_multi
    def create(self, vals_list):
        """Ensure that the only existing club.club record is referenced as club_id."""
        club = self.env['club.club'].search([], limit=1)
        if not club:
            raise ValueError(_('No club.club record found. This model requires exactly one club.'))

        for vals in vals_list:
            vals['club_id'] = club.id

        records = super().create(vals_list)

        _logger.info("ClubCustomField created for club: %s (%s)", club.name, club.id)

        return records
        

    #######################################
    # ONCHANGE HOOKS
    #######################################
    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        """When one company is selected, auto-select all companies sharing its parent_id."""
        if not self.company_ids:
            return

        parent_ids = self.company_ids.mapped('parent_id').ids
        selected_ids = self.company_ids.ids

        related_companies = self.env['res.company'].search([
            '|',
            ('parent_id', 'in', parent_ids),
            ('id', 'in', selected_ids)
        ])

        current_ids = set(selected_ids)
        extended_ids = current_ids.union(related_companies.ids)
        self.company_ids = [(6, 0, list(extended_ids))]