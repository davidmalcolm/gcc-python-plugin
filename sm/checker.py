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

import gcc

class Checker:
    # Top-level object representing a .sm file
    def __init__(self, sms):
        self.sms = sms # list of Sm

    def __repr__(self):
        return 'Checker(%r)' % self.sms

    def to_dot(self, name):
        from sm.dot import checker_to_dot
        return checker_to_dot(self, name)

class Sm:
    def __init__(self, name, varclauses, stateclauses):
        self.name = name
        self.varclauses = varclauses
        self.stateclauses = stateclauses

    def __repr__(self):
        return ('Sm(name=%r, varclauses=%r, stateclauses=%r)'
                % (self.name, self.varclauses, self.stateclauses))

    def iter_states(self):
        statenames = set()
        for sc in self.stateclauses:
            for statename in sc.statelist:
                if statename not in statenames:
                    yield statename

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

class Match:
    """
    A match of a pattern
    """
    def __init__(self, pattern, var):
        self.pattern = pattern
        self.var = var

    def __eq__(self, other):
        if isinstance(other, Match):
            return self.pattern == other.pattern and self.var == other.var

    def __hash__(self):
        return hash(self.pattern) ^ hash(self.var)

    def __repr__(self):
        return 'Match(%r, %r)' % (self.pattern, self.var)

    def description(self, ctxt):
        return self.pattern.description(self, ctxt)

class Pattern:
    def iter_matches(self, stmt, edge, ctxt):
        print('self: %r' % self)
        raise NotImplementedError()

    def iter_expedge_matches(self, expedge, ctxt):
        return []

    def description(self, match, ctxt):
        print('self: %r' % self)
        raise NotImplementedError()

    def __hash__(self):
        return id(self)

class AssignmentFromLiteral(Pattern):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
    def __repr__(self):
        return 'AssignmentFromLiteral(lhs=%r, rhs=%r)' % (self.lhs, self.rhs)
    def __str__(self):
        return '%s = %s' % (self.lhs, self.rhs)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.rhs == other.rhs:
                    return True

    def iter_matches(self, stmt, edge, ctxt):
        if isinstance(stmt, gcc.GimpleAssign):
            if ctxt.compare(stmt.lhs, self.lhs):
                if ctxt.compare(stmt.rhs[0], self.rhs):
                    yield Match(self, var=stmt.lhs)

    def description(self, match, ctxt):
        return '%s assigned to %s' % (ctxt.describe(match.var), self.rhs)

class FunctionCall(Pattern):
    def __init__(self, fnname):
        self.fnname = fnname

    def __str__(self):
        return '%s(...)' % self.fnname

    def iter_matches(self, stmt, edge, ctxt):
        if isinstance(stmt, gcc.GimpleCall):
            if isinstance(stmt.fn, gcc.AddrExpr):
                if isinstance(stmt.fn.operand, gcc.FunctionDecl):
                    if stmt.fn.operand.name == self.fnname:
                        # We have a matching function name
                        yield Match(self, None)

class ResultOfFnCall(FunctionCall):
    def __init__(self, lhs, func):
        FunctionCall.__init__(self, func)
        self.lhs = lhs
        self.func = func
    def __repr__(self):
        return 'ResultOfFnCall(lhs=%r, func=%r)' % (self.lhs, self.func)
    def __str__(self):
        return '%s = %s(...)' % (self.lhs, self.func)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.func == other.func:
                    return True

    def iter_matches(self, stmt, edge, ctxt):
        for m in FunctionCall.iter_matches(self, stmt, edge, ctxt):
            if ctxt.compare(stmt.lhs, self.lhs):
                yield Match(self, var=stmt.lhs)

    def description(self, match, ctxt):
        return '%s assigned to the result of %s()' % (ctxt.describe(match.var), self.func)


class ArgOfFnCall(FunctionCall):
    def __init__(self, func, arg):
        FunctionCall.__init__(self, func)
        self.func = func
        self.arg = arg
    def __repr__(self):
        return 'ArgOfFnCall(func=%r, arg=%r)' % (self.func, self.arg)
    def __str__(self):
        return '%s(..., %s, ...)' % (self.fnname, self.arg)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.func == other.func:
                if self.arg == other.arg:
                    return True

    def iter_matches(self, stmt, edge, ctxt):
        for m in FunctionCall.iter_matches(self, stmt, edge, ctxt):
            # FIXME: index hardcoded to 0 for now...
            if ctxt.compare(stmt.args[0], self.arg):
                yield Match(self, var=stmt.args[0])

    def description(self, match, ctxt):
        return '%s passed to %s()' % (ctxt.describe(match.var), self.func)

