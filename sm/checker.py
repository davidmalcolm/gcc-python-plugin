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

class Checker:
    # Top-level object representing a .sm file
    def __init__(self, sms):
        self.sms = sms # list of Sm

    def __repr__(self):
        return 'Checker(%r)' % self.sms

class Sm:
    def __init__(self, name, varclauses, stateclauses):
        self.name = name
        self.varclauses = varclauses
        self.stateclauses = stateclauses

    def __repr__(self):
        return ('Sm(name=%r, varclauses=%r, stateclauses=%r)'
                % (self.name, self.varclauses, self.stateclauses))

class Var:
    # a matchable thing
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Var(%r)' % self.name

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.name == other.name:
                return True

class StateClause:
    def __init__(self, statelist, patternrulelist):
        self.statelist = statelist
        self.patternrulelist = patternrulelist

    def __repr__(self):
        return 'StateClause(statelist=%r, patternrulelist=%r)' % (self.statelist, self.patternrulelist)

class PatternRule:
    def __init__(self, pattern, outcomes):
        self.pattern = pattern
        self.outcomes = outcomes

    def __repr__(self):
        return 'PatternRule(pattern=%r, outcomes=%r)' % (self.pattern, self.outcomes)

class Pattern:
    pass

class ResultOfFnCall(Pattern):
    def __init__(self, lhs, func):
        self.lhs = lhs
        self.func = func
    def __repr__(self):
        return 'ResultOfFnCall(lhs=%r, func=%r)' % (self.lhs, self.func)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.func == other.func:
                    return True

class ArgOfFnCall(Pattern):
    def __init__(self, func, arg):
        self.func = func
        self.arg = arg
    def __repr__(self):
        return 'ArgOfFnCall(func=%r, arg=%r)' % (self.func, self.arg)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.func == other.func:
                if self.arg == other.arg:
                    return True

class Comparison(Pattern):
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
    def __repr__(self):
        return 'Comparison(%r, %r, %r)' % (self.lhs, self.op, self.rhs)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.op == other.op:
                    if self.rhs == other.rhs:
                        return True

class VarDereference(Pattern):
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return 'VarDereference(var=%r)' % self.var
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.var == other.var:
                return True

class VarUsage(Pattern):
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return 'VarUsage(var=%r)' % self.var
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.var == other.var:
                return True

class Outcome:
    pass

class TransitionTo(Outcome):
    def __init__(self, state):
        self.state = state
    def __repr__(self):
        return 'TransitionTo(state=%r)' % self.state
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.state == other.state:
                return True

class BooleanOutcome(Outcome):
    def __init__(self, guard, outcome):
        self.guard = guard
        self.outcome = outcome
    def __repr__(self):
        return 'BooleanOutcome(guard=%r, outcome=%r)' % (self.guard, self.outcome)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.guard == other.guard:
                if self.outcome == other.outcome:
                    return True

class PythonOutcome(Outcome):
    def __init__(self, src):
        self.src = src
    def __repr__(self):
        return 'PythonOutcome(%r)' % (self.src, )
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.src == other.src:
                return True
