import csv
import io

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from tcms.management.models import Product
from tcms.testcases.models import Category, TestCase
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestExecution, TestRun


def _get_report_queryset(request):
    """Return a filtered queryset based on request GET params."""
    ids = request.GET.get("ids")
    product_id = request.GET.get("product")
    status_id = request.GET.get("status")
    priority_id = request.GET.get("priority")
    is_automated = request.GET.get("is_automated")

    queryset = TestCase.objects.select_related(
        "case_status",
        "priority",
        "author",
        "category",
        "category__product",
    ).order_by("id")

    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            return queryset.filter(pk__in=id_list)

    if product_id:
        queryset = queryset.filter(category__product_id=product_id)
    if status_id:
        queryset = queryset.filter(case_status_id=status_id)
    if priority_id:
        queryset = queryset.filter(priority_id=priority_id)
    if is_automated is not None:
        queryset = queryset.filter(is_automated=is_automated == "true")

    return queryset


def _tc_row(tc):
    """Return a list of display values for a single test case."""
    return [
        tc.pk,
        tc.summary,
        tc.category.product.name if tc.category and tc.category.product else "",
        tc.category.name if tc.category else "",
        tc.case_status.name if tc.case_status else "",
        tc.priority.value if tc.priority else "",
        "Yes" if tc.is_automated else "No",
        tc.author.username if tc.author else "",
        tc.create_date.strftime("%Y-%m-%d") if tc.create_date else "",
    ]


REPORT_HEADERS = [
    "ID", "Summary", "Product", "Category",
    "Status", "Priority", "Automated", "Author", "Created",
]


@method_decorator(login_required, name="dispatch")
class TestCaseBrowserView(TemplateView):
    """
    Test Case Browser with tree navigation.
    Left panel: Product → Category tree with test case counts
    Right panel: Selected test case details
    """

    template_name = "tcms_test_browser/browser.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all products with categories and test case counts in 2 queries
        categories_qs = (
            Category.objects.annotate(testcase_count=Count("category_case"))
            .order_by("name")
        )
        products = Product.objects.prefetch_related(
            Prefetch("category", queryset=categories_qs)
        ).order_by("name")

        tree_data = []
        for product in products:
            categories = product.category.all()

            product_testcase_count = sum(c.testcase_count for c in categories)

            category_list = [
                {
                    "id": cat.pk,
                    "name": cat.name,
                    "count": cat.testcase_count,
                }
                for cat in categories
            ]

            tree_data.append(
                {
                    "id": product.pk,
                    "name": product.name,
                    "count": product_testcase_count,
                    "categories": category_list,
                }
            )

        context["tree_data"] = tree_data
        return context


@login_required
def api_testcases_by_category(request, category_id):
    """API endpoint to get test cases for a category."""
    testcases = TestCase.objects.filter(category_id=category_id).select_related(
        "case_status", "priority", "author", "category"
    ).order_by("summary")

    data = [
        {
            "id": tc.pk,
            "summary": tc.summary,
            "case_status": tc.case_status.name if tc.case_status else None,
            "priority": tc.priority.value if tc.priority else None,
            "author": tc.author.username if tc.author else None,
            "is_automated": tc.is_automated,
            "create_date": tc.create_date.isoformat() if tc.create_date else None,
        }
        for tc in testcases
    ]

    return JsonResponse({"testcases": data})


@login_required
def api_testcase_detail(request, testcase_id):
    """API endpoint to get test case details."""
    try:
        tc = TestCase.objects.select_related(
            "case_status", "priority", "author", "default_tester", "reviewer", "category"
        ).get(pk=testcase_id)
    except TestCase.DoesNotExist:
        return JsonResponse({"error": "Test case not found"}, status=404)

    # Get related data
    components = list(tc.component.values_list("name", flat=True))
    tags = list(tc.tag.values_list("name", flat=True))
    plans = list(tc.plan.values("id", "name"))

    data = {
        "id": tc.pk,
        "summary": tc.summary,
        "text": tc.text or "",
        "notes": tc.notes or "",
        "case_status": tc.case_status.name if tc.case_status else None,
        "case_status_id": tc.case_status_id,
        "priority": tc.priority.value if tc.priority else None,
        "priority_id": tc.priority_id,
        "category": tc.category.name if tc.category else None,
        "category_id": tc.category_id,
        "author": tc.author.username if tc.author else None,
        "default_tester": tc.default_tester.username if tc.default_tester else None,
        "reviewer": tc.reviewer.username if tc.reviewer else None,
        "is_automated": tc.is_automated,
        "script": tc.script or "",
        "arguments": tc.arguments or "",
        "requirement": tc.requirement or "",
        "extra_link": tc.extra_link or "",
        "setup_duration": str(tc.setup_duration) if tc.setup_duration else None,
        "testing_duration": str(tc.testing_duration) if tc.testing_duration else None,
        "create_date": tc.create_date.isoformat() if tc.create_date else None,
        "components": components,
        "tags": tags,
        "plans": plans,
    }

    return JsonResponse(data)


@login_required
def api_search_testcases(request):
    """API endpoint to search test cases."""
    query = request.GET.get("q", "").strip()
    product_id = request.GET.get("product")
    category_id = request.GET.get("category")
    status_id = request.GET.get("status")
    is_automated = request.GET.get("is_automated")

    testcases = TestCase.objects.select_related(
        "case_status", "priority", "author", "category", "category__product"
    )

    if query:
        testcases = testcases.filter(summary__icontains=query)

    if product_id:
        testcases = testcases.filter(category__product_id=product_id)

    if category_id:
        testcases = testcases.filter(category_id=category_id)

    if status_id:
        testcases = testcases.filter(case_status_id=status_id)

    if is_automated is not None:
        testcases = testcases.filter(is_automated=is_automated == "true")

    testcases = testcases.order_by("summary")[:100]  # Limit results

    data = [
        {
            "id": tc.pk,
            "summary": tc.summary,
            "case_status": tc.case_status.name if tc.case_status else None,
            "priority": tc.priority.value if tc.priority else None,
            "author": tc.author.username if tc.author else None,
            "category": tc.category.name if tc.category else None,
            "product": tc.category.product.name if tc.category and tc.category.product else None,
            "is_automated": tc.is_automated,
        }
        for tc in testcases
    ]

    return JsonResponse({"testcases": data})


@login_required
def api_statistics(request):
    """API endpoint returning test case statistics for charts."""
    product_id = request.GET.get("product")

    queryset = TestCase.objects.all()
    if product_id:
        queryset = queryset.filter(category__product_id=product_id)

    total = queryset.count()

    by_status = list(
        queryset.values("case_status__name")
        .annotate(count=Count("id"))
        .order_by("case_status__name")
    )

    by_priority = list(
        queryset.values("priority__value")
        .annotate(count=Count("id"))
        .order_by("priority__value")
    )

    automated_count = queryset.filter(is_automated=True).count()
    manual_count = total - automated_count

    by_product = list(
        queryset.values("category__product__name")
        .annotate(count=Count("id"))
        .order_by("category__product__name")
    )

    return JsonResponse(
        {
            "total": total,
            "by_status": [
                {"name": item["case_status__name"] or "Unknown", "count": item["count"]}
                for item in by_status
            ],
            "by_priority": [
                {"name": item["priority__value"] or "Unknown", "count": item["count"]}
                for item in by_priority
            ],
            "automation": {"automated": automated_count, "manual": manual_count},
            "by_product": [
                {
                    "name": item["category__product__name"] or "Unknown",
                    "count": item["count"],
                }
                for item in by_product
            ],
        }
    )


