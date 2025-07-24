# Copyright (c) 2025, Upeosoft Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProjectExpense(Document):
    def validate(self):
        if not self.is_paid:
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
            # Fetch the expense account from the linked Expense Category
            expense_category = frappe.get_doc("Expense Categories", self.expense_category)
            expense_account = expense_category.expense_account

            # Get the paying account from the Project Expense document
            paying_account = self.paying_account

            if not expense_account:
                frappe.throw("Expense account is missing in the selected Project Expense Category.")
            if not paying_account:
                frappe.throw("Paying account is not set.")

            # Create a Journal Entry
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Journal Entry"
            journal_entry.posting_date = frappe.utils.today()
            journal_entry.user_remark = f"Expense for Project {self.project}"

            # Create Debit entry (Expense)
            journal_entry.append("accounts", {
                "account": expense_account,
                "debit_in_account_currency": self.amount,
                "credit_in_account_currency": 0,
                "project": self.project
            })

            # Create Credit entry (Paying Account)
            journal_entry.append("accounts", {
                "account": paying_account,
                "credit_in_account_currency": self.amount,
                "debit_in_account_currency": 0,
                "project": self.project
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
