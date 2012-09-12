import gcc
from libcpychecker.absinterp import Location, get_locations

############################################################################
# Hierarchy of Constraint classes.  Instances are immutable
############################################################################

class Constraint:
    def __and__(self, other):
        return And([self, other])

    def __or__(self, other):
        return Or([self, other])

    def simplify(self, fubar):
        return self

    def delete(self, term):
        # Recursively delete the constraints on the given term
        # For use when handling assignment, to remove the constraints from
        # the old value of the LHS.
        raise NotImplementedError()

    def as_html(self):
        raise NotImplementedError()

class Boolean(Constraint):
    def __init__(self, terms):
        assert isinstance(terms, (set, frozenset, list))
        self.terms = frozenset(terms)

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            if self.terms == other.terms:
                return True

    def __hash__(self):
        return hash(self.terms)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', ' .join(repr(term) for term in self.terms))

    def __str__(self):
        return '(' + (' %s ' % self.name).join(str(term) for term in self.terms) + ')'

    def simplify(self, fubar):
        newterms = set()
        for term in self.terms:
            term = term.simplify(fubar)

            # promote
            #   And(..., And(a, b, c), ....)
            # to:
            #   And(..., a, b, c, ...)
            # and analogously for Or(..., Or(), ...)
            if term.__class__ == self.__class__:
                for innerterm in term.terms:
                    newterms.add(innerterm)
            else:
                # Eliminate redundant
                #    and Top()
                # and
                #    or Bottom()
                # terms:
                if isinstance(term, Top):
                    if isinstance(self, Or):
                        # "or Top()" is always True:
                        return Top()
                elif isinstance(term, Bottom):
                    if isinstance(self, And):
                        # "and Bottom()" is impossible:
                        return Bottom()
                newterms.add(term)

        # Now that we've handled the "always True" and "impossible" case, strip
        # remaining "Top()" and "Bottom()" terms, as long as there are
        # other terms (in which case they are redundant):
        if len(newterms) > 1:
            newterms = {term for term in newterms
                        if not isinstance(term, Top)}
        if len(newterms) > 1:
            newterms = {term for term in newterms
                        if not isinstance(term, Bottom)}

        # If we have just a single term, eliminate this And() or Or() clause
        # around it, just using the term itself:
        if len(newterms) == 1:
            return newterms.pop()

        # Verify that And() clauses are actually possible:
        # This isn't a full solver, but will catch some cases that are
        # impossible
        if isinstance(self, And) and fubar:
            # Gather predicates by LHS:
            # dict of expr -> And() condition affecting that expr:
            exprpreds = {}
            satisfiableterms = set()
            for term in newterms:
                if isinstance(term, Predicate):
                    print(term)
                    # FIXME: only the lhs for now
                    if term.lhs in exprpreds:
                        exprpreds[term.lhs] = exprpreds[term.lhs] & term
                        if isinstance(exprpreds[term.lhs], Bottom):
                            return Bottom()
                    else:
                        exprpreds[term.lhs] = term
                else:
                    satisfiableterms.add(term)
            for expr in exprpreds:
                satisfiableterms.add(exprpreds[expr])
            return And(satisfiableterms).simplify(False)

        return self.__class__(newterms)

    def delete(self, term):
        newterms = set()
        for t in self.terms:
            t = t.delete(term)
            newterms.add(t)
        return self.__class__(newterms).simplify(True)

    def as_html(self):
        return ('(\n' +
                ('\n %s\n' % self.name).join(
                ['\n'.join('  %s' % line
                           for line in term.as_html().splitlines())
                 for term in self.terms]) +
                '\n)')

class And(Boolean):
    name = 'and'

    def __and__(self, other):
        return And(list(self.terms) + [other])

    #def __or__(self, other):
    #    return And([term | other for term in self.terms])

class Or(Boolean):
    name = 'or'

    def __and__(self, other):
        return Or([term & other for term in self.terms])

    def __or__(self, other):
        return Or(list(self.terms) + [other])

