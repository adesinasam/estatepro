import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils import nowdate


class ReceivePayment(Document):
    def on_submit(self):
        if not self.plot_sale:
            frappe.throw("Plot Sales reference is required.")

        if not (self.paid_amount and self.paid_amount > 0):
            frappe.throw("Paid amount must be greater than zero.")

        sale = frappe.get_doc("Plot Sales", self.plot_sale)
        settings = frappe.get_single("EstatePro Accounts Settings")

        debtors_account=settings.debtors_account
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
        je.posting_date = self.posting_date
        je.company = frappe.defaults.get_user_default("Company")
        je.voucher_type = "Journal Entry"
        je.remark = f"Payment received and income recognized for plot {sale.plot_name}"
        je.project = self.project 
        je.title = self.name

        if self.is_bulk_plot_payment == 0:
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

        # Update Plot Sales totals
        total_paid = flt(sale.total_paid or 0) + flt(self.paid_amount)
        new_balance = flt(sale.sale_amount) - flt(total_paid)

        frappe.logger().debug(f"Updating Plot Sales {sale.name}: total_paid={total_paid}, new_balance={new_balance}")

        frappe.db.set_value("Plot Sales", sale.name, {
            "total_paid": total_paid,
            "balance": new_balance,
            "payment_status": "Paid" if new_balance <= 0 else "Partly Paid"
            })
        # frappe.db.set_value("Plot Sales", sale.name, "total_paid", total_paid)
        # frappe.db.set_value("Plot Sales", sale.name, "balance", new_balance)
        # frappe.db.set_value("Plot Sales", sale.name, "payment_status",
        #     "Paid" if new_balance <= 0 else "Partly Paid")
       
        if sale.allow_installment == "Yes":
            if sale.down_payment_terms == "Amount":
                self.down_payment = sale.down_payment_amount or 0
            else:  # Assume "Percent"
                self.down_payment = sale.sale_amount * (sale.set_downpayment_percentage or 0) / 100

            self.apply_to_payment_schedule()
            self.update_invoice_table()

        self.create_realtor_gl_entry()


        # if sale.allow_installment == "Yes":
        #     self.apply_to_payment_schedule()
        #     self.update_invoice_table()


    def create_realtor_gl_entry(self):
        sale = frappe.get_doc("Plot Sales", self.plot_sale)
        team_names = self.get("sales_team")

        for team in team_names:
            try:
                sales_person = team.sales_person

                # Create GL Entry for each Realtor
                glentry = frappe.new_doc("Realtor GL Entry")
                glentry.posting_date = self.posting_date  
                glentry.sales_person = team.sales_person
                glentry.customer = self.customer
                glentry.amount_paid = self.paid_amount
                glentry.commission_percent = team.allocated_percentage
                glentry.credit = float(team.incentives)
                glentry.credit_in_account_currency = float(team.incentives)
                glentry.voucher_type = "Receive Payment"
                glentry.voucher_no = self.name
                glentry.project = self.project
                glentry.cost_center = self.cost_center

                glentry.insert()
                frappe.db.commit()

                sale_team = frappe.get_doc(
                    "Sales Team", 
                    filters={
                        "sales_person": sales_person, 
                        "parent": sale.name, 
                        "parenttype": 'Plot Sales'
                    }
                )
                if sale_team:
                    new_allocated_amount = flt(sale_team.custom_allocated_amount or 0) + flt(team.incentives or 0)
                    new_outstanding = flt(sale_team.custom_outstanding or 0) + flt(team.incentives or 0)
                    sale_team.db_set('custom_allocated_amount', new_allocated_amount)
                    sale_team.db_set('custom_outstanding', new_outstanding)
                    frappe.db.commit()

            except Exception as e:
                frappe.log_error(f"Failed to create realtor GL entry for sales person {sales_person}", str(e))

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
        sale = frappe.get_doc("Plot Sales", self.plot_sale)

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

        # Save the HTML to a field in Plot Sales
        sale.invoice = html
        sale.save(ignore_permissions=True)

    def on_cancel(self):
        # Get the Plot Sales document
        sale = frappe.get_doc("Plot Sales", self.plot_sale)

        # Cancel and delete the Journal Entry
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.cancel()
            self.db_set("journal_entry", "")

        # Revert the Plot Sales totals
        total_paid = flt(sale.total_paid or 0) - flt(self.paid_amount)
        new_balance = flt(sale.sale_amount) + flt(total_paid)

        frappe.db.set_value("Plot Sales", sale.name, {
            "total_paid": total_paid,
            "balance": new_balance,
            "payment_status": "Paid" if new_balance <= 0 else "Partly Paid"
            })
        # frappe.db.set_value("Plot Sales", sale.name, "total_paid", total_paid)
        # frappe.db.set_value("Plot Sales", sale.name, "balance", new_balance)
        # frappe.db.set_value("Plot Sales", sale.name, "payment_status",
        #     "Paid" if new_balance <= 0 else "Partly Paid")

        # Revert payment schedule entries
        if sale.allow_installment == "Yes":
            self.revert_payment_schedule()

        # Delete Realtor GL Entries
        self.delete_realtor_gl_entries()

        # Update invoice table
        self.update_invoice_table()

    def revert_payment_schedule(self):
        sched = frappe.get_doc("Plot Payment Schedule", {"plot_sale": self.plot_sale})
        amt = flt(self.paid_amount)

        for row in reversed(sched.plot_payment):  # Process in reverse order
            if amt <= 0:
                break

            if flt(row.paid_amount) > 0:
                deduct_amt = min(amt, flt(row.paid_amount))
                row.paid_amount = flt(row.paid_amount) - deduct_amt
                row.status = "Paid" if flt(row.paid_amount) >= flt(row.amount) else "Partially Paid"
                if flt(row.paid_amount) == 0:
                    row.status = "Unpaid"
                amt -= deduct_amt

        sched.save(ignore_permissions=True)

    def delete_realtor_gl_entries(self):
        # Delete all Realtor GL Entries linked to this payment
        gl_entries = frappe.get_all("Realtor GL Entry", 
            filters={"voucher_type": "Receive Payment", "voucher_no": self.name})

        for entry in gl_entries:
            frappe.delete_doc("Realtor GL Entry", entry.name)

        # Revert Sales Team allocations
        sale = frappe.get_doc("Plot Sales", self.plot_sale)
        team_names = self.get("sales_team")

        for team in team_names:
            try:
                sales_person = team.sales_person
                sale_team = frappe.get_doc(
                    "Sales Team", 
                    filters={
                        "sales_person": sales_person, 
                        "parent": sale.name, 
                        "parenttype": 'Plot Sales'
                    }
                )
                if sale_team:
                    new_allocated_amount = flt(sale_team.custom_allocated_amount or 0) - flt(team.incentives or 0)
                    new_outstanding = flt(sale_team.custom_outstanding or 0) - flt(team.incentives or 0)
                    sale_team.db_set('custom_allocated_amount', new_allocated_amount)
                    sale_team.db_set('custom_outstanding', new_outstanding)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Failed to revert sales team allocation for {sales_person}", str(e))
