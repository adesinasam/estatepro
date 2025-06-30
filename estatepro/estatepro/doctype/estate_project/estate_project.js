// Copyright (c) 2025, Adesina Akinyemi and contributors
// For license information, please see license.txt

frappe.ui.form.on('Estate Project', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.docstatus > 0 && frm.doc.payment_status !== 'Paid') {
            frm.add_custom_button('Make Payment', () => {
                const new_doc = frappe.model.get_new_doc('Make Land Payment');
                new_doc.project_name = frm.doc.name;
                new_doc.paid_amount = frm.doc.balance;
                frappe.set_route('Form', new_doc.doctype, new_doc.name);
            }, 'Actions');
        }
    },
});
frappe.ui.form.on('Estate Project', {
    refresh(frm) {
        toggle_installment_fields(frm);
    },
    down_payment_terms(frm) {
        toggle_installment_fields(frm);
    },
    allow_installments(frm) {
        toggle_installment_fields(frm);
    }
});
function toggle_installment_fields(frm) {
    const isYes = cint(frm.doc.allow_installments) === 1 || frm.doc.allow_installments === 'Yes';

    frm.toggle_display(['set_downpayment_percentage', 'payment_period', 'down_payment_terms', 'down_payment_amount'], false);

    if (isYes) {
        frm.toggle_display(['down_payment_terms', 'payment_period'], true);

        if (frm.doc.down_payment_terms === 'Percent') {
            frm.toggle_display('set_downpayment_percentage', true);
            frm.toggle_display('down_payment_amount', false);
        } else if (frm.doc.down_payment_terms === 'Amount') {
            frm.toggle_display('down_payment_amount', true);
            frm.toggle_display('set_downpayment_percentage', false);
        }
    }

    frm.refresh_fields(['down_payment_terms', 'set_downpayment_percentage', 'down_payment_amount', 'payment_period']);
}


frappe.ui.form.on('Estate Project', {
    refresh: function(frm) {
        frm.toggle_display('ignore_difference_amount', frm.doc.difference_amount < 1);
    },
    difference_amount: function(frm) {
        frm.toggle_display('ignore_difference_amount', frm.doc.difference_amount < 1);
    }
});