class Predicate(Constraint):
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    def __repr__(self):
        return 'Predicate(%r, %r, %r)' % (self.lhs, self.op, self.rhs)

    def __str__(self):
        return '%s %s %s' % (self.lhs, self.op, self.rhs)

    def __eq__(self, other):
        if isinstance(other, Predicate):
            if self.lhs == other.lhs:
                if self.op == other.op:
                    if self.rhs == other.rhs:
                        return True

    def __hash__(self):
        return hash(self.lhs) ^ hash(self.op) ^ hash(self.rhs)

    def __and__(self, other):
        print('%s __and__ %s' % (self, other))
        if isinstance(other, Predicate):
            if self.lhs == other.lhs:
                if isinstance(self.rhs, (int, long)) and isinstance(other.rhs, (int, long)):
                    if self.op == '==' and other.op == '==':
                        # We have (EXPR == valA) AND (EXPR == valB)
                        if self.rhs == other.rhs:
                            # second clause has no effect:
                            raise 'foo'
                            return self
                        else:
                            # impossible:
                            return Bottom()
                    elif self.op == '==' and other.op == '!=':
                        if self.rhs == other.rhs:
                            # impossible:
                            return Bottom()
                        else:
                            # second clause has no effect:
                            raise 'foo'
                            return self
                    elif self.op == '!=' and other.op == '==':
                        if self.rhs == other.rhs:
                            # impossible:
                            raise 'foo'
                            return Bottom()
                        else:
                            # second clause is a better condition:
                            return other
                    elif self.op == '==' and other.op == '<=':
                        if self.rhs <= other.rhs:
                            # second clause is redundant:
                            return self
                        else:
                            # impossible:
                            return Bottom()
                    elif self.op == '==' and other.op == '<':
                        if self.rhs < other.rhs:
                            # second clause is redundant:
                            return self
                        else:
                            # impossible:
                            return Bottom()
                    elif self.op == '==' and other.op == '>=':
                        if self.rhs >= other.rhs:
                            # second clause is redundant:
                            return self
                        else:
                            # impossible:
                            return Bottom()
                    elif self.op == '==' and other.op == '>':
                        if self.rhs > other.rhs:
                            # second clause is redundant:
                            return self
                        else:
                            # impossible:
                            return Bottom()

        return Constraint.__and__(self, other)

    def delete(self, term):
        if self.lhs == term or self.rhs == term:
            return Top()
        return self

    def as_html(self):
        return '%s %s %s' % (self.lhs, self.op, self.rhs)

class IsUnitialized(Constraint):
    def __init__(self, var):
        self.var = var

    def __repr__(self):
        return 'IsUnitialized(%r)' % self.var

    def __str__(self):
        return 'IsUnitialized(%r)' % self.var

class Note(Constraint):
    def __init__(self, msg):
        self.msg = msg

    def __hash__(self):
        return hash(self.msg)

    def __eq__(self, other):
        if isinstance(other, Note):
            if self.msg == other.msg:
                return True

    def __repr__(self):
        return 'Note(%r)' % self.msg

    def __str__(self):
        return repr(self.msg)

    def delete(self, term):
        return self

    def as_html(self):
        return '%s' % self.msg

class Top(Constraint):
    # no constraints, and reachable
    def __repr__(self):
        return 'Top()'

    def __str__(self):
        return 'Top()'

    def __eq__(self, other):
        return isinstance(other, Top)

    def __hash__(self):
        return 1

    def delete(self, term):
        return self

    def as_html(self):
        return 'Top()'

class Bottom(Constraint):
    # no constraints, but not reachable
    def __repr__(self):
        return 'Bottom()'

    def __str__(self):
        return 'Bottom()'

    def __eq__(self, other):
        return isinstance(other, Bottom)

    def __hash__(self):
        return 0

    def delete(self, term):
        return self

    def as_html(self):
        return 'Bottom()'

############################################################################

class DummyExpr:
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'DummyExpr(%r)' % self.text
    def __str__(self):
        return self.text

    def __hash__(self):
        return hash(self.text)

    def __eq__(self, other):
        if isinstance(other, DummyExpr):
            return self.text == other.text

