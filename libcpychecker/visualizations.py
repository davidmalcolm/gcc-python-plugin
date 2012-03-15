#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

import gcc
from gccutils import CfgPrettyPrinter, get_src_for_loc, check_isinstance

class StatePrettyPrinter(CfgPrettyPrinter):
    """
    Various ways of annotating a CFG with state information
    """
    def state_to_dot_label(self, state):
        result = '<table cellborder="0" border="0" cellspacing="0">\n'
        for key in state.data:
            value = state.data[key]
            result += ('<tr> %s %s </tr>\n'
                       % (self._dot_td(key),
                          self._dot_td(value)))
        result += '</table>\n'
        return result

class TracePrettyPrinter(StatePrettyPrinter):
    """
    Annotate a CFG, showing a specific trace of execution through it
    """
    def __init__(self, cfg, trace):
        self.cfg = cfg
        self.trace = trace

    def extra_items(self):
        # Hook for expansion
        result = ''
        result += ' subgraph cluster_trace {\n'
        result += '  label="Trace";\n'
        for i, state in enumerate(self.trace.states):

            result += ('  state%i [label=<%s>];\n'
                       % (i, self.state_to_dot_label(state)))

            if i > 0:
                result += ' state%i -> state%i;\n' % (i-1, i)
            result += '  state%i -> %s:stmt%i;\n' % (i,
                                                     self.block_id(state.loc.bb),
                                                     state.loc.idx)
        result += ' }\n';
        return result

class StateGraphPrettyPrinter(StatePrettyPrinter):
    """
    Annotate a CFG, showing all possible states as execution proceeds through
    it
    """
    def __init__(self, sg):
        self.sg = sg
        self.name = sg.fun.decl.name
        self.cfg = sg.fun.cfg

    def state_id(self, state):
        return 'state%i' % id(state)

    def state_to_dot_label(self, state, prevstate):
        result = '<table cellborder="0" border="0" cellspacing="0">\n'

        # Show data:
        result += '<tr><td colspan="2"><table border="0" cellborder="1">'
        result += ('<tr> %s %s %s</tr>\n'
                  % (self._dot_td('Expression'),
                     self._dot_td('lvalue'),
                     self._dot_td('rvalue')))
        for key in state.region_for_var:
            region = state.region_for_var[key]
            value = state.value_for_region.get(region, None)

            # Highlight new and changing values:
            is_new_key = True
            is_different_value = False
            if prevstate:
                if key in prevstate.region_for_var:
                    is_new_key = False
                    prevregion = prevstate.region_for_var[key]
                    prevvalue = prevstate.value_for_region.get(prevregion, None)
                    if value != prevvalue:
                        is_different_value = True

            if is_new_key:
                bgcolor = 'green'
                value_bgcolor = 'green'
            else:
                bgcolor = None
                if is_different_value:
                    value_bgcolor = 'green'
                else:
                    value_bgcolor = None

            result += ('<tr> %s %s %s</tr>\n'
                       % (self._dot_td(key, bgcolor=bgcolor),
                          self._dot_td(region, bgcolor=bgcolor),
                          self._dot_td(value, bgcolor=value_bgcolor)))

        # Show any return value:
        if state.return_rvalue:
            result += ('<tr> %s %s %s</tr>\n'
                       % (self._dot_td(''),
                          self._dot_td('Return Value', bgcolor='green'),
                          self._dot_td(state.return_rvalue, bgcolor='green')))
        result += '</table></td></tr>'

        # Show location:
        stmt = state.loc.get_stmt()
        if stmt:
            if stmt.loc:
                result += ('<tr><td>'
                           + self.to_html('%4i ' % stmt.loc.line)
                           + self.code_to_html(get_src_for_loc(stmt.loc))
                           + '<br/>'
                           + (' ' * (5 + stmt.loc.column-1)) + '^'
                           + '</td></tr>\n')
                result += '<tr><td></td>' + self.stmt_to_html(stmt, state.loc.idx) + '</tr>\n'

        result += '</table>\n'
        return result

    def extra_items(self):
        # Hook for expansion
        result = ''
        result += ' subgraph cluster_state_transitions {\n'
        result += '  label="State Transitions";\n'
        result += '  node [shape=box];\n'
        for state in self.sg.states:
            prevstate = self.sg.get_prev_state(state)
            result += ('  %s [label=<%s>];\n'
                       % (self.state_id(state),
                          self.state_to_dot_label(state, prevstate)))

            #result += ('  %s -> %s:stmt%i;\n'
            #           % (self.state_id(state),
            #              self.block_id(state.loc.bb),
            #              state.loc.idx))

        for transition in self.sg.transitions:
            if transition.desc:
                attrliststr = '[label = "%s"]' % self.to_html(transition.desc)
            else:
                attrliststr = ''
            result += ('  %s -> %s %s;\n'
                       % (self.state_id(transition.src),
                          self.state_id(transition.dest),
                          attrliststr))

        result += ' }\n';
        return result

    #def to_dot(self):
    #    result = 'digraph {\n'
    #    result += self.extra_items()
    #    result += '}\n';
    #    return result

