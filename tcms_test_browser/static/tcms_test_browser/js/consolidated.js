/*
 * Consolidated Browser JavaScript
 * Dashboard, Plan Drill-Down, and Case Drill-Down tabs
 */

(function($) {
    'use strict';

    var COLORS = ['#3f9c35', '#cc0000', '#ec7a08', '#0088ce', '#703fec', '#39a5dc', '#f0ab00', '#3a9ca6'];

    var currentPlanDDId = null;
    var currentCaseDDId = null;

    var PLAN_DD_EXPORT_URLS = {
        csv: '/tcms_test_browser/consolidated/api/plan/{id}/report/',
        excel: '/tcms_test_browser/consolidated/api/plan/{id}/report/excel/',
        docx: '/tcms_test_browser/consolidated/api/plan/{id}/report/docx/',
        pdf: '/tcms_test_browser/consolidated/api/plan/{id}/report/pdf/'
    };

    var CASE_DD_EXPORT_URLS = {
        csv: '/tcms_test_browser/consolidated/api/case/{id}/report/',
        excel: '/tcms_test_browser/consolidated/api/case/{id}/report/excel/',
        docx: '/tcms_test_browser/consolidated/api/case/{id}/report/docx/',
        pdf: '/tcms_test_browser/consolidated/api/case/{id}/report/pdf/'
    };

    $(document).ready(function() {
        loadDashboard();

        $('#filter-product').on('change', function() {
            loadDashboard();
        });

        initPlanSearch();
        initCaseSearch();
        initDrillDownExports();
    });

    // ==========================================
    // Dashboard Tab
    // ==========================================

    function loadDashboard() {
        var productId = $('#filter-product').val();
        var params = {};
        if (productId) {
            params.product = productId;
        }

        $.ajax({
            url: '/tcms_test_browser/consolidated/api/dashboard/',
            method: 'GET',
            data: params,
            dataType: 'json',
            success: function(data) {
                renderDashboard(data);
            },
            error: function() {
                $('#dash-total-cases, #dash-total-plans, #dash-total-runs').text('--');
                $('#dash-pass-rate').text('--%');
            }
        });
    }

    function renderDashboard(data) {
        // Stat cards
        $('#dash-total-cases').text(data.totals.cases);
        $('#dash-total-plans').text(data.totals.plans);
        $('#dash-total-runs').text(data.totals.runs);

        var rates = data.execution_rates;
        var passRate = rates.total > 0 ? Math.round(rates.passed / rates.total * 100) : 0;
        $('#dash-pass-rate').text(passRate + '%');

        // Execution status chart
        if (typeof window.c3 !== 'undefined' && data.by_exec_status.length > 0) {
            var columns = [];
            for (var i = 0; i < data.by_exec_status.length; i++) {
                columns.push([data.by_exec_status[i].name, data.by_exec_status[i].count]);
            }
            c3.generate({
                bindto: '#dash-chart-exec-status',
                data: { columns: columns, type: 'donut' },
                donut: {
                    width: 20,
                    title: data.execution_rates.total + ' executions',
                    label: { show: true, format: function(v) { return v; } }
                },
                color: { pattern: COLORS },
                legend: { show: true, position: 'right' },
                size: { height: 250 }
            });
        } else {
            $('#dash-chart-exec-status').html('<div class="text-muted text-center">No execution data</div>');
        }

        // Coverage gaps
        var casesNoPlan = data.cases_without_plans;
        $('#dash-cases-no-plans-count').text(casesNoPlan.length);
        if (casesNoPlan.length > 0) {
            var html = casesNoPlan.map(function(c) {
                return '<a href="/case/' + c.id + '/" class="list-group-item" target="_blank" style="padding: 5px 10px; font-size: 12px;">' +
                    'TC-' + c.id + ': ' + escapeHtml(c.summary) + '</a>';
            }).join('');
            $('#dash-cases-no-plans').html(html);
        } else {
            $('#dash-cases-no-plans').html('<div class="text-muted small">All cases are in plans</div>');
        }

        var plansNoRun = data.plans_without_runs;
        $('#dash-plans-no-runs-count').text(plansNoRun.length);
        if (plansNoRun.length > 0) {
            var html2 = plansNoRun.map(function(p) {
                return '<a href="/plan/' + p.id + '/" class="list-group-item" target="_blank" style="padding: 5px 10px; font-size: 12px;">' +
                    'TP-' + p.id + ': ' + escapeHtml(p.name) + '</a>';
            }).join('');
            $('#dash-plans-no-runs').html(html2);
        } else {
            $('#dash-plans-no-runs').html('<div class="text-muted small">All plans have runs</div>');
        }

        // Recent runs
        var $runsBody = $('#dash-recent-runs tbody');
        $runsBody.empty();
        if (data.recent_runs.length > 0) {
            data.recent_runs.forEach(function(r) {
                var statusLabel = r.stop_date ?
                    '<span class="label label-success">Completed</span>' :
                    '<span class="label label-info">In Progress</span>';
                $runsBody.append(
                    '<tr>' +
                        '<td><a href="/runs/' + r.id + '/" target="_blank">TR-' + r.id + '</a></td>' +
                        '<td>' + escapeHtml(r.summary) + '</td>' +
                        '<td>' + escapeHtml(r.plan || '') + '</td>' +
                        '<td>' + statusLabel + '</td>' +
                    '</tr>'
                );
            });
        } else {
            $runsBody.html('<tr><td colspan="4" class="text-muted text-center">No runs</td></tr>');
        }

        // Recent cases
        var $casesBody = $('#dash-recent-cases tbody');
        $casesBody.empty();
        if (data.recent_cases.length > 0) {
            data.recent_cases.forEach(function(c) {
                $casesBody.append(
                    '<tr>' +
                        '<td><a href="/case/' + c.id + '/" target="_blank">TC-' + c.id + '</a></td>' +
                        '<td>' + escapeHtml(c.summary) + '</td>' +
                        '<td>' + escapeHtml(c.product || '') + '</td>' +
                        '<td>' + escapeHtml(c.author || '') + '</td>' +
                    '</tr>'
                );
            });
        } else {
            $casesBody.html('<tr><td colspan="4" class="text-muted text-center">No cases</td></tr>');
        }
    }

    // ==========================================
    // Plan Drill-Down Tab
    // ==========================================

    function initPlanSearch() {
        var searchTimeout;

        $('#plan-search-input').on('input', function() {
            clearTimeout(searchTimeout);
            var query = $(this).val().trim();
            if (query.length >= 2) {
                searchTimeout = setTimeout(function() {
                    searchPlans(query);
                }, 300);
            } else {
                $('#plan-search-results').hide();
            }
        });

        $('#btn-plan-search').on('click', function() {
            var query = $('#plan-search-input').val().trim();
            if (query.length >= 2) {
                searchPlans(query);
            }
        });

        // Close dropdown on click outside
        $(document).on('click', function(e) {
            if (!$(e.target).closest('#plan-search-input, #plan-search-results').length) {
                $('#plan-search-results').hide();
            }
        });
    }

    function searchPlans(query) {
        var productId = $('#filter-product').val();
        $.ajax({
            url: '/tcms_test_browser/plans/api/search/',
            method: 'GET',
            data: { q: query, product: productId },
            dataType: 'json',
            success: function(data) {
                var $results = $('#plan-search-results');
                $results.empty();

                if (data.plans.length === 0) {
                    $results.html('<div class="list-group-item text-muted">No plans found</div>');
                } else {
                    data.plans.forEach(function(p) {
                        var statusBadge = p.is_active ?
                            '<span class="label label-success">Active</span>' :
                            '<span class="label label-danger">Inactive</span>';
                        $results.append(
                            '<a href="#" class="list-group-item plan-search-item" data-id="' + p.id + '">' +
                                'TP-' + p.id + ': ' + escapeHtml(p.name) +
                                ' <span class="text-muted small">(' + escapeHtml(p.product || '') + ')</span> ' +
                                statusBadge +
                            '</a>'
                        );
                    });

                    $results.find('.plan-search-item').on('click', function(e) {
                        e.preventDefault();
                        var planId = $(this).data('id');
                        $('#plan-search-input').val($(this).text().trim());
                        $results.hide();
                        loadPlanDrillDown(planId);
                    });
                }

                $results.show();
            }
        });
    }

    function loadPlanDrillDown(planId) {
        currentPlanDDId = planId;
        $('#plan-drilldown-placeholder').hide();
        $('#plan-drilldown-content').show();
        $('#pd-plan-name').text('Loading...');

        $.ajax({
            url: '/tcms_test_browser/consolidated/api/plan/' + planId + '/detail/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                renderPlanDrillDown(data);
            },
            error: function() {
                $('#pd-plan-name').text('Error loading plan');
            }
        });
    }

    function renderPlanDrillDown(data) {
        var plan = data.plan;

        // Header
        $('#pd-plan-name').text(plan.name);
        if (plan.is_active) {
            $('#pd-plan-status').text('Active').attr('class', 'label label-success');
        } else {
            $('#pd-plan-status').text('Inactive').attr('class', 'label label-danger');
        }
        $('#pd-product').text(plan.product || 'N/A');
        $('#pd-version').text(plan.version || 'N/A');
        $('#pd-type').text(plan.type || 'N/A');
        $('#pd-author').text(plan.author || 'N/A');

        // Runs table
        var $runsBody = $('#pd-runs-table tbody');
        $runsBody.empty();
        if (data.runs.length > 0) {
            data.runs.forEach(function(r) {
                var barColor = r.completion_pct >= 80 ? '#3f9c35' :
                               r.completion_pct >= 50 ? '#ec7a08' : '#cc0000';
                $runsBody.append(
                    '<tr>' +
                        '<td><a href="/runs/' + r.id + '/" target="_blank">TR-' + r.id + '</a></td>' +
                        '<td>' + escapeHtml(r.summary) + '</td>' +
                        '<td>' + (r.start_date ? new Date(r.start_date).toLocaleDateString() : '') + '</td>' +
                        '<td>' + (r.stop_date ? new Date(r.stop_date).toLocaleDateString() : '<span class="label label-info">In Progress</span>') + '</td>' +
                        '<td>' + r.total_executions + '</td>' +
                        '<td>' + r.passed + '</td>' +
                        '<td><div class="progress" style="margin: 0; min-width: 80px;">' +
                            '<div class="progress-bar" style="width: ' + r.completion_pct + '%; background-color: ' + barColor + ';">' +
                                r.completion_pct + '%' +
                            '</div></div></td>' +
                    '</tr>'
                );
            });
        } else {
            $runsBody.html('<tr><td colspan="7" class="text-muted text-center">No runs</td></tr>');
        }

        // Cases × Runs matrix
        var $matrixHead = $('#pd-matrix-head');
        var $matrixBody = $('#pd-matrix-body');
        $matrixHead.empty();
        $matrixBody.empty();

        if (data.cases.length > 0) {
            // Header row
            var headerHtml = '<tr><th>Case</th><th>Status</th><th>Passed</th><th>Failed</th>';
            data.runs.forEach(function(r) {
                headerHtml += '<th title="' + escapeHtml(r.summary) + '" style="min-width: 50px; text-align: center;">TR-' + r.id + '</th>';
            });
            headerHtml += '</tr>';
            $matrixHead.html(headerHtml);

            // Data rows
            data.cases.forEach(function(c) {
                var rowHtml = '<tr>';
                rowHtml += '<td><a href="/case/' + c.id + '/" target="_blank">TC-' + c.id + ': ' + escapeHtml(c.summary) + '</a></td>';
                rowHtml += '<td>' + escapeHtml(c.status || '') + '</td>';
                rowHtml += '<td class="text-success">' + c.passed + '</td>';
                rowHtml += '<td class="text-danger">' + c.failed + '</td>';

                data.runs.forEach(function(r) {
                    var exec = c.exec_by_run[String(r.id)];
                    if (exec) {
                        var bgColor = exec.color || '#d1d1d1';
                        rowHtml += '<td style="text-align: center; background-color: ' + bgColor + '; color: #fff;" title="' + escapeHtml(exec.status) + '">' +
                            escapeHtml(exec.status).substring(0, 1) + '</td>';
                    } else {
                        rowHtml += '<td style="text-align: center;" class="text-muted">-</td>';
                    }
                });

                rowHtml += '</tr>';
                $matrixBody.append(rowHtml);
            });
        } else {
            $matrixBody.html('<tr><td colspan="4" class="text-muted text-center">No cases</td></tr>');
        }
    }

    // ==========================================
    // Case Drill-Down Tab
    // ==========================================

    function initCaseSearch() {
        var searchTimeout;

        $('#case-search-input').on('input', function() {
            clearTimeout(searchTimeout);
            var query = $(this).val().trim();
            if (query.length >= 2) {
                searchTimeout = setTimeout(function() {
                    searchCases(query);
                }, 300);
            } else {
                $('#case-search-results').hide();
            }
        });

        $('#btn-case-search').on('click', function() {
            var query = $('#case-search-input').val().trim();
            if (query.length >= 2) {
                searchCases(query);
            }
        });

        $(document).on('click', function(e) {
            if (!$(e.target).closest('#case-search-input, #case-search-results').length) {
                $('#case-search-results').hide();
            }
        });
    }

    function searchCases(query) {
        var productId = $('#filter-product').val();
        $.ajax({
            url: '/tcms_test_browser/api/search/',
            method: 'GET',
            data: { q: query, product: productId },
            dataType: 'json',
            success: function(data) {
                var $results = $('#case-search-results');
                $results.empty();

                if (data.testcases.length === 0) {
                    $results.html('<div class="list-group-item text-muted">No cases found</div>');
                } else {
                    data.testcases.forEach(function(tc) {
                        $results.append(
                            '<a href="#" class="list-group-item case-search-item" data-id="' + tc.id + '">' +
                                'TC-' + tc.id + ': ' + escapeHtml(tc.summary) +
                                ' <span class="text-muted small">(' + escapeHtml(tc.product || '') + ')</span>' +
                            '</a>'
                        );
                    });

                    $results.find('.case-search-item').on('click', function(e) {
                        e.preventDefault();
                        var caseId = $(this).data('id');
                        $('#case-search-input').val($(this).text().trim());
                        $results.hide();
                        loadCaseDrillDown(caseId);
                    });
                }

                $results.show();
            }
        });
    }

    function loadCaseDrillDown(caseId) {
        currentCaseDDId = caseId;
        $('#case-drilldown-placeholder').hide();
        $('#case-drilldown-content').show();
        $('#cd-case-summary').text('Loading...');

        $.ajax({
            url: '/tcms_test_browser/consolidated/api/case/' + caseId + '/detail/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                renderCaseDrillDown(data);
            },
            error: function() {
                $('#cd-case-summary').text('Error loading case');
            }
        });
    }

    function renderCaseDrillDown(data) {
        var tc = data.case;

        // Header
        $('#cd-case-id').text(tc.id);
        $('#cd-case-summary').text(tc.summary);
        $('#cd-status').text(tc.status || 'N/A');
        $('#cd-priority').text(tc.priority || 'N/A');
        $('#cd-product').text(tc.product || 'N/A');
        $('#cd-author').text(tc.author || 'N/A');

        // Plans table
        var $plansBody = $('#cd-plans tbody');
        $plansBody.empty();
        if (data.plans.length > 0) {
            data.plans.forEach(function(p) {
                var statusBadge = p.is_active ?
                    '<span class="label label-success">Active</span>' :
                    '<span class="label label-danger">Inactive</span>';
                $plansBody.append(
                    '<tr>' +
                        '<td><a href="/plan/' + p.id + '/" target="_blank">TP-' + p.id + '</a></td>' +
                        '<td>' + escapeHtml(p.name) + '</td>' +
                        '<td>' + statusBadge + '</td>' +
                    '</tr>'
                );
            });
        } else {
            $plansBody.html('<tr><td colspan="3" class="text-muted text-center">Not in any test plan</td></tr>');
        }

        // Executions table
        var $tbody = $('#cd-executions-table tbody');
        $tbody.empty();

        if (data.timeline.length > 0) {
            // Build a run_id -> plan_name map from executions_by_run
            var runPlanMap = {};
            data.executions_by_run.forEach(function(r) {
                runPlanMap[r.run_id] = r.plan_name || '';
            });

            data.timeline.forEach(function(e) {
                var statusStyle = e.status_color ?
                    'background-color: ' + e.status_color + '; color: #fff;' : '';
                $tbody.append(
                    '<tr>' +
                        '<td><a href="/runs/' + e.run_id + '/" target="_blank">TR-' + e.run_id + ': ' + escapeHtml(e.run_summary) + '</a></td>' +
                        '<td>' + escapeHtml(runPlanMap[e.run_id] || '') + '</td>' +
                        '<td><span class="label status-badge" style="' + statusStyle + '">' + escapeHtml(e.status || '') + '</span></td>' +
                        '<td>' + escapeHtml(e.tested_by || '') + '</td>' +
                        '<td>' + (e.stop_date ? new Date(e.stop_date).toLocaleDateString() : '') + '</td>' +
                    '</tr>'
                );
            });
        } else {
            $tbody.html('<tr><td colspan="5" class="text-muted text-center">No executions</td></tr>');
        }
    }

    // ==========================================
    // Drill-Down Exports
    // ==========================================

    function initDrillDownExports() {
        $('.btn-plan-dd-export').on('click', function(e) {
            e.preventDefault();
            if (!currentPlanDDId) return;
            var format = $(this).data('format');
            var url = PLAN_DD_EXPORT_URLS[format];
            if (!url) return;
            window.location.href = url.replace('{id}', currentPlanDDId);
        });

        $('.btn-case-dd-export').on('click', function(e) {
            e.preventDefault();
            if (!currentCaseDDId) return;
            var format = $(this).data('format');
            var url = CASE_DD_EXPORT_URLS[format];
            if (!url) return;
            window.location.href = url.replace('{id}', currentCaseDDId);
        });
    }

    // ==========================================
    // Utilities
    // ==========================================

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})(jQuery);
