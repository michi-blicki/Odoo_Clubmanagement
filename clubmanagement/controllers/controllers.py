# -*- coding: utf-8 -*-
# from odoo import http


# class Clubmanagement(http.Controller):
#     @http.route('/clubmanagement/clubmanagement', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/clubmanagement/clubmanagement/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('clubmanagement.listing', {
#             'root': '/clubmanagement/clubmanagement',
#             'objects': http.request.env['clubmanagement.clubmanagement'].search([]),
#         })

#     @http.route('/clubmanagement/clubmanagement/objects/<model("clubmanagement.clubmanagement"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('clubmanagement.object', {
#             'object': obj
#         })

