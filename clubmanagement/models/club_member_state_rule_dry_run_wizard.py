from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClubMemberStateRuleDryRunWizard(models.TransientModel):
    _name = 'club.member.state.rule.dry.run.wizard'
    _description = 'Club Member State Rule Dry Run Wizard'

    rule_ids = fields.Many2many(
        comodel_name='club.member.state.rule',
        relation='club_rule_dryrun_rule_rel',
        column1='wizard_id',
        column2='rule_id',
        string='Rules',
        required=True,
    )
    max_members = fields.Integer(string='Max Members Per Rule', default=200, required=True)
    line_ids = fields.One2many(
        comodel_name='club.member.state.rule.dry.run.wizard.line',
        inverse_name='wizard_id',
        string='Results',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if values.get('rule_ids'):
            return values

        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        if active_model == 'club.member.state.rule' and active_ids:
            values['rule_ids'] = [(6, 0, active_ids)]
        return values

    def action_run_dry_run(self):
        self.ensure_one()
        if not self.rule_ids:
            raise UserError(_('Please select at least one rule for the dry run.'))

        self.line_ids.unlink()
        line_values = []

        for rule in self.rule_ids.sorted(key=lambda r: (r.sequence, r.id)):
            for result in rule._run_dry_run(max_members=self.max_members):
                line_values.append(
                    {
                        'wizard_id': self.id,
                        'rule_id': rule.id,
                        'member_id': result['member_id'],
                        'matched': bool(result.get('matched')),
                        'would_execute_action': bool(result.get('would_execute_action')),
                        'error': result.get('error') or False,
                    }
                )

        if line_values:
            self.env['club.member.state.rule.dry.run.wizard.line'].create(line_values)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Rule Dry Run'),
            'res_model': 'club.member.state.rule.dry.run.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class ClubMemberStateRuleDryRunWizardLine(models.TransientModel):
    _name = 'club.member.state.rule.dry.run.wizard.line'
    _description = 'Club Member State Rule Dry Run Wizard Line'

    wizard_id = fields.Many2one(
        comodel_name='club.member.state.rule.dry.run.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    rule_id = fields.Many2one(comodel_name='club.member.state.rule', string='Rule', required=True, readonly=True)
    member_id = fields.Many2one(comodel_name='club.member', string='Member', required=True, readonly=True)
    matched = fields.Boolean(string='Matched', readonly=True)
    would_execute_action = fields.Boolean(string='Would Execute Action', readonly=True)
    error = fields.Text(string='Error', readonly=True)
