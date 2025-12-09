from odoo import models, fields, api, _

class ClubCustomFieldValue(models.Model):
    _name = 'club.custom.field.value'
    _description = 'Value of custom field'
    _rec_name = 'field_id'

    field_id = fields.Many2one(comodel_name='club.custom.field', required=True, ondelete='cascade')
    model = fields.Selection([
        ('club.club', _('Club')),
        ('club.subclub', _('Subclub')),
        ('club.department', _('Department')),
        ('club.pool', _('Pool')),
        ('club.team', _('Team')),
        ('club.member', _('Member'))
    ], required=True)
    res_id = fields.Integer(string=_('Record ID'), required=True, index=True)
    value_char = fields.Char()
    value_text = fields.Text()
    value_integer = fields.Integer()
    value_float = fields.Float()
    value_date = fields.Date()
    value_datetime = fields.Datetime()
    value_selection = fields.Char()
    value_boolean = fields.Boolean()

    _sql_constraints = [
        (
            'unique_field_per_entity',
            'unique(field_id, model, res_id)',
            'Each field can only be used once for an entity'
        )
    ]

def _post_init_hook(env):
    env.cr.execute("""
        CREATE INDEX IF NOT EXISTS club_custom_field_value_lookup_idx
        ON club_custom_field_value (model, res_id, field_id)
    """)

    env.cr.execute("""
        CREATE INDEX IF NOT EXISTS club_custom_field_value_reverselookup_idx
        ON club_custom_field_value (field_id, model, res_id)
    """)