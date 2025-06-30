import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils import nowdate


class ReceivePayment(Document):
    def on_submit(self):
        settings = frappe.get_single("EstatePro Accounts Settings")
        debtors_account=settings.debtors_account
        if not self.plot_sale:
            frappe.throw("Plot Sale reference is required.")

        sale = frappe.get_doc("Plot Sale", self.plot_sale)
        settings = frappe.get_single("EstatePro Accounts Settings")

        sales_account = settings.sales_account
        cogs_account = settings.cost_of_goods_sold_account
        unearned_revenue_account = settings.unearned_revenue_account
        land_inventory_accont = settings.land_inventory_accont
        
        if self.paid_amount > sale.balance:
            frappe.throw(f"Cannot pay more than outstanding balance: {sale.balance}")

        if self.paid_amount > sale.sale_amount:
            frappe.throw("Paid amount cannot exceed sale amount.")

        if sale.sale_amount == 0:
            frappe.throw("Sale amount cannot be zero.")

        valuation_to_post = (self.valuation or 0) * (self.paid_amount / sale.sale_amount)

        je = frappe.new_doc("Journal Entry")
        je.posting_date = nowdate()
        je.company = frappe.defaults.get_user_default("Company")
        je.voucher_type = "Journal Entry"
        je.remark = f"Payment received and income recognized for plot {sale.plot_name}"
        je.project = self.project 
        je.custom_estatepro_doctype = "Receive Payment"
        je.custom_estatepro_reference = self.name

        # 1. Debit Bank
        je.append("accounts", {
            "account": self.receiving_account,
            "debit_in_account_currency": self.paid_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        # 2. Credit Debtors
        je.append("accounts", {
            "account": debtors_account,
            "party_type": "Customer",
            "party": sale.customer,
            "credit_in_account_currency": self.paid_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        # 3. Debit Unearned Revenue
        je.append("accounts", {
            "account": unearned_revenue_account,
            "debit_in_account_currency": self.paid_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        # 4. Credit Sales
        je.append("accounts", {
            "account": sales_account,
            "credit_in_account_currency": self.paid_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        # 5. Debit COGS (partial)
        je.append("accounts", {
            "account": cogs_account,
            "debit_in_account_currency": valuation_to_post,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        # 6. Credit Land Inventory (partial)
        je.append("accounts", {
            "account": land_inventory_accont,
            "credit_in_account_currency": valuation_to_post,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        je.save()
        je.submit()
        self.db_set("journal_entry", je.name)

        # Update Plot Sale totals
        total_paid = (sale.total_paid or 0) + self.paid_amount
        new_balance = sale.sale_amount - total_paid

        frappe.db.set_value("Plot Sale", sale.name, "total_paid", total_paid)
        frappe.db.set_value("Plot Sale", sale.name, "balance", new_balance)
        frappe.db.set_value("Plot Sale", sale.name, "payment_status",
            "Paid" if new_balance <= 0 else "Partly Paid")
        
        if not (self.paid_amount and self.paid_amount > 0):
            frappe.throw("Paid amount must be greater than zero.")

        total_paid = (sale.total_paid or 0) + self.paid_amount
        new_balance = sale.sale_amount - total_paid
        sale.db_set("total_paid", total_paid)
        sale.db_set("balance", new_balance)
        sale.db_set("payment_status", "Paid" if new_balance == 0 else "Partly Paid")
        
        if sale.allow_installment == "Yes":
            if sale.down_payment_terms == "Amount":
                self.down_payment = sale.down_payment_amount or 0
            else:  # Assume "Percent"
                self.down_payment = sale.sale_amount * (sale.set_downpayment_percentage or 0) / 100

            self.apply_to_payment_schedule()
            self.update_invoice_table()


        # if sale.allow_installment == "Yes":
        #     self.apply_to_payment_schedule()
        #     self.update_invoice_table()


    def apply_to_payment_schedule(self):
        sched = frappe.get_doc("Plot Payment Schedule", {"plot_sale": self.plot_sale})
        amt = flt(self.paid_amount)  # Ensure amt is a float

        for row in sched.plot_payment:
            if amt <= 0:
                break

            due = flt(row.amount) - flt(row.paid_amount)  # Convert both to float
            if due <= 0:
                continue

            apply_amt = min(amt, due)
            row.paid_amount = flt(row.paid_amount) + apply_amt
            row.status = "Paid" if flt(row.paid_amount) >= flt(row.amount) else "Partially Paid"
            amt -= apply_amt

        if amt > 0:
            frappe.throw("Payment exceeds the remaining amount in the schedule.")

        sched.save(ignore_permissions=True)


    def update_invoice_table(self):
        sale = frappe.get_doc("Plot Sale", self.plot_sale)

        sched = frappe.get_doc("Plot Payment Schedule", {"plot_sale": self.plot_sale})

        # Begin building the HTML table
        html = """
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Reference ID</th>
                    <th>Posting Date</th>
                    <th>Amount</th>
                    <td>{Payment Type}</td>
                    <th>Outstanding</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """

        for row in sched.plot_payment:
            outstanding = flt(row.amount) - flt(row.paid_amount)
            html += f"""
                <tr>
                    <td>{self.plot_sale}</td>
                    <td>{row.due_date}</td>
                    <td>{row.payment_type}</td>
                    <td>{row.amount}</td>
                    <td>{outstanding}</td>
                    <td>{row.status}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """

        # Save the HTML to a field in Plot Sale
        sale.invoice = html
        sale.save(ignore_permissions=True)

