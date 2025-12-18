from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class ClubMemberMembershipAdditionalProduct(models.Model):
    _name = 'club.member.membership.additional.product'
    _description = 'Additional Product for Membership'

    membership_id = fields.Many2one(string=_("Membership"), comodel_name="club.member.membership", required=True)
    product_id = fields.Many2one(string=_("Product"), comodel_name="product.product", required=True)
    price = fields.Monetary(string=_("Price"), compute='_compute_price', readonly=True, store=True, currency_field='currency_id')
    currency_id = fields.Many2one(string=_("Currency"), comodel_name="res.currency", related='membership_id.currency_id')

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.depends('product_id', 'product_id.list_price')
    def _compute_price(self):
        for record in self:
            record.price = record.product_id.list_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price = self.product_id.list_price