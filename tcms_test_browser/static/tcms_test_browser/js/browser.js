/*
 * Test Case Browser JavaScript
 * Handles tree navigation and detail panel updates
 */

(function($) {
    'use strict';

    var currentTestCaseId = null;
    var loadedCategories = {};
    var checkedIds = {};

    // Initialize on document ready
    $(document).ready(function() {
        initTreeToggle();
        initSearch();
        initFilterProduct();
        initStatsPanel();
        initSelectionControls();
        loadStatistics();
    });

    /**
     * Initialize tree toggle functionality
     */
    function initTreeToggle() {
        // Product node toggle
        $('#tree-view').on('click', '.tree-item[data-type="product"] .tree-toggle', function(e) {
            e.stopPropagation();
            var $item = $(this).closest('.tree-item');
            var $node = $item.closest('.tree-node');
            var $children = $node.find('> .tree-children');

            toggleNode($item, $children);
        });

        // Category node toggle - load test cases on first expand
        $('#tree-view').on('click', '.tree-item[data-type="category"] .tree-toggle', function(e) {
            e.stopPropagation();
            var $item = $(this).closest('.tree-item');
            var $node = $item.closest('.tree-node');
            var $children = $node.find('> .tree-children');
            var categoryId = $item.data('id');

            // Load test cases if not already loaded
            if (!loadedCategories[categoryId]) {
                loadTestCasesForCategory(categoryId, $children, function() {
                    toggleNode($item, $children);
                });
            } else {
                toggleNode($item, $children);
            }
        });

        // Click on category label to show test cases in list
        $('#tree-view').on('click', '.tree-item[data-type="category"]', function(e) {
            if ($(e.target).hasClass('tree-toggle')) return;

            var categoryId = $(this).data('id');
            var $node = $(this).closest('.tree-node');
            var $children = $node.find('> .tree-children');

            // Mark as active
            $('.tree-item').removeClass('active');
            $(this).addClass('active');

            // Expand if not already
            if (!$children.is(':visible')) {
                if (!loadedCategories[categoryId]) {
                    loadTestCasesForCategory(categoryId, $children, function() {
                        $children.slideDown(200);
                        updateToggleIcon($(e.target).closest('.tree-item'), true);
                    });
                } else {
                    $children.slideDown(200);
                    updateToggleIcon($(this), true);
                }
            }
        });

        // Click on test case to show details
        $('#tree-view').on('click', '.tree-item[data-type="testcase"]', function() {
            var testcaseId = $(this).data('id');

            // Mark as active
            $('.tree-item').removeClass('active');
            $(this).addClass('active');

            loadTestCaseDetail(testcaseId);
        });
    }

    /**
     * Toggle node expand/collapse
     */
    function toggleNode($item, $children) {
        var isExpanded = $children.is(':visible');

        if (isExpanded) {
            $children.slideUp(200);
        } else {
            $children.slideDown(200);
        }

        updateToggleIcon($item, !isExpanded);
    }

    /**
     * Update toggle icon based on expanded state
     */
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

    /**
     * Load test cases for a category
     */
    function loadTestCasesForCategory(categoryId, $container, callback) {
        $.ajax({
            url: '/tcms_test_browser/api/category/' + categoryId + '/testcases/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                loadedCategories[categoryId] = true;
                $container.empty();

                if (data.testcases.length === 0) {
                    $container.html('<div class="text-muted" style="padding: 5px 15px;">No test cases</div>');
                } else {
                    data.testcases.forEach(function(tc) {
                        var statusClass = getStatusClass(tc.case_status);
                        var isChecked = checkedIds[tc.id] ? ' checked' : '';
                        var $tcItem = $(
                            '<div class="list-group-item tree-item testcase-item" data-type="testcase" data-id="' + tc.id + '">' +
                                '<input type="checkbox" class="tree-checkbox" data-id="' + tc.id + '" title="Select for export"' + isChecked + '> ' +
                                '<span class="pficon pficon-catalog"></span> ' +
                                '<span class="tree-label">' + escapeHtml(tc.summary) + '</span>' +
                                '<span class="label ' + statusClass + '" style="margin-left: 5px;">' + escapeHtml(tc.case_status || '') + '</span>' +
                            '</div>'
                        );
                        $container.append($tcItem);
                    });
                }

                if (callback) callback();
            },
            error: function() {
                $container.html('<div class="text-danger" style="padding: 5px 15px;">Error loading test cases</div>');
                if (callback) callback();
            }
        });
    }

    /**
     * Load test case detail
     */
    function loadTestCaseDetail(testcaseId) {
        currentTestCaseId = testcaseId;

        // Show loading state
        $('#detail-placeholder').hide();
        $('#search-results').hide();
        $('#detail-content').show();
        $('#tc-summary').text('Loading...');

        $.ajax({
            url: '/tcms_test_browser/api/testcase/' + testcaseId + '/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                populateDetail(data);
            },
            error: function() {
                $('#tc-summary').text('Error loading test case');
            }
        });
    }

    /**
     * Populate detail panel with test case data
     */
    function populateDetail(data) {
        // Header
        $('#tc-summary').text(data.summary);
        $('#tc-id').text(data.id);
        $('#tc-id-link').attr('href', '/case/' + data.id + '/');
        $('#btn-view-full').attr('href', '/case/' + data.id + '/');
        $('#btn-edit').attr('href', '/case/' + data.id + '/edit/');

        // Quick Info
        $('#tc-status').text(data.case_status || 'N/A').attr('class', 'label ' + getStatusClass(data.case_status));
        $('#tc-priority').text(data.priority || 'N/A');
        $('#tc-automated').html(data.is_automated ?
            '<span class="pficon pficon-ok text-success"></span> Yes' :
            '<span class="pficon pficon-error-circle-o text-muted"></span> No'
        );

        // Steps Tab
        if (data.text) {
            // Simple markdown-like rendering
            var textHtml = escapeHtml(data.text)
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.+?)\*/g, '<em>$1</em>');
            $('#tc-text').html(textHtml);
        } else {
            $('#tc-text').html('<em class="text-muted">No steps defined</em>');
        }

        if (data.notes) {
            var notesHtml = escapeHtml(data.notes)
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.+?)\*/g, '<em>$1</em>');
            $('#tc-notes').html(notesHtml);
            $('#tc-notes-section').show();
        } else {
            $('#tc-notes-section').hide();
        }

        // Info Tab
        $('#tc-author').text(data.author || 'N/A');
        $('#tc-default-tester').text(data.default_tester || 'N/A');
        $('#tc-reviewer').text(data.reviewer || 'N/A');
        $('#tc-created').text(data.create_date ? new Date(data.create_date).toLocaleDateString() : 'N/A');
        $('#tc-category').text(data.category || 'N/A');
        $('#tc-setup-duration').text(data.setup_duration || 'N/A');
        $('#tc-testing-duration').text(data.testing_duration || 'N/A');
        $('#tc-script').text(data.script || 'N/A');

        if (data.extra_link) {
            $('#tc-extra-link').attr('href', data.extra_link).text(data.extra_link);
            $('#tc-extra-link-row').show();
        } else {
            $('#tc-extra-link-row').hide();
        }

        // Related Tab
        if (data.components.length > 0) {
            $('#tc-components').html(data.components.map(function(c) {
                return '<span class="label label-info" style="margin-right: 5px;">' + escapeHtml(c) + '</span>';
            }).join(''));
        } else {
            $('#tc-components').html('<em class="text-muted">No components</em>');
        }

        if (data.tags.length > 0) {
            $('#tc-tags').html(data.tags.map(function(t) {
                return '<span class="label label-default" style="margin-right: 5px;">' + escapeHtml(t) + '</span>';
            }).join(''));
        } else {
            $('#tc-tags').html('<em class="text-muted">No tags</em>');
        }

        var $plansBody = $('#tc-plans tbody');
        $plansBody.empty();
        if (data.plans.length > 0) {
            data.plans.forEach(function(p) {
                $plansBody.append(
                    '<tr>' +
                        '<td><a href="/plan/' + p.id + '/" target="_blank">TP-' + p.id + '</a></td>' +
                        '<td>' + escapeHtml(p.name) + '</td>' +
                    '</tr>'
                );
            });
        } else {
            $plansBody.html('<tr><td colspan="2" class="text-muted text-center">Not in any test plan</td></tr>');
        }
    }

    /**
     * Initialize search functionality
     */
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
                // Clear search results
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

    /**
     * Perform search
     */
    function performSearch(query) {
        var productFilter = $('#filter-product').val();

        $.ajax({
            url: '/tcms_test_browser/api/search/',
            method: 'GET',
            data: {
                q: query,
                product: productFilter
            },
            dataType: 'json',
            success: function(data) {
                displaySearchResults(data.testcases);
            },
            error: function() {
                alert('Error performing search');
            }
        });
    }

    /**
     * Display search results
     */
    function displaySearchResults(testcases) {
        var $tbody = $('#search-results-table tbody');
        $tbody.empty();

        $('#detail-placeholder').hide();
        $('#detail-content').hide();
        $('#search-results').show();

        if (testcases.length === 0) {
            $tbody.html('<tr><td colspan="5" class="text-center text-muted">No results found</td></tr>');
            return;
        }

        testcases.forEach(function(tc) {
            var $row = $(
                '<tr class="clickable-row" data-id="' + tc.id + '">' +
                    '<td>TC-' + tc.id + '</td>' +
                    '<td>' + escapeHtml(tc.summary) + '</td>' +
                    '<td>' + escapeHtml(tc.product || '') + '</td>' +
                    '<td>' + escapeHtml(tc.category || '') + '</td>' +
                    '<td><span class="label ' + getStatusClass(tc.case_status) + '">' + escapeHtml(tc.case_status || '') + '</span></td>' +
                '</tr>'
            );
            $tbody.append($row);
        });

        // Click handler for search results
        $tbody.find('.clickable-row').on('click', function() {
            var testcaseId = $(this).data('id');
            loadTestCaseDetail(testcaseId);
            $('#search-results').hide();
        });
    }

    /**
     * Initialize product filter
     */
    function initFilterProduct() {
        $('#filter-product').on('change', function() {
            var productId = $(this).val();

            if (productId) {
                // Hide non-matching products
                $('.product-node').each(function() {
                    if ($(this).data('product-id') == productId) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });
            } else {
                // Show all products
                $('.product-node').show();
            }

            // Reload statistics for the selected product
            loadStatistics();
        });
    }

    /**
     * Get status CSS class
     */
    function getStatusClass(status) {
        if (!status) return 'label-default';

        var statusLower = status.toLowerCase();
        if (statusLower === 'confirmed') return 'label-success';
        if (statusLower === 'proposed') return 'label-info';
        if (statusLower === 'need_update' || statusLower === 'need update') return 'label-warning';
        if (statusLower === 'disabled') return 'label-danger';
        return 'label-default';
    }

    /**
     * Escape HTML to prevent XSS
     */
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
        // Checkbox click — stop propagation so detail doesn't load
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

        // Select All toggle
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
        csv: '/tcms_test_browser/api/report/',
        excel: '/tcms_test_browser/api/report/excel/',
        docx: '/tcms_test_browser/api/report/docx/',
        pdf: '/tcms_test_browser/api/report/pdf/'
    };

    /**
     * Initialize stats panel collapse toggle and export buttons
     */
    function initStatsPanel() {
        // Manual toggle — avoids Bootstrap collapse event issues
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

        // Export dropdown
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

    /**
     * Load statistics from API and render all widgets
     */
    function loadStatistics() {
        var productId = $('#filter-product').val();
        var params = {};
        if (productId) {
            params.product = productId;
        }

        $.ajax({
            url: '/tcms_test_browser/api/statistics/',
            method: 'GET',
            data: params,
            dataType: 'json',
            success: function(data) {
                $('#stat-total-count').text(data.total);
                renderAutomation(data.automation, data.total);

                if (typeof window.c3 === 'undefined') {
                    $('#chart-status, #chart-priority, #chart-product').html(
                        '<div class="text-danger small text-center">c3.js not loaded</div>'
                    );
                    return;
                }

                renderDonutChart('#chart-status', data.by_status,
                    ['#3f9c35', '#39a5dc', '#ec7a08', '#cc0000', '#703fec']);
                renderDonutChart('#chart-priority', data.by_priority,
                    ['#cc0000', '#ec7a08', '#0088ce', '#3f9c35', '#d1d1d1']);
                renderBarChart('#chart-product', data.by_product);
            },
            error: function() {
                $('#stat-total-count').text('--');
            }
        });
    }

    /**
     * Render a donut chart into the given selector
     */
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
            data: {
                columns: columns,
                type: 'donut'
            },
            donut: {
                width: 12,
                label: {
                    show: true,
                    format: function(value) { return value; }
                }
            },
            color: {
                pattern: colors || COLORS
            },
            tooltip: {
                show: true
            },
            legend: {
                show: true,
                position: 'right'
            },
            size: {
                height: 180
            }
        });
    }

    /**
     * Render automation progress bar
     */
    function renderAutomation(automation, total) {
        var automated = (automation && automation.automated) ? automation.automated : 0;
        var manual = (automation && automation.manual) ? automation.manual : 0;

        if (!total || total === 0) {
            $('#automation-percent').text('0%');
            $('#automation-auto-count').text(0);
            $('#automation-manual-count').text(0);
            return;
        }

        var autoPercent = Math.round(automated / total * 100);
        var manualPercent = 100 - autoPercent;

        $('#automation-percent').text(autoPercent + '%');
        $('#automation-bar-auto')
            .css('width', autoPercent + '%')
            .attr('aria-valuenow', autoPercent)
            .attr('title', automated + ' Automated');
        $('#automation-bar-manual')
            .css('width', manualPercent + '%')
            .attr('aria-valuenow', manualPercent)
            .attr('title', manual + ' Manual');
        $('#automation-auto-count').text(automated);
        $('#automation-manual-count').text(manual);
    }

    /**
     * Render a bar chart into the given selector
     */
    function renderBarChart(selector, data) {
        if (!data || data.length === 0) {
            $(selector).html('<div class="text-muted text-center small">No data</div>');
            return;
        }

        var categories = [];
        var counts = ['Test Cases'];

        for (var i = 0; i < data.length; i++) {
            categories.push(data[i].name);
            counts.push(data[i].count);
        }

        c3.generate({
            bindto: selector,
            data: {
                columns: [counts],
                type: 'bar'
            },
            axis: {
                x: {
                    categories: categories,
                    type: 'category',
                    tick: {
                        multiline: false,
                        rotate: 30
                    }
                },
                y: {
                    tick: {
                        format: function(d) { return (d === Math.floor(d)) ? d : ''; }
                    }
                }
            },
            color: {
                pattern: ['#0088ce']
            },
            tooltip: {
                show: true
            },
            legend: {
                show: false
            },
            grid: {
                y: { show: false }
            },
            size: {
                height: 180
            }
        });
    }

})(jQuery);
