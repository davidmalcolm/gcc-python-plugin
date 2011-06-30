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

from gccutils import CfgPrettyPrinter, get_src_for_loc

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

    def state_to_dot_label(self, state):
        result = '<table cellborder="0" border="0" cellspacing="0">\n'

        # Show data:
        for key in state.data:
            value = state.data[key]
            result += ('<tr> %s %s </tr>\n'
                       % (self._dot_td(key + ' : '),
                          self._dot_td(value)))
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

            result += ('  %s [label=<%s>];\n'
                       % (self.state_id(state),
                          self.state_to_dot_label(state)))

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
