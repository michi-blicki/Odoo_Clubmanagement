from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import psycopg2

import logging
_logger = logging.getLogger(__name__)


class ClubFieldMixin(models.Model):
    _name = 'club.field.mixin'
    _description = 'Unified representation of Odoo field and custom club field'

    _sql_constraints = [
        ('unique_model_technical_name', 'unique(model, technical_name)',
        'Technical name must be unique within each model.')
    ]

    # Das Modell kann sowohl auf ir.model.fields (Systemfelder) als auch club.custom.field (Customfelder) verweisen
    field_type = fields.Selection([
        ('system', 'System Field'),
        ('custom', 'Custom Field'),
    ], string="Field Type", required=True, default='system')

    # Referenzen
    ir_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='System Field',
        ondelete='cascade'
    )

    custom_field_id = fields.Many2one(
        comodel_name='club.custom.field',
        string='Custom Field',
        ondelete='cascade'
    )

    # Gemeinsame Metafelder
    technical_name = fields.Char(string='Technical Name', compute='_compute_common', store=False)
    label = fields.Char(string='Label', compute='_compute_common', store=False)
    required = fields.Boolean(string='Required', compute='_compute_common', store=False)
    sequence = fields.Integer(string='Sequence', compute='_compute_common', store=False)
    model = fields.Char(string='Model', compute='_compute_common', store=False)

    _sql_constraints = [
        ('unique_field_source', 'unique(field_type, ir_field_id, custom_field_id)',
         'Duplicate field reference not allowed.'),
    ]

    ###########################################
    # COMPUTE COMMON DISPLAY INFO
    ###########################################
    @api.depends('field_type', 'ir_field_id', 'custom_field_id')
    def _compute_common(self):
        for rec in self:
            if rec.field_type == 'system' and rec.ir_field_id:
                field = rec.ir_field_id
                rec.technical_name = field.name
                rec.label = field.field_description or field.name
                rec.required = field.required
                rec.model = field.model
                rec.sequence = 10
            elif rec.field_type == 'custom' and rec.custom_field_id:
                field = rec.custom_field_id
                rec.technical_name = field.technical_name
                rec.label = field.label
                rec.required = field.required
                rec.model = field.model
                rec.sequence = field.sequence or 10
            else:
                rec.technical_name = False
                rec.label = False
                rec.required = False
                rec.sequence = 10
                rec.model = False

    ###########################################
    # DISPLAY
    ###########################################
    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.model}] {rec.label or rec.technical_name}"
            if rec.required:
                name += " *"
            result.append((rec.id, name))
        return result

    #######################################
    # CREATE HOOK
    #######################################
    @api.model_create_multi
    def create(self, vals_list):
        try:
            records = super(ClubFieldMixin, self).create(vals_list)
            return records
        except psycopg2.errors.UniqueViolation:
            _logger.warning('Duplicate technical_name detected during create() hook')
            raise ValidationError(_("Technical name must be unique within model '%s'. Please choose another name.") % (vals.get('model') or self.model))

    #######################################
    # WRITE HOOK
    #######################################
    def write(self, vals):
        try:
            return super(ClubFieldMixin, self).write(vals)
        except psycopg2.errors.UniqueViolation:
            _logger.warning('Duplicate technical_name detected during write() hook.')
            raise ValidationError(_("Technical name must be unique within model '%s'. Please choose another name.") % (vals.get('model') or self.model))

    ###########################################
    # UTILS
    ###########################################
    @api.model
    def create_from_system_fields(self, field_recs):
        """Erzeuge oder hole Mixin-Einträge aus ir.model.fields Records."""
        created = self.env['club.field.mixin']
        for field in field_recs:
            existing = self.search([
                ('field_type', '=', 'system'),
                ('ir_field_id', '=', field.id),
            ], limit=1)
            if existing:
                created |= existing
                continue

            mixin = self.create({
                'field_type': 'system',
                'ir_field_id': field.id,
            })
            created |= mixin
        return created

    @api.model
    def create_from_custom_fields(self, field_recs):
        """Erzeuge oder hole Mixin-Einträge aus club.custom.field Records."""
        created = self.env['club.field.mixin']
        for field in field_recs:
            existing = self.search([
                ('field_type', '=', 'custom'),
                ('custom_field_id', '=', field.id),
            ], limit=1)
            if existing:
                created |= existing
                continue

            mixin = self.create({
                'field_type': 'custom',
                'custom_field_id': field.id,
            })
            created |= mixin
        return created
