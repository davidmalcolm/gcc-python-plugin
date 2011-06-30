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

# Attempt to check that C code is implementing CPython's reference-counting
# rules.  See:
#   http://docs.python.org/c-api/intro.html#reference-counts
# for a description of how such code is meant to be written

import sys
import gcc

from gccutils import cfg_to_dot, invoke_dot, get_src_for_loc

from absinterp import *
from PyArg_ParseTuple import log

def stmt_is_assignment_to_count(stmt):
    if hasattr(stmt, 'lhs'):
        if stmt.lhs:
            if isinstance(stmt.lhs, gcc.ComponentRef):
                # print 'stmt.lhs.target: %s' % stmt.lhs.target
                # print 'stmt.lhs.target.type: %s' % stmt.lhs.target.type
                # (presumably we need to filter these to structs that are
                # PyObject, or subclasses)
                if stmt.lhs.field.name == 'ob_refcnt':
                    return True

def type_is_pyobjptr(t):
    assert t is None or isinstance(t, gcc.Type)
    if str(t) == 'struct PyObject *':
        return True

def stmt_is_assignment_to_objptr(stmt):
    if hasattr(stmt, 'lhs'):
        if stmt.lhs:
            if type_is_pyobjptr(stmt.lhs.type):
                return True

def stmt_is_return_of_objptr(stmt):
    if isinstance(stmt, gcc.GimpleReturn):
        if stmt.retval:
            if type_is_pyobjptr(stmt.retval.type):
                return True

