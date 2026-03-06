/*
 * Test Plan Browser JavaScript
 * Handles tree navigation and detail panel updates
 */

(function($) {
    'use strict';

    var currentPlanId = null;
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

        // Click on plan to show details
        $('#tree-view').on('click', '.tree-item[data-type="plan"]', function() {
            var planId = $(this).data('id');
            $('.tree-item').removeClass('active');
            $(this).addClass('active');
            loadPlanDetail(planId);
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

    function loadPlanDetail(planId) {
        currentPlanId = planId;

        $('#detail-placeholder').hide();
        $('#search-results').hide();
        $('#detail-content').show();
        $('#plan-name').text('Loading...');

        $.ajax({
            url: '/tcms_test_browser/plans/api/plan/' + planId + '/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                populateDetail(data);
            },
            error: function() {
                $('#plan-name').text('Error loading test plan');
            }
        });
    }

    function populateDetail(data) {
        // Header
        $('#plan-name').text(data.name);
        $('#plan-id').text(data.id);
        $('#plan-id-link').attr('href', '/plan/' + data.id + '/');
        $('#btn-view-full').attr('href', '/plan/' + data.id + '/');
        $('#btn-edit').attr('href', '/plan/' + data.id + '/edit/');

        // Quick Info
        if (data.is_active) {
            $('#plan-status').text('Active').attr('class', 'label label-success');
        } else {
            $('#plan-status').text('Inactive').attr('class', 'label label-danger');
        }
        $('#plan-type').text(data.type || 'N/A');
        $('#plan-counts').text(data.case_count + ' cases / ' + data.run_count + ' runs');

        // Description Tab
        if (data.text) {
            var textHtml = escapeHtml(data.text)
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.+?)\*/g, '<em>$1</em>');
            $('#plan-text').html(textHtml);
        } else {
            $('#plan-text').html('<em class="text-muted">No description</em>');
        }

        // Info Tab
        $('#plan-product').text(data.product || 'N/A');
        $('#plan-version').text(data.product_version || 'N/A');
        $('#plan-type-info').text(data.type || 'N/A');
        $('#plan-author').text(data.author || 'N/A');
        $('#plan-created').text(data.create_date ? new Date(data.create_date).toLocaleDateString() : 'N/A');

        if (data.extra_link) {
            $('#plan-extra-link').attr('href', data.extra_link).text(data.extra_link);
            $('#plan-extra-link-row').show();
        } else {
            $('#plan-extra-link-row').hide();
        }

        // Related Tab - Cases (table)
        $('#plan-case-count').text('(' + data.case_count + ' total)');
        var $casesBody = $('#plan-cases tbody');
        $casesBody.empty();
        if (data.cases.length > 0) {
            data.cases.forEach(function(c) {
                $casesBody.append(
                    '<tr>' +
                        '<td><a href="/case/' + c.id + '/" target="_blank">TC-' + c.id + '</a></td>' +
                        '<td>' + escapeHtml(c.summary) + '</td>' +
                    '</tr>'
                );
            });
            if (data.case_count > 20) {
                $casesBody.append('<tr><td colspan="2" class="text-muted small">... and ' + (data.case_count - 20) + ' more</td></tr>');
            }
        } else {
            $casesBody.html('<tr><td colspan="2" class="text-muted text-center">No test cases</td></tr>');
        }

        // Related Tab - Runs (table)
        $('#plan-run-count').text('(' + data.run_count + ' total)');
        var $runsBody = $('#plan-runs tbody');
        $runsBody.empty();
        if (data.runs.length > 0) {
            data.runs.forEach(function(r) {
                $runsBody.append(
                    '<tr>' +
                        '<td><a href="/runs/' + r.id + '/" target="_blank">TR-' + r.id + '</a></td>' +
                        '<td>' + escapeHtml(r.summary) + '</td>' +
                    '</tr>'
                );
            });
            if (data.run_count > 20) {
                $runsBody.append('<tr><td colspan="2" class="text-muted small">... and ' + (data.run_count - 20) + ' more</td></tr>');
            }
        } else {
            $runsBody.html('<tr><td colspan="2" class="text-muted text-center">No test runs</td></tr>');
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
            url: '/tcms_test_browser/plans/api/search/',
            method: 'GET',
            data: { q: query, product: productFilter },
            dataType: 'json',
            success: function(data) {
                displaySearchResults(data.plans);
            },
            error: function() {
                alert('Error performing search');
            }
        });
    }

    function displaySearchResults(plans) {
        var $tbody = $('#search-results-table tbody');
        $tbody.empty();

        $('#detail-placeholder').hide();
        $('#detail-content').hide();
        $('#search-results').show();

        if (plans.length === 0) {
            $tbody.html('<tr><td colspan="5" class="text-center text-muted">No results found</td></tr>');
            return;
        }

        plans.forEach(function(p) {
            var statusLabel = p.is_active ?
                '<span class="label label-success">Active</span>' :
                '<span class="label label-danger">Inactive</span>';
            var $row = $(
                '<tr class="clickable-row" data-id="' + p.id + '">' +
                    '<td>TP-' + p.id + '</td>' +
                    '<td>' + escapeHtml(p.name) + '</td>' +
                    '<td>' + escapeHtml(p.product || '') + '</td>' +
                    '<td>' + escapeHtml(p.type || '') + '</td>' +
                    '<td>' + statusLabel + '</td>' +
                '</tr>'
            );
            $tbody.append($row);
        });

        $tbody.find('.clickable-row').on('click', function() {
            var planId = $(this).data('id');
            loadPlanDetail(planId);
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
        csv: '/tcms_test_browser/plans/api/report/',
        excel: '/tcms_test_browser/plans/api/report/excel/',
        docx: '/tcms_test_browser/plans/api/report/docx/',
        pdf: '/tcms_test_browser/plans/api/report/pdf/'
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
            url: '/tcms_test_browser/plans/api/statistics/',
            method: 'GET',
            data: params,
            dataType: 'json',
            success: function(data) {
                $('#stat-total-count').text(data.total);
                renderActiveInactive(data.active_inactive, data.total);

                if (typeof window.c3 === 'undefined') {
                    $('#chart-type, #chart-product').html(
                        '<div class="text-danger small text-center">c3.js not loaded</div>'
                    );
                    return;
                }

                renderDonutChart('#chart-type', data.by_type,
                    ['#0088ce', '#3f9c35', '#ec7a08', '#cc0000', '#703fec']);
                renderBarChart('#chart-product', data.by_product, 'Test Plans');
            },
            error: function() {
                $('#stat-total-count').text('--');
            }
        });
    }

    function renderActiveInactive(activeInactive, total) {
        var active = (activeInactive && activeInactive.active) ? activeInactive.active : 0;
        var inactive = (activeInactive && activeInactive.inactive) ? activeInactive.inactive : 0;

        if (!total || total === 0) {
            $('#active-percent').text('0%');
            $('#active-count').text(0);
            $('#inactive-count').text(0);
            return;
        }

        var activePercent = Math.round(active / total * 100);
        var inactivePercent = 100 - activePercent;

        $('#active-percent').text(activePercent + '%');
        $('#active-bar')
            .css('width', activePercent + '%')
            .attr('aria-valuenow', activePercent)
            .attr('title', active + ' Active');
        $('#inactive-bar')
            .css('width', inactivePercent + '%')
            .attr('aria-valuenow', inactivePercent)
            .attr('title', inactive + ' Inactive');
        $('#active-count').text(active);
        $('#inactive-count').text(inactive);
    }

    function renderDonutChart(selector, data, colors) {
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
            data: { columns: columns, type: 'donut' },
            donut: {
                width: 12,
                label: { show: true, format: function(value) { return value; } }
            },
            color: { pattern: colors || COLORS },
            tooltip: { show: true },
            legend: { show: true, position: 'right' },
            size: { height: 180 }
        });
    }

    function renderBarChart(selector, data, seriesName) {
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

        c3.generate({
            bindto: selector,
            data: { columns: [counts], type: 'bar' },
            axis: {
                x: { categories: categories, type: 'category', tick: { multiline: false, rotate: 30 } },
                y: { tick: { format: function(d) { return (d === Math.floor(d)) ? d : ''; } } }
            },
            color: { pattern: ['#0088ce'] },
            tooltip: { show: true },
            legend: { show: false },
            grid: { y: { show: false } },
            size: { height: 180 }
        });
    }

})(jQuery);