class HtmlRenderer:
    """
    Render a function as HTML, possibly with annotations

    Uses pygments to syntax-highlight the code.

    The resulting HTML uses jsplumb to add lines indicating control flow:
      http://code.google.com/p/jsplumb/
    which requires JavaScript and the HTML <canvas> element
    """
    def __init__(self, fun):
        check_isinstance(fun, gcc.Function)
        self.fun = fun

        from pygments.styles import get_style_by_name
        from pygments.formatters import HtmlFormatter

        # Get ready to use Pygments:
        style = get_style_by_name('default')
        self.formatter = HtmlFormatter(classprefix='source_')

        self.trace_idx = 0

    def make_header(self):
        result = '<html>\n'
        result += '  <head>\n'
        result += '    <title>%s</title>\n' % self.fun.decl.name

        # CSS defs, as part of the file:
        result += '''    <style type="text/css">
.unreached-line {
    #margin:1em;
    #border:0.1em dotted #00aa00;

    opacity:1.0;
    filter:alpha(opacity=0);
    #color:black;
}

.reached-line {
    #margin:1em;
    #border:0.1em dotted #00aa00;
    border: 0.1em solid blue;
    font-weight: bold;

    opacity:1.0;
    filter:alpha(opacity=0);
    #color:black;
}

.reached-lineno {
    border: 0.1em solid blue;
    font-weight: bold;
}

pre {
    #line-height:200%
}

._jsPlumb_connector { z-index: -2; }
._jsPlumb_endpoint { z-index: -1; }

.transition {
    #border: 0.1em dotted #ddffdd;
    #padding: 1em;
    border: 0.1em solid #ccc;
    -moz-box-shadow: 2px 2px 2px #ccc;
    -webkit-box-shadow: 2px 2px 2px #ccc;
    box-shadow: 2px 2px 2px #ccc;
    margin-left: 5em;
    font-family: proportional;
    font-style: italic;
    font-size: 90%;
}

.error {
    #border: 0.1em dotted #ddffdd;
    #padding: 1em;
    border: 0.1em solid #cc0000;
    -moz-box-shadow: 2px 2px 2px #cc0000;
    -webkit-box-shadow: 2px 2px 2px #cc0000;
    box-shadow: 2px 2px 2px #cc0000;
    margin-left: 5em;
    color: red;
    font-family: proportional;
    font-weight: bold;
    font-style: italic;
    font-size: 90%;
}

.note {
    #border: 0.1em dotted #ddffdd;
    #padding: 1em;
    border: 0.1em solid #ccc;
    -moz-box-shadow: 2px 2px 2px #ccc;
    -webkit-box-shadow: 2px 2px 2px #ccc;
    box-shadow: 2px 2px 2px #ccc;
    margin-left: 5em;
    font-family: proportional;
    font-weight: bold;
    font-style: italic;
    font-size: 90%;
}

'''
        result += self.formatter.get_style_defs()
        result += '    </style>\n'

        result += '  </head>\n'

        result += '  <body>\n'

        # Add scripts for jsplumb:
        result += '<script type="text/javascript" src="http://explorercanvas.googlecode.com/svn/trunk/excanvas.js"></script>\n'
        result += '<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.0/jquery.min.js"></script>\n'
        result += '<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.13/jquery-ui.min.js"></script>\n'
        result += '<script type="text/javascript" src="http://jsplumb.googlecode.com/files/jquery.jsPlumb-1.2.6-all-min.js"></script>\n'

        return result

    def make_report(self, report):
        result = '<div id="report-%i">\n' % self.trace_idx
        # Heading:
        result += '<table>\n'
        result += '  <tr><td>File:</td> <td><b>%s</b></td></tr>\n' % self.fun.start.file
        result += '  <tr><td>Function:</td> <td><b>%s</b></td></tr>\n' % self.fun.decl.name
        result += '  <tr><td>Error:</td> <td><b>%s</b></td></tr>\n' % report.msg
        result += '</table>\n'

        # Render any trace that we have:
        if report.trace:
            result += self.make_html_for_trace(report, report.trace)
            result += '<hr/>'

        result += '</div>\n'
        return result

    def make_html_for_trace(self, report, trace):
        start_line = self.fun.decl.location.line - 1
        end_line = self.fun.end.line + 1

        # Figure out which lines get executed.
        # (Is this the finest granularity we can measure?)
        reached_lines = set()
        for state in trace.states:
            loc = state.get_gcc_loc_or_none()
            if loc:
                reached_lines.add(loc.line)

        # Render source code:
        srcfile = self.fun.start.file

        # Extract the source code for the function:
        import linecache
        code = ''
        for linenum in range(start_line, end_line):
            code += linecache.getline(srcfile, linenum)

        # Use pygments to convert it all to HTML:
        from pygments import highlight
        from pygments.lexers import CLexer
        html = highlight(code,
                         CLexer(),
                         # FIXME: ^^^ this hardcodes the source language
                         # (e.g. what about C++?)
                         self.formatter)

        # Carve it up by line, adding our own line numbering:
        # It contains some initial content, leading up to a <pre> element
        # Break on it, starting "result" with the initial material:
        html = html.replace('<pre>', '<pre>\n')
        lines = html.splitlines()
        result = lines[0]

        # Generate any notes from the report's annotator (if any):
        notes = []
        annotator = report.get_annotator_for_trace(trace)
        if annotator:
            for trans in trace.transitions:
                notes += annotator.get_notes(trans)

        # The rest contains the actual source lines:
        lines = lines[1:]
        for linenum, line in zip(range(start_line, end_line), lines):
            # Line number:
            if linenum in reached_lines:
                cls = 'reached-lineno'
            else:
                cls = 'lineno'
            result += '<span class="%s">%i</span> ' % (cls, linenum)

            # The body of the line:
            if linenum in reached_lines:
                cls = 'reached-line'
            else:
                cls = 'unreached-line'
            result += '<span id="trace%i-line%i" class="%s">' % (self.trace_idx, linenum, cls)
            result += line
            result += '</span>\n'

            # Add any comments for this line:
            for trans in trace.transitions:
                if trans.desc:
                    src_loc = trans.src.get_gcc_loc_or_none()
                    if src_loc and src_loc.line == linenum:
                        result += '<span class="transition">%s</span>\n' % trans.desc
            # Report the top-level message, if it happens here:
            if report.loc.line == linenum:
                result += '<span class="error">%s</span>\n' % report.msg
            # Add notes attached to the report:
            for note in report.notes:
                if note.loc and note.loc.line == linenum:
                    result += '<span class="note">%s</span>\n' % note.msg
            # Add any notes from the annotator:
            for note in notes:
                if note.loc and note.loc.line == linenum:
                    result += '<span class="transition">%s</span>\n' % note.msg

        result += '</pre></div>\n'
        result += '\n'
        result += '<script type="text/javascript">\n'
        result += '  jsPlumb.bind("ready", function() {\n'
        result += '    /* Set up defaults: */\n'
        result += '    jsPlumb.Defaults.Connector = [ "Bezier", 1 ];\n'
        result += '    jsPlumb.Defaults.Connector = [ "Straight" ];\n'
        result += '    jsPlumb.Defaults.PaintStyle = { strokeStyle:"blue", lineWidth:1 };\n'
        result += '    jsPlumb.Defaults.EndpointStyle = { radius:2, fillStyle:"red" };\n'
        result += '    jsPlumb.Defaults.Anchors =  [ "BottomCenter", "TopCenter" ];\n'
        #result += '    jsPlumb.Defaults.Anchors =  [ "Center", "Center" ];\n'
        result += '\n'
        result += '    /* Add lines: */\n'
        for i, trans in enumerate(trace.transitions):
            if trans.desc:
                src_loc = trans.src.get_gcc_loc_or_none()
                dest_loc = trans.dest.get_gcc_loc_or_none()
                if src_loc and dest_loc and src_loc != dest_loc:
                    result += ("    jsPlumb.connect({source:'trace%i-line%i',\n"
                               "                     target:'trace%i-line%i',\n"
                               "                     label:%r,\n"
                               "                     overlays:[['PlainArrow', { width:10, length:10, location:1.0 }]]\n"
                               "                   });\n"
                               % (self.trace_idx, src_loc.line,
                                  self.trace_idx, dest_loc.line,
                                  ''))#trans.desc))
        result += '  })\n'
        result += '</script>\n'

        self.trace_idx += 1

        return result

    def make_footer(self):
        result = '  </body>\n'
        return result
