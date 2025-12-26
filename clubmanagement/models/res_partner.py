from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ssnid = fields.Char(string='SSN No', help='Social Security Number', groups="base.group_user", copy=False, tracking=True)

    is_club_member = fields.Boolean(string="Is Club Member", compute="_compute_is_club_member", store=True, index=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    def _compute_is_club_member(self):
        # Mapping aller partner_ids, die in club.member existieren
        member_partners = self.env["club.member"].sudo().search([]).mapped("partner_id.id")
        for rec in self:
            rec.is_club_member = rec.id in member_partners