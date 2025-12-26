from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

import secrets


class ClubApiConfig(models.Model):
    _name = 'club.api.config'
    _description = 'Club API Configuration'

    name = fields.Char(string='Name', required=True)
    company_ids = fields.Many2many(string='Companies', comodel_name='res.company', required=True, ondelete="cascade")
    club_id = fields.Many2one(string='Club', comodel_name='club.club', required=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    api_name = fields.Selection([
        ('register_member', 'Member Registration')
    ], string="API", required=True)
    api_key = fields.Char(string='API Key', required=True, readonly=True, copy=False, default=lambda self: secrets.token_urlsafe(48))
    user_id = fields.Many2one(string="API User", comodel_name="res.users", help="User used for this API calls")

    cors_allow_origin = fields.Char(string='CORS Allowed Origin', help='Optional domain for Access-Control-Allow-Origin header (eq. https://portal.myclub.club)')
    enforce_https = fields.Boolean(string='Enforce HTTPS Header', required=True, default=True, help='Adds HSTS headers to enforce HTTPS in client browsers')
    rate_limit_enabled = fields.Boolean(string='Enable Rate Limitign', required=True, default=False)
    rate_limit_per_minute = fields.Integer(string='Rate Limit per IP per Minute', required=False, default=60)

    # Jetzt generisch, damit auch club.custom.fields verarbeitet werden können
    allowed_fields = fields.Many2many(string='Allowed API Fields', comodel_name='club.field.mixin', relation='club_api_config_allowed_field_rel', column1='config_id', column2='field_id', domain=lambda self: self._domain_allowed_fields())

    active = fields.Boolean(default=True, required=True)

    #######################################
    # CREATE HOOK
    #######################################
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('api_key'):
                vals['api_key'] = self._generate_secure_key()
        records = super().create(vals_list)
        for record in records:
            required_mixins = record._get_required_fields()
            record.allowed_fields |= required_mixins

        return records

    #######################################
    # DOMAIN GENERATOR for allowed_fields
    #######################################
    @api.model
    def _domain_allowed_fields(self):
        domain_ids = self._get_available_fields().ids
        _logger.debug("Domain generated with %s available fields.", len(domain_ids))
        return [('id', 'in', domain_ids)]

    #######################################
    # User ID Validator
    #######################################
    @api.constrains("user_id")
    def _check_api_user_group(self):
        api_group = self.env.ref("clubmanagement.group_clubmanagement_api_user", raise_if_not_found=False)
        for rec in self:
            if rec.user_id and api_group not in rec.user_id.groups_id:
                raise ValidationError(
                    "Der ausgewählte Benutzer muss in der Gruppe 'API User' sein."
                )

    #######################################
    # INTERNAL HELPER
    #######################################
    @api.model
    def _get_available_fields(self):
        _logger.info("_get_available_fields() called.")
        member_fields = self.env['ir.model.fields'].search([
            ('model', '=', 'club.member'),
            ('readonly', '=', False),
            ('name', 'not in', ['id', 'create_uid', 'create_date', 'write_uid', 'write_date'])
        ])
        custom_fields = self.env['club.custom.field'].search([('model', '=', 'club.member')])

        # Erzeuge Mixin-Einträge (temporär oder persistent je nach Implementierung)
        mixin_model = self.env['club.field.mixin']
        system_mixins = mixin_model.create_from_system_fields(member_fields)
        custom_mixins = mixin_model.create_from_custom_fields(custom_fields)

        _logger.info("_get_available_fields(): No of Fields: %s", len(system_mixins | custom_mixins))

        return system_mixins | custom_mixins

    #######################################
    # AUTO-ADD required Felder
    #######################################
    @api.model
    def _get_required_fields(self):
        """Return all available fields that are required and can't be deselected."""
        required_system_fields = self.env['ir.model.fields'].search([
            ('model', '=', 'club.member'),
            ('required', '=', True)
        ])
        required_custom_fields = self.env['club.custom.field'].search([
            ('model', '=', 'club.member'),
            ('required', '=', True)
        ])
        mixin_model = self.env['club.field.mixin']
        sys_req = mixin_model.create_from_system_fields(required_system_fields)
        cust_req = mixin_model.create_from_custom_fields(required_custom_fields)
        return sys_req | cust_req

    #######################################
    # AUTO api_key
    #######################################
    @api.model
    def _generate_secure_key(self):
        return secrets.token_urlsafe(48)