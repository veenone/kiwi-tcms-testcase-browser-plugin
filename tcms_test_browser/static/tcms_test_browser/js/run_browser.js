/*
 * Test Run Browser JavaScript
 * Handles tree navigation and detail panel updates
 */

(function($) {
    'use strict';

    var currentRunId = null;
    var checkedIds = {};

    $(document).ready(function() {
        initTreeToggle();
        initSearch();
        initFilterProduct();
        initStatsPanel();
        initSelectionControls();
        loadStatistics();
    });

    function initTreeToggle() {
        // Product node toggle
        $('#tree-view').on('click', '.tree-item[data-type="product"] .tree-toggle', function(e) {
            e.stopPropagation();
            var $item = $(this).closest('.tree-item');
            var $node = $item.closest('.tree-node');
            var $children = $node.find('> .tree-children');
            toggleNode($item, $children);
        });

        // Click on product label to expand
        $('#tree-view').on('click', '.tree-item[data-type="product"]', function(e) {
            if ($(e.target).hasClass('tree-toggle')) return;
            var $node = $(this).closest('.tree-node');
            var $children = $node.find('> .tree-children');
            toggleNode($(this), $children);
        });

        // Plan node toggle
        $('#tree-view').on('click', '.tree-item[data-type="plan"] .tree-toggle', function(e) {
            e.stopPropagation();
            var $item = $(this).closest('.tree-item');
            var $node = $item.closest('.tree-node');
            var $children = $node.find('> .tree-children');
            toggleNode($item, $children);
        });

        // Click on plan label to expand
        $('#tree-view').on('click', '.tree-item[data-type="plan"]', function(e) {
            if ($(e.target).hasClass('tree-toggle')) return;
            var $node = $(this).closest('.tree-node');
            var $children = $node.find('> .tree-children');
            toggleNode($(this), $children);
        });

        // Click on run to show details
        $('#tree-view').on('click', '.tree-item[data-type="run"]', function() {
            var runId = $(this).data('id');
            $('.tree-item').removeClass('active');
            $(this).addClass('active');
            loadRunDetail(runId);
        });
    }

    function toggleNode($item, $children) {
        var isExpanded = $children.is(':visible');
        if (isExpanded) {
            $children.slideUp(200);
        } else {
            $children.slideDown(200);
        }
        updateToggleIcon($item, !isExpanded);
    }

    function updateToggleIcon($item, isExpanded) {
        var $toggle = $item.find('.tree-toggle');
        var $folder = $item.find('.pficon-folder-close, .pficon-folder-open');
        if (isExpanded) {
            $toggle.removeClass('fa-angle-right').addClass('fa-angle-down');
            $folder.removeClass('pficon-folder-close').addClass('pficon-folder-open');
        } else {
            $toggle.removeClass('fa-angle-down').addClass('fa-angle-right');
            $folder.removeClass('pficon-folder-open').addClass('pficon-folder-close');
        }
    }

    function loadRunDetail(runId) {
        currentRunId = runId;

        $('#detail-placeholder').hide();
        $('#search-results').hide();
        $('#detail-content').show();
        $('#run-summary').text('Loading...');

        $.ajax({
            url: '/tcms_test_browser/runs/api/run/' + runId + '/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                populateDetail(data);
            },
            error: function() {
                $('#run-summary').text('Error loading test run');
            }
        });
    }

    function populateDetail(data) {
        // Header
        $('#run-summary').text(data.summary);
        $('#run-id').text(data.id);
        $('#run-id-link').attr('href', '/runs/' + data.id + '/');
        $('#btn-view-full').attr('href', '/runs/' + data.id + '/');

        // Quick Info
        if (data.stop_date) {
            $('#run-status').text('Completed').attr('class', 'label label-success');
        } else {
            $('#run-status').text('In Progress').attr('class', 'label label-info');
        }

        $('#run-plan').text(data.plan_name || 'N/A');
        if (data.plan_id) {
            $('#run-plan-link').attr('href', '/plan/' + data.plan_id + '/');
        }
        $('#run-build').text(data.build || 'N/A');

        // Executions Tab
        var $tbody = $('#executions-body');
        $tbody.empty();

        if (data.executions.length === 0) {
            $tbody.html('<tr><td colspan="5" class="text-center text-muted">No executions</td></tr>');
        } else {
            data.executions.forEach(function(exec) {
                var statusStyle = '';
                if (exec.status_color) {
                    statusStyle = 'background-color: ' + exec.status_color + '; color: #fff;';
                }
                var $row = $(
                    '<tr>' +
                        '<td><a href="/case/' + exec.case_id + '/" target="_blank">TC-' + exec.case_id + '</a></td>' +
                        '<td>' + escapeHtml(exec.case_summary) + '</td>' +
                        '<td><span class="label status-badge" style="' + statusStyle + '">' + escapeHtml(exec.status || '') + '</span></td>' +
                        '<td>' + escapeHtml(exec.tested_by || '') + '</td>' +
                        '<td>' + (exec.stop_date ? new Date(exec.stop_date).toLocaleDateString() : '') + '</td>' +
                    '</tr>'
                );
                $tbody.append($row);
            });
        }

        // Info Tab
        $('#run-product').text(data.product || 'N/A');
        if (data.plan_id) {
            $('#run-plan-info').html('<a href="/plan/' + data.plan_id + '/" target="_blank">' + escapeHtml(data.plan_name || '') + '</a>');
        } else {
            $('#run-plan-info').text('N/A');
        }
        $('#run-build-info').text(data.build || 'N/A');
        $('#run-manager').text(data.manager || 'N/A');
        $('#run-default-tester').text(data.default_tester || 'N/A');
        $('#run-start-date').text(data.start_date ? new Date(data.start_date).toLocaleDateString() : 'N/A');
        $('#run-stop-date').text(data.stop_date ? new Date(data.stop_date).toLocaleDateString() : 'N/A');
        $('#run-planned-start').text(data.planned_start ? new Date(data.planned_start).toLocaleDateString() : 'N/A');
        $('#run-planned-stop').text(data.planned_stop ? new Date(data.planned_stop).toLocaleDateString() : 'N/A');

        // Notes Tab
        if (data.notes) {
            var notesHtml = escapeHtml(data.notes)
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.+?)\*/g, '<em>$1</em>');
            $('#run-notes').html(notesHtml);
        } else {
            $('#run-notes').html('<em class="text-muted">No notes</em>');
        }
    }

    function initSearch() {
        var searchTimeout;

        $('#tree-search').on('input', function() {
            clearTimeout(searchTimeout);
            var query = $(this).val().trim();

            if (query.length >= 2) {
                searchTimeout = setTimeout(function() {
                    performSearch(query);
                }, 300);
            } else if (query.length === 0) {
                $('#search-results').hide();
                $('#detail-placeholder').show();
                $('#detail-content').hide();
            }
        });

        $('#btn-search').on('click', function() {
            var query = $('#tree-search').val().trim();
            if (query.length >= 2) {
                performSearch(query);
            }
        });

        $('#tree-search').on('keypress', function(e) {
            if (e.which === 13) {
                var query = $(this).val().trim();
                if (query.length >= 2) {
                    performSearch(query);
                }
            }
        });
    }

    function performSearch(query) {
        var productFilter = $('#filter-product').val();

        $.ajax({
            url: '/tcms_test_browser/runs/api/search/',
            method: 'GET',
            data: { q: query, product: productFilter },
            dataType: 'json',
            success: function(data) {
                displaySearchResults(data.runs);
            },
            error: function() {
                alert('Error performing search');
            }
        });
    }

    function displaySearchResults(runs) {
        var $tbody = $('#search-results-table tbody');
        $tbody.empty();

        $('#detail-placeholder').hide();
        $('#detail-content').hide();
        $('#search-results').show();

        if (runs.length === 0) {
            $tbody.html('<tr><td colspan="5" class="text-center text-muted">No results found</td></tr>');
            return;
        }

        runs.forEach(function(r) {
            var statusLabel = r.stop_date ?
                '<span class="label label-success">Completed</span>' :
                '<span class="label label-info">In Progress</span>';
            var $row = $(
                '<tr class="clickable-row" data-id="' + r.id + '">' +
                    '<td>TR-' + r.id + '</td>' +
                    '<td>' + escapeHtml(r.summary) + '</td>' +
                    '<td>' + escapeHtml(r.plan || '') + '</td>' +
                    '<td>' + escapeHtml(r.product || '') + '</td>' +
                    '<td>' + statusLabel + '</td>' +
                '</tr>'
            );
            $tbody.append($row);
        });

        $tbody.find('.clickable-row').on('click', function() {
            var runId = $(this).data('id');
            loadRunDetail(runId);
            $('#search-results').hide();
        });
    }

    function initFilterProduct() {
        $('#filter-product').on('change', function() {
            var productId = $(this).val();
            if (productId) {
                $('.product-node').each(function() {
                    if ($(this).data('product-id') == productId) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });
            } else {
                $('.product-node').show();
            }
            loadStatistics();
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Initialize selection controls (checkboxes + select all)
     */
    function initSelectionControls() {
        $('#tree-view').on('click', '.tree-checkbox', function(e) {
            e.stopPropagation();
            var id = $(this).data('id');
            if ($(this).is(':checked')) {
                checkedIds[id] = true;
            } else {
                delete checkedIds[id];
            }
            updateSelectionCount();
        });

        $('#select-all-tree').on('change', function() {
            var isChecked = $(this).is(':checked');
            $('#tree-view .tree-checkbox:visible').each(function() {
                $(this).prop('checked', isChecked);
                var id = $(this).data('id');
                if (isChecked) {
                    checkedIds[id] = true;
                } else {
                    delete checkedIds[id];
                }
            });
            updateSelectionCount();
        });
    }

    function updateSelectionCount() {
        var count = Object.keys(checkedIds).length;
        var $badge = $('#selection-count');
        if (count > 0) {
            $badge.text(count).show();
        } else {
            $badge.hide();
        }
    }

    // ==========================================
    // Statistics Dashboard
    // ==========================================

    var COLORS = ['#0088ce', '#3f9c35', '#ec7a08', '#cc0000', '#703fec', '#39a5dc', '#f0ab00', '#3a9ca6'];

    var EXPORT_URLS = {
        csv: '/tcms_test_browser/runs/api/report/',
        excel: '/tcms_test_browser/runs/api/report/excel/',
        docx: '/tcms_test_browser/runs/api/report/docx/',
        pdf: '/tcms_test_browser/runs/api/report/pdf/'
    };

    function initStatsPanel() {
        $('#btn-toggle-stats').on('click', function() {
            var $body = $('#stats-body');
            var $icon = $(this).find('.fa');
            if ($body.is(':visible')) {
                $body.slideUp(200, function() {
                    $icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
                });
            } else {
                $body.slideDown(200, function() {
                    $icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
                });
            }
        });

        $('.btn-export').on('click', function(e) {
            e.preventDefault();
            var format = $(this).data('format');
            var url = EXPORT_URLS[format];
            if (!url) return;

            var selectedIds = Object.keys(checkedIds);
            if (selectedIds.length > 0) {
                url += '?ids=' + selectedIds.join(',');
            } else {
                var productId = $('#filter-product').val();
                if (productId) {
                    url += '?product=' + encodeURIComponent(productId);
                }
            }
            window.location.href = url;
        });
    }

    function loadStatistics() {
        var productId = $('#filter-product').val();
        var params = {};
        if (productId) {
            params.product = productId;
        }

        $.ajax({
            url: '/tcms_test_browser/runs/api/statistics/',
            method: 'GET',
            data: params,
            dataType: 'json',
            success: function(data) {
                $('#stat-total-count').text(data.total);
                renderCompletion(data.completion, data.total);

                if (typeof window.c3 === 'undefined') {
                    $('#chart-exec-status, #chart-product').html(
                        '<div class="text-danger small text-center">c3.js not loaded</div>'
                    );
                    return;
                }

                renderDonutChart('#chart-exec-status', data.by_exec_status,
                    ['#3f9c35', '#cc0000', '#ec7a08', '#0088ce', '#703fec'], 'exec_status');
                renderBarChart('#chart-product', data.by_product, 'Test Runs', 'product_name');
            },
            error: function() {
                $('#stat-total-count').text('--');
            }
        });
    }

    function renderCompletion(completion, total) {
        var completed = (completion && completion.completed) ? completion.completed : 0;
        var inProgress = (completion && completion.in_progress) ? completion.in_progress : 0;

        if (!total || total === 0) {
            $('#completed-percent').text('0%');
            $('#completed-count').text(0);
            $('#inprogress-count').text(0);
            return;
        }

        var completedPercent = Math.round(completed / total * 100);
        var inProgressPercent = 100 - completedPercent;

        $('#completed-percent').text(completedPercent + '%');
        $('#completed-bar')
            .css('width', completedPercent + '%')
            .attr('aria-valuenow', completedPercent)
            .attr('title', completed + ' Completed');
        $('#inprogress-bar')
            .css('width', inProgressPercent + '%')
            .attr('aria-valuenow', inProgressPercent)
            .attr('title', inProgress + ' In Progress');
        $('#completed-count').text(completed);
        $('#inprogress-count').text(inProgress);
    }

    function renderDonutChart(selector, data, colors, filterType) {
        if (!data || data.length === 0) {
            $(selector).html('<div class="text-muted text-center small">No data</div>');
            return;
        }

        var columns = [];
        for (var i = 0; i < data.length; i++) {
            columns.push([data[i].name, data[i].count]);
        }

        c3.generate({
            bindto: selector,
            data: {
                columns: columns,
                type: 'donut',
                onclick: function(d) {
                    if (filterType) openChartFilterModal(filterType, d.name);
                }
            },
            donut: {
                width: 12,
                label: { show: true, format: function(value) { return value; } }
            },
            color: { pattern: colors || COLORS },
            tooltip: { show: true },
            legend: { show: true, position: 'right' },
            size: { height: 220 },
            padding: { top: 10, right: 10, bottom: 10, left: 10 }
        });
    }

    function renderBarChart(selector, data, seriesName, filterType) {
        if (!data || data.length === 0) {
            $(selector).html('<div class="text-muted text-center small">No data</div>');
            return;
        }

        var categories = [];
        var counts = [seriesName];
        for (var i = 0; i < data.length; i++) {
            categories.push(data[i].name);
            counts.push(data[i].count);
        }

        var chartHeight = Math.max(180, categories.length * 32 + 40);

        c3.generate({
            bindto: selector,
            data: {
                columns: [counts],
                type: 'bar',
                onclick: function(d) {
                    if (filterType) openChartFilterModal(filterType, categories[d.index]);
                }
            },
            axis: {
                rotated: true,
                x: { categories: categories, type: 'category', tick: { multiline: false } },
                y: { tick: { format: function(d) { return (d === Math.floor(d)) ? d : ''; } } }
            },
            color: { pattern: ['#0088ce'] },
            tooltip: { show: true },
            legend: { show: false },
            grid: { y: { show: false } },
            size: { height: chartHeight }
        });
    }

    // ==========================================
    // Chart Click-to-Filter Modal
    // ==========================================

    function openChartFilterModal(filterType, filterValue) {
        var titleMap = {
            'exec_status': 'Test Runs \u2014 Execution Status: ',
            'product_name': 'Test Runs \u2014 Product: '
        };
        $('#chart-filter-modal-title').text((titleMap[filterType] || 'Filtered Results \u2014 ') + filterValue);
        $('#chart-filter-loading').show();
        $('#chart-filter-table').hide();
        $('#chart-filter-empty').hide();
        $('#chart-filter-pagination').empty();
        $('#chart-filter-modal').modal('show');
        loadChartFilterResults(filterType, filterValue, 1);
    }

    function loadChartFilterResults(filterType, filterValue, page) {
        var params = { page: page, page_size: 25 };
        params[filterType] = filterValue;

        var productId = $('#filter-product').val();
        if (productId) {
            params.product = productId;
        }

        $.ajax({
            url: '/tcms_test_browser/runs/api/browse/',
            method: 'GET',
            data: params,
            dataType: 'json',
            success: function(data) {
                $('#chart-filter-loading').hide();
                var $thead = $('#chart-filter-thead');
                var $tbody = $('#chart-filter-tbody');
                $thead.empty();
                $tbody.empty();

                if (data.runs.length === 0) {
                    $('#chart-filter-empty').show();
                    return;
                }

                $('#chart-filter-table').show();
                $thead.html('<th>ID</th><th>Summary</th><th>Product</th><th>Plan</th>');

                data.runs.forEach(function(r) {
                    $tbody.append(
                        '<tr>' +
                            '<td><a href="/runs/' + r.id + '/" target="_blank">TR-' + r.id + '</a></td>' +
                            '<td>' + escapeHtml(r.summary) + '</td>' +
                            '<td>' + escapeHtml(r.product || '') + '</td>' +
                            '<td>' + escapeHtml(r.plan || '') + '</td>' +
                        '</tr>'
                    );
                });

                renderBrowsePagination('#chart-filter-pagination', data.page, data.total_pages, function(pg) {
                    loadChartFilterResults(filterType, filterValue, pg);
                });
            },
            error: function() {
                $('#chart-filter-loading').hide();
                $('#chart-filter-empty').text('Error loading results').show();
            }
        });
    }

    function renderBrowsePagination(selector, currentPage, totalPages, loadFn) {
        var $nav = $(selector);
        $nav.empty();

        if (totalPages <= 1) return;

        var html = '<ul class="pagination pagination-sm" style="margin: 5px 0;">';

        if (currentPage > 1) {
            html += '<li><a href="#" data-page="' + (currentPage - 1) + '">&laquo;</a></li>';
        } else {
            html += '<li class="disabled"><span>&laquo;</span></li>';
        }

        var startPage = Math.max(1, currentPage - 3);
        var endPage = Math.min(totalPages, currentPage + 3);

        if (startPage > 1) {
            html += '<li><a href="#" data-page="1">1</a></li>';
            if (startPage > 2) {
                html += '<li class="disabled"><span>...</span></li>';
            }
        }

        for (var i = startPage; i <= endPage; i++) {
            if (i === currentPage) {
                html += '<li class="active"><span>' + i + '</span></li>';
            } else {
                html += '<li><a href="#" data-page="' + i + '">' + i + '</a></li>';
            }
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += '<li class="disabled"><span>...</span></li>';
            }
            html += '<li><a href="#" data-page="' + totalPages + '">' + totalPages + '</a></li>';
        }

        if (currentPage < totalPages) {
            html += '<li><a href="#" data-page="' + (currentPage + 1) + '">&raquo;</a></li>';
        } else {
            html += '<li class="disabled"><span>&raquo;</span></li>';
        }

        html += '</ul>';
        $nav.html(html);

        $nav.find('a[data-page]').on('click', function(e) {
            e.preventDefault();
            var pg = parseInt($(this).data('page'), 10);
            loadFn(pg);
        });
    }

})($);
