// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Expense', {
    refresh: function(frm) {
        // Clear value_addition_item field for all rows if form is new
        // if (frm.is_new()) {
        //     (frm.doc.expenses || []).forEach(function(row) {
        //         frappe.model.set_value(row.doctype, row.name, 'value_addition_item', '');
        //     });
        // }
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

    get_plot_size_details: function(frm) {
        if (!frm.doc.estate_project) {
            frappe.msgprint(__("Please enter Estate Project first"));
            return;
        }
        frm.call({
            doc: frm.doc,
            method: "get_plot_size_details",
            callback: function() {
                frm.trigger("set_applicable_charges_for_item");
            }
        });
    },

    set_applicable_charges_for_item: function(frm) {
        if (!frm.doc.expenses || !frm.doc.expenses.length) return;

        var based_on = (frm.doc.distribute_charges_based_on || "").toLowerCase();
        if (based_on === "distribute manually") return;

        var total_item_cost = 0.0;
        $.each(frm.doc.plots || [], function(i, d) {
            total_item_cost += flt(d[based_on]);
        });

        if (total_item_cost <= 0) return;

        var total_charges = 0.0;
        $.each(frm.doc.plots || [], function(i, item) {
            item.applicable_charges = (flt(item[based_on]) * flt(frm.doc.total_expense)) / flt(total_item_cost);
            item.applicable_charges = flt(item.applicable_charges, precision("applicable_charges", item));
            total_charges += item.applicable_charges;
        });

        // Adjust rounding difference in the last item
        if (total_charges != frm.doc.total_expense && frm.doc.plots.length) {
            var diff = frm.doc.total_expense - flt(total_charges);
            frm.doc.plots.slice(-1)[0].applicable_charges += diff;
        }
        refresh_field("plots");
    },

    estate_project: function(frm) {
        frm.trigger("get_plot_size_details");
    },

    distribute_charges_based_on: function(frm) {
        frm.trigger("set_applicable_charges_for_item");
        refresh_field("plots");
    },

    plots_remove: function(frm) {
        frm.trigger("set_applicable_charges_for_item");
    },

    amount: function(frm) {
        calculate_totals(frm);
    },

    supplier: function(frm) {
        if (!frm.doc.supplier) {
            frm.set_value("payment_to", "");
        } else {
            frm.set_value("payment_to", frm.doc.supplier);
        }
    }
});

frappe.ui.form.on('Value Addition Detail', {
    expenses_remove: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },

    amount_spent: function(frm, cdt, cdn) {
        calculate_totals(frm);
        frm.trigger("set_applicable_charges_for_item");
    },

    value_addition_item: function(frm, cdt, cdn) {
        calculate_totals(frm);
        frm.trigger("set_applicable_charges_for_item");
    }
});

function calculate_totals(frm) {
    let total_expense = 0;
    let difference_amount = 0;
    
    if (frm.doc.expenses) {
        frm.doc.expenses.forEach(function(row) {
            total_expense += flt(row.amount_spent || 0);
        });
        difference_amount = flt(total_expense) - flt(frm.doc.amount || 0);
    }
    
    frm.set_value("total_expense", total_expense);
    frm.set_value("difference_amount", difference_amount);
    
    if (frm.doc.is_paid) {
        frm.set_value("amount", total_expense);
        frm.set_value("difference_amount", 0);
    }
}