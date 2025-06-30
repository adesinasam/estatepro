// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Plot', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.status === 'Available') {
            frm.add_custom_button('Sell Plot', () => {
                const new_doc = frappe.model.get_new_doc('Plot Sale');
                new_doc.plot_name = frm.doc.name;
                new_doc.valuation = frm.doc.valuation;
                new_doc.project_creator = frm.doc.project;
                frappe.set_route('Form', 'Plot Sale', new_doc.name);
            }, 'Actions');
        }
    }
});

