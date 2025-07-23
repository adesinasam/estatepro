// Copyright (c) 2025, Adesina Akinyemi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plot Sales", {
    refresh: function(frm) {
        // Add "Receive Payment" button for submitted documents
        if (!frm.is_new() && frm.doc.docstatus === 1) {
            frm.add_custom_button('Receive Payment', function () {
                frappe.call({
                    method: 'estatepro.services.rest.get_receive_payment_defaults',
                    args: { plot_sale_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            frappe.route_options = r.message;
                            frappe.new_doc('Receive Payment');
                        }
                    }
                });
            }, 'Actions');
        }

        // Add "View Payment Schedule" button
        if (!frm.is_new()) {
            frappe.call({
                method: 'estatepro.estatepro.doctype.plot_sale.plot_sale.get_payment_schedule',
                args: { plot_sale: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        frm.add_custom_button('View Payment Schedule', function () {
                            frappe.set_route('Form', 'Plot Payment Schedule', r.message);
                        }, 'Actions');
                    }
                }
            });
        }

        // Calculate incentives when form loads
        calculateIncentives(frm);

        // Initialize totals when form loads
        calculate_totals(frm);

        // Clear land_bin field for all rows if form is new
        if (frm.is_new()) {
            (frm.doc.plots || []).forEach(function(row) {
                frappe.model.set_value(row.doctype, row.name, 'land_bin', '');
            });
        }

        // Set query for land_bin field in Plot Sales Detail child table
        frm.set_query('land_bin', 'plots', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            // If estate_project is not selected, return empty query to prevent selection
            if (!frm.doc.estate_project) {
                return {
                    filters: {
                        name: ['in', []] // Empty list to disable selection
                    }
                };
            }
            // Filter land_bin based on estate_project
            return {
                filters: {
                    estate_project: frm.doc.estate_project
                }
            };
        });
    },

    onload: function(frm) {
        if (frm.doc.docstatus === 1) {
            frappe.call({
                method: "estatepro.services.rest.get_invoice_table_html",
                args: { plot_sale: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        frm.fields_dict.invoice_html.$wrapper.html(r.message);

                        frm.fields_dict.invoice_html.$wrapper.on('click', '.pay-now-btn', function() {
                            let reference = $(this).data('reference');
                            let due_date = $(this).data('date');
                            let amount = $(this).data('amount');

                            let valuation = frm.doc.total_valuation || 0;
                            let sale_amount = frm.doc.sale_amount || 0;
                            let customer = frm.doc.customer;
                            let estate_project = frm.doc.estate_project;

                            frappe.new_doc('Receive Payment', {
                                plot_sale: reference,
                                paid_amount: amount,
                                posting_date: due_date,
                                valuation: valuation,
                                sale_amount: sale_amount,
                                customer: customer,
                                estate_project: estate_project
                            });
                        });
                    }
                }
            });
        }
    },

    // Re-apply query when estate_project changes
    estate_project: function(frm) {
        // Clear land_bin in child table when estate_project changes
        (frm.doc.plots || []).forEach(function(row) {
            frappe.model.set_value(row.doctype, row.name, 'land_bin', '');
        });
        // Refresh the plots field to apply updated query
        frm.refresh_field('plots');
    },

    estate_project: function(frm) {
        if (frm.doc.estate_project) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Estate Project",
                    name: frm.doc.estate_project
                },
                callback: function(project_res) {
                    if (project_res.message) {
                        const period = project_res.message.payment_period;
                        const terms = project_res.message.down_payment_terms;

                        // Temporarily fill if empty — user can still change it
                        if (!frm.doc.payment_plan) {
                            frm.set_value("payment_plan", period);
                        }
                        if (!frm.doc.down_payment_terms) {
                            frm.set_value("down_payment_terms", terms);
                            if (!frm.doc.down_payment_amount && project_res.message.down_payment_amount) {
                                frm.set_value("down_payment_amount", project_res.message.down_payment_amount);
                            }
                            if (!frm.doc.set_downpayment_percentage && project_res.message.set_downpayment_percentage) {
                                frm.set_value("set_downpayment_percentage", project_res.message.set_downpayment_percentage);
                            }
                        }
                    }
                }
            });
        }
    },

    sale_amount: function(frm) {
        // Recalculate when sale_amount changes
        calculateIncentives(frm);
        if(frm.doc.commission_rate){
            total_commission = (frm.doc.commission_rate / 100) * frm.doc.sale_amount;
            frm.set_value("total_commission", total_commission);
            frm.set_value("amount_eligible_for_commission", total_commission);
        }
    },

    commission_rate: function(frm) {
        // Recalculate when commission_rate changes
        if(frm.doc.sale_amount){
            total_commission = (frm.doc.commission_rate / 100) * frm.doc.sale_amount;
            frm.set_value("total_commission", total_commission);
            frm.set_value("amount_eligible_for_commission", total_commission);
        }
    },

    customer: function(frm) {
        // Fetch and set sales_team when customer changes
        if (!frm.doc.customer) {
            frm.set_value("sales_team", []);
            return;
        }
        
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Customer",
                name: frm.doc.customer,
                fieldname: ["sales_team"]
            },
            callback: function(response) {
                if (response.message && response.message.sales_team) {
                    frm.set_value("sales_team", []);
                    
                    response.message.sales_team.forEach(function(row) {
                        var new_row = frm.add_child("sales_team");
                        new_row.sales_person = row.sales_person;
                        new_row.allocated_percentage = row.allocated_percentage;
                        // Calculate incentives if sale_amount exists
                        if (frm.doc.sale_amount) {
                            new_row.incentives = (row.allocated_percentage / 100) * frm.doc.sale_amount;
                        }
                    });
                    
                    frm.refresh_field("sales_team");
                }
            }
        });
    }
});

