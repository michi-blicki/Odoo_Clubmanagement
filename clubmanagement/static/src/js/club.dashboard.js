/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class ClubDashboard extends Component {
    setup() {
        this.http = useService("http");
        this.state = { loading: true };
        this.load();
    }
    async load() {
        const data = await this.http.post('/clubmanagement/dashboard/data', {});
        this.state = Object.assign({ loading: false }, data || {});
    }
}
ClubDashboard.template = "club.club.dashboard";
registry.category("actions").add("club.club.dashboard", ClubDashboard);
