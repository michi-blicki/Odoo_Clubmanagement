from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

#
# For Club Boards and Working Groups
#
class ClubBoard(models.Model):
    _name = 'club.board'
    _description = 'Club Board / Working Group'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name = fields.Char(required=True, tracking=True)

    group_type = fields.Selection([
        ('board', _('Board')),
        ('working', _('Working Group'))
    ], default='board', tracking=True)

    scope_type = fields.Selection([
        ('club', _('Club')),
        ('subclub', _('Subclub')),
        ('department', _('Department')),
        ('pool', _('Pool'))
    ], readonly=True)

    club_id = fields.Many2one(comodel_name='club.club', string=_('Club'), required=True, readonly=True)
    subclub_id = fields.Many2one(comodel_name='club.subclub', string=_('Subclub'), tracking=True)
    department_id = fields.Many2one(comodel_name='club.department', string=_('Department'), tracking=True)
    pool_id = fields.Many2one(comodel_name='club.pool', string=_('Pool'), tracking=True)

    role_ids = fields.One2many(comodel_name='club.role', inverse_name='board_id', string=_("Roles / Functions"), tracking=True)

    active = fields.Boolean(default=True, tracking=True)

    @api.constrains('scope_type', 'club_id', 'subclub_id', 'department_id', 'pool_id')
    def _check_scope(self):
        for board in self:
            types = {
                'club': board.club_id,
                'subclub': board.subclub_id,
                'department': board.department_id,
                'pool': board.pool_id
            }

            for t, value in types.items():
                if board.scope_type == t and not value:
                    raise ValidationError(_("For scope type '%s', you must select the corresponding %s.") % (t, t))
                if board.scope_type != t and value:
                    raise ValidationError(_("For scope type '%s', only the corresponding field should be filled.") % (board.scope_type,))
        return True

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals):
        boards = super(ClubBoard, self).create(vals)

        for board in boards:

            self.env['club.log'].log_event(
                scope_type='board',
                activity_type='create',
                model=self._name,
                res_id=board.id,
                res_name=board.name,
                description=_("Board created: %s") % board.name
            )

        return boards

    ########################
    # UNLINK HOOK
    ########################
    def unlink(self):
        for board in self:
            if board.role_ids:
                raise ValidationError(
                    _("Board has assigned Roles. Cannot delete board! Consider deactivating it instead.")
                )

            self.env['club.log'].log_event(
                scope_type='board',
                activity_type='unlink',
                model=self._name,
                res_id=board.id,
                res_name=board.name,
                description=_("Board deleted: %s") % board.name
            )

        return super(ClubBoard, self).unlink()