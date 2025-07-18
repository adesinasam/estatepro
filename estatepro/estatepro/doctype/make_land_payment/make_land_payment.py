# Copyright (c) 2025, Upeosoft Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate
from frappe.model.document import Document


class MakeLandPayment(Document):
    def on_submit(self):
        settings = frappe.get_single("EstatePro Accounts Settings")
        land_inventory_accont = settings.land_inventory_accont

        if not land_inventory_accont:
            frappe.throw("Estate Inventory Account is not configured in EstatePro Accounts Settings.")
        
        if not self.paying_account:
            frappe.throw("Paying Account is required.")
        
        if not frappe.db.exists("Account", land_inventory_accont):
            frappe.throw(f"Account '{land_inventory_accont}' does not exist.")
        
        if not frappe.db.exists("Account", self.paying_account):
            frappe.throw(f"Account '{self.paying_account}' does not exist.")

        if self.paid_amount <= 0:
            frappe.throw("Paid Amount must be greater than 0.")

        project = frappe.get_doc("Estate Project", self.project_name)

        if (project.total_paid or 0) + self.paid_amount > project.total_project_cost:
            frappe.throw("Payment exceeds the total project cost.")

        je = frappe.new_doc("Journal Entry")
        je.posting_date = self.posting_date
        je.company = frappe.defaults.get_user_default("Company")
        je.remark = f"Purchase of the project {self.project_name}"
        je.voucher_type = "Journal Entry"
        je.title = self.name
        # je.custom_estatepro_doctype = "Make Land Payment"
        # je.custom_estatepro_reference = self.name

        je.append("accounts", {
            "account": land_inventory_accont,
            "debit_in_account_currency": self.paid_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        je.append("accounts", {
            "account": self.paying_account,
            "credit_in_account_currency": self.paid_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        je.save()
        je.submit()
        self.db_set("payment_journal", je.name)

        new_total_paid = (project.total_paid or 0) + self.paid_amount
        new_balance = project.total_project_cost - new_total_paid

        project.db_set("total_paid", new_total_paid)
        project.db_set("balance", new_balance)

        if new_balance == 0 or new_balance == self.paid_amount:
            project.db_set("payment_status", "Paid")
        else:
            project.db_set("payment_status", "Partly Paid")

    # def on_cancel(self):
    #     # Get the linked Journal Entry
    #     je = frappe.get_all("Journal Entry",
    #         filters={
    #             "custom_estatepro_doctype": "Make Land Payment",
    #             "custom_estatepro_reference": self.name,
    #             "docstatus": 1
    #         },
    #         limit=1
    #     )

    #     if je:
    #         je_doc = frappe.get_doc("Journal Entry", je[0].name)
    #         je_doc.cancel()

    #     # Update the project's payment details
    #     project = frappe.get_doc("Estate Project", self.project_name)
    #     new_total_paid = (project.total_paid or 0) - self.paid_amount

    #     # Ensure we don't go negative
    #     if new_total_paid < 0:
    #         new_total_paid = 0

    #     new_balance = project.total_project_cost - new_total_paid

    #     project.db_set("total_paid", new_total_paid)
    #     project.db_set("balance", new_balance)

    #     # Update payment status
    #     if new_total_paid == 0:
    #         project.db_set("payment_status", "Unpaid")
    #     elif new_total_paid >= project.total_project_cost:
    #         project.db_set("payment_status", "Paid")
    #     else:
    #         project.db_set("payment_status", "Partly Paid")

    def on_cancel(self):
        # Get the linked Journal Entry
        if not self.payment_journal:
            frappe.throw("No Journal Entry linked to this document to cancel.")

        je = frappe.get_doc("Journal Entry", self.payment_journal)

        # Check if Journal Entry is already cancelled
        if je.docstatus == 2:
            frappe.throw("The linked Journal Entry is already cancelled.")

        # Cancel the Journal Entry first
        je.cancel()

        # Update the Estate Project document
        project = frappe.get_doc("Estate Project", self.project_name)
        new_total_paid = (project.total_paid or 0) - self.paid_amount
        new_balance = project.total_project_cost - new_total_paid

        project.db_set("total_paid", new_total_paid)
        project.db_set("balance", new_balance)

        # Update payment status
        if new_total_paid == 0:
            project.db_set("payment_status", "Unpaid")
        elif new_total_paid >= project.total_project_cost:
            project.db_set("payment_status", "Paid")
        else:
            project.db_set("payment_status", "Partly Paid")

        # Clear the reference to the Journal Entry
        self.db_set("payment_journal", "")