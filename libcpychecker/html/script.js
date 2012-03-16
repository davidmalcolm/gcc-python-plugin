$(function() {
    "use strict";

    var $reports = $('#reports > li');
    $reports.each(function() {
        var $report = $(this);

        // Add line numbers to the source code, and create a mapping of line
        // numbers to table rows
        var $source = $report.find('.source table');
        var first_line = parseInt($source.data('first-line'), 10);
        var $lines = $source.find('tr');
        var $line_index = {};
        $lines.each(function(idx) {
            var $line = $(this);
            var lineno = first_line + idx;
            $line.prepend($('<td>', { 'class': 'lineno' }).append(lineno));

            $line_index[lineno] = $line;
        });

        // Figure out the state flow based on the state list: this is a list of
        // lists of line numbers that strictly increase.  If the flow moves
        // backwards, that starts a new subflow
        var $states = $report.find('.states li');
        var source_flow = [];
        var last_line = null;
        $states.each(function() {
            var $state = $(this);
            var lineno = parseInt($state.data('line'), 10);
            var $assoc_line = $line_index[lineno];
            $state.data('line-element', $assoc_line);
            $state.prepend($('<h2>').text(String(lineno)));

            var flow;
            if (! last_line || last_line >= lineno) {
                // Mark commentary that starts a new subflow (but not the
                // first)
                if (source_flow.length) {
                    $state.addClass('new-subflow');
                }

                flow = [];
                source_flow.push(flow);
            }
            else {
                flow = source_flow[source_flow.length - 1];
            }
            flow.push({ 'lineno': lineno, '$state': $state });

            last_line = lineno;
        });

        // Add the flows to the source code table.  Each subflow becomes its
        // own column.  A line actually executed within this subflow gets a
        // td.flow-line; otherwise it gets td.flow-empty.  If there's
        // commentary for a particular line, the cell gets a .flow-dot child as
        // well.
        var started = [];
        $.each($line_index, function(lineno, $row) {
            var $paths = $();
            var $selectables = $();
            $.each(source_flow, function(idx, flow) {
                // Lines mentioned in the flow get dots...
                if (flow.length && flow[0].lineno == lineno) {
                    var $new_cell = $('<td>', { "class": "flow-line" }).html('&#x200b;');
                    $new_cell.append($('<span>', { "class": "flow-dot" }));
                    $paths = $paths.add($new_cell);
                    $selectables = $selectables.add($new_cell).add(flow[0].$state);
                    started[idx] = true;

                    // When hovering either the dotted cell or the associated
                    // state commentary, highlight the dot and the comment and
                    // the row itself
                    var $group = $row.add(flow[0].$state).add($new_cell);
                    $new_cell.add(flow[0].$state).hover(
                        function() { $group.addClass('selected'); },
                        function() { $group.removeClass('selected'); }
                    );

                    flow.shift();
                }
                // Lines between the start and end of a subflow, or before the
                // start of the first subflow, or after the end of the last
                // subflow, get undotted lines
                else if (
                    (idx == 0 && flow.length) ||
                    (idx == source_flow.length - 1 && ! flow.length) ||
                    (started[idx] && flow.length)
                ) {
                    $paths = $paths.add($('<td>', { "class": "flow-line" }).html('&#x200b;'));
                }
                // Anywhere else gets nothing
                else {
                    $paths = $paths.add($('<td>', { "class": "flow-empty" }).html('&#x200b;'));
                }
            });
            $row.prepend($paths);

            // When hovering the row, highlight *all* commentary associated
            // with that line
            if ($selectables.length) {
                $selectables = $selectables.add($row);
                $row.find('td:last-child').hover(
                    function() { $selectables.addClass('selected') },
                    function() { $selectables.removeClass('selected') }
                );
            }
        });
    });
});