class MyState(State):
    def __init__(self, loc, data, owned_refs, resources):
        State.__init__(self, loc, data)
        self.owned_refs = owned_refs
        self.resources = resources

    def copy(self):
        return self.__class__(self.loc, self.data.copy(), self.owned_refs[:],
                              self.resources.copy())

    def _extra(self):
        return ' %s' % self.owned_refs

    def acquire(self, resource):
        self.resources.acquire(resource)

    def release(self, resource):
        self.resources.release(resource)

    def make_assignment(self, key, value, desc, additional_ptr=None):
        if desc:
            assert isinstance(desc, str)
        transition = State.make_assignment(self, key, value, desc)
        if additional_ptr:
            transition.dest.owned_refs.append(additional_ptr)
        return transition

    def get_transitions(self, oldstate):
        # Return a list of Transition instances, based on input State
        stmt = self.loc.get_stmt()
        if stmt:
            return self._get_transitions_for_stmt(stmt, oldstate)
        else:
            result = []
            for loc in self.loc.next_locs():
                newstate = self.copy()
                newstate.loc = loc
                result.append(Transition(self, newstate, ''))
            log('result: %s' % result)
            return result

    def _get_transitions_for_stmt(self, stmt, oldstate):
        log('_get_transitions_for_stmt: %r %s' % (stmt, stmt), 2)
        log('dir(stmt): %s' % dir(stmt), 3)
        if isinstance(stmt, gcc.GimpleCall):
            return self._get_transitions_for_GimpleCall(stmt)
        elif isinstance(stmt, (gcc.GimpleDebug, gcc.GimpleLabel)):
            return [self.use_next_loc()]
        elif isinstance(stmt, gcc.GimpleCond):
            return self._get_transitions_for_GimpleCond(stmt)
        elif isinstance(stmt, gcc.GimplePhi):
            return self._get_transitions_for_GimplePhi(stmt, oldstate)
        elif isinstance(stmt, gcc.GimpleReturn):
            return []
        elif isinstance(stmt, gcc.GimpleAssign):
            return self._get_transitions_for_GimpleAssign(stmt)
        else:
            raise "foo"

    def eval_expr(self, expr):
        if isinstance(expr, gcc.IntegerCst):
            return expr.constant
        if isinstance(expr, gcc.VarDecl):
            if expr.name in self.data:
                return self.data[expr.name]
            else:
                return UnknownValue(expr.type, None)
        if isinstance(expr, gcc.AddrExpr):
            #log(dir(expr))
            #log(expr.operand)
            # Handle Py_None, which is a #define of (&_Py_NoneStruct)
            if isinstance(expr.operand, gcc.VarDecl):
                if expr.operand.name == '_Py_NoneStruct':
                    # FIXME: do we need a stmt?
                    return PtrToGlobal(1, None, expr.operand.name)
        if expr is None:
            return None
        return UnknownValue(expr.type, None) # FIXME

    def _get_transitions_for_GimpleCall(self, stmt):
        log('stmt.lhs: %s %r' % (stmt.lhs, stmt.lhs), 3)
        log('stmt.fn: %s %r' % (stmt.fn, stmt.fn), 3)
        log('dir(stmt.fn): %s' % dir(stmt.fn), 4)
        log('stmt.fn.operand: %s' % stmt.fn.operand, 4)
        returntype = stmt.fn.type.dereference.type
        log('returntype: %s' % returntype)
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            log('dir(stmt.fn.operand): %s' % dir(stmt.fn.operand), 4)
            log('stmt.fn.operand.name: %r' % stmt.fn.operand.name, 4)
            fnname = stmt.fn.operand.name
            # Function returning new references:
            if fnname in ('PyList_New', 'PyLong_FromLong'):
                nonnull = NonNullPtrValue(1, stmt)
                return [self.make_assignment(stmt.lhs, nonnull, '%s() succeeded' % fnname, nonnull),
                        self.make_assignment(stmt.lhs, NullPtrValue(), '%s() failed' % fnname)]
            # Function returning borrowed references:
            elif fnname in ('Py_InitModule4_64',):
                return [self.make_assignment(stmt.lhs, NonNullPtrValue(1, stmt)),
                        self.make_assignment(stmt.lhs, NullPtrValue())]
            #elif fnname in ('PyList_SetItem'):
            #    pass
            else:
                from libcpychecker.c_stdio import c_stdio_functions, handle_c_stdio_function

                if fnname in c_stdio_functions:
                    return handle_c_stdio_function(self, fnname, stmt)

                # Unknown function:
                log('Invocation of unknown function: %r' % fnname)
                return [self.make_assignment(stmt.lhs,
                                             UnknownValue(returntype, stmt),
                                             None)]

        log('stmt.args: %s %r' % (stmt.args, stmt.args), 3)
        for i, arg in enumerate(stmt.args):
            log('args[%i]: %s %r' % (i, arg, arg), 4)

    def _get_transitions_for_GimpleCond(self, stmt):
        def make_transition_for_true(stmt):
            e = true_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = True
            return Transition(self, nextstate, 'taking True path')

        def make_transition_for_false(stmt):
            e = false_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = False
            return Transition(self, nextstate, 'taking False path')

        log('stmt.exprcode: %s' % stmt.exprcode, 4)
        log('stmt.exprtype: %s' % stmt.exprtype, 4)
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs), 4)
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs), 4)
        log('dir(stmt.lhs): %s' % dir(stmt.lhs), 5)
        log('dir(stmt.rhs): %s' % dir(stmt.rhs), 5)
        boolval = self.eval_condition(stmt)
        if boolval is True:
            log('taking True edge', 2)
            nextstate = make_transition_for_true(stmt)
            return [nextstate]
        elif boolval is False:
            log('taking False edge', 2)
            nextstate = make_transition_for_false(stmt)
            return [nextstate]
        else:
            assert isinstance(boolval, UnknownValue)
            # We don't have enough information; both branches are possible:
            return [make_transition_for_true(stmt),
                    make_transition_for_false(stmt)]

    def _get_transitions_for_GimplePhi(self, stmt, oldstate):
        log('stmt: %s' % stmt)
        log('stmt.lhs: %s' % stmt.lhs)
        log('stmt.args: %s' % stmt.args)
        # Choose the correct new value, based on the edge we came in on
        for expr, edge in stmt.args:
            if edge.src == oldstate.loc.bb:
                # Update the LHS appropriately:
                next = self.use_next_loc()
                next.data[str(stmt.lhs)] = self.eval_expr(expr)
                return [next]
        raise AnalysisError('incoming edge not found')

    def eval_condition(self, stmt):
        log('eval_condition: %s' % stmt)
        lhs = self.eval_expr(stmt.lhs)
        rhs = self.eval_expr(stmt.rhs)
        log('eval of lhs: %r' % lhs)
        log('eval of rhs: %r' % rhs)
        log('stmt.exprcode: %r' % stmt.exprcode)
        if stmt.exprcode == gcc.EqExpr:
            if isinstance(lhs, NonNullPtrValue) and rhs == 0:
                return False
            if isinstance(lhs, NullPtrValue) and rhs == 0:
                return True
        log('got here')
        return UnknownValue(None, stmt)

    def _get_transitions_for_GimpleAssign(self, stmt):
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs))
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs))

        nextstate = self.use_next_loc()
        if isinstance(stmt.lhs, gcc.MemRef):
            value = self.eval_expr(stmt.rhs[0])
            log('value: %s %r' % (value, value))
            # We're writing a value to memory; if it's a PyObject*
            # then we're surrending a reference on it:
            if value in nextstate.owned_refs:
                log('removing ownership of %s' % value)
                nextstate.owned_refs.remove(value)
        return [Transition(self, nextstate, None)] # for now

