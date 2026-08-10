/** @odoo-module **/
/*
    Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.
*/

import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

patch(StatusBarField.prototype, {
    setup() {
        super.setup(...arguments);

        if (
            this.props?.record?.resModel === "club.member"
            && this.props?.name === "current_state_id"
        ) {
            this.props.isDisabled = false;
        }
    },

    async selectItem(item) {
        const { name, record } = this.props;

        if (
            record?.resModel === "club.member"
            && name === "current_state_id"
            && this.field.type === "many2one"
            && record.resId
            && item
            && item.value
        ) {
            const currentValue = record.data[name];
            const currentStateId = Array.isArray(currentValue) ? currentValue[0] : false;
            if (currentStateId === item.value) {
                return;
            }

            await this.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "club.member.state.change.wizard",
                    views: [[false, "form"]],
                    target: "new",
                },
                {
                    additionalContext: {
                    default_member_id: record.resId,
                    default_current_state_id: currentStateId || false,
                    default_target_state_id: item.value,
                    },
                },
            );
            return;
        }

        return super.selectItem(...arguments);
    },
});
