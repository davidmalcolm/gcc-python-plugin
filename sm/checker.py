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

from gccutils.graph import ReturnNode

def indent(text):
    return '\n'.join(['  %s' % line
                      for line in text.splitlines()])

class Checker:
    # Top-level object representing a .sm file
    def __init__(self, sms):
        self.sms = sms # list of Sm

    def __repr__(self):
        return 'Checker(%r)' % self.sms

    def __str__(self):
        return '\n'.join(str(sm) for sm in self.sms)

    def to_dot(self, name):
        from sm.dot import checker_to_dot
        return checker_to_dot(self, name)

class Sm:
    def __init__(self, name, clauses):
        self.name = name
        self.clauses = clauses

    def __str__(self):
        result = 'sm %s {\n' % self.name
        for clause in self.clauses:
            result += indent(str(clause)) + '\n\n'
        result += '}\n'
        return result

    def __repr__(self):
        return ('Sm(name=%r, clauses=%r)'
                % (self.name, self.clauses))

    def iter_states(self):
        statenames = set()
        for sc in self.clauses:
            if isinstance(sc, StateClause):
                for statename in sc.statelist:
                    if statename not in statenames:
                        statenames.add(statename)
                        yield statename

class Clause:
    # top-level item within an sm
    pass

class Decl(Clause):
    # a matchable thing
    def __init__(self, has_state, name):
        self.has_state = has_state
        self.name = name

    def __str__(self):
        return ('%sdecl %s %s;\n'
                % ('state ' if self.has_state else '',
                   self.kind,
                   self.name))

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def make(cls, has_state, declkind, name):
        if declkind == 'any_pointer':
            return AnyPointer(has_state, name)
        elif declkind == 'any_expr':
            return AnyExpr(has_state, name)
        raise UnknownDeclkind(declkind)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.name == other.name:
                return True

    def matched_by(self, gccexpr):
        print(self)
        raise NotImplementedError()

class AnyPointer(Decl):
    kind = 'any_pointer'
    def matched_by(self, gccexpr):
        return isinstance(gccexpr.type, gcc.PointerType)

class AnyExpr(Decl):
    kind = 'any_expr'
    def matched_by(self, gccexpr):
        return True

class NamedPattern(Clause):
    """
    The definition of a named pattern
    """
    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def __str__(self):
        return 'pat %s %s;' % (self.name, self.pattern)

class PythonFragment(Clause):
    """
    A fragment of Python
    """
    def __init__(self, src):
        self.src = src
    def __str__(self):
        return '{{%s}}' % self.src
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.src, )
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.src == other.src:
                return True

    def get_source(self):
        # Get at python code
        lines = self.src.splitlines()
        # Strip leading fully-whitespace lines:
        while lines and (lines[0] == '' or lines[0].isspace()):
            lines = lines[1:]
        def try_to_fix_indent():
            # Locate any source-wide indentation based on indentation of first non-whitespace line:
            indent = len(lines[0]) - len(lines[0].lstrip())
            outdented_lines = []
            for line in lines:
                prefix = line[:indent]
                if not (prefix == '' or prefix.isspace()):
                    # indentation error
                    return lines
                outdented_lines.append(line[indent:])
            return outdented_lines

        lines = try_to_fix_indent()
        return '\n'.join(lines)

class StateClause(Clause):
    def __init__(self, statelist, patternrulelist):
        self.statelist = statelist
        self.patternrulelist = patternrulelist

    def __str__(self):
        result = ('%s:\n'
                  % (', '.join([str(state)
                                for state in self.statelist])))
        prs = '\n| '.join([str(pr)
                            for pr in self.patternrulelist])
        result += indent(prs)
        return result

    def __repr__(self):
        return 'StateClause(statelist=%r, patternrulelist=%r)' % (self.statelist, self.patternrulelist)

class PatternRule:
    def __init__(self, pattern, outcomes):
        self.pattern = pattern
        self.outcomes = outcomes

    def __str__(self):
        result = '%s => ' % self.pattern
        result += ', '.join([str(outcome)
                             for outcome in self.outcomes])
        result += ';'
        return result

    def __repr__(self):
        return 'PatternRule(pattern=%r, outcomes=%r)' % (self.pattern, self.outcomes)