class Solution:
    def __init__(self, fun):
        # a mapping from Location to Constraint
        # i.e. a snapshot of what we know at each location within the function
        self.fun = fun
        self.locations = get_locations(fun)
        self.loc_to_constraint = {loc:Bottom() for loc in self.locations}

        # The initial state is the first block after entry (which has no statements):
        initbb = fun.cfg.entry.succs[0].dest
        initloc = Location(initbb, 0)
        self.loc_to_constraint[initloc] = Top()

        # FIXME: initial state of vars

    def __eq__(self, other):
        if not isinstance(other, Solution):
            return False
        return self.loc_to_constraint == other.loc_to_constraint

    def as_html_tr(self, out, stage, oldsol):
        out.write('<tr>')
        out.write('<td>%s</td>' % stage)
        for loc in self.locations:
            if oldsol:
                oldconstraint = oldsol.loc_to_constraint[loc]
            else:
                oldconstraint = None
            constraint = self.loc_to_constraint[loc]
            if not (constraint == oldconstraint):
                out.write('<td><b><pre>%s</pre></b></td>' % constraint.as_html())
            else:
                out.write('<td><pre>%s</pre></td>' % constraint.as_html())
        out.write('</tr>\n')

    def eval(self, expr):
        print('expr: %r' % expr)
        if isinstance(expr, gcc.VarDecl):
            return expr
        if isinstance(expr, gcc.Constant):
            return expr.constant
        if isinstance(expr, gcc.ArrayRef):
            return expr
        if isinstance(expr, DummyExpr):
            return expr
        if expr is None:
            return None
        raise foo


    def get_constraint_for_edge(self, srcloc, dstloc, edge):
        class NewObj:
            def __repr__(self):
                return 'NewObj()'
            def __str__(self):
                return 'NewObj()'
        class DerefField:
            def __init__(self, ptr, fieldname):
                self.ptr = ptr
                self.fieldname = fieldname
            def __repr__(self):
                return 'DerefField(%r, %r)' % (self.ptr, self.fieldname)
            def __str__(self):
                return '%s->%s' % (self.ptr, self.fieldname)

        stmt = srcloc.get_stmt()
        print('  %s ' % stmt)

        srcconstraint = self.loc_to_constraint[srcloc]

        if isinstance(stmt, gcc.GimpleAssign):
            print('    %r %r %r' % (stmt.lhs, stmt.rhs, stmt.exprcode))
            if stmt.exprcode == gcc.IntegerCst:
                rhs = self.eval(stmt.rhs[0])
            elif stmt.exprcode == gcc.VarDecl:
                rhs = DummyExpr(stmt.rhs[0].name) # FIXME
            elif stmt.exprcode == gcc.PlusExpr:
                rhs = DummyExpr(str(stmt)) # FIXME
            elif stmt.exprcode == gcc.Constructor:
                rhs = DummyExpr(str(stmt)) # FIXME
            else:
                raise UnhandledAssignment()
            lhs = self.eval(stmt.lhs)
            # Remove old value from srcconstraint:
            return srcconstraint.delete(lhs) & Predicate(lhs, '==', rhs)

        elif isinstance(stmt, gcc.GimpleCall):
            print('%r %r %r' % (stmt.lhs, stmt.fn, stmt.args))
            if isinstance(stmt.fn, gcc.AddrExpr):
                if isinstance(stmt.fn.operand, gcc.FunctionDecl):
                    print('stmt.fn.operand.name: %r' % stmt.fn.operand.name)
                    fnname = stmt.fn.operand.name
                    def make_result(message, op, value):
                        note = Note(message)
                        if stmt.lhs:
                            return note & Predicate(self.eval(stmt.lhs), op, value)
                        else:
                            return note

                    def make_success(op, value):
                        return make_result('%s() succeeded' % fnname, op, value)

                    def make_failure(op, value):
                        return make_result('%s() failed' % fnname, op, value)

                    if fnname == 'PyArg_ParseTuple':
                        success = make_success('==', 1)
                        # FIXME: also update the args ^^^
                        failure = make_failure('==', 0)
                        return srcconstraint & (success | failure)
                    elif fnname == 'PyList_New':

                        newobj = NewObj() # FIXME
                        success = make_success('!=', 0)
                        """
                        success = (Note('%s() succeeded' % fnname) &
                                   Predicate(self.eval(stmt.lhs), '!=', 0)
                                   #Predicate(self.eval(stmt.lhs), '==', newobj) &
                                   #Predicate(newobj, '!=', 0) #&
                                   #Predicate(DerefField(newobj, 'ob_refcnt'), '==', 1) & # FIXME
                                   #Predicate(DerefField(newobj, 'ob_type'), '==', 'PyList_Type')
                                   )
                        """
                        failure = make_failure('==', 0)
                        return srcconstraint & (success | failure)
                    elif fnname == 'PyList_Append':
                        # etc
                        success = make_success('==', 0)
                        failure = make_failure('==', -1)
                        return srcconstraint & (success | failure)
                    elif fnname == 'PyLong_FromLong':
                        newobj = NewObj() # FIXME
                        success = make_success('!=', 0)
                        """
                        success = (Note('%s() succeeded' % fnname) &
                                   Predicate(self.eval(stmt.lhs), '!=', 0)
                                   #Predicate(self.eval(stmt.lhs), '==', newobj) &
                                   #Predicate(newobj, '!=', 0) #&
                                   #Predicate(DerefField(newobj, 'ob_refcnt'), '==', 1) & # FIXME
                                   #Predicate(DerefField(newobj, 'ob_type'), '==', 'PyLong_Type')
                                   )
                        """
                        failure = make_failure('==', 0)
                        return srcconstraint & (success | failure)

                    elif fnname == 'random':
                        # FIXME: only listing this one for completeness
                        return srcconstraint & Top() # FIXME: make lhs not be uninitialized
                    else:
                        # Unknown function:

                        # FIXME:
                        raise UnknownFunction()

                        return Top() # FIXME: make lhs not be uninitialized
            raise CantHandlePointerToFunctionYet()
        elif isinstance(stmt, gcc.GimpleCond):
            print('    %r %r %r %r %r' % (stmt.lhs, stmt.rhs, stmt.exprcode, stmt.true_label, stmt.false_label))
            print('edge: %r' % edge)

            if stmt.exprcode == gcc.EqExpr:
                op = '==' if edge.true_value else '!='
            elif stmt.exprcode == gcc.LtExpr:
                op = '<' if edge.true_value else '>='
            elif stmt.exprcode == gcc.LeExpr:
                op = '<=' if edge.true_value else '>'
            else:
                raise UnhandledConditional() # FIXME

            cond = Predicate(self.eval(stmt.lhs), op, self.eval(stmt.rhs))
            return srcconstraint & cond
        elif isinstance(stmt, gcc.GimpleLabel):
            return srcconstraint & Top()
        else:
            raise UnhandledStatementType()
        raise ShouldntGetHere()

