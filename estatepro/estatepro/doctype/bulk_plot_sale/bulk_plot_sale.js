// Copyright (c) 2025, Adesina Akinyemi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Plot Sale", {
    refresh: function(frm) {
        // Initialize totals when form loads
        calculate_totals(frm);
        
        // Clear plot_sale field for all rows if form is new
        if (frm.is_new()) {
            (frm.doc.plots || []).forEach(function(row) {
                frappe.model.set_value(row.doctype, row.name, 'plot_sale', '');
            });
        }
    }    
});


frappe.ui.form.on('Plot Sale Items', {
    plot_name: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.plot_name) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Plot",
                    name: row.plot_name
                },
                callback: function(plot_res) {
                    if (plot_res.message && plot_res.message.project) {
                        frappe.call({
                            method: "frappe.client.get",
                            args: {
                                doctype: "Estate Project",
                                name: plot_res.message.project
                            },
                            callback: function(project_res) {
                                if (project_res.message) {
                                    // Set project-level defaults for this plot row
                                    frappe.model.set_value(cdt, cdn, {
                                        'allow_installment': project_res.message.allow_installments,
                                        'payment_plan': project_res.message.payment_period,
                                        'down_payment_terms': project_res.message.down_payment_terms
                                    });

                                    // Set down payment amount/percentage based on project settings
                                    if (project_res.message.down_payment_terms === "Amount") {
                                        frappe.model.set_value(cdt, cdn, 'down_payment_amount', project_res.message.down_payment_amount);
                                    } else {
                                        frappe.model.set_value(cdt, cdn, 'set_downpayment_percentage', project_res.message.set_downpayment_percentage);
                                    }
                                }
                            }
                        });
                    }
                }
            });
        }
        calculate_totals(frm);
    },

    plots_remove: function(frm, cdt, cdn){
        calculate_totals(frm);
    },

    sale_amount: function(frm, cdt, cdn) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let total_sale = 0;
    let total_valuation = 0;
    
    if (frm.doc.plots) {
        frm.doc.plots.forEach(function(row) {
            total_sale += flt(row.sale_amount || 0);
            total_valuation += flt(row.valuation || 0);
        });
    }
    
    frm.set_value("total_sale_amount", total_sale);
    frm.set_value("total_valuation", total_valuation);
    frm.set_value("balance", total_sale);
}

