// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Expense', {
    refresh: function(frm){
        // Clear value_addition_item field for all rows if form is new
        if (frm.is_new()) {
            (frm.doc.expenses || []).forEach(function(row) {
                frappe.model.set_value(row.doctype, row.name, 'value_addition_item', '');
            });
        }
    },

    setup: function(frm) {
        frm.set_query('paying_account', function() {
            return {
                filters: {
                    account_type: ['in', ['Bank', 'Cash']],
                    is_group: 0
                }
            };
        });
    },

    amount: function(frm) {
        // Recalculate when amount changes
        calculate_totals(frm);
    },

    supplier: function(frm) {
        // Fetch and set sales_team when customer changes
        if (!frm.doc.supplier) {
            frm.set_value("payment_to", "");
            return;
        }
        if (frm.doc.supplier) {
            frm.set_value("payment_to", frm.doc.supplier);
            return;
        }
    }
});

frappe.ui.form.on('Value Addition Detail', {
    expenses_remove: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },

    amount_spent: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },

    value_addition_item: function(frm, cdt, cdn) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let total_expense = 0;
    
    if (frm.doc.expenses) {
        frm.doc.expenses.forEach(function(row) {
            total_expense += flt(row.amount_spent || 0);
            difference_amount = flt(total_expense || 0) - flt(frm.doc.amount || 0);
        });
    }
    
    frm.set_value("total_expense", total_expense);
    frm.set_value("difference_amount", difference_amount);
    if (frm.doc.is_paid){
        frm.set_value("amount", total_expense);
        frm.set_value("difference_amount", 0);
    }
}