frappe.ui.form.on('Plot Sales Detail', {
    plots_remove: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },

    sale_amount: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        // Type checking and default values
        d.qty = flt(d.qty) || 0;
        d.size = flt(d.size) || 0;
        d.valuation = flt(d.valuation) || 0;
        d.sale_amount = flt(d.sale_amount) || 0;
        
        d.total_size = flt(d.qty * d.size);
        d.total_valuation = flt(d.qty * d.valuation);
        d.total_amount = flt(d.qty * d.sale_amount);
        
        refresh_field('plots');
        calculate_totals(frm);
    },

    land_bin: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (d.plot_size && typeof d.plot_size === 'string') {
            frappe.call({
                method: "frappe.client.get",
                args: {  // Fixed parameter name from 'arg' to 'args'
                    doctype: "Plot Size",
                    name: d.plot_size
                },
                callback: function(plot_res) {
                    if (!plot_res.exc && plot_res.message) {
                        frappe.model.set_value(cdt, cdn, {
                            'size': flt(plot_res.message.size_no) || 0,
                            'uom': plot_res.message.uom || ''
                        }).then(() => {
                            // Recalculate after values are set
                            let row = locals[cdt][cdn];
                            row.total_size = flt(row.qty) * flt(row.size);
                            row.total_valuation = flt(row.qty) * flt(row.valuation);
                            row.total_amount = flt(row.qty) * flt(row.sale_amount);
                            refresh_field('plots');
                            calculate_totals(frm);
                        });
                    }
                },
                error: function(err) {
                    console.error("Error fetching Plot Size:", err);
                    frappe.msgprint(__("Error fetching Plot Size details"));
                }
            });
        }
        
        // Initial calculations if plot_size not set
        d.total_size = flt(d.qty) * flt(d.size);
        d.total_valuation = flt(d.qty) * flt(d.valuation);
        d.total_amount = flt(d.qty) * flt(d.sale_amount);
        refresh_field('plots');
        calculate_totals(frm);
    },

    qty: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        // Type checking and default values
        d.qty = flt(d.qty) || 0;
        d.size = flt(d.size) || 0;
        d.valuation = flt(d.valuation) || 0;
        d.sale_amount = flt(d.sale_amount) || 0;
        
        d.total_size = flt(d.qty * d.size);
        d.total_valuation = flt(d.qty * d.valuation);
        d.total_amount = flt(d.qty * d.sale_amount);
        
        refresh_field('plots');
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let total_sale = 0;
    let total_size = 0;
    let total_qty = 0;
    let total_valuation = 0;
    
    if (frm.doc.plots) {
        frm.doc.plots.forEach(function(row) {
            total_sale += flt(row.total_amount || 0);
            total_size += flt(row.total_size || 0);
            total_qty += flt(row.qty || 0);
            total_valuation += flt(row.total_valuation || 0);
        });
    }
    
    frm.set_value("sale_amount", total_sale);
    frm.set_value("total_size", total_size);
    frm.set_value("total_qty", total_qty);
    frm.set_value("total_valuation", total_valuation);
}

// Function to calculate incentives for all sales_team rows
function calculateIncentives(frm) {
    if (!frm.doc.sale_amount || !frm.doc.sales_team) return;
    
    frm.doc.sales_team.forEach(function(row) {
        row.incentives = (row.allocated_percentage / 100) * frm.doc.sale_amount;
    });
    
    frm.refresh_field("sales_team");
}

// Recalculate when any allocated_percentage changes
frappe.ui.form.on("Sales Team", {
    allocated_percentage: function(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        if (frm.doc.sale_amount) {
            row.incentives = (row.allocated_percentage / 100) * frm.doc.sale_amount;
            frm.refresh_field("sales_team");
        }
    }
});