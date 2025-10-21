/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalCustomerSelect = publicWidget.Widget.extend({
    selector: '#clear_customer_selection',
    events: {
        'click': '_onClearCustomer',
    },

    /**
     * Clear the selected customer from session
     * @private
     */
    _onClearCustomer: function (ev) {
        ev.preventDefault();
        const self = this;

        this._rpc({
            route: '/my/orders/clear_customer',
        }).then(function (result) {
            if (result.status === 'ok') {
                // Reload the page to update the UI
                window.location.href = '/shop';
            }
        });
    },
});

export default publicWidget.registry.PortalCustomerSelect;

/**
 * Global function to clear customer selection
 * Called from the indicator bar
 */
window.clearCustomerSelection = function() {
    if (confirm('Vuoi annullare l\'ordine corrente e tornare alla home del portale?')) {
        fetch('/my/orders/clear_customer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({}),
        }).then(function() {
            window.location.href = '/my/home';
        });
    }
    return false;
};