@login_required
def api_report(request):
    """API endpoint to download a CSV report of test cases."""
    queryset = _get_report_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="test_cases_report.csv"'

    writer = csv.writer(response)
    writer.writerow(REPORT_HEADERS)

    for tc in queryset.iterator():
        writer.writerow(_tc_row(tc))

    return response


@login_required
def api_report_excel(request):
    """API endpoint to download an Excel report of test cases."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    queryset = _get_report_queryset(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"

    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0088CE", end_color="0088CE", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    data_alignment = Alignment(vertical="top", wrap_text=True)
    stripe_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    # Header row
    for col_idx, header in enumerate(REPORT_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    ws.row_dimensions[1].height = 25

    # Data rows
    row_idx = 2
    for tc in queryset.iterator():
        for col_idx, value in enumerate(_tc_row(tc), 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = data_alignment
            if row_idx % 2 == 0:
                cell.fill = stripe_fill
        row_idx += 1

    last_row = row_idx - 1

    # Auto-fit column widths
    for col in ws.columns:
        max_length = 0
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

    # Freeze header row
    ws.freeze_panes = "A2"

    # Auto-filter on all columns
    if last_row >= 1:
        ws.auto_filter.ref = (
            f"A1:{get_column_letter(len(REPORT_HEADERS))}{last_row}"
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="test_cases_report.xlsx"'
    return response


@login_required
def api_report_docx(request):
    """API endpoint to download a Word document report of test cases."""
    from docx import Document
    from docx.shared import Inches, Pt

    queryset = _get_report_queryset(request)

    doc = Document()
    doc.add_heading("Test Cases Report", level=1)

    table = doc.add_table(rows=1, cols=len(REPORT_HEADERS))
    table.style = "Table Grid"

    # Header row
    for idx, header in enumerate(REPORT_HEADERS):
        cell = table.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(9)

    # Data rows
    for tc in queryset.iterator():
        row_cells = table.add_row().cells
        for idx, value in enumerate(_tc_row(tc)):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(8)

    # Adjust table width for landscape-like fit
    for col_idx in range(len(REPORT_HEADERS)):
        for row in table.rows:
            row.cells[col_idx].width = Inches(1.2)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="test_cases_report.docx"'
    return response


@login_required
def api_report_pdf(request):
    """API endpoint to download a PDF report of test cases."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    queryset = _get_report_queryset(request)
    styles = getSampleStyleSheet()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=0.5 * inch)
    elements = []

    elements.append(Paragraph("Test Cases Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Build table data — wrap long text in Paragraphs for word-wrap
    cell_style = styles["Normal"]
    cell_style.fontSize = 7
    cell_style.leading = 9

    table_data = [REPORT_HEADERS]
    for tc in queryset.iterator():
        row = _tc_row(tc)
        # Wrap summary (col 1) in a Paragraph for word-wrap
        row[1] = Paragraph(str(row[1]), cell_style)
        table_data.append(row)

    col_widths = [
        0.5 * inch,   # ID
        2.8 * inch,   # Summary
        1.0 * inch,   # Product
        1.0 * inch,   # Category
        0.8 * inch,   # Status
        0.6 * inch,   # Priority
        0.7 * inch,   # Automated
        0.8 * inch,   # Author
        0.8 * inch,   # Created
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0088ce")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="test_cases_report.pdf"'
    return response


# ==========================================
# Test Plan Browser
# ==========================================

PLAN_REPORT_HEADERS = [
    "ID", "Name", "Product", "Type", "Status",
    "Version", "Author", "Created", "Cases", "Runs",
]


def _get_plan_report_queryset(request):
    """Return a filtered TestPlan queryset based on request GET params."""
    ids = request.GET.get("ids")
    product_id = request.GET.get("product")
    type_id = request.GET.get("type")
    is_active = request.GET.get("is_active")

    queryset = TestPlan.objects.select_related(
        "product",
        "product_version",
        "type",
        "author",
    ).annotate(
        case_count=Count("cases", distinct=True),
        run_count=Count("run", distinct=True),
    ).order_by("id")

    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            return queryset.filter(pk__in=id_list)

    if product_id:
        queryset = queryset.filter(product_id=product_id)
    if type_id:
        queryset = queryset.filter(type_id=type_id)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active == "true")

    return queryset


def _plan_row(plan):
    """Return a list of display values for a single test plan."""
    return [
        plan.pk,
        plan.name,
        plan.product.name if plan.product else "",
        plan.type.name if plan.type else "",
        "Active" if plan.is_active else "Inactive",
        plan.product_version.value if plan.product_version else "",
        plan.author.username if plan.author else "",
        plan.create_date.strftime("%Y-%m-%d") if plan.create_date else "",
        plan.case_count,
        plan.run_count,
    ]


@method_decorator(login_required, name="dispatch")
class TestPlanBrowserView(TemplateView):
    """
    Test Plan Browser with tree navigation.
    Left panel: Product → TestPlan tree
    Right panel: Selected test plan details
    """

    template_name = "tcms_test_browser/plan_browser.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        plans_qs = TestPlan.objects.select_related(
            "type", "product_version", "author",
        ).order_by("name")

        products = Product.objects.prefetch_related(
            Prefetch("plan", queryset=plans_qs)
        ).order_by("name")

        tree_data = []
        for product in products:
            plans = product.plan.all()
            plan_list = [
                {
                    "id": plan.pk,
                    "name": plan.name,
                    "type": plan.type.name if plan.type else "",
                    "is_active": plan.is_active,
                }
                for plan in plans
            ]
            tree_data.append(
                {
                    "id": product.pk,
                    "name": product.name,
                    "count": len(plan_list),
                    "plans": plan_list,
                }
            )

        context["tree_data"] = tree_data
        return context


@login_required
def api_plan_detail(request, plan_id):
    """API endpoint to get test plan details."""
    try:
        plan = TestPlan.objects.select_related(
            "product", "product_version", "type", "author",
        ).get(pk=plan_id)
    except TestPlan.DoesNotExist:
        return JsonResponse({"error": "Test plan not found"}, status=404)

    cases = list(
        plan.cases.values("id", "summary")
        .order_by("id")[:20]
    )
    runs = list(
        plan.run.values("id", "summary")
        .order_by("-id")[:20]
    )

    data = {
        "id": plan.pk,
        "name": plan.name,
        "text": plan.text or "",
        "is_active": plan.is_active,
        "product": plan.product.name if plan.product else None,
        "product_id": plan.product_id,
        "product_version": plan.product_version.value if plan.product_version else None,
        "type": plan.type.name if plan.type else None,
        "author": plan.author.username if plan.author else None,
        "create_date": plan.create_date.isoformat() if plan.create_date else None,
        "extra_link": plan.extra_link if hasattr(plan, "extra_link") and plan.extra_link else "",
        "cases": cases,
        "runs": runs,
        "case_count": plan.cases.count(),
        "run_count": plan.run.count(),
    }

    return JsonResponse(data)


@login_required
def api_search_plans(request):
    """API endpoint to search test plans."""
    query = request.GET.get("q", "").strip()
    product_id = request.GET.get("product")
    type_id = request.GET.get("type")
    is_active = request.GET.get("is_active")

    plans = TestPlan.objects.select_related(
        "product", "type", "author",
    )

    if query:
        plans = plans.filter(name__icontains=query)
    if product_id:
        plans = plans.filter(product_id=product_id)
    if type_id:
        plans = plans.filter(type_id=type_id)
    if is_active is not None:
        plans = plans.filter(is_active=is_active == "true")

    plans = plans.order_by("name")[:100]

    data = [
        {
            "id": p.pk,
            "name": p.name,
            "product": p.product.name if p.product else None,
            "type": p.type.name if p.type else None,
            "is_active": p.is_active,
            "author": p.author.username if p.author else None,
        }
        for p in plans
    ]

    return JsonResponse({"plans": data})


@login_required
def api_plan_statistics(request):
    """API endpoint returning test plan statistics for charts."""
    product_id = request.GET.get("product")

    queryset = TestPlan.objects.all()
    if product_id:
        queryset = queryset.filter(product_id=product_id)

    total = queryset.count()

    by_type = list(
        queryset.values("type__name")
        .annotate(count=Count("id"))
        .order_by("type__name")
    )

    active_count = queryset.filter(is_active=True).count()
    inactive_count = total - active_count

    by_product = list(
        queryset.values("product__name")
        .annotate(count=Count("id"))
        .order_by("product__name")
    )

    return JsonResponse(
        {
            "total": total,
            "by_type": [
                {"name": item["type__name"] or "Unknown", "count": item["count"]}
                for item in by_type
            ],
            "active_inactive": {"active": active_count, "inactive": inactive_count},
            "by_product": [
                {"name": item["product__name"] or "Unknown", "count": item["count"]}
                for item in by_product
            ],
        }
    )


@login_required
def api_plan_report(request):
    """API endpoint to download a CSV report of test plans."""
    queryset = _get_plan_report_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="test_plans_report.csv"'

    writer = csv.writer(response)
    writer.writerow(PLAN_REPORT_HEADERS)

    for plan in queryset.iterator():
        writer.writerow(_plan_row(plan))

    return response


@login_required
def api_plan_report_excel(request):
    """API endpoint to download an Excel report of test plans."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    queryset = _get_plan_report_queryset(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Plans"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0088CE", end_color="0088CE", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    data_alignment = Alignment(vertical="top", wrap_text=True)
    stripe_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    for col_idx, header in enumerate(PLAN_REPORT_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    ws.row_dimensions[1].height = 25

    row_idx = 2
    for plan in queryset.iterator():
        for col_idx, value in enumerate(_plan_row(plan), 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = data_alignment
            if row_idx % 2 == 0:
                cell.fill = stripe_fill
        row_idx += 1

    last_row = row_idx - 1

    for col in ws.columns:
        max_length = 0
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

    ws.freeze_panes = "A2"

    if last_row >= 1:
        ws.auto_filter.ref = (
            f"A1:{get_column_letter(len(PLAN_REPORT_HEADERS))}{last_row}"
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="test_plans_report.xlsx"'
    return response


@login_required
def api_plan_report_docx(request):
    """API endpoint to download a Word document report of test plans."""
    from docx import Document
    from docx.shared import Inches, Pt

    queryset = _get_plan_report_queryset(request)

    doc = Document()
    doc.add_heading("Test Plans Report", level=1)

    table = doc.add_table(rows=1, cols=len(PLAN_REPORT_HEADERS))
    table.style = "Table Grid"

    for idx, header in enumerate(PLAN_REPORT_HEADERS):
        cell = table.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(9)

    for plan in queryset.iterator():
        row_cells = table.add_row().cells
        for idx, value in enumerate(_plan_row(plan)):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(8)

    for col_idx in range(len(PLAN_REPORT_HEADERS)):
        for row in table.rows:
            row.cells[col_idx].width = Inches(1.2)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="test_plans_report.docx"'
    return response


@login_required
def api_plan_report_pdf(request):
    """API endpoint to download a PDF report of test plans."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    queryset = _get_plan_report_queryset(request)
    styles = getSampleStyleSheet()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=0.5 * inch)
    elements = []

    elements.append(Paragraph("Test Plans Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    cell_style = styles["Normal"]
    cell_style.fontSize = 7
    cell_style.leading = 9

    table_data = [PLAN_REPORT_HEADERS]
    for plan in queryset.iterator():
        row = _plan_row(plan)
        row[1] = Paragraph(str(row[1]), cell_style)
        table_data.append(row)

    col_widths = [
        0.5 * inch,   # ID
        2.5 * inch,   # Name
        1.0 * inch,   # Product
        0.8 * inch,   # Type
        0.7 * inch,   # Status
        0.8 * inch,   # Version
        0.8 * inch,   # Author
        0.8 * inch,   # Created
        0.5 * inch,   # Cases
        0.5 * inch,   # Runs
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0088ce")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="test_plans_report.pdf"'
    return response


# ==========================================
# Test Run Browser
# ==========================================

RUN_REPORT_HEADERS = [
    "ID", "Summary", "Plan", "Product", "Build",
    "Manager", "Started", "Stopped", "Total Executions", "Passed", "Failed",
]


def _get_run_report_queryset(request):
    """Return a filtered TestRun queryset based on request GET params."""
    ids = request.GET.get("ids")
    product_id = request.GET.get("product")
    plan_id = request.GET.get("plan")
    build_id = request.GET.get("build")

    queryset = TestRun.objects.select_related(
        "plan",
        "plan__product",
        "build",
        "manager",
    ).order_by("id")

    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            return queryset.filter(pk__in=id_list)

    if product_id:
        queryset = queryset.filter(plan__product_id=product_id)
    if plan_id:
        queryset = queryset.filter(plan_id=plan_id)
    if build_id:
        queryset = queryset.filter(build_id=build_id)

    return queryset


def _run_row(run):
    """Return a list of display values for a single test run."""
    total = getattr(run, "exec_count", 0)
    passed = getattr(run, "passed_count", 0)
    failed = getattr(run, "failed_count", 0)
    return [
        run.pk,
        run.summary,
        run.plan.name if run.plan else "",
        run.plan.product.name if run.plan and run.plan.product else "",
        run.build.name if run.build else "",
        run.manager.username if run.manager else "",
        run.start_date.strftime("%Y-%m-%d") if run.start_date else "",
        run.stop_date.strftime("%Y-%m-%d") if run.stop_date else "",
        total,
        passed,
        failed,
    ]


@method_decorator(login_required, name="dispatch")
class TestRunBrowserView(TemplateView):
    """
    Test Run Browser with tree navigation.
    Left panel: Product → TestPlan → TestRun tree
    Right panel: Selected test run details
    """

    template_name = "tcms_test_browser/run_browser.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        runs_qs = TestRun.objects.select_related("build", "manager").order_by("summary")
        plans_qs = TestPlan.objects.prefetch_related(
            Prefetch("run", queryset=runs_qs)
        ).order_by("name")

        products = Product.objects.prefetch_related(
            Prefetch("plan", queryset=plans_qs)
        ).order_by("name")

        tree_data = []
        for product in products:
            plans = product.plan.all()
            plan_list = []
            product_run_count = 0
            for plan in plans:
                runs = plan.run.all()
                run_list = [
                    {
                        "id": run.pk,
                        "summary": run.summary,
                        "stop_date": run.stop_date.isoformat() if run.stop_date else None,
                    }
                    for run in runs
                ]
                product_run_count += len(run_list)
                plan_list.append(
                    {
                        "id": plan.pk,
                        "name": plan.name,
                        "count": len(run_list),
                        "runs": run_list,
                    }
                )

            tree_data.append(
                {
                    "id": product.pk,
                    "name": product.name,
                    "count": product_run_count,
                    "plans": plan_list,
                }
            )

        context["tree_data"] = tree_data
        return context


@login_required
def api_run_detail(request, run_id):
    """API endpoint to get test run details with executions."""
    try:
        run = TestRun.objects.select_related(
            "plan", "plan__product", "build", "manager", "default_tester",
        ).get(pk=run_id)
    except TestRun.DoesNotExist:
        return JsonResponse({"error": "Test run not found"}, status=404)

    executions = list(
        TestExecution.objects.filter(run=run)
        .select_related("case", "status", "tested_by")
        .order_by("case__summary")
        .values(
            "id",
            "case__id",
            "case__summary",
            "status__name",
            "status__color",
            "tested_by__username",
            "stop_date",
        )
    )

    data = {
        "id": run.pk,
        "summary": run.summary,
        "notes": run.notes or "",
        "plan_id": run.plan_id,
        "plan_name": run.plan.name if run.plan else None,
        "product": run.plan.product.name if run.plan and run.plan.product else None,
        "build": run.build.name if run.build else None,
        "manager": run.manager.username if run.manager else None,
        "default_tester": run.default_tester.username if run.default_tester else None,
        "start_date": run.start_date.isoformat() if run.start_date else None,
        "stop_date": run.stop_date.isoformat() if run.stop_date else None,
        "planned_start": run.planned_start.isoformat() if hasattr(run, "planned_start") and run.planned_start else None,
        "planned_stop": run.planned_stop.isoformat() if hasattr(run, "planned_stop") and run.planned_stop else None,
        "executions": [
            {
                "id": e["id"],
                "case_id": e["case__id"],
                "case_summary": e["case__summary"],
                "status": e["status__name"],
                "status_color": e["status__color"] or "",
                "tested_by": e["tested_by__username"],
                "stop_date": e["stop_date"].isoformat() if e["stop_date"] else None,
            }
            for e in executions
        ],
    }

    return JsonResponse(data)


@login_required
def api_search_runs(request):
    """API endpoint to search test runs."""
    query = request.GET.get("q", "").strip()
    product_id = request.GET.get("product")
    plan_id = request.GET.get("plan")
    build_id = request.GET.get("build")

    runs = TestRun.objects.select_related(
        "plan", "plan__product", "build", "manager",
    )

    if query:
        runs = runs.filter(summary__icontains=query)
    if product_id:
        runs = runs.filter(plan__product_id=product_id)
    if plan_id:
        runs = runs.filter(plan_id=plan_id)
    if build_id:
        runs = runs.filter(build_id=build_id)

    runs = runs.order_by("summary")[:100]

    data = [
        {
            "id": r.pk,
            "summary": r.summary,
            "plan": r.plan.name if r.plan else None,
            "product": r.plan.product.name if r.plan and r.plan.product else None,
            "build": r.build.name if r.build else None,
            "manager": r.manager.username if r.manager else None,
            "stop_date": r.stop_date.isoformat() if r.stop_date else None,
        }
        for r in runs
    ]

    return JsonResponse({"runs": data})


@login_required
def api_run_statistics(request):
    """API endpoint returning test run statistics for charts."""
    product_id = request.GET.get("product")

    run_qs = TestRun.objects.all()
    if product_id:
        run_qs = run_qs.filter(plan__product_id=product_id)

    total = run_qs.count()

    # Execution status distribution (aggregated from TestExecution)
    exec_qs = TestExecution.objects.all()
    if product_id:
        exec_qs = exec_qs.filter(run__plan__product_id=product_id)

    by_exec_status = list(
        exec_qs.values("status__name")
        .annotate(count=Count("id"))
        .order_by("status__name")
    )

    # Completed vs in-progress (based on stop_date presence)
    completed_count = run_qs.exclude(stop_date=None).count()
    in_progress_count = total - completed_count

    by_product = list(
        run_qs.values("plan__product__name")
        .annotate(count=Count("id"))
        .order_by("plan__product__name")
    )

    return JsonResponse(
        {
            "total": total,
            "by_exec_status": [
                {"name": item["status__name"] or "Unknown", "count": item["count"]}
                for item in by_exec_status
            ],
            "completion": {"completed": completed_count, "in_progress": in_progress_count},
            "by_product": [
                {"name": item["plan__product__name"] or "Unknown", "count": item["count"]}
                for item in by_product
            ],
        }
    )


@login_required
def api_run_report(request):
    """API endpoint to download a CSV report of test runs."""
    queryset = _get_run_report_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="test_runs_report.csv"'

    writer = csv.writer(response)
    writer.writerow(RUN_REPORT_HEADERS)

    for run in queryset:
        execs = TestExecution.objects.filter(run=run)
        total_exec = execs.count()
        passed = execs.filter(status__weight__gt=0).count()
        failed = execs.filter(status__weight__lt=0).count()
        writer.writerow([
            run.pk,
            run.summary,
            run.plan.name if run.plan else "",
            run.plan.product.name if run.plan and run.plan.product else "",
            run.build.name if run.build else "",
            run.manager.username if run.manager else "",
            run.start_date.strftime("%Y-%m-%d") if run.start_date else "",
            run.stop_date.strftime("%Y-%m-%d") if run.stop_date else "",
            total_exec,
            passed,
            failed,
        ])

    return response


@login_required
def api_run_report_excel(request):
    """API endpoint to download an Excel report of test runs."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    queryset = _get_run_report_queryset(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Runs"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0088CE", end_color="0088CE", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    data_alignment = Alignment(vertical="top", wrap_text=True)
    stripe_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    for col_idx, header in enumerate(RUN_REPORT_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    ws.row_dimensions[1].height = 25

    row_idx = 2
    for run in queryset:
        execs = TestExecution.objects.filter(run=run)
        total_exec = execs.count()
        passed = execs.filter(status__weight__gt=0).count()
        failed = execs.filter(status__weight__lt=0).count()
        row_data = [
            run.pk,
            run.summary,
            run.plan.name if run.plan else "",
            run.plan.product.name if run.plan and run.plan.product else "",
            run.build.name if run.build else "",
            run.manager.username if run.manager else "",
            run.start_date.strftime("%Y-%m-%d") if run.start_date else "",
            run.stop_date.strftime("%Y-%m-%d") if run.stop_date else "",
            total_exec,
            passed,
            failed,
        ]
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = data_alignment
            if row_idx % 2 == 0:
                cell.fill = stripe_fill
        row_idx += 1

    last_row = row_idx - 1

    for col in ws.columns:
        max_length = 0
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

    ws.freeze_panes = "A2"

    if last_row >= 1:
        ws.auto_filter.ref = (
            f"A1:{get_column_letter(len(RUN_REPORT_HEADERS))}{last_row}"
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="test_runs_report.xlsx"'
    return response


@login_required
def api_run_report_docx(request):
    """API endpoint to download a Word document report of test runs."""
    from docx import Document
    from docx.shared import Inches, Pt

    queryset = _get_run_report_queryset(request)

    doc = Document()
    doc.add_heading("Test Runs Report", level=1)

    table = doc.add_table(rows=1, cols=len(RUN_REPORT_HEADERS))
    table.style = "Table Grid"

    for idx, header in enumerate(RUN_REPORT_HEADERS):
        cell = table.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(9)

    for tr in queryset:
        execs = TestExecution.objects.filter(run=tr)
        total_exec = execs.count()
        passed = execs.filter(status__weight__gt=0).count()
        failed = execs.filter(status__weight__lt=0).count()
        row_data = [
            tr.pk,
            tr.summary,
            tr.plan.name if tr.plan else "",
            tr.plan.product.name if tr.plan and tr.plan.product else "",
            tr.build.name if tr.build else "",
            tr.manager.username if tr.manager else "",
            tr.start_date.strftime("%Y-%m-%d") if tr.start_date else "",
            tr.stop_date.strftime("%Y-%m-%d") if tr.stop_date else "",
            total_exec,
            passed,
            failed,
        ]
        row_cells = table.add_row().cells
        for idx, value in enumerate(row_data):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run_obj in paragraph.runs:
                    run_obj.font.size = Pt(8)

    for col_idx in range(len(RUN_REPORT_HEADERS)):
        for row in table.rows:
            row.cells[col_idx].width = Inches(1.0)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="test_runs_report.docx"'
    return response


@login_required
def api_run_report_pdf(request):
    """API endpoint to download a PDF report of test runs."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    queryset = _get_run_report_queryset(request)
    styles = getSampleStyleSheet()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=0.5 * inch)
    elements = []

    elements.append(Paragraph("Test Runs Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    cell_style = styles["Normal"]
    cell_style.fontSize = 7
    cell_style.leading = 9

    table_data = [RUN_REPORT_HEADERS]
    for tr in queryset:
        execs = TestExecution.objects.filter(run=tr)
        total_exec = execs.count()
        passed = execs.filter(status__weight__gt=0).count()
        failed = execs.filter(status__weight__lt=0).count()
        row = [
            tr.pk,
            Paragraph(str(tr.summary), cell_style),
            tr.plan.name if tr.plan else "",
            tr.plan.product.name if tr.plan and tr.plan.product else "",
            tr.build.name if tr.build else "",
            tr.manager.username if tr.manager else "",
            tr.start_date.strftime("%Y-%m-%d") if tr.start_date else "",
            tr.stop_date.strftime("%Y-%m-%d") if tr.stop_date else "",
            total_exec,
            passed,
            failed,
        ]
        table_data.append(row)

    col_widths = [
        0.4 * inch,   # ID
        2.0 * inch,   # Summary
        1.2 * inch,   # Plan
        0.9 * inch,   # Product
        0.7 * inch,   # Build
        0.7 * inch,   # Manager
        0.7 * inch,   # Started
        0.7 * inch,   # Stopped
        0.6 * inch,   # Total
        0.5 * inch,   # Passed
        0.5 * inch,   # Failed
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0088ce")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="test_runs_report.pdf"'
    return response


# ==========================================
# Consolidated Browser
# ==========================================


@method_decorator(login_required, name="dispatch")
class ConsolidatedBrowserView(TemplateView):
    """
    Consolidated Browser with Dashboard, Plan-centric, and Case-centric tabs.
    """

    template_name = "tcms_test_browser/consolidated.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.order_by("name")
        return context


@login_required
def api_consolidated_dashboard(request):
    """Dashboard data: totals, coverage gaps, recent activity."""
    product_id = request.GET.get("product")

    case_qs = TestCase.objects.all()
    plan_qs = TestPlan.objects.all()
    run_qs = TestRun.objects.all()
    exec_qs = TestExecution.objects.all()

    if product_id:
        case_qs = case_qs.filter(category__product_id=product_id)
        plan_qs = plan_qs.filter(product_id=product_id)
        run_qs = run_qs.filter(plan__product_id=product_id)
        exec_qs = exec_qs.filter(run__plan__product_id=product_id)

    total_cases = case_qs.count()
    total_plans = plan_qs.count()
    total_runs = run_qs.count()

    # Execution pass/fail rates
    total_execs = exec_qs.count()
    passed_execs = exec_qs.filter(status__weight__gt=0).count()
    failed_execs = exec_qs.filter(status__weight__lt=0).count()

    # Coverage gaps: cases not in any plan
    cases_without_plans = (
        case_qs.filter(plan=None)
        .values("id", "summary")
        .order_by("-id")[:20]
    )

    # Plans without runs
    plans_without_runs = (
        plan_qs.filter(run=None)
        .values("id", "name")
        .order_by("-id")[:20]
    )

    # Recent activity
    recent_runs = list(
        run_qs.select_related("plan", "plan__product", "manager")
        .order_by("-id")[:10]
        .values(
            "id", "summary", "plan__name", "plan__product__name",
            "manager__username", "start_date", "stop_date",
        )
    )
    recent_cases = list(
        case_qs.select_related("category", "category__product", "author")
        .order_by("-id")[:10]
        .values(
            "id", "summary", "category__product__name",
            "author__username", "create_date",
        )
    )

    # Execution status breakdown
    by_exec_status = list(
        exec_qs.values("status__name")
        .annotate(count=Count("id"))
        .order_by("status__name")
    )

    return JsonResponse({
        "totals": {
            "cases": total_cases,
            "plans": total_plans,
            "runs": total_runs,
            "executions": total_execs,
        },
        "execution_rates": {
            "passed": passed_execs,
            "failed": failed_execs,
            "other": total_execs - passed_execs - failed_execs,
            "total": total_execs,
        },
        "by_exec_status": [
            {"name": item["status__name"] or "Unknown", "count": item["count"]}
            for item in by_exec_status
        ],
        "cases_without_plans": list(cases_without_plans),
        "plans_without_runs": list(plans_without_runs),
        "recent_runs": [
            {
                "id": r["id"],
                "summary": r["summary"],
                "plan": r["plan__name"],
                "product": r["plan__product__name"],
                "manager": r["manager__username"],
                "start_date": r["start_date"].isoformat() if r["start_date"] else None,
                "stop_date": r["stop_date"].isoformat() if r["stop_date"] else None,
            }
            for r in recent_runs
        ],
        "recent_cases": [
            {
                "id": r["id"],
                "summary": r["summary"],
                "product": r["category__product__name"],
                "author": r["author__username"],
                "create_date": r["create_date"].isoformat() if r["create_date"] else None,
            }
            for r in recent_cases
        ],
    })


@login_required
def api_consolidated_plan_detail(request, plan_id):
    """Plan-centric drill-down: cases with execution status across runs."""
    try:
        plan = TestPlan.objects.select_related(
            "product", "product_version", "type", "author",
        ).get(pk=plan_id)
    except TestPlan.DoesNotExist:
        return JsonResponse({"error": "Test plan not found"}, status=404)

    # All cases in this plan
    cases = list(
        plan.cases.select_related("case_status", "priority")
        .order_by("id")
        .values("id", "summary", "case_status__name", "priority__value")
    )

    # All runs for this plan
    runs = list(
        plan.run.order_by("-id")
        .values("id", "summary", "start_date", "stop_date")
    )
    run_ids = [r["id"] for r in runs]
    case_ids = [c["id"] for c in cases]

    # All executions for these cases in these runs
    executions = list(
        TestExecution.objects.filter(run_id__in=run_ids, case_id__in=case_ids)
        .select_related("status")
        .values("case_id", "run_id", "status__name", "status__color", "status__weight")
    )

    # Build execution map: case_id -> run_id -> status
    exec_map = {}
    for e in executions:
        case_id = e["case_id"]
        run_id = e["run_id"]
        if case_id not in exec_map:
            exec_map[case_id] = {}
        exec_map[case_id][run_id] = {
            "status": e["status__name"],
            "color": e["status__color"] or "",
            "weight": e["status__weight"],
        }

    # Per-case aggregated stats
    cases_with_stats = []
    for c in cases:
        cid = c["id"]
        case_execs = exec_map.get(cid, {})
        total = len(case_execs)
        passed = sum(1 for e in case_execs.values() if e["weight"] and e["weight"] > 0)
        failed = sum(1 for e in case_execs.values() if e["weight"] and e["weight"] < 0)
        cases_with_stats.append({
            "id": cid,
            "summary": c["summary"],
            "status": c["case_status__name"],
            "priority": c["priority__value"],
            "total_executions": total,
            "passed": passed,
            "failed": failed,
            "exec_by_run": {
                str(rid): case_execs.get(rid, None)
                for rid in run_ids
            },
        })

    # Per-run completion percentages
    runs_with_stats = []
    for r in runs:
        rid = r["id"]
        run_execs = [
            exec_map.get(cid, {}).get(rid)
            for cid in case_ids
        ]
        total = sum(1 for e in run_execs if e is not None)
        passed = sum(1 for e in run_execs if e and e["weight"] and e["weight"] > 0)
        runs_with_stats.append({
            "id": rid,
            "summary": r["summary"],
            "start_date": r["start_date"].isoformat() if r["start_date"] else None,
            "stop_date": r["stop_date"].isoformat() if r["stop_date"] else None,
            "total_executions": total,
            "passed": passed,
            "completion_pct": round(passed / total * 100) if total > 0 else 0,
        })

    return JsonResponse({
        "plan": {
            "id": plan.pk,
            "name": plan.name,
            "product": plan.product.name if plan.product else None,
            "version": plan.product_version.value if plan.product_version else None,
            "type": plan.type.name if plan.type else None,
            "author": plan.author.username if plan.author else None,
            "is_active": plan.is_active,
        },
        "cases": cases_with_stats,
        "runs": runs_with_stats,
    })


@login_required
def api_consolidated_case_detail(request, case_id):
    """Case-centric drill-down: all plans and executions across runs."""
    try:
        tc = TestCase.objects.select_related(
            "case_status", "priority", "author", "category", "category__product",
        ).get(pk=case_id)
    except TestCase.DoesNotExist:
        return JsonResponse({"error": "Test case not found"}, status=404)

    # All plans containing this case
    plans = list(
        tc.plan.select_related("product")
        .order_by("id")
        .values("id", "name", "product__name", "is_active")
    )

    # All executions of this case across all runs
    executions = list(
        TestExecution.objects.filter(case=tc)
        .select_related("run", "run__plan", "status", "tested_by")
        .order_by("-run__id")
        .values(
            "id", "run_id", "run__summary", "run__plan__name",
            "status__name", "status__color", "status__weight",
            "tested_by__username", "stop_date",
        )
    )

    # Group executions by run
    runs_map = {}
    for e in executions:
        rid = e["run_id"]
        if rid not in runs_map:
            runs_map[rid] = {
                "run_id": rid,
                "run_summary": e["run__summary"],
                "plan_name": e["run__plan__name"],
                "executions": [],
            }
        runs_map[rid]["executions"].append({
            "id": e["id"],
            "status": e["status__name"],
            "status_color": e["status__color"] or "",
            "weight": e["status__weight"],
            "tested_by": e["tested_by__username"],
            "stop_date": e["stop_date"].isoformat() if e["stop_date"] else None,
        })

    # Execution timeline (flat list, most recent first)
    timeline = [
        {
            "id": e["id"],
            "run_id": e["run_id"],
            "run_summary": e["run__summary"],
            "status": e["status__name"],
            "status_color": e["status__color"] or "",
            "tested_by": e["tested_by__username"],
            "stop_date": e["stop_date"].isoformat() if e["stop_date"] else None,
        }
        for e in executions
    ]

    return JsonResponse({
        "case": {
            "id": tc.pk,
            "summary": tc.summary,
            "status": tc.case_status.name if tc.case_status else None,
            "priority": tc.priority.value if tc.priority else None,
            "author": tc.author.username if tc.author else None,
            "product": tc.category.product.name if tc.category and tc.category.product else None,
            "category": tc.category.name if tc.category else None,
        },
        "plans": list(plans),
        "executions_by_run": list(runs_map.values()),
        "timeline": timeline,
    })


# ==========================================
# Consolidated Plan Drill-Down Exports
# ==========================================


def _get_plan_drilldown_data(plan_id):
    """Gather runs and cases data for a plan drill-down export."""
    plan = TestPlan.objects.select_related(
        "product", "product_version", "type", "author",
    ).get(pk=plan_id)

    cases = list(
        plan.cases.select_related("case_status")
        .order_by("id")
        .values("id", "summary", "case_status__name")
    )
    runs = list(
        plan.run.order_by("-id")
        .values("id", "summary", "start_date", "stop_date")
    )
    run_ids = [r["id"] for r in runs]
    case_ids = [c["id"] for c in cases]

    executions = list(
        TestExecution.objects.filter(run_id__in=run_ids, case_id__in=case_ids)
        .values("case_id", "run_id", "status__weight")
    )

    exec_map = {}
    for e in executions:
        exec_map.setdefault(e["case_id"], {}).setdefault(e["run_id"], []).append(
            e["status__weight"]
        )

    runs_rows = []
    for r in runs:
        rid = r["id"]
        run_execs = TestExecution.objects.filter(run_id=rid)
        total = run_execs.count()
        passed = run_execs.filter(status__weight__gt=0).count()
        pct = round(passed / total * 100) if total > 0 else 0
        runs_rows.append([
            rid,
            r["summary"],
            r["start_date"].strftime("%Y-%m-%d") if r["start_date"] else "",
            r["stop_date"].strftime("%Y-%m-%d") if r["stop_date"] else "",
            total,
            passed,
            "{}%".format(pct),
        ])

    cases_rows = []
    for c in cases:
        cid = c["id"]
        case_execs = exec_map.get(cid, {})
        total = sum(len(v) for v in case_execs.values())
        passed = sum(
            1 for weights in case_execs.values()
            for w in weights if w and w > 0
        )
        failed = sum(
            1 for weights in case_execs.values()
            for w in weights if w and w < 0
        )
        cases_rows.append([
            cid,
            c["summary"],
            c["case_status__name"] or "",
            total,
            passed,
            failed,
        ])

    return plan, runs_rows, cases_rows


PLAN_DD_RUN_HEADERS = [
    "ID", "Summary", "Started", "Stopped", "Executions", "Passed", "Completion",
]
PLAN_DD_CASE_HEADERS = [
    "ID", "Summary", "Status", "Total Executions", "Passed", "Failed",
]


@login_required
def api_consolidated_plan_report(request, plan_id):
    """CSV export for plan drill-down."""
    try:
        plan, runs_rows, cases_rows = _get_plan_drilldown_data(plan_id)
    except TestPlan.DoesNotExist:
        return JsonResponse({"error": "Test plan not found"}, status=404)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="plan_drilldown_TP{}.csv"'.format(plan_id)
    )

    writer = csv.writer(response)
    writer.writerow(["Plan Drill-Down: {} (TP-{})".format(plan.name, plan.pk)])
    writer.writerow([])
    writer.writerow(["Runs"])
    writer.writerow(PLAN_DD_RUN_HEADERS)
    for row in runs_rows:
        writer.writerow(row)
    writer.writerow([])
    writer.writerow(["Cases"])
    writer.writerow(PLAN_DD_CASE_HEADERS)
    for row in cases_rows:
        writer.writerow(row)

    return response


@login_required
def api_consolidated_plan_report_excel(request, plan_id):
    """Excel export for plan drill-down."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    try:
        plan, runs_rows, cases_rows = _get_plan_drilldown_data(plan_id)
    except TestPlan.DoesNotExist:
        return JsonResponse({"error": "Test plan not found"}, status=404)

    wb = Workbook()
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0088CE", end_color="0088CE", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    data_alignment = Alignment(vertical="top", wrap_text=True)
    stripe_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    def write_sheet(ws, headers, rows):
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        ws.row_dimensions[1].height = 25
        row_idx = 2
        for row in rows:
            for col_idx, value in enumerate(row, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                cell.alignment = data_alignment
                if row_idx % 2 == 0:
                    cell.fill = stripe_fill
            row_idx += 1
        for col in ws.columns:
            max_length = 0
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)
        ws.freeze_panes = "A2"

    ws_runs = wb.active
    ws_runs.title = "Runs"
    write_sheet(ws_runs, PLAN_DD_RUN_HEADERS, runs_rows)

    ws_cases = wb.create_sheet("Cases")
    write_sheet(ws_cases, PLAN_DD_CASE_HEADERS, cases_rows)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        'attachment; filename="plan_drilldown_TP{}.xlsx"'.format(plan_id)
    )
    return response


@login_required
def api_consolidated_plan_report_docx(request, plan_id):
    """Word export for plan drill-down."""
    from docx import Document
    from docx.shared import Inches, Pt

    try:
        plan, runs_rows, cases_rows = _get_plan_drilldown_data(plan_id)
    except TestPlan.DoesNotExist:
        return JsonResponse({"error": "Test plan not found"}, status=404)

    doc = Document()
    doc.add_heading(
        "Plan Drill-Down: {} (TP-{})".format(plan.name, plan.pk), level=1
    )

    doc.add_heading("Runs", level=2)
    table = doc.add_table(rows=1, cols=len(PLAN_DD_RUN_HEADERS))
    table.style = "Table Grid"
    for idx, header in enumerate(PLAN_DD_RUN_HEADERS):
        cell = table.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run_obj in paragraph.runs:
                run_obj.bold = True
                run_obj.font.size = Pt(9)
    for row in runs_rows:
        row_cells = table.add_row().cells
        for idx, value in enumerate(row):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run_obj in paragraph.runs:
                    run_obj.font.size = Pt(8)

    doc.add_paragraph()
    doc.add_heading("Cases", level=2)
    table2 = doc.add_table(rows=1, cols=len(PLAN_DD_CASE_HEADERS))
    table2.style = "Table Grid"
    for idx, header in enumerate(PLAN_DD_CASE_HEADERS):
        cell = table2.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run_obj in paragraph.runs:
                run_obj.bold = True
                run_obj.font.size = Pt(9)
    for row in cases_rows:
        row_cells = table2.add_row().cells
        for idx, value in enumerate(row):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run_obj in paragraph.runs:
                    run_obj.font.size = Pt(8)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="plan_drilldown_TP{}.docx"'.format(plan_id)
    )
    return response


@login_required
def api_consolidated_plan_report_pdf(request, plan_id):
    """PDF export for plan drill-down."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    try:
        plan, runs_rows, cases_rows = _get_plan_drilldown_data(plan_id)
    except TestPlan.DoesNotExist:
        return JsonResponse({"error": "Test plan not found"}, status=404)

    styles = getSampleStyleSheet()
    cell_style = styles["Normal"]
    cell_style.fontSize = 7
    cell_style.leading = 9

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=0.5 * inch)
    elements = []

    elements.append(Paragraph(
        "Plan Drill-Down: {} (TP-{})".format(plan.name, plan.pk),
        styles["Title"],
    ))
    elements.append(Spacer(1, 12))

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0088ce")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])

    # Runs table
    elements.append(Paragraph("Runs", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    runs_data = [PLAN_DD_RUN_HEADERS]
    for row in runs_rows:
        r = list(row)
        r[1] = Paragraph(str(r[1]), cell_style)
        runs_data.append(r)
    run_widths = [
        0.4 * inch, 2.5 * inch, 0.8 * inch, 0.8 * inch,
        0.7 * inch, 0.6 * inch, 0.8 * inch,
    ]
    t1 = Table(runs_data, colWidths=run_widths, repeatRows=1)
    t1.setStyle(table_style)
    elements.append(t1)
    elements.append(Spacer(1, 18))

    # Cases table
    elements.append(Paragraph("Cases", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    cases_data = [PLAN_DD_CASE_HEADERS]
    for row in cases_rows:
        r = list(row)
        r[1] = Paragraph(str(r[1]), cell_style)
        cases_data.append(r)
    case_widths = [
        0.5 * inch, 3.0 * inch, 0.8 * inch,
        0.8 * inch, 0.6 * inch, 0.6 * inch,
    ]
    t2 = Table(cases_data, colWidths=case_widths, repeatRows=1)
    t2.setStyle(table_style)
    elements.append(t2)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="plan_drilldown_TP{}.pdf"'.format(plan_id)
    )
    return response


# ==========================================
# Consolidated Case Drill-Down Exports
# ==========================================


def _get_case_drilldown_data(case_id):
    """Gather plans and execution timeline data for a case drill-down export."""
    tc = TestCase.objects.select_related(
        "case_status", "priority", "author", "category", "category__product",
    ).get(pk=case_id)

    plans = list(
        tc.plan.select_related("product")
        .order_by("id")
        .values("id", "name", "product__name", "is_active")
    )
    plans_rows = [
        [
            p["id"],
            p["name"],
            p["product__name"] or "",
            "Active" if p["is_active"] else "Inactive",
        ]
        for p in plans
    ]

    executions = list(
        TestExecution.objects.filter(case=tc)
        .select_related("run", "run__plan", "status", "tested_by")
        .order_by("-run__id")
        .values(
            "run_id", "run__summary", "run__plan__name",
            "status__name", "tested_by__username", "stop_date",
        )
    )
    timeline_rows = [
        [
            e["run_id"],
            e["run__summary"],
            e["run__plan__name"] or "",
            e["status__name"] or "",
            e["tested_by__username"] or "",
            e["stop_date"].strftime("%Y-%m-%d") if e["stop_date"] else "",
        ]
        for e in executions
    ]

    return tc, plans_rows, timeline_rows


CASE_DD_PLAN_HEADERS = ["ID", "Name", "Product", "Status"]
CASE_DD_TIMELINE_HEADERS = [
    "Run ID", "Run Summary", "Plan", "Status", "Tested By", "Date",
]


@login_required
def api_consolidated_case_report(request, case_id):
    """CSV export for case drill-down."""
    try:
        tc, plans_rows, timeline_rows = _get_case_drilldown_data(case_id)
    except TestCase.DoesNotExist:
        return JsonResponse({"error": "Test case not found"}, status=404)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="case_drilldown_TC{}.csv"'.format(case_id)
    )

    writer = csv.writer(response)
    writer.writerow(["Case Drill-Down: {} (TC-{})".format(tc.summary, tc.pk)])
    writer.writerow([])
    writer.writerow(["Plans"])
    writer.writerow(CASE_DD_PLAN_HEADERS)
    for row in plans_rows:
        writer.writerow(row)
    writer.writerow([])
    writer.writerow(["Execution Timeline"])
    writer.writerow(CASE_DD_TIMELINE_HEADERS)
    for row in timeline_rows:
        writer.writerow(row)

    return response


@login_required
def api_consolidated_case_report_excel(request, case_id):
    """Excel export for case drill-down."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    try:
        tc, plans_rows, timeline_rows = _get_case_drilldown_data(case_id)
    except TestCase.DoesNotExist:
        return JsonResponse({"error": "Test case not found"}, status=404)

    wb = Workbook()
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0088CE", end_color="0088CE", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    data_alignment = Alignment(vertical="top", wrap_text=True)
    stripe_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

    def write_sheet(ws, headers, rows):
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        ws.row_dimensions[1].height = 25
        row_idx = 2
        for row in rows:
            for col_idx, value in enumerate(row, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                cell.alignment = data_alignment
                if row_idx % 2 == 0:
                    cell.fill = stripe_fill
            row_idx += 1
        for col in ws.columns:
            max_length = 0
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)
        ws.freeze_panes = "A2"

    ws_plans = wb.active
    ws_plans.title = "Plans"
    write_sheet(ws_plans, CASE_DD_PLAN_HEADERS, plans_rows)

    ws_timeline = wb.create_sheet("Execution Timeline")
    write_sheet(ws_timeline, CASE_DD_TIMELINE_HEADERS, timeline_rows)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        'attachment; filename="case_drilldown_TC{}.xlsx"'.format(case_id)
    )
    return response


@login_required
def api_consolidated_case_report_docx(request, case_id):
    """Word export for case drill-down."""
    from docx import Document
    from docx.shared import Inches, Pt

    try:
        tc, plans_rows, timeline_rows = _get_case_drilldown_data(case_id)
    except TestCase.DoesNotExist:
        return JsonResponse({"error": "Test case not found"}, status=404)

    doc = Document()
    doc.add_heading(
        "Case Drill-Down: {} (TC-{})".format(tc.summary, tc.pk), level=1
    )

    doc.add_heading("Plans", level=2)
    table = doc.add_table(rows=1, cols=len(CASE_DD_PLAN_HEADERS))
    table.style = "Table Grid"
    for idx, header in enumerate(CASE_DD_PLAN_HEADERS):
        cell = table.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run_obj in paragraph.runs:
                run_obj.bold = True
                run_obj.font.size = Pt(9)
    for row in plans_rows:
        row_cells = table.add_row().cells
        for idx, value in enumerate(row):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run_obj in paragraph.runs:
                    run_obj.font.size = Pt(8)

    doc.add_paragraph()
    doc.add_heading("Execution Timeline", level=2)
    table2 = doc.add_table(rows=1, cols=len(CASE_DD_TIMELINE_HEADERS))
    table2.style = "Table Grid"
    for idx, header in enumerate(CASE_DD_TIMELINE_HEADERS):
        cell = table2.rows[0].cells[idx]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run_obj in paragraph.runs:
                run_obj.bold = True
                run_obj.font.size = Pt(9)
    for row in timeline_rows:
        row_cells = table2.add_row().cells
        for idx, value in enumerate(row):
            row_cells[idx].text = str(value)
            for paragraph in row_cells[idx].paragraphs:
                for run_obj in paragraph.runs:
                    run_obj.font.size = Pt(8)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="case_drilldown_TC{}.docx"'.format(case_id)
    )
    return response


@login_required
def api_consolidated_case_report_pdf(request, case_id):
    """PDF export for case drill-down."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    try:
        tc, plans_rows, timeline_rows = _get_case_drilldown_data(case_id)
    except TestCase.DoesNotExist:
        return JsonResponse({"error": "Test case not found"}, status=404)

    styles = getSampleStyleSheet()
    cell_style = styles["Normal"]
    cell_style.fontSize = 7
    cell_style.leading = 9

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=0.5 * inch)
    elements = []

    elements.append(Paragraph(
        "Case Drill-Down: {} (TC-{})".format(tc.summary, tc.pk),
        styles["Title"],
    ))
    elements.append(Spacer(1, 12))

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0088ce")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])

    # Plans table
    elements.append(Paragraph("Plans", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    plans_data = [CASE_DD_PLAN_HEADERS]
    for row in plans_rows:
        r = list(row)
        r[1] = Paragraph(str(r[1]), cell_style)
        plans_data.append(r)
    plan_widths = [
        0.5 * inch, 3.0 * inch, 1.5 * inch, 0.8 * inch,
    ]
    t1 = Table(plans_data, colWidths=plan_widths, repeatRows=1)
    t1.setStyle(table_style)
    elements.append(t1)
    elements.append(Spacer(1, 18))

    # Timeline table
    elements.append(Paragraph("Execution Timeline", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    timeline_data = [CASE_DD_TIMELINE_HEADERS]
    for row in timeline_rows:
        r = list(row)
        r[1] = Paragraph(str(r[1]), cell_style)
        timeline_data.append(r)
    timeline_widths = [
        0.5 * inch, 2.5 * inch, 1.5 * inch,
        0.8 * inch, 0.8 * inch, 0.8 * inch,
    ]
    t2 = Table(timeline_data, colWidths=timeline_widths, repeatRows=1)
    t2.setStyle(table_style)
    elements.append(t2)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="case_drilldown_TC{}.pdf"'.format(case_id)
    )
    return response
