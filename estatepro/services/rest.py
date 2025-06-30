import frappe
from frappe.utils import nowdate
from frappe.utils import flt
from frappe.utils import flt, fmt_money
from frappe.utils import flt, fmt_money



def update_item_status_on_submit(doc, method):
    for item in doc.items:
        frappe.db.set_value("Item", item.item_code, "custom_sale_status", "Sold")
    frappe.db.commit()

def revert_item_status_on_cancel(doc, method):
    for item in doc.items:
        frappe.db.set_value("Item", item.item_code, "custom_sale_status", "Unallocated")
    frappe.db.commit()


# @frappe.whitelist()
# def get_receive_payment_defaults(plot_sale_name):
#     doc = frappe.get_doc("Plot Sale", plot_sale_name)

#     next_due = frappe.get_list("Plot Payment Schedule",
#         filters={
#             "parent": plot_sale_name,
#             "status": ["in", ["Unpaid", "Partially Paid"]],
#             "due_date": ["<=", nowdate()]
#         },
#         fields=["amount"],
#         order_by="due_date asc",
#         limit_page_length=1
#     )
#     amt = next_due[0].amount if next_due else 0

#     plot = frappe.get_doc("Plot", doc.plot_name)

#     if not plot.project:
#         frappe.throw("Plot not linked to Land Project.")
#     project = frappe.get_doc("Land Project", plot.project)

#     default_amt = (
#         doc.sale_amount * float(project.set_downpayment_percentage or 0) / 100
#         if project.allow_installments == "Yes" else doc.sale_amount
#     )

#     return {
#         "plot_sale": doc.name,
#         "receiving_account": doc.get("receiving_account"),
#         "valuation": plot.valuation or 0,
#         "sale_amount": doc.sale_amount,
#         "project": plot.project,
#         # "payment_period": project.payment_period,
#         "paid_amount": amt or default_amt
#     }
@frappe.whitelist()
def get_receive_payment_defaults(plot_sale_name):
    doc = frappe.get_doc("Plot Sale", plot_sale_name)

    next_due = frappe.get_list("Plot Payment Schedule",
        filters={
            "parent": plot_sale_name,
            "status": ["in", ["Unpaid", "Partially Paid"]],
            "due_date": ["<=", nowdate()]
        },
        fields=["amount"],
        order_by="due_date asc",
        limit_page_length=1
    )
    amt = next_due[0].amount if next_due else 0

    plot = frappe.get_doc("Plot", doc.plot_name)

    if not plot.project:
        frappe.throw("Plot not linked to Land Project.")

    project = frappe.get_doc("Land Project", plot.project)

    if project.allow_installments == "Yes":
        if project.down_payment_terms == "Amount":
            default_amt = project.down_payment_amount or 0
        else:  # Percent
            default_amt = doc.sale_amount * float(project.set_downpayment_percentage or 0) / 100
    else:
        default_amt = doc.sale_amount

    return {
        "plot_sale": doc.name,
        "receiving_account": doc.get("receiving_account"),
        "valuation": plot.valuation or 0,
        "sale_amount": doc.sale_amount,
        "project": plot.project,
        "paid_amount": amt or default_amt
    }


@frappe.whitelist()
def get_invoice_table_html(plot_sale):
    sale = frappe.get_doc("Plot Sale", plot_sale)
    if sale.allow_installment == "Yes":
        sched = frappe.get_doc("Plot Payment Schedule", {"plot_sale": plot_sale})

        html = """
        <table class="table table-bordered" id="invoice-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Reference ID</th>
                    <th>Due Date</th>
                    <th>Payment Type</th>
                    <th>Amount</th>
                    <th>Outstanding</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, row in enumerate(sched.plot_payment, start=1):
            outstanding = flt(row.amount) - flt(row.paid_amount)
            action_html = (
                '<span class="text-success">&#10003;</span>' if row.status.lower() == "paid"
                else f"""
                    <button class="btn btn-sm btn-primary pay-now-btn" 
                        data-reference="{plot_sale}" 
                        data-date="{row.due_date}" 
                        data-amount="{outstanding}">
                        Pay
                    </button>
                """
            )

            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{plot_sale}</td>
                    <td>{row.due_date}</td>
                    <td>{row.payment_type}</td>
                    <td>{fmt_money(row.amount)}</td>
                    <td>{fmt_money(outstanding)}</td>
                    <td>{row.status}</td>
                    <td>{action_html}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        <div id="pagination-controls" class="mt-3 d-flex align-items-center gap-2">
            <button id="prev-btn" class="btn btn-sm btn-light">Previous</button>
            <span id="page-info">Page 1</span>
            <button id="next-btn" class="btn btn-sm btn-light">Next</button>
        </div>

        <script>
            function paginateTable(tableId, rowsPerPage) {
                const table = document.getElementById(tableId);
                const tbody = table.querySelector("tbody");
                const rows = Array.from(tbody.rows);
                const totalRows = rows.length;
                const totalPages = Math.ceil(totalRows / rowsPerPage);

                let currentPage = 1;

                const pageInfo = document.getElementById("page-info");
                const prevBtn = document.getElementById("prev-btn");
                const nextBtn = document.getElementById("next-btn");

                function showPage(page) {
                    currentPage = page;
                    const start = (currentPage - 1) * rowsPerPage;
                    const end = currentPage * rowsPerPage;

                    rows.forEach((row, index) => {
                        row.style.display = (index >= start && index < end) ? "" : "none";
                    });

                    pageInfo.textContent = `${currentPage}`;
                    prevBtn.disabled = currentPage === 1;
                    nextBtn.disabled = currentPage === totalPages;
                }

                prevBtn.addEventListener("click", () => {
                    if (currentPage > 1) showPage(currentPage - 1);
                });

                nextBtn.addEventListener("click", () => {
                    if (currentPage < totalPages) showPage(currentPage + 1);
                });

                showPage(1);
            }

            setTimeout(() => paginateTable("invoice-table", 5), 100);
        </script>
        """

        return html

