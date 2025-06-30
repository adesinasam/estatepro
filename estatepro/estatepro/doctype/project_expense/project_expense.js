// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Expense', {
    setup: function(frm) {
        frm.set_query('paying_account', function() {
            return {
                filters: {
                    account_type: ['in', ['Bank', 'Cash']],
                    is_group: 0
                }
            };
        });
    }
});