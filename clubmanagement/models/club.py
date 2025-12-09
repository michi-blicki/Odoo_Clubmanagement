from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta

class Club(models.Model):
    _name = 'club.club'
    _description = 'Club'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin'
    ]

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company)
    subclub_ids = fields.One2many(comodel_name='club.subclub', inverse_name='club_id', string='Sub Club')
    board_ids = fields.One2many(comodel_name='club.board', inverse_name='club_id', string="Board")
    department_ids = fields.One2many(comodel_name='club.department', inverse_name='club_id', string='Departments')
    pool_ids = fields.One2many(string=_("Pools"), comodel_name='club.pool', inverse_name='club_id')
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='club_id', string=_("Roles / Functions"))
    member_ids = fields.Many2many(comodel_name='club.member', relation='club_club_member_rel', column1='club_id', column2='member_id', string=_('Members'))
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids', store=False)
    active = fields.Boolean(default=True)

    @api.depends('member_ids', 'subclub_ids.member_ids_display', 'department_ids.member_ids_display')
    def _compute_member_ids(self):
        for club in self:
            direct = club.member_ids
            subclub_members = club.subclub_ids.mapped('member_ids_display')
            dept_members = club.department_ids.mapped('member_ids_display')
            all_members = direct | subclub_members | dept_members
            club.member_ids_display = [(6, 0, all_members.ids)]
            

    def view_config_roles_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Roles'),
            'res_model': 'club.role',
            'view_mode': 'list,form',
            'domain': [('club_id', '=', self.id)],
            'context': {
                'default_club_id': self.id,
                'search_default_club_id': self.id,
            }
        }

    def get_upcoming_birthdays(self, days=7):
        today = date.today()
        birthdays = []
        for member in self.member_ids_display:
            bd = member.birthdate_date
            if not bd:
                continue
            try:
                this_year_bday = date(today.year, bd.month, bd.day)
            except ValueError:
                continue
            if this_year_bday < today:
                next_bday = date(today.year + 1, bd.month, bd.day)
                next_age = today.year + 1 - bd.year
            else:
                next_bday = this_year_bday
                next_age = today.year - bd.year
            delta = (next_bday - today).days
            if 0 <= delta <= days:
                birthdays.append({
                    'id': member.id,
                    'firstname': member.firstname,
                    'lastname': member.lastname,
                    'birthdate': member.birthdate_date,
                    'next_age': next_age
                })
        birthdays.sort(key=lambda rec: (rec['birthdate'].month, rec['birthdate'].day))
        return birthdays

    #######################
    # GET CLUB HELPER
    #######################
    def get_club(self):
        club = self.search([], limit=1)
        if not club:
            raise ValidationError(_("No club has been created yes."))
        
        return club

    ########################
    # CREATE HOOK
    ########################

    @api.model_create_multi
    def create(self, vals_list):
        if self.search_count([]) >= 1:
            raise ValidationError(_('Only one club can be created in this system.'))
            
        clubs = super(Club, self).create(vals_list)
        self.env.cr.flush()

        for club in clubs:
            self.env['club.log'].log_event(
                scope_type='club',
                activity_type='create',
                model=self._name,
                res_id=club.id,
                res_name=club.name,
                description=_("Club created: %s") % club.name
            )

        return clubs

    def action_create_default_roles_and_boards(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('club_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant', 'admin']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'scope_type': 'club',
                    'club_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'CLUB_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        if not self.board_ids:
            board = self.env['club.board'].create({
                'name': _("%s - Executive Board") % self.name,
                'group_type': 'board',
                'scope_type': 'club',
                'club_id': self.id,
            })

        return {
            'type': "ir.actions.client",
            'tag': 'reload',
        }
    

    ########################
    # UNLINK HOOK
    ########################

    def unlink(self):
        for club in self:
            if club.subclub_ids:
                raise ValidationError(
                    _("Subclubs associated to club. Club cannot be deleted!")
                )
            if club.board_ids:
                raise ValidationError(
                    _("Boards associated to club. Club cannot be deleted!")
                )
            if club.department_ids:
                raise ValidationError(
                    _("Departments associated to club. Club cannot be deleted! Deactivate Club instead.")
                )
            
            if club.role_ids:
                club.role_ids.unlink()

            self.env['club.log'].log_event(
                scope_type='club',
                activity_type='unlink',
                model=self._name,
                res_id=club.id,
                res_name=club.name,
                description=_("Club deleted: %s") % club.name
            )

        return super(Club, self).unlink()
        

