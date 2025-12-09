from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

#####################################
# Club Log
#------------------------------------
# class ClubLog: main logging model
# class ClubLogMixin: abstract model
#####################################

class ClubLog(models.Model):
    _name = 'club.log'
    _description = 'Club Logfile'
    _order = 'create_date DESC, id DESC'

    name = fields.Char(string=_("Log Entry"), compute='_compute_name', store=True)
    user_id = fields.Many2one(string=_('User'), comodel_name='res.users', default=lambda self: self.env.user, readonly=True)
    create_date = fields.Datetime(string=_('Date'), readonly=True)

    scope_type = fields.Selection([
        ('club', _('Club')),
        ('board', _('Board')),
        ('subclub', _('Subclub')),
        ('department', _('Department')),
        ('pool', _('Pool')),
        ('team', _('Team')),
        ('member', _('Member')),
        ('role', _('Role / Function'))
    ], required=True)

    activity_type = fields.Selection([
        ('create', _('USer Create')),
        ('update', _('User Update')),
        ('unlink', _('User Unlink')),
        ('state_change', _('State Change')),
        ('system_action', _('System Action')),
        ('other', _('Other'))
    ], required=True)

    model = fields.Char(string=_('Model'), readonly=True)
    res_id = fields.Integer(string=_('Resource ID'), readonly=True)
    res_name = fields.Char(string=_('Resource Name'), readonly=True)

    description = fields.Text(string=_('Description'), readonly=True)
    old_value = fields.Text(string=_('Old Value'), readonly=True)
    new_value = fields.Text(string=_('New Value'), readonly=True)

    @api.depends('scope_type', 'activity_type', 'model', 'res_name')
    def _compute_name(self):
        for log in self:
            log.name = f"{log.scope_type.capitalize()} - {log.activity_type.capitalize()} - {log.model}: {log.res_name}"

    def _get_logging_models(self):
        return [
            'club.club',
            'club.subclub',
            'club.board',
            'club.department',
            'club.pool',
            'club.team',
            'club.member'
        ]
    def _should_log(self, model):
        return model in self._get_logging_models()

    ########################
    # CREATE HOOK
    ########################
    def log_event(self, scope_type, activity_type, model, res_id, res_name, description=False, old_value=False, new_value=False):
        self.create({
            'scope_type': scope_type,
            'activity_type': activity_type,
            'model': model,
            'res_id': res_id,
            'res_name': res_name,
            'description': description,
            'old_value': old_value,
            'new_value': new_value,
        })

    ########################
    # UNLINK HOOK
    #-----------------------
    # unlink not allowed!
    ########################
    def unlink(self):
        raise AccessError(_("Log Entries cannot be deleted!"))



class ClubLogMixin(models.AbstractModel):
    _name = 'club.log.mixin'
    _description = 'Club Log Mixin'

    def _get_log_scope_type(self):
        return self._name.split('.')[1]

    def create(self, vals):
        record = super(ClubLogMixin, self).create(vals)
        if self.env['club.log']._should_log(self._name):
            self.env['club.log'].log_event(
                scope_type=self._get_log_scope_type(),
                activity_type='create',
                model=self._name,
                res_id=record.id,
                res_name=record.display_name,
                description=_("Created %s") % self._description,
                new_value=str(vals)
            )
        return record

    def write(self,vals):
        if self.env['club.log']._should_log(self._name):
            for record in self:
                old_values = record.read(list(vals.keys()))[0]
                self.env['club.log'].log_event(
                    scope_type=self._get_log_scope_type(),
                    activity_type='update',
                    model=self._name,
                    res_id=record.id,
                    res_name=record.display_name,
                    description=_("Updated %s") % self._description,
                    old_value=str({k: v for k, v in old_values.items() if k in vals}),
                    new_value=str(vals)
                )
        return super(ClubLogMixin, self).write(vals)

    def unlink(self):
        if self.env['club.log']._should_log(self._name):
            for record in self:
                self.env['club.log'].log_event(
                    scope_type=self._get_log_scope_type(),
                    activity_type='unlink',
                    model=self._name,
                    res_id=record.id,
                    res_name=record.display_name,
                    description=_("Deleted %s") % self._description,
                    old_value=str(record.read()[0])
                )
        return super(ClubLogMixin, self).unlink()