from odoo import models, fields

class ClubMembership(models.Model):
    _name = 'club.membership'
    _description = 'Club Membership'

    name = fields.Char('Designation', required=True)
    description = fields.Text('Description')
    product_id = fields.Many2one('product.product', string='Membership Product', required=True)
    active = fields.Boolean(default=True)