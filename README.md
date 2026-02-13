# tcms-test-browser

Test Case Browser plugin for Kiwi TCMS with tree navigation, statistics dashboard, and report generation.

## Features

- **Statistics Dashboard**: Collapsible panel showing total count, status/priority donut charts (C3.js), automation progress bar, and per-product bar chart
- **Tree View Navigation**: Browse test cases organized by Product > Category > Test Case
- **Test Case Counts**: See the number of test cases at each level in the tree
- **Quick Search**: Search test cases with live results
- **Product Filter**: Filter tree view and statistics by product
- **Detail Panel**: View test case details (steps, info, related items) without leaving the page
- **Report Export**: Download test case reports in CSV, Excel (.xlsx), Word (.docx), and PDF formats
- **Responsive Design**: Works on desktop and tablet

## Layout

```
+---------------------------------------------------------------+
| Statistics Dashboard (collapsible)                [Export v]   |
| +------+ +----------+ +----------+ +----------+ +-----------+ |
| |Total | | Status   | | Priority | |Automation| |By Product | |
| | 150  | | (donut)  | | (donut)  | |(progress)| |  (bar)    | |
| +------+ +----------+ +----------+ +----------+ +-----------+ |
+---------------------------------------------------------------+
| Tree Nav (left)          | Detail Panel (right)               |
| [Search]                 | TC-123: Login test                 |
| [Filter]                 | Status: Confirmed  Priority: P1    |
| v Product A (15)         |                                    |
|   v Login (5)            | [Steps] [Information] [Related]    |
|     * TC-123             |                                    |
|     * TC-124             | 1. Open the login page             |
|   > Registration (3)     | 2. Enter valid username            |
| > Product B (23)         | 3. Click Submit                    |
|                          |                                    |
|                          | [View Full Details] [Edit]         |
+--------------------------+------------------------------------+
```

## Installation

```bash
pip install tcms-test-browser
```

Or for development:

```bash
cd tcms-test-browser
pip install -e .
```

This installs the required dependencies:

- **openpyxl** - Excel export
- **python-docx** - Word export
- **reportlab** - PDF export

## Usage

After installation:

1. The plugin automatically registers via the `kiwitcms.plugins` entry point
2. Access the browser from **MORE** > **Test Case Browser** in the navigation menu
3. Or navigate directly to `/tcms_test_browser/`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tcms_test_browser/` | GET | Main browser page |
| `/tcms_test_browser/api/category/<id>/testcases/` | GET | Test cases for a category |
| `/tcms_test_browser/api/testcase/<id>/` | GET | Test case detail |
| `/tcms_test_browser/api/search/?q=<query>` | GET | Search test cases |
| `/tcms_test_browser/api/statistics/` | GET | Statistics for charts |
| `/tcms_test_browser/api/report/` | GET | Download CSV report |
| `/tcms_test_browser/api/report/excel/` | GET | Download Excel report |
| `/tcms_test_browser/api/report/docx/` | GET | Download Word report |
| `/tcms_test_browser/api/report/pdf/` | GET | Download PDF report |

All endpoints accept an optional `?product=<id>` filter parameter.

## Requirements

- Kiwi TCMS 12.0+
- Python 3.8+

## License

GPLv2
