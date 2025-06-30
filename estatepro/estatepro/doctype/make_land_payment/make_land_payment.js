// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Make Land Payment', {
    
// });
frappe.ui.form.on('Make Land Payment', {
    onload(frm) {
        if (frm.doc.project_name) {
            frappe.db.get_doc('Estate Project', frm.doc.project_name)
                .then(project => {
                    apply_land_payment_logic(frm, project);
                });
        }
    }
});

