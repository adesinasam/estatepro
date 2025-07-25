# Copyright (c) 2025, Upeosoft Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProjectExpense(Document):
    def validate(self):
        if not self.paying_account and self.amount > 0:
            frappe.throw(
                f"Paying Account cannot be empty since Paid Amount is greater than zero"
            )

    def on_submit(self):
        try:
            self.create_journal_entry()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Project Expense: Journal Entry Error")
            frappe.throw(f"An error occurred while creating the journal entry: {str(e)}")

    def create_journal_entry(self):
        try:
            settings = frappe.get_single("EstatePro Accounts Settings")

            creditors_account=settings.creditors_account
            land_inventory_accont = settings.land_inventory_accont

            # Get the paying account from the Project Expense document
            if self.amount > 0:
                paying_account = self.paying_account
                if not paying_account:
                    frappe.throw("Paying account is not set.")

            if self.is_paid:
                for expense_row in self.expenses:
                    expense_account = expense_row.expense_account
                    amount_spent = expense_row.amount_spent

                    if not expense_account:
                        frappe.throw(f"No Expense Account found for Value Addition Item {expense_row.value_addition_item}")

                    #Create a Journal Entry
                    journal_entry = frappe.new_doc("Journal Entry")
                    journal_entry.voucher_type = "Journal Entry"
                    journal_entry.posting_date = self.expense_date
                    journal_entry.user_remark = f"Valuation addition expense for Estate Project {self.estate_project}"

                    # 1 Create Debit entry (Land Stock)
                    journal_entry.append("accounts", {
                        "account": land_inventory_accont,
                        "debit_in_account_currency": amount_spent,
                        "credit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                    # 2 Create Credit entry (Expense Account)
                    journal_entry.append("accounts", {
                        "account": expense_account,
                        "credit_in_account_currency": amount_spent,
                        "debit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                    # 3 Create Debit entry (Expense Account)
                    journal_entry.append("accounts", {
                        "account": expense_account,
                        "debit_in_account_currency": amount_spent,
                        "credit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                    # 4 Create Credit entry (Paying Account)
                    journal_entry.append("accounts", {
                        "account": paying_account,
                        "credit_in_account_currency": amount_spent,
                        "debit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                    # Submit the Journal Entry
                    journal_entry.insert()
                    journal_entry.submit()

            else:
                # Create a Journal Entry
                journal_entry = frappe.new_doc("Journal Entry")
                journal_entry.voucher_type = "Journal Entry"
                journal_entry.posting_date = self.expense_date
                journal_entry.user_remark = f"Valuation addition expense for Estate Project {self.estate_project}"

                # 1 Create Debit entry (Land Stock)
                journal_entry.append("accounts", {
                    "account": land_inventory_accont,
                    "debit_in_account_currency": self.total_expense,
                    "credit_in_account_currency": 0,
                    "project": self.project,
                    "cost_center": self.cost_center
                })

                # 2 Create Credit entry (Creditor Account)
                journal_entry.append("accounts", {
                    "account": creditors_account,
                    "party_type": "Supplier",
                    "party": self.supplier,
                    "credit_in_account_currency": self.total_expense,
                    "debit_in_account_currency": 0,
                    "project": self.project,
                    "cost_center": self.cost_center
                })

                if self.amount > 0:
                    # 3 Create Debit entry (Creditor Account)
                    journal_entry.append("accounts", {
                        "account": creditors_account,
                        "party_type": "Supplier",
                        "party": self.supplier,
                        "debit_in_account_currency": self.amount,
                        "credit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                    # 4 Create Credit entry (Paying Account)
                    journal_entry.append("accounts", {
                        "account": paying_account,
                        "credit_in_account_currency": self.amount,
                        "debit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                # Submit the Journal Entry
                journal_entry.insert()
                journal_entry.submit()

            frappe.msgprint(f"Project Expense created successfully.")
        except frappe.DoesNotExistError as e:
            frappe.throw(f"A required document does not exist: {str(e)}")
        except frappe.ValidationError as e:
            frappe.throw(f"Validation error: {str(e)}")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Project Expense: Journal Entry Error")
            frappe.throw(f"An unexpected error occurred: {str(e)}")
