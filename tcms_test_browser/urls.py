from django.urls import re_path

from tcms_test_browser import views

urlpatterns = [
    re_path(r"^$", views.TestCaseBrowserView.as_view(), name="testcase-browser"),
    re_path(
        r"^api/category/(?P<category_id>\d+)/testcases/$",
        views.api_testcases_by_category,
        name="testcase-browser-api-category",
    ),
    re_path(
        r"^api/testcase/(?P<testcase_id>\d+)/$",
        views.api_testcase_detail,
        name="testcase-browser-api-detail",
    ),
    re_path(
        r"^api/search/$",
        views.api_search_testcases,
        name="testcase-browser-api-search",
    ),
    re_path(
        r"^api/statistics/$",
        views.api_statistics,
        name="testcase-browser-api-stats",
    ),
    re_path(
        r"^api/report/$",
        views.api_report,
        name="testcase-browser-api-report",
    ),
    re_path(
        r"^api/report/excel/$",
        views.api_report_excel,
        name="testcase-browser-api-report-excel",
    ),
    re_path(
        r"^api/report/docx/$",
        views.api_report_docx,
        name="testcase-browser-api-report-docx",
    ),
    re_path(
        r"^api/report/pdf/$",
        views.api_report_pdf,
        name="testcase-browser-api-report-pdf",
    ),
]
