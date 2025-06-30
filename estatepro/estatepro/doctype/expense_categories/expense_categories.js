// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Expense Categories', {
    setup: function(frm) {
        if (!frm.is_quick_entry) {
            frm.fields_dict.expense_account.get_query = function() {
                return {
                    filters: [
                        ["Account", "root_type", "=", "Expense"],
                        ["Account", "is_group", "=", 0]
                    ]
                };
            };
        }
    }
});