class Match:
    """
    A match of a pattern
    """
    def __init__(self, pattern):
        self.pattern = pattern
        self._dict = {}

    def __eq__(self, other):
        if isinstance(other, Match):
            return self.pattern == other.pattern and self._dict == other._dict

    def __hash__(self):
        return hash(self.pattern)

    def __repr__(self):
        return 'Match(%r, %r)' % (self.pattern, self._dict)

    def description(self, ctxt):
        return self.pattern.description(self, ctxt)

    def match_term(self, ctxt, gccexpr, smexpr):
        """
        Determine whether gccexpr matches smexpr;
        if it does, add it to this Match's dictionary
        """
        if 0:
            ctxt.debug('Match.match_term(self=%r, ctxt=%r, gccexpr=%r, smexpr=%r)'
                       % (self, ctxt, gccexpr, smexpr))
        gccexpr = ctxt.compare(gccexpr, smexpr)
        if gccexpr:
            if isinstance(smexpr, str):
                decl = ctxt.lookup_decl(smexpr)
                if isinstance(gccexpr, gcc.SsaName):
                    gccexpr = gccexpr.var
                self._dict[decl] = gccexpr
            return True

    def describe(self, ctxt, smexpr):
        #print('Match.describe(self=%r, smexpr=%r)' % (self, smexpr))
        if isinstance(smexpr, str):
            decl = ctxt.lookup_decl(smexpr)
            return str(self._dict[decl])
        else:
            return str(smexpr)

    def describe_stateful_smexpr(self, ctxt):
        gccvar = self.get_stateful_gccvar(ctxt)
        return str(gccvar)

    def get_stateful_gccvar(self, ctxt):
        return self._dict[ctxt._stateful_decl]

    def iter_binding(self):
        for decl, gccexpr in self._dict.iteritems():
            yield (decl, gccexpr)

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

class Assignment(Pattern):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
    def __repr__(self):
        return 'Assignment(lhs=%r, rhs=%r)' % (self.lhs, self.rhs)
    def __str__(self):
        return '{ %s = %s }' % (self.lhs, self.rhs)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.rhs == other.rhs:
                    return True

    def iter_matches(self, stmt, edge, ctxt):
        if isinstance(stmt, gcc.GimpleAssign):
            if len(stmt.rhs) == 1:
                m = Match(self)
                if m.match_term(ctxt, stmt.lhs, self.lhs):
                    if m.match_term(ctxt, stmt.rhs[0], self.rhs):
                        yield m

    def description(self, match, ctxt):
        return ('%s assigned to %s'
                % (match.describe(ctxt, self.lhs), self.rhs))

class FunctionCall(Pattern):
    def __init__(self, fnname, args):
        self.fnname = fnname
        self.args = args

    def __str__(self):
        return '{ %s(...) }' % self.fnname

    def iter_matches(self, stmt, edge, ctxt):
        if isinstance(stmt, gcc.GimpleCall):
            if isinstance(stmt.fn, gcc.AddrExpr):
                if isinstance(stmt.fn.operand, gcc.FunctionDecl):
                    if stmt.fn.operand.name == self.fnname:
                        # We have a matching function name:
                        m = Match(self)
                        def matches_args():
                            for i, arg in enumerate(self.args):
                                if not m.match_term(ctxt, stmt.args[i], arg):
                                    if 0:
                                        print('arg match failed on: %i %s %s'
                                              % (i, arg, stmt.args[i]))
                                    return False
                            return True
                        if matches_args():
                            yield m

class ResultOfFnCall(FunctionCall):
    def __init__(self, lhs, fnname, args):
        FunctionCall.__init__(self, fnname, args)
        self.lhs = lhs

    def __repr__(self):
        return 'ResultOfFnCall(lhs=%r, fnname=%r, args=%r)' % (self.lhs, self.fnname, self.args)
    def __str__(self):
        return ('{ %s = %s(%s) }'
                % (self.lhs,
                   self.fnname,
                   ', '.join([str(arg) for arg in self.args])))
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.lhs == other.lhs:
                if self.fnname == other.fnname:
                    if self.args == other.args:
                        return True

    def iter_matches(self, stmt, edge, ctxt):
        for m in FunctionCall.iter_matches(self, stmt, edge, ctxt):
            if m.match_term(ctxt, stmt.lhs, self.lhs):
                yield m

    def description(self, match, ctxt):
        return ('%s assigned to the result of %s(%s)'
                % (match.describe(ctxt, self.lhs), self.fnname,
                   ', '.join([match.describe(ctxt, arg)
                              for arg in self.args])))


