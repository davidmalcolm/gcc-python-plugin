#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
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

from gccutils.dot import to_html

from sm.checker import TransitionTo, BooleanOutcome, PythonOutcome, \
    StateClause

def checker_to_dot(checker, name):
    result = 'digraph %s {\n' % name
    for sm in checker.sms:
        result += sm_to_dot(sm)
    result += '}\n'
    return result

def statename_to_dot(statename):
    return statename.replace('.', '_')

def pattern_to_dot(pattern):
    return str(pattern)

def python_to_dot(outcome):
    return to_html(outcome.src)

def sm_to_dot(sm):
    result = '  subgraph %s {\n' % sm.name
    for state in sm.iter_states():
        result += '    %s [label=<%s>];\n' % (statename_to_dot(state), state)
    result += '\n'
    for sc in sm.clauses:
        if not isinstance(sc, StateClause):
            continue
        for state in sc.statelist:
            for pr in sc.patternrulelist:
                for outcome in pr.outcomes:
                    def make_edge(src, dst, label):
                        return '    %s -> %s [label=<%s>];\n' % (src, dst, label)
                    def make_label(condition, guardtext, actiontext):
                        if guardtext:
                            guardedtext = '%s %s' % (condition, guardtext)
                        else:
                            guardedtext = str(condition)
                        if actiontext:
                            return '%s: %s' % (guardedtext, actiontext)
                        else:
                            return guardedtext
                    def edge_for_outcome(outcome, guardtext):
                        if isinstance(outcome, TransitionTo):
                            return make_edge(statename_to_dot(state),
                                             statename_to_dot(outcome.statename),
                                             make_label(pattern_to_dot(pr.pattern),
                                                        guardtext,
                                                        ''))
                        elif isinstance(outcome, BooleanOutcome):
                            return edge_for_outcome(outcome.outcome,
                                                    'is %s' % outcome.guard)
                        elif isinstance(outcome, PythonOutcome):
                            return make_edge(statename_to_dot(state),
                                             statename_to_dot(state),
                                             make_label(pattern_to_dot(pr.pattern),
                                                        guardtext,
                                                        python_to_dot(outcome)))
                        else:
                            print(outcome)
                            raise UnknownOutcome(outcome)
                    result += edge_for_outcome(outcome, '')
    result += '  }\n'
    return result
