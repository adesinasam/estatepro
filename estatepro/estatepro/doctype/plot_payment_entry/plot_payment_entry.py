# Copyright (c) 2025, Adesina Akinyemi and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_months
from frappe.model.document import Document


class PlotPaymentEntry(Document):
    def on_submit(self):
        settings = frappe.get_single("EstatePro Accounts Settings")
        debtors_account=settings.debtors_account
        if not self.customer:
            frappe.throw("Customer is required to post to Debtors account.")
            
        if not self.payments:
            frappe.throw("At least one Payment Details is required to submit Plot Payment Entry.")

        created_sales = []
        for idx, payment_row in enumerate(self.payments):
            receive_payment = self.create_receive_payment(payment_row)
            receive_payment.submit()
            
            # Update the child table row with the created Receive Payment reference
            self.payments[idx].receive_payment = receive_payment.name
            created_sales.append(receive_payment.name)

        je = frappe.new_doc("Journal Entry")
        je.posting_date = self.posting_date
        je.company = self.company or frappe.defaults.get_user_default("Company")
        je.voucher_type = "Journal Entry"
        je.remark = f"Payment received from {self.customer}"
        # je.project = self.project 
        je.title = self.name

        # 1. Debit Bank
        je.append("accounts", {
            "account": self.receiving_account,
            "debit_in_account_currency": self.total_paid,
        })

        # 2. Credit Debtors
        je.append("accounts", {
            "account": debtors_account,
            "party_type": "Customer",
            "party": self.customer,
            "credit_in_account_currency": self.total_paid,
        })

        je.save()
        je.submit()
        self.db_set("journal_entry", je.name)

            
        # Save the updated child table with receive_payment references
        self.save()
        
        frappe.msgprint(f"Created and submitted {len(created_sales)} Receive Payment documents")

    def create_receive_payment(self, payment_row):
        """Create individual Receive Payment document for each plot row"""
        receive_payment = frappe.new_doc("Receive Payment")
        
        # Copy fields from Bulk Receive Payment
        for field in ["company", "customer", "posting_date", 
        "set_posting_time", "receiving_account", "remarks"]:
            receive_payment.set(field, self.get(field))
        
        # Set plot-specific fields
        receive_payment.plot_sale = payment_row.plot_sale
        receive_payment.plot = payment_row.plot
        receive_payment.plot_name = payment_row.plot_name
        receive_payment.plot_size = payment_row.plot_size
        receive_payment.valuation = payment_row.valuation
        receive_payment.sale_amount = payment_row.sale_amount
        receive_payment.outstanding = payment_row.outstanding
        receive_payment.paid_amount = payment_row.paid_amount
        receive_payment.is_bulk_plot_payment = payment_row.is_bulk_plot_payment
        receive_payment.cost_center = payment_row.cost_center
        receive_payment.project = payment_row.project
        receive_payment.estate_project = payment_row.estate_project
       
        # Set status
        receive_payment.status = "Submitted"
              
        # Save the document (will trigger validate)
        receive_payment.insert(ignore_permissions=True)
        
        return receive_payment

    def on_cancel(self):
        # Cancel and delete the Journal Entry
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.cancel()
            self.db_set("journal_entry", "")

        """Cancel all linked Receive Payments when bulk sale is cancelled"""
        for payment_row in self.payments:
            if payment_row.receive_payment:
                try:
                    receive_payment = frappe.get_doc("Receive Payment", payment_row.receive_payment)
                    if receive_payment.docstatus == 1:
                        receive_payment.cancel()

                    payment_row.receive_payment = ""

                except frappe.DoesNotExistError:
                    pass
        
        frappe.msgprint("All linked Receive Payment documents have been cancelled")
