frappe.ui.form.on('Plot Sale', {
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

                            let valuation = frm.doc.valuation || 0;
                            let sale_amount = frm.doc.sale_amount || 0;

                            frappe.new_doc('Receive Payment', {
                                plot_sale: reference,
                                paid_amount: amount,
                                posting_date: due_date,
                                valuation: valuation,
                                sale_amount: sale_amount
                            });
                        });
                    }
                }
            });
        }
    },

    plot_name: function(frm) {
        if (frm.doc.plot_name) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Plot",
                    name: frm.doc.plot_name
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

                                    toggle_installment_fields(frm);
                                }
                            }
                        });
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