class HtmlLog:
    def __init__(self, out, solver):
        self.out = out
        out.write('<table border="1">\n')

        # Write headings:
        out.write('<tr>')
        out.write('<td>Stage</td>')
        for loc in solver.locations:
            out.write('<th>block %i stmt:%i</th>'
                      % (loc.bb.index, loc.idx))
        out.write('</tr>\n')
        out.write('<tr>')
        out.write('<td>Stage</td>')
        for loc in solver.locations:
            out.write('<th>%r</th>' % loc.get_stmt())
        out.write('</tr>\n')
        out.write('<tr>')
        out.write('<td>Stage</td>')
        for loc in solver.locations:
            out.write('<th>%s</th>' % loc.get_stmt())
        out.write('</tr>\n')

class Solver:
    def __init__(self, fun):
        self.fun = fun
        self.locations = get_locations(fun)
        self.solutions = []

    def solve(self):
        # calculate least fixed point
        with open('constraints.html', 'w') as out:
            html = HtmlLog(out, self)
            while True:
                idx = len(self.solutions)
                if self.solutions:
                    oldsol = self.solutions[-1]
                else:
                    oldsol = None
                newsol = Solution(self.fun)
                if oldsol:
                    # FIXME: optimize using a worklist:
                    for loc in self.locations:
                        newval = oldsol.loc_to_constraint[loc]
                        for prevloc, edge in loc.prev_locs():
                            print('  edge from: %s' % prevloc)
                            print('         to: %s' % loc)
                            value = oldsol.get_constraint_for_edge(prevloc, loc, edge)
                            print(' str(value): %s' % value)
                            print('repr(value): %r' % value)
                            newval = newval | value
                            newval = newval.simplify(True)
                            print('  new value: %s' % newval)

                        newsol.loc_to_constraint[loc] = newval
                        # TODO: update based on transfer functions
                self.solutions.append(newsol)
                print(newsol.loc_to_constraint)
                newsol.as_html_tr(out, idx, oldsol)
                if oldsol == newsol:
                    # We've reached a fixed point
                        break

                if len(self.solutions) > 20:
                    # bail out: termination isn't working for some reason
                    raise BailOut()


class ConstraintPass(gcc.GimplePass):
    def __init__(self):
        gcc.GimplePass.__init__(self, 'constraint-pass-gimple')

    def execute(self, fun):
        print(fun)

        if 0:
            # Dump location information
            for loc in get_locations(fun):
                print(loc)
                for prevloc in loc.prev_locs():
                    print('  prev: %s' % prevloc)
                for nextloc in loc.next_locs():
                    print('  next: %s' % nextloc)

        solver = Solver(fun)
        solver.solve()
        #with open('solution.html', 'w') as out:
        #    constraint.dump_as_html(out)

def main():
    gimple_ps = ConstraintPass()

    """
    c1 = IsUnitialized('count')
    print('c1')
    print(c1)
    print(repr(c1))

    c2 = Or([And([Predicate('D1', '!=', 0),
                  Predicate('count', '>=', -0x80000000),
                  Predicate('count', '<', 0x80000000),
                  Note('PyArg_ParseTuple() succeeded')]),
             And([Predicate('D1', '==', 0),
                  IsUnitialized('count'),
                  Note('PyArg_ParseTuple() failed')])
             ])
    print('c2')
    print(c2)
    print(repr(c2))

    c3 = ((Predicate('D1', '!=', 0) &
           Predicate('count', '>=', -0x80000000) &
           Predicate('count', '<', 0x80000000) &
           Note('PyArg_ParseTuple() succeeded')) |
          (Predicate('D1', '==', 0) &
           IsUnitialized('count') &
           Note('PyArg_ParseTuple() failed')))
    print('c3')
    print(c3)
    print(repr(c3))
    """

    if 1:
        # non-SSA version:
        gimple_ps.register_before('*warn_function_return')
    else:
        # SSA version:
        gimple_ps.register_after('ssa')