class ArgsOfFnCall(FunctionCall):
    def __repr__(self):
        return 'ArgsOfFnCall(fnname=%r, args=%r)' % (self.fnname, self.args)
    def __str__(self):
        return '{ %s(%s) } ' % (self.fnname,
                                ', '.join([str(arg)
                                           for arg in self.args]))
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.fnname == other.fnname:
                if self.args == other.args:
                    return True

    def description(self, match, ctxt):
        return ('%s passed to %s()'
                % (match.get_stateful_gccvar(ctxt), self.fnname))

class Comparison(Pattern):
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
    def __repr__(self):
        return 'Comparison(%r, %r, %r)' % (self.lhs, self.op, self.rhs)
    def __str__(self):
        return '{ %s %s %s }' % (self.lhs, self.op, self.rhs)
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
            codes_for_ops = {'==' : gcc.EqExpr,
                             '!=' : gcc.NeExpr,
                             '<'  : gcc.LtExpr,
                             '<=' : gcc.LeExpr,
                             '>'  : gcc.GtExpr,
                             '>=' : gcc.GeExpr}
            exprcode = codes_for_ops[self.op]
            if stmt.exprcode == exprcode:
                m = Match(self)
                if m.match_term(ctxt, stmt.lhs, self.lhs):
                    if m.match_term(ctxt, stmt.rhs, self.rhs):
                        yield m

    def description(self, match, ctxt):
        return ('%s compared against %s'
                % (match.describe(ctxt, self.lhs),
                   match.describe(ctxt, self.rhs)))

class VarDereference(Pattern):
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return 'VarDereference(var=%r)' % self.var
    def __str__(self):
        return '{ *%s }' % self.var
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.var == other.var:
                return True
    def iter_matches(self, stmt, edge, ctxt):
        def check_for_match(node, loc):
            if isinstance(node, gcc.MemRef):
                if ctxt.compare(node.operand, self.var):
                    return True
        # We don't care about the args during return-handling:
        if isinstance(edge.srcnode, ReturnNode):
            return
        t = stmt.walk_tree(check_for_match, stmt.loc)
        if t:
            m = Match(self)
            m.match_term(ctxt, t.operand, self.var)
            yield m

    def description(self, match, ctxt):
        return ('dereference of %s'
                % (match.describe(ctxt, self.var)))

class ArrayLookup(Pattern):
    def __init__(self, array, index):
        self.array = array
        self.index = index
    def __repr__(self):
        return 'ArrayLookup(array=%r, index=%r)' % (self.array, self.index)
    def __str__(self):
        return '{ %s[%s] }' % (self.array, self.index)
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.array == other.array:
                if self.index == other.index:
                    return True
    def iter_matches(self, stmt, edge, ctxt):
        def check_for_match(node, loc):
            if isinstance(node, gcc.ArrayRef):
                return True
        t = stmt.walk_tree(check_for_match, stmt.loc)
        if t:
            m = Match(self)
            if m.match_term(ctxt, t.array, self.array):
                if m.match_term(ctxt, t.index, self.index):
                    yield m

    def description(self, match, ctxt):
        return ('%s[%s]'
                % (match.describe(ctxt, self.array),
                   match.describe(ctxt, self.index)))

class VarUsage(Pattern):
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return 'VarUsage(var=%r)' % self.var
    def __str__(self):
        return '{ %s }' % self.var
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.var == other.var:
                return True
    def iter_matches(self, stmt, edge, ctxt):
        def check_for_match(node, loc):
            # print('check_for_match(%r, %r)' % (node, loc))
            if isinstance(node, (gcc.VarDecl, gcc.ParmDecl, gcc.SsaName)):
                if ctxt.compare(node, self.var):
                    return True
        # We don't care about the args during return-handling:
        if isinstance(edge.srcnode, ReturnNode):
            return
        t = stmt.walk_tree(check_for_match, stmt.loc)
        if t:
            m = Match(self)
            m.match_term(ctxt, t, self.var)
            yield m

    def description(self, match, ctxt):
        return ('usage of %s' % match.describe(self.rhs))

class NamedPatternReference(Pattern):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def iter_matches(self, stmt, edge, ctxt):
        namedpattern = ctxt.lookup_pattern(self.name)
        return namedpattern.pattern.iter_matches(stmt, edge, ctxt)

