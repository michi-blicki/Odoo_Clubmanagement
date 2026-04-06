from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError, UserError

from dateutil.relativedelta import relativedelta
import base64
from io import BytesIO
from datetime import date

from PIL import Image

import logging
_logger = logging.getLogger(__name__)


class ClubMember(models.Model):
    _name = 'club.member'
    _description = 'Club Member'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
        'club.custom.field.mixin',
        'club.security.mixin',
    ]

    #
    # Personal Identification Fields
    partner_id              = fields.Many2one(string="Contact", comodel_name="res.partner", required=True, ondelete="restrict", store=True)
    member_id               = fields.Integer(string="Member ID", required=True, readonly=True)
    photo                   = fields.Binary(string="Photo", attachment=True, help="Member photo of size 680x960 or 1360x1920")

    #
    # Under-Age specialities
    guardian_ids            = fields.One2many(string='Guardians', comodel_name='club.member.guardian', inverse_name='member_id', required=False)
    primary_guardian_id     = fields.Many2one(string='Primary Guardian', comodel_name='res.partner', compute='_compute_primary_guardian', store=True)
    requires_guardian       = fields.Boolean(string='Requires Guardian', compute='_compute_age', store=True)

    #
    # HR Special Fields
    is_employee             = fields.Boolean(string="Is Employee", default=False)
    employee_id             = fields.Many2one(string="Employee", comodel_name="hr.employee", tracking=True)

    #
    # Clubmanagement Special Fields
    club_id                 = fields.Many2one(string="Club", comodel_name="club.club", store=True, readonly=True, default=lambda self: self.env["club.club"].search([], limit=1).id)
    subclub_ids             = fields.Many2many(string="Subclubs", comodel_name="club.subclub", relation="club_subclub_member_rel", column1="member_id", column2="subclub_id")
    department_ids          = fields.Many2many(string="Departments", comodel_name="club.department", relation="club_department_member_rel", column1="member_id", column2="department_id")
    pool_ids                = fields.Many2many(string="Pools", comodel_name="club.pool", relation="club_pool_member_rel", column1="member_id", column2="pool_id")
    team_ids                = fields.Many2many(string="Teams", comodel_name="club.team", relation="club_team_member_rel", column1="member_id", column2="team_id")

    role_ids                = fields.One2many(string="Roles / Functions", comodel_name="club.role", inverse_name="member_id")

    invoice_partner_id      = fields.Many2one(
        string="Invoice Partner",
        comodel_name="res.partner",
        tracking=True,
    )
    invoice_partner_source  = fields.Selection(
        selection=[
            ('self', 'Self'),
            ('primary_guardian', 'Primary Guardian'),
            ('manual', 'Manual'),
        ],
        string="Invoice Partner Source",
        tracking=True,
        default=lambda self: self._default_invoice_partner_source(),
    )
    invoice_grouping_mode   = fields.Selection(
        selection=[
            ('single', 'Single Invoice'),
            ('by_payer', 'Group by Payer'),
        ],
        string="Invoice Grouping Mode",
        tracking=True,
        default=lambda self: self._default_invoice_grouping_mode(),
    )

    current_membership_id  = fields.Many2one(string="Current Membership", comodel_name="club.member.membership", compute="_compute_current_membership", store=True)
    membership_history_ids = fields.One2many(string="Membership History", comodel_name="club.member.membership.history", inverse_name="member_id")
    membership_date_start  = fields.Date(string="Membership Start Date", compute="_compute_current_membership", store=True)
    membership_date_end    = fields.Date(string="Membership End Date", compute="_compute_current_membership", store=True)

    current_state_id       = fields.Many2one(string="Current Member State", comodel_name="club.member.state", compute="_compute_current_state", store=True)
    state_history_ids      = fields.One2many(string="Member State History", comodel_name="club.member.state.history", inverse_name="member_id")
    state_date_start       = fields.Date(string="State Start Date", compute="_compute_current_state", store=True)
    state_days_in_state    = fields.Integer(string="Days in current state", compute="_compute_state_days_since_start", store=False)
    state_header_color     = fields.Char(string="Kanban Header Color", compute="_compute_state_days_since_start", store=False)

    active                 = fields.Boolean(default=True, tracking=True)

    year_of_birth          = fields.Integer(string="Year of Birth", compute="_compute_year_of_birth", store=True)
    age                    = fields.Integer(string="Age", compute="_compute_age", store=True)
    years_in_club          = fields.Float(string="Years in Club", compute="_compute_membership_duration", store=True)
    months_in_club         = fields.Integer(string="Months in Club", compute="_compute_membership_duration", store=True)
    days_in_club           = fields.Integer(string="Days in Club", compute="_compute_membership_duration", store=True)

    custom_field_lines     = fields.Json(string="Custom Fields", compute="_compute_custom_fields")


    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.model
    def _default_invoice_grouping_mode(self):
        value = self.env['ir.config_parameter'].sudo().get_param('clubmanagement.default_invoice_grouping_mode', 'single')
        return value if value in ('single', 'by_payer') else 'single'

    @api.model
    def _default_invoice_partner_source(self):
        value = self.env['ir.config_parameter'].sudo().get_param('clubmanagement.default_minor_invoice_source', 'primary_guardian')
        return value if value in ('self', 'primary_guardian', 'manual') else 'manual'

    @api.model
    def _get_age_of_majority(self):
        value = self.env['ir.config_parameter'].sudo().get_param('clubmanagement.age_of_majority', 18)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 18

    @api.model
    def _is_minor_for_billing(self, birthdate_value):
        if not birthdate_value:
            return False
        birthdate = fields.Date.to_date(birthdate_value)
        if not birthdate:
            return False
        age = relativedelta(fields.Date.today(), birthdate).years
        return age < self._get_age_of_majority()

    @api.model
    def _can_manage_billing_fields(self):
        user = self.env.user
        return (
            user.has_group('account.group_account_invoice')
            or user.has_group('account.group_account_manager')
            or user.has_group('clubmanagement.group_clubmanagement_key_user')
        )

    @api.model
    def _check_billing_field_permissions(self, vals):
        if self._context.get('club_billing_internal'):
            return

        billing_fields = {'invoice_partner_id', 'invoice_partner_source', 'invoice_grouping_mode'}
        if billing_fields.intersection(set(vals.keys())) and not self._can_manage_billing_fields():
            raise AccessError(_("You are not allowed to modify member billing fields."))

    def _validate_invoice_partner_quality(self):
        for member in self:
            partner = member.invoice_partner_id
            if not partner:
                continue

            missing = []
            if not partner.name:
                missing.append('name')
            if not partner.street:
                missing.append('street')
            if not partner.zip:
                missing.append('zip')
            if not partner.city:
                missing.append('city')

            if missing:
                raise ValidationError(
                    _("Invoice partner '%s' is missing required billing fields: %s")
                    % (partner.display_name, ', '.join(missing))
                )

    def _apply_billing_defaults(self):
        default_minor_source = self._default_invoice_partner_source()
        default_grouping = self._default_invoice_grouping_mode()

        for member in self:
            values = {}

            if not member.invoice_grouping_mode:
                values['invoice_grouping_mode'] = default_grouping

            is_minor = self._is_minor_for_billing(member.birthdate_date)
            if not is_minor:
                if member.invoice_partner_source != 'self':
                    values['invoice_partner_source'] = 'self'
                if member.invoice_partner_id != member.partner_id:
                    values['invoice_partner_id'] = member.partner_id.id
            else:
                if member.invoice_partner_source != 'manual':
                    if default_minor_source == 'primary_guardian' and member.primary_guardian_id:
                        values['invoice_partner_source'] = 'primary_guardian'
                        values['invoice_partner_id'] = member.primary_guardian_id.id
                    elif not member.invoice_partner_source:
                        values['invoice_partner_source'] = 'manual'

            if values:
                member.with_context(club_billing_internal=True).write(values)

    @api.constrains('partner_id')
    def _check_unique_member_for_partner(self):
        for member in self:
            duplicate = self.search([
                ('partner_id', '=', member.partner_id.id),
                ('id', '!=', member.id)
            ])
            if duplicate:
                raise ValidationError(_("Partner '%s' is already linked to another club member.") % member.partner_id.display_name)

    @api.depends('birthdate_date')
    def _compute_year_of_birth(self):
        for mem in self:
            mem.year_of_birth = mem.birthdate_date.year if mem.birthdate_date else False

    @api.depends('birthdate_date')
    def _compute_age(self):
        force_guardian_requirement = bool(self.env['ir.config_parameter'].sudo().get_param('clubmanagement.force_guardian_requirement', False))
        age_of_majority = int(self.env['ir.config_parameter'].sudo().get_param('clubmanagement.age_of_majority', 18))
        today = fields.Date.today()
        for member in self:
            if member.birthdate_date:
                member.age = relativedelta(today, member.birthdate_date).years
                if force_guardian_requirement:
                    member.requires_guardian = member.age < age_of_majority
            else:
                member.age = False
                member.requires_guardian = False

    @api.depends('photo')
    def _check_photo_size(self):
        for member in self:
            if member.photo:
                try:
                    image_data = base64.b64decode(member.photo)
                    im = Image.open(BytesIO(image_data))
                    if(im.width, im.height) not in [(680,960), (1360,1920)]:
                        raise ValidationError(
                            _("The member photo must be exactly 680x960 or 1360x1920 pixels. Your photo is: %sx%s", im.width, im.height)
                        )
                except Exception:
                    raise ValidationError(
                        _("Could not verify the member photo. Please upload a valid image file")
                    )

    @api.depends('guardian_ids', 'guardian_ids.is_primary')
    def _compute_primary_guardian(self):
        for member in self:
            primary = member.guardian_ids.filtered(lambda g: g.is_primary)
            member.primary_guardian_id = primary.guardian_id if primary else False

    @api.constrains('requires_guardian', 'guardian_ids')
    def _check_guardian_required(self):
        for member in self:
            if member.requires_guardian and not member.guardian_ids:
                raise ValidationError(_('A guardian is required for members under the age of majority.'))

    def add_or_update_guardian(self, guardian_data):
        self.ensure_one()
        Guardian = self.env['club.member.guardian']
        existing = Guardian.search({
            ('member_id', '=', self.id),
            ('guardian_id', '=', guardian_data['guardian_id'])
        })

        if existing:
            existing.write(guardian_data)
        else:
            guardian_data['member_id'] = self.id
            Guardian.create(guardian_data)


    #######################################
    # CREATE HOOK
    #######################################
    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            existing_partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)
            if existing_partner:
                return {
                    'warning': {
                        'title': _("Existing Contact Found"),
                        'message': _("A contact '%s' already exists with this email. Please link instead of creating new.") % existing_partner.display_name,
                    }
                }

    @api.onchange('firstname', 'lastname')
    def _onchange_firstname_lastname(self):
        if self.firstname and self.lastname:
            duplicates = self.env['res.partner'].search([
                ('firstname', 'ilike', self.firstname),
                ('lastname', 'ilike', self.lastname),
            ])
            if len(duplicates) > 0:
                return {
                    'warning': {
                        'title': _("Similar Names Found"),
                        'message': _("There are %s contacts named '%s %s'. Please confirm this is a different person or link to an existing contact.") %
                                (len(duplicates), self.firstname, self.lastname),
                    }
                }

    @api.model_create_multi
    def create(self, vals_list):
        Partner = self.env['res.partner']

        self._check_user_action_permissions('create', record=self.env['club.member'])

        for vals in vals_list:
            self._check_billing_field_permissions(vals)
            # Generiere Partner
            if not vals.get('partner_id'):
                partner_vals = {
                    key: vals[key] for key in vals if key in Partner._fields
                }
                new_partner = Partner.create(partner_vals)
                vals['partner_id'] = new_partner.id
            # Generiere Member ID
            vals['member_id'] = self._generate_member_id()
        members = super(ClubMember, self).create(vals_list)

        members.with_context(club_billing_internal=True)._apply_billing_defaults()

        for member in members:
            if member.partner_id:
                member.partner_id.is_club_member = True
                member.partner_id.club_member_id = member.id

        for member in members:
            if member.requires_guardian and not member.guardian_ids:
                pass

        for member, vals in zip(members, vals_list):
            custom_data = vals.get('custom_field_lines')
            if custom_data:
                member.write_custom_fields(custom_data)

        self.env['club.member.state.rule']._apply_registratoin_rules(members)

        for member in members:
            self.env['club.log'].log_event(
                scope_type='member',
                activity_type='create',
                model=self._name,
                res_id=member.id,
                res_name=member.display_name,
                description=_("Member created: %s") % member.name
            )

        return members

    def _generate_member_id(self):
        """Generiert fortlaufende Member ID.
        Nutzt Startwert aus den Systemeinstellungen, wenn gesetzt.
        """
        # 1️⃣ Letzten Member bestimmen
        last_member = self.search([], order="member_id desc", limit=1)

        # 2️⃣ Wenn schon Mitglieder vorhanden → normal weiterzählen
        if last_member:
            return last_member.member_id + 1

        # 3️⃣ Sonst Startwert aus ResConfigSettings (Systemparameter) laden
        IrConfig = self.env["ir.config_parameter"].sudo()
        start_id_set = IrConfig.get_param("clubmanagement.start_member_id_set")
        start_id_val = IrConfig.get_param("clubmanagement.start_member_id")

        try:
            start_id_val = int(start_id_val) if start_id_val else 1
        except ValueError:
            start_id_val = 1

        # Wenn Startwert explizit aktiviert wurde und vorhanden ist
        if start_id_set in ("True", True) and start_id_val > 0:
            return start_id_val

        # 4️⃣ Standard-Fallback
        return 1

    #######################################
    # WRITE HOOK
    #######################################
    def write(self, vals):
        self._check_billing_field_permissions(vals)

        for rec in self:
            rec._check_user_action_permissions('write', record=rec)

        res = super().write(vals)

        if {'birthdate_date', 'primary_guardian_id', 'guardian_ids', 'partner_id', 'invoice_partner_source', 'invoice_partner_id', 'invoice_grouping_mode'}.intersection(set(vals.keys())):
            self.with_context(club_billing_internal=True)._apply_billing_defaults()

        # Update custom fields, if available and required
        if 'custom_field_lines' in vals:
            for rec in self:
                rec.write_custom_fields(vals['custom_field_lines'])

        return res

    #######################################
    # UNLINK HOOK
    #######################################
    def unlink(self):
        for member in self:
            self._check_user_action_permissions('unlink', record=member)

            partner = member.partner_id
            partner.is_club_member = False
            
        return super(ClubMember, self).unlink()

    ###################################
    # MEMBER STATES - Functionalities
    ###################################
    @api.depends('state_history_ids.start_date', 'state_history_ids.end_date')
    def _compute_current_state(self):
        for member in self:
            current_state = self.env['club.member.state.history'].search([
                ('member_id', '=', member.id),
                ('start_date', '<=', fields.Datetime.now()),
                '|', ('end_date', '=', False), ('end_date', '>', fields.Datetime.now())
            ], order='start_date desc, id desc', limit=1)
            member.current_state_id = current_state.state_id if current_state else False
            member.state_date_start = current_state.start_date if current_state else False

    @api.depends('state_history_ids.start_date', 'state_history_ids.end_date')
    def _compute_membership_duration(self):
        today = fields.Date.context_today(self)
        for member in self:
            # Ältesten State-History-Eintrag suchen
            oldest_state = member.state_history_ids.sorted('start_date')[:1]
            if oldest_state:
                start_date = fields.Date.to_date(oldest_state.start_date)
                delta = relativedelta(today, start_date)
                member.years_in_club = delta.years + (delta.months / 12.0)
                member.months_in_club = (delta.years * 12) + delta.months
                member.days_in_club = (today - start_date).days
            else:
                member.years_in_club = 0.0
                member.months_in_club = 0
                member.days_in_club = 0

    @api.depends('state_date_start')
    def _compute_state_days_since_start(self):
        for member in self:
            if member.state_date_start:
                member.state_days_in_state = (fields.Date.today() - member.state_date_start).days
                if member.state_days_in_state > 28:
                    member.state_header_color = "kanban-header-red"
                elif member.state_days_in_state >= 10:
                    member.state_header_color = "kanban-header-yellow"
                else:
                    member.state_header_color = ""
            else:
                member.state_days_in_state = 0

    def set_state(self, state_id, reason=None):
        self.ensure_one()
        current_state = self.state_history_ids.filtered(lambda r: not r.end_date)
        if current_state:
            current_state.write({'end_date': fields.Datetime.now()})

        self.env['club.member.state.history'].create({
            'member_id': self.id,
            'state_id': state_id,
            'reason': reason,
        })

    #######################################
    # MEMBER MEMBERSHIP - Functionalities
    #######################################
    @api.depends('membership_history_ids.date_start', 'membership_history_ids.date_end', 'membership_history_ids.active')
    def _compute_current_membership(self):
        today = fields.Date.context_today(self)
        for member in self:
            current_membership = self.env['club.member.membership.history'].search([
                ('member_id', '=', member.id),
                ('date_start', '<=', today),
                '|', ('date_end', '=', False), ('date_end', '>=', today),
                ('active', '=', True)
            ], order='date_start DESC, id DESC', limit=1)

            member.current_membership_id = current_membership.membership_id if current_membership else False
            member.membership_date_start = current_membership.date_start if current_membership else False
            member.membership_date_end   = current_membership.date_end if current_membership else False

    def set_membership(self, membership_id, date_start=None, date_end=None, note=None):
        self.ensure_one()
        if not date_start:
            date_start = fields.Date.context_today(self)

        current_active_membership = self.membership_history_ids.filtered(lambda r: r.active and r.date_start <= date_start and (not r.date_end or r.date_end >= date_start))
        if current_active_membership:
            current_active_membership.write({
                'active': False,
                'date_end': date_start,
            })

        self.env['club.member.membership.history'].create({
            'member_id': self.id,
            'membership_id': membership_id,
            'date_start': date_start,
            'date_end': date_end,
            'note': note,
        })

        self.env['club.log'].log_event(
            scope_type='member',
            activity_type='update',
            model=self._name,
            res_id=self.id,
            res_name=self.display_name,
            description=_("Membership changed to %s") % self.env['club.member.membership'].browse(membership_id).name,
            old_value=self.current_membership_id.name if self.current_membership_id else 'None',
            new_value=self.env['club.member.membership'].browse(membership_id).name
        )

        self._compute_current_membership()

    def end_current_membership(self, end_date=None, note=None):
        self.ensure_one()
        if not end_date:
            end_date = fields.Date.context_today(self)

        current_active_membership = self.membership_history_ids.filtered(lambda r: r.active and r.date_start <= end_date and (not r.date_end or r.date_end >= end_date))
        if current_active_membership:
            current_active_membership.write({
                'active': False,
                'date_end': end_date,
                'note': note,
            })

            self.env['club.log'].log_event(
                scope_type='member',
                activity_type='update',
                model=self._name,
                res_id=self.id,
                res_name=self.display_name,
                description=_("Membership Ended: %s") % current_active_membership.membership_id.name,
                old_value=current_active_membership.membership_id.name,
                new_value='None'
            )

        self._compute_current_membership()

    #######################################
    # CLUB SECURITY MIXIN
    #######################################
    @api.model
    def search(self, args, **kwargs):
        if self.env.su or self._context.get('club_security_internal'):
            return super().search(args, **kwargs)

        user = self.env.user
        
        if not (
            user.has_group('clubmanagement.group_clubmanagement_administrator') or
            user.has_group('clubmanagement.group_clubmanagement_master_user')
        ):
            visible_members = self._get_visible_member_ids(user)
            args = [('id', 'in', visible_members.ids)] + list(args)
        return super().search(args, **kwargs)