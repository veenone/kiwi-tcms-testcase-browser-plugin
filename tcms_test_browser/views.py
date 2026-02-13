import csv
import io

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from tcms.management.models import Product
from tcms.testcases.models import Category, TestCase


def _get_report_queryset(request):
    """Return a filtered queryset based on request GET params."""
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
