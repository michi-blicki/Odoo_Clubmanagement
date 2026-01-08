/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CustomFieldsWidget extends Component {
    static template = "clubmanagement.CustomFieldsWidget";

    // Use Odoo's standard field props to receive `value`, `field`, `record`, `update`, etc.
    static props = {
        ...standardFieldProps,
    };

    /**
     * Returns the list of custom fields stored as JSON in this field's value.
     * Safely handles cases where the value is not yet initialized.
     */
    get fields() {
        return Array.isArray(this.props.value) ? this.props.value : [];
    }

    /**
     * Triggered whenever an input value changes.
     * Updates the corresponding field value and writes it back to the record.
     */
    onValueChange(field, ev) {
        const isCheckbox = ev.target.type === "checkbox";
        const val = isCheckbox ? ev.target.checked : ev.target.value;
        field.value = val;

        // Preferred method since Odoo 17+ to update field values.
        if (typeof this.props.update === "function") {
            this.props.update({ [this.props.name]: this.fields });
        }
        // Fallback for older versions using record.update().
        else if (this.props.record && typeof this.props.record.update === "function") {
            this.props.record.update({ [this.props.name]: this.fields });
        }
    }
}

// Register the widget as a custom field type.
registry.category("fields").add("clubmanagement_custom_fields", {
    component: CustomFieldsWidget,
});
