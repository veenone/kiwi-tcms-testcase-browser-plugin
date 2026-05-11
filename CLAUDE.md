# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

A Kiwi TCMS plugin that adds three browser pages — Test Case Browser, Test Plan Browser, and Test Run Browser — each with tree navigation, a statistics dashboard with charts, a detail panel, and report exports (CSV, Excel, Word, PDF).

## Development

```bash
pip install -e .                  # Install in editable mode (pulls openpyxl, python-docx, reportlab)
```

This is a Django app plugin — there is no standalone runserver. It must be installed into a running Kiwi TCMS instance. The plugin auto-registers via the `kiwitcms.plugins` entry point in `setup.cfg`.

No tests, linter config, or CI exist yet.

## Architecture

Single Django app in `tcms_test_browser/`. All backend logic is in `views.py`.

**Plugin registration chain:** `setup.cfg` entry point `kiwitcms.plugins` → `__init__.py` sets `default_app_config` → `apps.py` `TestBrowserConfig` → `menu.py` adds 3 items ("Test Case Browser", "Test Plan Browser", "Test Run Browser") to the Kiwi TCMS MORE menu via `MENU_ITEMS`.

**URL mounting:** Kiwi TCMS mounts the app at `/tcms_test_browser/`. URLs defined in `urls.py`:
- Test Case Browser: `/tcms_test_browser/` and `/tcms_test_browser/api/...`
- Test Plan Browser: `/tcms_test_browser/plans/` and `/tcms_test_browser/plans/api/...`
- Test Run Browser: `/tcms_test_browser/runs/` and `/tcms_test_browser/runs/api/...`

**Backend (`views.py`):**
- **Test Case Browser:** `TestCaseBrowserView` — Product > Category tree with annotated test case counts. Helpers: `_get_report_queryset()`, `_tc_row()`, `REPORT_HEADERS`. API: category testcases, detail, search, statistics, 4 report exports.
- **Test Plan Browser:** `TestPlanBrowserView` — Product > TestPlan tree (2-level, all loaded upfront). Helpers: `_get_plan_report_queryset()`, `_plan_row()`, `PLAN_REPORT_HEADERS`. API: plan detail, search, statistics, 4 report exports.
- **Test Run Browser:** `TestRunBrowserView` — Product > TestPlan > TestRun tree (3-level, all loaded upfront). Helpers: `_get_run_report_queryset()`. API: run detail (includes executions), search, statistics, 4 report exports.
- All views are `@login_required`. All API endpoints return `JsonResponse`. All report endpoints support CSV, Excel (openpyxl), Word (python-docx), PDF (reportlab).

**Frontend:**
- `browser.html` / `browser.js` — Test Case Browser (lazy-loads test cases per category via AJAX)
- `plan_browser.html` / `plan_browser.js` — Test Plan Browser (plans loaded upfront in tree)
- `run_browser.html` / `run_browser.js` — Test Run Browser (runs loaded upfront in tree)
- `browser.css` — shared styles for all three browsers
- All templates extend Kiwi TCMS `base.html`, use PatternFly/Bootstrap 3, D3.js, C3.js
- All JS files are jQuery IIFEs with the same pattern: `initTreeToggle`, `initSearch`, `initFilterProduct`, `initStatsPanel`, `loadStatistics`

**Key Kiwi TCMS models used:**
- `Product`, `Category`, `TestCase` (with relations: `case_status`, `priority`, `author`, `default_tester`, `reviewer`, `category`, `component`, `tag`, `plan`)
- `TestPlan` (with relations: `product`, `product_version`, `type`, `author`, `case`, `run`)
- `TestRun` (with relations: `plan`, `build`, `manager`, `default_tester`, `executions`)
- `TestExecution` (with relations: `case`, `status`, `tested_by`)
