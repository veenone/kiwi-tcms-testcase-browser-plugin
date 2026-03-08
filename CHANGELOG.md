# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-08

### Added
- Landing page with card-based navigation showing live counts for each browser view
- Navigation tabs across all views (Test Cases, Test Plans, Test Runs, Consolidated)
- Chart click-to-filter: clicking any chart segment opens a modal with filtered, paginated results
  - Test Case Browser: filter by status, priority, or product
  - Test Plan Browser: filter by type or product
  - Test Run Browser: filter by execution status or product
  - Consolidated Browser: filter by execution status
- Consolidated dashboard export (CSV, Excel, Word, PDF)
- New API endpoints: `api/browse/`, `plans/api/browse/`, `runs/api/browse/`, `api/executions/browse/`
- Consolidated dashboard report endpoints (CSV, Excel, Word, PDF)
- Pie charts embedded in all export reports (Excel, Word, PDF) with horizontal layout and legends below
  - Test Cases: By Status, By Priority, Automation
  - Test Plans: By Type, Active vs Inactive
  - Test Runs: Execution Status, Completion Status
  - Consolidated Dashboard: Execution Status
- Styled table formatting across all export reports (branded headers, alternating row colors, auto-fit columns)
- Pagination for coverage gaps in consolidated dashboard
- Screenshots in `docs/screenshots/` for documentation
- MIT LICENSE file

### Changed
- "By Product" bar charts switched to horizontal layout for better readability with many products
- Bar chart height scales dynamically based on number of categories
- "By Product" charts moved to dedicated full-width row in all browser views
- Statistics dashboard layout rebalanced (wider progress bars for Automation, Active/Inactive, Completion)
- CSS `.stat-chart-container` changed from fixed `height` to `min-height` to accommodate dynamic charts
- Cursor changes to pointer on hovering chart segments
- Report metadata: test plan lists displayed as bullet points (one per line) instead of comma-delimited
- Export report charts arranged horizontally in borderless tables (DOCX), side-by-side layout (Excel, PDF)

### Fixed
- IIFE wrappers in `browser.js`, `plan_browser.js`, and `run_browser.js` now use `})($)` instead of `})(jQuery)` to ensure Bootstrap modal events fire correctly (Kiwi TCMS ships two jQuery instances)

## [0.2.0] - 2026-03-07

### Added
- Test Plan Browser with tree navigation (Product > Plan), type/product statistics, active/inactive progress bar
- Test Run Browser with tree navigation (Product > Plan > Run), execution status donut, completion progress bar
- Consolidated Browser with dashboard tab (summary cards, execution status chart, coverage gaps, recent runs/cases), plan drill-down tab, and case drill-down tab
- Export reports (CSV, Excel, Word, PDF) for Test Case, Test Plan, and Test Run browsers
- Select All / multi-select checkboxes in tree for batch export
- Product filter dropdown in all browser views
- Search functionality in all browser views
- Detail panel with tabs for each browser (case details, plan details, run details)
- Pagination for consolidated drill-down tables

### Changed
- Test Case Browser statistics dashboard redesigned with donut charts (status, priority) and automation progress bar
- Refactored views.py with dedicated API endpoints per browser view
- Expanded URL routing for plan, run, and consolidated views

## [0.1.0] - 2026-03-06

### Added
- Initial release of Test Case Browser plugin for Kiwi TCMS
- Tree navigation by Product > Category > Test Case
- Statistics dashboard with status distribution, priority breakdown, and product counts
- Test case detail panel with description, steps, and metadata tabs
- Search test cases by summary
- Product filter in tree view
- Plugin auto-registers under Kiwi TCMS menu via `kiwitcms.plugins` entry point
