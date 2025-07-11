frappe.ui.form.on('Receive Payment', {
    validate(frm) {
        if (frm.doc.paid_amount <= 0) {
            frappe.throw("Paid amount must be greater than 0.");
        }
        if (frm.doc.plot_sale) {
            frappe.db.get_doc('Plot Sale', frm.doc.plot_sale).then(sale => {
                if (frm.doc.paid_amount > sale.balance) {
                    frappe.throw(`Paid amount exceeds remaining balance of ${sale.balance}`);
                }
            });
        }
    },

    onload: function(frm) {
        // If loaded via frappe.route_options, prefill fields
        if (frappe.route_options) {
            Object.keys(frappe.route_options).forEach(key => {
                if (!frm.doc[key]) {
                    frm.set_value(key, frappe.route_options[key]);
                }
            });
            frappe.route_options = null;  // clear it after use
        }
    },

    refresh(frm) {
        if (!frm.is_new() && frm.doc.docstatus === 1 && frm.doc.plot_sale) {
            frm.add_custom_button("View Plot Sale", () => {
                frappe.set_route('Form', 'Plot Sale', frm.doc.plot_sale);
            }, 'View');

            frappe.db.get_value('Plot Payment Schedule', { plot_sale: frm.doc.plot_sale }, 'name')
                .then(r => {
                    if (r.message) {
                        frm.add_custom_button("View Payment Schedule", () => {
                            frappe.set_route('Form', 'Plot Payment Schedule', r.message);
                        }, 'View');
                    }
                });
        }

        // Calculate incentives when form loads
        calculateIncentives(frm);

    },

    paid_amount: function(frm) {
        // Recalculate when paid_amount changes
        calculateIncentives(frm);
        if(frm.doc.commission_rate){
            total_commission = (frm.doc.commission_rate / 100) * frm.doc.paid_amount;
            frm.set_value("total_commission", total_commission);
            frm.set_value("amount_eligible_for_commission", total_commission);
        }
    },

    commission_rate: function(frm) {
        // Recalculate when commission_rate changes
        if(frm.doc.paid_amount){
            total_commission = (frm.doc.commission_rate / 100) * frm.doc.paid_amount;
            frm.set_value("total_commission", total_commission);
            frm.set_value("amount_eligible_for_commission", total_commission);
        }
    },

    plot_sale: function(frm) {
        // Fetch and set sales_team when plot_sale changes
        if (!frm.doc.plot_sale) {
            frm.set_value("sales_team", []);
            return;
        }
        
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Plot Sale",
                name: frm.doc.plot_sale,
                fieldname: ["sales_team"]
            },
            callback: function(response) {
                if (response.message && response.message.sales_team) {
                    frm.set_value("sales_team", []);
                    
                    response.message.sales_team.forEach(function(row) {
                        var new_row = frm.add_child("sales_team");
                        new_row.sales_person = row.sales_person;
                        new_row.allocated_percentage = row.allocated_percentage;
                        // Calculate incentives if paid_amount exists
                        if (frm.doc.paid_amount) {
                            new_row.incentives = (row.allocated_percentage / 100) * frm.doc.paid_amount;
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
    if (!frm.doc.paid_amount || !frm.doc.sales_team) return;
    
    frm.doc.sales_team.forEach(function(row) {
        row.incentives = (row.allocated_percentage / 100) * frm.doc.paid_amount;
    });
    
    frm.refresh_field("sales_team");
}

// Recalculate when any allocated_percentage changes
frappe.ui.form.on("Sales Team", {
    allocated_percentage: function(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        if (frm.doc.paid_amount) {
            row.incentives = (row.allocated_percentage / 100) * frm.doc.paid_amount;
            frm.refresh_field("sales_team");
        }
    }
});
