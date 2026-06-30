# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ClubCustomFieldMixin(models.AbstractModel):
    _name = "club.custom.field.mixin"
    _description = "Mixin for dynamic custom fields"

    custom_field_lines = fields.Json(
        string="Custom Fields (computed)",
        compute="_compute_custom_fields",
        inverse="_inverse_custom_fields",
        store=False
    )

    @api.depends_context('uid')
    def _compute_custom_fields(self):
        """Compute JSON structure for all fields of this model."""
        CustomField = self.env['club.custom.field']
        CustomValue = self.env['club.custom.field.value']

        for record in self:
            # holt Custom Fields für das konkrete Modell
            custom_fields = CustomField.search([
                ('model', '=', record._name),
                ('club_id', '=', record.env['club.club'].search([], limit=1).id),
            ])
            values = CustomValue.search([
                ('model', '=', record._name),
                ('res_id', '=', record.id),
            ])
            values_by_field = {v.field_id.id: v for v in values}

            lines = []
            for field in custom_fields:
                val = values_by_field.get(field.id)
                value = None
                if val:
                    for column in [
                        'value_char', 'value_text', 'value_integer', 'value_float',
                        'value_date', 'value_datetime', 'value_selection', 'value_boolean'
                    ]:
                        if val[column]:
                            value = val[column]
                            break

                lines.append({
                    'id': field.id,
                    'label': field.label,
                    'technical_name': field.technical_name,
                    'type': field.field_type,
                    'required': field.required,
                    'selection_values': field.selection_values.split(',') if field.selection_values else [],
                    'value': value,
                    'help': field.help or "",
                })
            record.custom_field_lines = lines

    # --------------------------------------------------
    # Save‑Hook (Inverse)
    # --------------------------------------------------
    def _inverse_custom_fields(self):
        for record in self:
            data = record.custom_field_lines or []
            record.write_custom_fields(data)

    # --------------------------------------------------
    # Shared Write/Update‑Logic
    # --------------------------------------------------
    def write_custom_fields(self, custom_field_data):
        """Create/Update all custom field values."""
        self.ensure_one()
        FieldValue = self.env['club.custom.field.value']
        CustomField = self.env['club.custom.field']

        for entry in custom_field_data:
            field = CustomField.browse(entry.get("id"))
            if not field.exists():
                continue

            value = entry.get("value")
            # required‑Check optional:
            if field.required and (value in [False, None, ""]):
                raise ValidationError(_("The custom field '%s' is required.") % field.label)

            target_field = f"value_{field.field_type}"
            domain = [
                ('field_id', '=', field.id),
                ('model', '=', self._name),
                ('res_id', '=', self.id),
            ]
            existing = FieldValue.search(domain, limit=1)
            vals = {
                'field_id': field.id,
                'model': self._name,
                'res_id': self.id,
                target_field: value
            }
            if existing:
                existing.write(vals)
            else:
                FieldValue.create(vals)