def check_refcounts(fun, show_traces):
    # Abstract interpretation:
    # Walk the CFG, gathering the information we're interested in

    if show_traces:
        from libcpychecker.visualizations import StateGraphPrettyPrinter
        sg = StateGraph(fun, log, MyState)
        sgpp = StateGraphPrettyPrinter(sg)
        dot = sgpp.to_dot()
        #dot = sgpp.extra_items()
        print(dot)
        invoke_dot(dot)

    traces = iter_traces(fun, MyState)
    if show_traces:
        traces = list(traces)
        for i, trace in enumerate(traces):
            def my_logger(item, indent=0):
                sys.stdout.write('%s%s\n' % ('  ' * indent, item))
            trace.log(my_logger, 'TRACE %i' % i, 0)

            # Show trace #0:
            if i == 0:
                from libcpychecker.visualizations import TracePrettyPrinter
                tpp = TracePrettyPrinter(fun.cfg, trace)
                dot = tpp.to_dot()
                print dot
                f = open('test.dot', 'w')
                f.write(dot)
                f.close()
                invoke_dot(dot)

    for i, trace in enumerate(traces):
        trace.log(log, 'TRACE %i' % i, 0)
        if trace.err:
            # This trace bails early with a fatal error; it probably doesn't
            # have a return value
            log('trace.err: %s %r' % (trace.err, trace.err))
            gcc.permerror(trace.err.loc,
                          str(trace.err))
            describe_trace(trace)
            # FIXME: in our example this ought to mention where the values came from
            continue
        # Otherwise, the trace proceeds normally
        return_value = trace.return_value()
        log('trace.return_value(): %s' % trace.return_value())
        # Ideally, we should "own" exactly one reference, and it should be
        # the return value.  Anything else is an error (and there are other
        # kinds of error...)
        final_refs = trace.final_references()
        if return_value in final_refs:
            final_refs.remove(return_value)
        else:
            if isinstance(return_value, NonNullPtrValue):
                gcc.permerror(trace.get_last_stmt().loc,
                              ('return of PyObject* (%s)'
                               ' without Py_INCREF()'
                               % return_value))
                if str(return_value) == '&_Py_NoneStruct':
                    extra_text('%s: suggest use of "Py_RETURN_NONE;"'
                               % trace.get_last_stmt().loc, 1)

        # Anything remaining is a leak:
        if len(final_refs) > 0:
            for ref in final_refs:
                gcc.permerror(ref.stmt.loc,
                              'leak of PyObject* reference acquired at %s'
                              % describe_stmt(ref.stmt))
                log('ref: %s' % ref, 1)
                # Print more details about the path through the function that
                # leads to the error:
                for j in range(len(trace.states)):
                    state = trace.states[j]
                    stmt = state.loc.get_stmt()
                    if isinstance(stmt, gcc.GimpleCond):
                        nextstate = trace.states[j+1]
                        next_stmt = nextstate.loc.get_stmt()
                        extra_text('%s: taking %s path at %s'
                                   % (stmt.loc,
                                      nextstate.prior_bool,
                                      get_src_for_loc(stmt.loc)), 1)
                        #log(next_stmt, 3)
                        # FIXME: phi nodes don't have locations:
                        if hasattr(next_stmt, 'loc'):
                            if next_stmt.loc:
                                extra_text('%s: reaching here %s'
                                           % (next_stmt.loc,
                                              get_src_for_loc(next_stmt.loc)),
                                           2)
                extra_text('%s: returning %s'
                           % (ref.stmt.loc, return_value),
                           1) # FIXME: loc is wrong

    if 0:
        dot = cfg_to_dot(fun.cfg)
        invoke_dot(dot)