class SpecialPattern(Pattern):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '$%s$' % self.name

    @classmethod
    def make(cls, name):
        if name == 'leaked':
            return LeakedPattern(name)

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
                m = Match(self)
                m._dict[expgraph.ctxt._stateful_decl]=srcgccvar
                yield m

    def description(self, match, ctxt):
        return 'leak of %s' % match.get_stateful_gccvar(ctxt)

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return True

class OrPattern(Pattern):
    """
    A compound pattern which matches if any of its component patterns match
    """
    def __init__(self, *patterns):
        self.patterns = patterns
        # Fold away:
        #    OrPattern(pat1, OrPattern(pat2, OrPattern(pat3, ...)))
        # to:
        #    OrPattern(pat1, pat2, pat3, ...)
        if isinstance(self.patterns[-1], OrPattern):
            self.patterns = self.patterns[:-1] + self.patterns[-1].patterns

    def __repr__(self):
        return 'OrPattern(patterns=%r)' % (self.patterns,)

    def __str__(self):
        return ' | '.join([str(pat)
                           for pat in self.patterns])

    def iter_matches(self, stmt, edge, ctxt):
        for pattern in self.patterns:
            for match in pattern.iter_matches(stmt, edge, ctxt):
                yield match

class Outcome:
    pass

class TransitionTo(Outcome):
    def __init__(self, statename):
        self.statename = statename
    def __str__(self):
        return str(self.statename)
    def __repr__(self):
        return 'TransitionTo(statename=%r)' % self.statename
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.statename == other.statename:
                return True
    def apply(self, mctxt):
        # print('transition %s to %s' % (match.var, outcome.state))
        from sm.solver import State
        dststate = State(self.statename)
        dstshape, shapevars = mctxt.srcshape._copy()
        dstshape.set_state(mctxt.get_stateful_gccvar(), dststate)
        dstexpnode = mctxt.expgraph.lazily_add_node(mctxt.dstnode, dstshape)
        expedge = mctxt.expgraph.lazily_add_edge(mctxt.srcexpnode, dstexpnode,
                                                 mctxt.inneredge, mctxt.match, None)

    def iter_reachable_statenames(self):
        yield self.statename

class BooleanOutcome(Outcome):
    def __init__(self, guard, outcome):
        self.guard = guard
        self.outcome = outcome
    def __str__(self):
        return ('%s=%s' % ('true' if self.guard else 'false',
                           self.outcome))
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

    def iter_reachable_statenames(self):
        for statename in self.outcome.iter_reachable_statenames():
            yield statename

class PythonOutcome(Outcome, PythonFragment):
    def apply(self, mctxt):
        ctxt = mctxt.expgraph.ctxt
        if 0:
            print('run(): %r' % self)
            print('  match: %r' % match)
            print('  expgraph: %r' % expgraph)
            print('  expnode: %r' % expnode)

        filename = ctxt.ch.filename
        if not filename:
            filename = '<string>'
        expr = self.get_source()
        code = compile(expr, filename, 'exec')
        # FIXME: the filename of the .sm file is correct, but the line
        # numbers will be wrong

        # Create environment for execution of the code:
        def error(msg):
            ctxt.add_error(mctxt.expgraph, mctxt.srcexpnode, mctxt.match, msg)
        def set_state(name, **kwargs):
            ctxt.set_state(mctxt, name, **kwargs)

        globals_ = {'error' : error,
                    'set_state' : set_state,
                    'state': mctxt.srcstate}
        ctxt.python_globals.update(globals_)

        # Bind the names for the matched Decls
        # For example, when:
        #      state decl any_pointer ptr;
        # has been matched by:
        #      void *q;
        # then we bind the string "ptr" to the gcc.VarDecl for q
        # (which has str() == 'q')
        locals_ = {}
        for decl, value in mctxt.match.iter_binding():
            locals_[decl.name] = value
        ctxt.python_locals.update(locals_)

        if 0:
            print('  globals_: %r' % globals_)
            print('  locals_: %r' % locals_)
        # Now run the code:
        result = eval(code, ctxt.python_globals, ctxt.python_locals)

        # Clear the binding:
        for name in locals_:
            del ctxt.python_locals[name]

    def iter_reachable_statenames(self):
        return []
