// Copyright (c) 2025, Adesina Akinyemi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plot Payment Entry", {
	refresh(frm) {
        // Initialize totals when form loads
        calculate_totals(frm);

	// },
	// onload(frm){
		frm.set_query("plot_sale", 'payments', () => {
			return {
				filters: [
					["Plot Sale", "company", "=", frm.doc.company],
					["Plot Sale","payment_status","!=","Paid"],
					["Plot Sale","docstatus","=", 1]					
				]
			}
		});	
	}
});

frappe.ui.form.on("Plot Payment Items", {
	payments_remove: function(frm, cdt, cdn){
        calculate_totals(frm);
	},
    paid_amount: function(frm, cdt, cdn) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let total_paid = 0;
    
    if (frm.doc.payments) {
        frm.doc.payments.forEach(function(row) {
            total_paid += flt(row.paid_amount || 0);
        });
    }
    
    frm.set_value("total_paid", total_paid);
}

