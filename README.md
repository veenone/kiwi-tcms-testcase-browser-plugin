# tcms-test-browser

Test Case, Test Plan, Test Run, and Consolidated Browser plugin for Kiwi TCMS with tree navigation, statistics dashboards, detail panels, and report exports (CSV, Excel, Word, PDF).

## Features

### Test Case Browser
- **Tree View**: Product > Category > Test Case hierarchy with counts
- **Statistics Dashboard**: Total count, status/priority donuts, automation progress, per-product bar chart
- **Detail Panel**: Steps, information, and related items tabs
- **Related Items**: Test plans displayed as sortable table (ID, Name)
- **Quick Search**: Live search with 300ms debounce
- **Product Filter**: Filter tree and stats by product
- **Selection Export**: Checkbox selection for filtered CSV/Excel/Word/PDF exports

### Test Plan Browser
- **Tree View**: Product > Test Plan hierarchy with counts
- **Statistics Dashboard**: Total count, by-type donut, active/inactive progress bar, per-product bar chart
- **Detail Panel**: Description, information, and related tabs
- **Related Items**: Test cases and test runs displayed as tables (ID, Summary)
- **Quick Search**: Search plans by name
- **Selection Export**: Checkbox selection for filtered CSV/Excel/Word/PDF exports

### Test Run Browser
- **Tree View**: Product > Test Plan > Test Run hierarchy with counts
- **Statistics Dashboard**: Total count, execution status donut, completion progress bar, per-product bar chart
- **Detail Panel**: Executions table (with colored status badges), information, and notes tabs
- **Quick Search**: Search runs by summary
- **Selection Export**: Checkbox selection for filtered CSV/Excel/Word/PDF exports

### Consolidated Browser
- **Dashboard Tab**: Totals (cases, plans, runs, pass rate), execution status donut, coverage gaps (cases without plans, plans without runs), recent activity tables
- **Plan Drill-Down Tab**: Search any plan, view runs summary table, cases-by-runs execution matrix with color-coded status cells, CSV/Excel/Word/PDF export
- **Case Drill-Down Tab**: Search any case, view associated plans as table, execution timeline across all runs, CSV/Excel/Word/PDF export
- **Product Filter**: Filter dashboard data by product

### Common
- **Responsive Design**: Works on desktop and tablet
- **PatternFly/Bootstrap 3**: Consistent with Kiwi TCMS UI
- **C3.js Charts**: Donut and bar charts for statistics
- **Selection Checkboxes**: Select items in tree for filtered exports

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
|     [x] TC-123           |                                    |
|     [ ] TC-124           | 1. Open the login page             |
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
2. Access the browsers from **MORE > Test Browser** in the navigation:
   - **Test Case Browser** - `/tcms_test_browser/`
   - **Test Plan Browser** - `/tcms_test_browser/plans/`
   - **Test Run Browser** - `/tcms_test_browser/runs/`
   - **Consolidated Browser** - `/tcms_test_browser/consolidated/`

## API Endpoints

### Test Case Browser

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

### Test Plan Browser

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tcms_test_browser/plans/` | GET | Plan browser page |
| `/tcms_test_browser/plans/api/plan/<id>/` | GET | Plan detail |
| `/tcms_test_browser/plans/api/search/?q=<query>` | GET | Search plans |
| `/tcms_test_browser/plans/api/statistics/` | GET | Plan statistics |
| `/tcms_test_browser/plans/api/report/` | GET | Download CSV report |
| `/tcms_test_browser/plans/api/report/excel/` | GET | Download Excel report |
| `/tcms_test_browser/plans/api/report/docx/` | GET | Download Word report |
| `/tcms_test_browser/plans/api/report/pdf/` | GET | Download PDF report |

### Test Run Browser

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tcms_test_browser/runs/` | GET | Run browser page |
| `/tcms_test_browser/runs/api/run/<id>/` | GET | Run detail with executions |
| `/tcms_test_browser/runs/api/search/?q=<query>` | GET | Search runs |
| `/tcms_test_browser/runs/api/statistics/` | GET | Run statistics |
| `/tcms_test_browser/runs/api/report/` | GET | Download CSV report |
| `/tcms_test_browser/runs/api/report/excel/` | GET | Download Excel report |
| `/tcms_test_browser/runs/api/report/docx/` | GET | Download Word report |
| `/tcms_test_browser/runs/api/report/pdf/` | GET | Download PDF report |

### Consolidated Browser

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tcms_test_browser/consolidated/` | GET | Consolidated browser page |
| `/tcms_test_browser/consolidated/api/dashboard/` | GET | Dashboard data |
| `/tcms_test_browser/consolidated/api/plan/<id>/detail/` | GET | Plan drill-down data |
| `/tcms_test_browser/consolidated/api/plan/<id>/report/` | GET | Plan drill-down CSV |
| `/tcms_test_browser/consolidated/api/plan/<id>/report/excel/` | GET | Plan drill-down Excel |
| `/tcms_test_browser/consolidated/api/plan/<id>/report/docx/` | GET | Plan drill-down Word |
| `/tcms_test_browser/consolidated/api/plan/<id>/report/pdf/` | GET | Plan drill-down PDF |
| `/tcms_test_browser/consolidated/api/case/<id>/detail/` | GET | Case drill-down data |
| `/tcms_test_browser/consolidated/api/case/<id>/report/` | GET | Case drill-down CSV |
| `/tcms_test_browser/consolidated/api/case/<id>/report/excel/` | GET | Case drill-down Excel |
| `/tcms_test_browser/consolidated/api/case/<id>/report/docx/` | GET | Case drill-down Word |
| `/tcms_test_browser/consolidated/api/case/<id>/report/pdf/` | GET | Case drill-down PDF |

All endpoints require authentication. Browser list endpoints accept an optional `?product=<id>` filter. Report endpoints accept `?ids=<comma-separated>` for selection-based export. Search endpoints support additional filters specific to their entity type.

## Requirements

- Kiwi TCMS 12.0+
- Python 3.8+

## License

GPLv2