class Comparison(Pattern):
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
    def __repr__(self):
        return 'Comparison(%r, %r, %r)' % (self.lhs, self.op, self.rhs)
    def __str__(self):
        return '(%s %s %s)' % (self.lhs, self.op, self.rhs)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.op == other.op:
                    if self.rhs == other.rhs:
                        return True

    def iter_matches(self, stmt, edge, ctxt):
        if isinstance(stmt, gcc.GimpleCond):
            if 0:
                print('    %r %r %r %r %r' % (stmt.lhs, stmt.rhs, stmt.exprcode, stmt.true_label, stmt.false_label))
                print('edge: %r' % edge)
                print('edge.true_value: %r' % edge.true_value)
                print('edge.false_value: %r' % edge.false_value)

            # For now, specialcase:
            if self.op == '==':
                exprcode = gcc.EqExpr
                if stmt.exprcode == exprcode:
                    if ctxt.compare(stmt.lhs, self.lhs):
                        if ctxt.compare(stmt.rhs, self.rhs):
                            yield Match(self, stmt.lhs)
            elif self.op == '!=':
                exprcode = gcc.NeExpr
                if stmt.exprcode == exprcode:
                    if ctxt.compare(stmt.lhs, self.lhs):
                        if ctxt.compare(stmt.rhs, self.rhs):
                            yield Match(self, stmt.lhs)
            else:
                raise UnhandledConditional() # FIXME
            """
            if stmt.exprcode == gcc.EqExpr:
                op = '==' if edge.true_value else '!='
            elif stmt.exprcode == gcc.LtExpr:
                op = '<' if edge.true_value else '>='
            elif stmt.exprcode == gcc.LeExpr:
                op = '<=' if edge.true_value else '>'
            """

    def description(self, match, ctxt):
        return '%s compared against %s' % (ctxt.describe(match.var), ctxt.describe(self.rhs))

class VarDereference(Pattern):
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return 'VarDereference(var=%r)' % self.var
    def __str__(self):
        return '*%s' % self.var
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.var == other.var:
                return True
    def iter_matches(self, stmt, edge, ctxt):
        def check_for_match(node, loc):
            if isinstance(node, gcc.MemRef):
                if ctxt.compare(node.operand, self.var):
                    return True
        t = stmt.walk_tree(check_for_match, stmt.loc)
        if t:
            yield Match(self, var=t.operand)

    def description(self, match, ctxt):
        return 'dereference of %s' % ctxt.describe(match.var)

class VarUsage(Pattern):
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return 'VarUsage(var=%r)' % self.var
    def __str__(self):
        return '%s' % self.var
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.var == other.var:
                return True
    def iter_matches(self, stmt, edge, ctxt):
        def check_for_match(node, loc):
            # print('check_for_match(%r, %r)' % (node, loc))
            if ctxt.compare(node, self.var):
                return True
        t = stmt.walk_tree(check_for_match, stmt.loc)
        if t:
            yield Match(self, var=t)

    def description(self, match, ctxt):
        return 'usage of %s' % ctxt.describe(match.var)

class SpecialPattern(Pattern):
    @classmethod
    def make(cls, name):
        if name == 'leaked':
            return LeakedPattern()

        class UnknownSpecialPattern(Exception):
            def __init__(self, name):
                self.name = name
        raise UnknownSpecialPattern(name)

class LeakedPattern(SpecialPattern):
    def iter_matches(self, stmt, edge, ctxt):
        return []

    def iter_expedge_matches(self, expedge, expgraph):
        if expedge.shapechange:
            for srcgccvar in expedge.shapechange.iter_leaks():
                yield Match(self, var=srcgccvar)

    def description(self, match, ctxt):
        return 'leak of %s' % ctxt.describe(match.var)

    def __eq__(self, other):
        if self.__class__ == other.__class__:
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
    def apply(self, mctxt):
        # print('transition %s to %s' % (match.var, outcome.state))
        dststate = self.state
        dstshape, shapevars = mctxt.srcshape._copy()
        dstshape.set_state(mctxt.match.var, dststate)
        dstexpnode = mctxt.expgraph.lazily_add_node(mctxt.dstnode, dstshape)
        expedge = mctxt.expgraph.lazily_add_edge(mctxt.srcexpnode, dstexpnode,
                                                 mctxt.inneredge, mctxt.match, None)

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
    def apply(self, mctxt):
        if mctxt.inneredge.true_value and self.guard:
            self.outcome.apply(mctxt)
        if mctxt.inneredge.false_value and not self.guard:
            self.outcome.apply(mctxt)

class PythonOutcome(Outcome):
    def __init__(self, src):
        self.src = src
    def __repr__(self):
        return 'PythonOutcome(%r)' % (self.src, )
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.src == other.src:
                return True

    def get_src(self):
        # Currently we only support a very limited subset:
        assert self.src[0] == 'error'
        assert self.src[1] == '('
        assert isinstance(self.src[2], str)
        assert self.src[3] == '%'
        assert self.src[4] == 'ptr'
        assert self.src[5] == ')'
        expr = '%s%s%r%s%s%s' % self.src
        if 0:
            print('expr: %r' % expr)
        return expr

    def apply(self, mctxt):
        ctxt = mctxt.expgraph.ctxt
        if 0:
            print('run(): %r' % self)
            print('  match: %r' % match)
            print('  expgraph: %r' % expgraph)
            print('  expnode: %r' % expnode)

        # Get at python code.
        expr = self.get_src()

        # Create environment for execution of the code:
        def error(msg):
            ctxt.add_error(mctxt.expgraph, mctxt.srcexpnode, mctxt.match, msg)
        locals_ = {}
        globals_ = {'error' : error}

        # Bind the name for the variable.
        # For example, when:
        #      state decl any_pointer ptr;
        # has been matched by:
        #      void *q;
        # then we bind the string "ptr" to the string "q"
        assert isinstance(ctxt.sm.varclauses, Var)
        locals_[ctxt.sm.varclauses.name] = mctxt.match.var.name
        if 0:
            print('  globals_: %r' % globals_)
            print('  locals_: %r' % locals_)
        # Now run the code:
        result = eval(expr, globals_, locals_)
