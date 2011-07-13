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
import gccutils
import sys
from gccutils import get_src_for_loc
from collections import OrderedDict
from PyArg_ParseTuple import log

class AbstractValue:
    def __init__(self, gcctype, loc):
        assert isinstance(gcctype, gcc.Type)
        if loc:
            assert isinstance(loc, gcc.Location)
        self.gcctype = gcctype
        self.loc = loc

    def __str__(self):
        if self.loc:
            return '%s from %s' % (self.gcctype, self.loc)
        else:
            return '%' % self.gcctype

    def __repr__(self):
        return 'AbstractValue(gcctype=%r, loc=%r)' % (str(self.gcctype), self.loc)

class UnknownValue(AbstractValue):
    """
    A value that we know nothing about
    """
    def __str__(self):
        return 'unknown %s from %s' % (self.gcctype, self.loc)

    def __repr__(self):
        return 'UnknownValue(gcctype=%r, loc=%r)' % (self.gcctype, self.loc)

class ConcreteValue(AbstractValue):
    """
    A known, specific value (e.g. 0)
    """
    def __init__(self, gcctype, loc, value):
        assert isinstance(gcctype, gcc.Type)
        if loc:
            assert isinstance(loc, gcc.Location)
        self.gcctype = gcctype
        self.loc = loc
        self.value = value

    def __str__(self):
        if self.loc:
            return '(%s)%r from %s' % (self.gcctype, self.value, self.loc)
        else:
            return '(%s)%r' % (self.gcctype, self.value)

    def __repr__(self):
        return 'ConcreteValue(gcctype=%r, loc=%r, value=%r)' % (str(self.gcctype), self.loc, self.value)

class PredictedError(Exception):
    pass

class InvalidlyNullParameter(PredictedError):
    # Use this when we can predict that a function is called with NULL as an
    # argument for an argument that must not be NULL
    def __init__(self, fnname, paramidx, nullvalue):
        self.fnname = fnname
        self.paramidx = paramidx # starts at 1
        self.nullvalue = nullvalue

    def __str__(self):
        return ('%s can be called with NULL as parameter %i; %s'
                % (self.fnname, self.paramidx, self.nullvalue))


class NullPtrDereference(PredictedError):
    def __init__(self, state, cr):
        assert isinstance(state, State)
        assert isinstance(cr, gcc.ComponentRef)
        self.state = state
        self.cr = cr

    def __str__(self):
        return ('dereferencing NULL (%s) at %s'
                % (self.cr, self.state.loc.get_stmt().loc))

class PtrValue(AbstractValue):
    """An abstract (PyObject*) value"""
    def __init__(self, nonnull):
        self.nonnull = nonnull

def describe_stmt(stmt):
    if isinstance(stmt, gcc.GimpleCall):
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            fnname = stmt.fn.operand.name
            return 'call to %s at line %i' % (fnname, stmt.loc.line)
    else:
        return str(stmt.loc)

class Location:
    """A location within a CFG: a gcc.BasicBlock together with an index into
    the gimple list.  (We don't support SSA passes)"""
    def __init__(self, bb, idx):
        self.bb = bb
        self.idx = idx

    def __str__(self):
        stmt = self.get_stmt()
        return ('block %i stmt:%i : %20r : %s'
                % (self.bb.index, self.idx, stmt, stmt))

    def next_locs(self):
        """Get a list of Location instances, for what can happen next"""
        if self.bb.gimple and len(self.bb.gimple) > self.idx + 1:
            # Next gimple statement:
            return [Location(self.bb, self.idx + 1)]
        else:
            # At end of gimple statements: successor BBs:
            return [Location.get_block_start(outedge.dest) for outedge in self.bb.succs]

    def next_loc(self):
        """Get the next Location, for when it's unique"""
        if self.bb.gimple:
            if len(self.bb.gimple) > self.idx + 1:
                # Next gimple statement:
                return Location(self.bb, self.idx + 1)
            else:
                assert len(self.bb.succs) == 1
                return Location.get_block_start(self.bb.succs[0].dest)

    @classmethod
    def get_block_start(cls, bb):
        # Don't bother iterating through phi_nodes if there aren't any:
        return Location(bb, 0)

    def get_stmt(self):
        if self.bb.gimple:
            return self.bb.gimple[self.idx]
        else:
            return None

class Region:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.children = []
        self.fields = {}
        if parent:
            parent.children.append(self)

    def __repr__(self):
        return 'Region(%r)' % self.name

class RegionForGlobal(Region):
    """
    Represents the area of memory (e.g. in .data or .bss section)
    used to store a particular globa
    """
    def __init__(self, vardecl):
        assert isinstance(vardecl, gcc.VarDecl)
        Region.__init__(self, vardecl.name, None)
        self.vardecl = vardecl

    def __repr__(self):
        return 'RegionForGlobal(%r)' % self.vardecl

# Used for making unique IDs:
num_heap_regions = 0

class State:
    """A Location with memory state"""
    def __init__(self, loc, region_for_var=None, value_for_region=None, return_rvalue=None):
        assert isinstance(loc, Location)
        self.loc = loc

        # Mapping from VarDecl.name to Region:
        if region_for_var:
            assert isinstance(region_for_var, OrderedDict)
            self.region_for_var = region_for_var
        else:
            self.region_for_var = OrderedDict()

        # Mapping from Region to AbstractValue:
        if value_for_region:
            assert isinstance(value_for_region, OrderedDict)
            self.value_for_region = value_for_region
        else:
            self.value_for_region = OrderedDict()

        self.return_rvalue = return_rvalue

    def __str__(self):
        return ('loc: %s region_for_var:%s value_for_region:%s%s'
                % (self.loc,
                   self.region_for_var,
                   self.value_for_region,
                   self._extra()))

    def __repr__(self):
        return ('loc: %r region_for_var:%r value_for_region:%r%r'
                % (self.loc,
                   self.region_for_var,
                   self.value_for_region,
                   self._extra()))

    def log(self, logger, indent):
        logger(str(self.region_for_var), indent + 1)
        logger(str(self.value_for_region), indent + 1)
        # Display data in tabular form:
        from gccutils import Table
        t = Table(['Expression', 'Region', 'Value'])
        for k in self.region_for_var:
            region = self.region_for_var[k]
            value = self.value_for_region.get(region, None)
            t.add_row((k, region, value),)
        from StringIO import StringIO
        s = StringIO()
        t.write(s)
        for line in s.getvalue().splitlines():
            logger(line, indent + 1)

        logger('extra: %s' % (self._extra(), ), indent)

        # FIXME: derived class/extra:
        self.resources.log(logger, indent)

        logger('loc: %s' % self.loc, indent)
        if self.loc.get_stmt():
            logger('%s' % self.loc.get_stmt().loc, indent + 1)

    def copy(self):
        c = self.__class__(loc,
                           self.region_for_var.copy(),
                           self.value_for_region.copy())
        c.return_rvalue = self.return_rvalue
        return c

    def eval_expr(self, expr):
        log('eval_expr: %r' % expr)
        if isinstance(expr, AbstractValue):
            return expr
        if isinstance(expr, Region):
            return expr
        if isinstance(expr, gcc.IntegerCst):
            return ConcreteValue(expr.type, None, expr.constant)
        if isinstance(expr, gcc.VarDecl):
            region = self.var_region(expr)
            value = self.get_store(region)
            return value
            #return UnknownValue(expr.type, str(expr))
        if isinstance(expr, gcc.ComponentRef):
            #assert isinstance(expr.field, gcc.FieldDecl)
            region = self.get_field_region(expr)#.target, expr.field.name)
            value = self.get_store(region)
            return value
        if isinstance(expr, gcc.AddrExpr):
            log(expr.operand)
            if isinstance(expr.operand, gcc.VarDecl):
                region = self.var_region(expr.operand)
                return region
        if expr is None:
            return None
        return UnknownValue(expr.type, None) # FIXME

    def assign(self, lhs, rhs):
        log('assign(%r, %r)' % (lhs, rhs))
        log('assign(%s, %s)' % (lhs, rhs))
        if isinstance(lhs, gcc.VarDecl):
            dest_region = self.var_region(lhs)
        elif isinstance(lhs, gcc.ComponentRef):
            assert isinstance(lhs.field, gcc.FieldDecl)
            dest_region = self.get_field_region(lhs)
        else:
            assert False # FIXME!
        value = self.eval_expr(rhs)
        log('value: %s %r' % (value, value))
        self.value_for_region[dest_region] = value
        #assert isinstance(rhs, gcc.VarDecl) # for now
        #self.value_for_region(

    def var_region(self, var):
        assert isinstance(var, gcc.VarDecl)
        if var not in self.region_for_var:
            # Presumably a reference to a global variable:
            log('adding region for global var: %r' % var)
            region = RegionForGlobal(var)
            # it is its own region:
            self.region_for_var[var] = region

            # Initialize the refcount of global PyObject instances
            # e.g. _Py_NoneStruct to 0 i.e. we don't own any references to them
            if str(var.type) == 'struct PyObject':
                from refcounts import RefcountValue
                ob_refcnt = self.make_field_region(region, 'ob_refcnt') # FIXME: this should be a memref and fieldref
                self.value_for_region[ob_refcnt] = RefcountValue(0)
        return self.region_for_var[var]

    def get_field_region(self, cr): #target, field):
        assert isinstance(cr, gcc.ComponentRef)
        #cr.debug()
        log('target: %r' % cr.target)
        log('field: %r' % cr.field)
        #fr = FIXME #self.make_field_region(target, field)
        if 1: # fr not in self.region_for_var:
            if 1: # cr.target not in self.region_for_var:
                log('foo')
                if isinstance(cr.target, gcc.MemRef):
                    ptr = self.eval_expr(cr.target.operand)
                    if isinstance(ptr, ConcreteValue) and ptr.value == 0:
                        raise NullPtrDereference(self, cr)
                    return self.make_field_region(ptr, cr.field.name)
                elif isinstance(cr.target, gcc.VarDecl):
                    log('bar')
                    vr = self.var_region(cr.target)
                    log(vr)
                    return self.make_field_region(vr, cr.field.name)
        log('cr: %r %s' % (cr, cr))
        return self.region_for_var[cr]

    def get_store(self, region):
        assert isinstance(region, Region)
        # self.log(log, 0)
        return self.value_for_region[region]

    def make_heap_region(self):
        global num_heap_regions
        region = Region('heap_region_%i' % num_heap_regions, None)
        num_heap_regions += 1
        # it is its own region:
        self.region_for_var[region] = region
        return region

    def make_field_region(self, target, field):
        assert isinstance(target, Region)
        assert isinstance(field, str)
        log('make_field_region(%r, %r)' % (target, field))
        if field in target.fields:
            log('reusing')
            return target.fields[field]
        log('not reusing')
        region = Region('%s.%s' % (target.name, field), target)
        target.fields[field] = region
        # it is its own region:
        self.region_for_var[region] = region
        return region


    def get_value_of_field_by_varname(self, varname, field):
        # Lookup varname.field
        # For use in writing selftests
        log('get_value_of_field_by_varname(%r, %r)' % (varname, field), 0)
        assert isinstance(varname, str)
        assert isinstance(field, str)
        for k in self.region_for_var:
            if isinstance(k, gcc.VarDecl):
                if k.name == varname:
                    region = self.region_for_var[k]
                    region =  self.make_field_region(region, field)
                    value = self.value_for_region.get(region, None)
                    return value

    def get_value_of_field_by_region(self, rvalue, field):
        # Lookup rvalue->field
        # For use in writing selftests
        log('get_value_of_field_by_region(%r, %r)' % (rvalue, field), 0)
        assert isinstance(rvalue, Region)
        assert isinstance(field, str)
        if field in rvalue.fields:
            field_region = rvalue.fields[field]
            return self.value_for_region.get(field_region, None)
        return None

    def init_for_function(self, fun):
        log('init_for_function(%r)' % fun)
        root_region = Region('root', None)
        stack = Region('stack for %s' % fun.decl.name, root_region)
        for local in fun.local_decls:
            region = Region('region for %r' % local, stack)
            self.region_for_var[local] = region
            self.value_for_region[region] = None # uninitialized

    def make_assignment(self, lhs, rhs, desc):
        log('make_assignment(%r, %r, %r)' % (lhs, rhs, desc))
        if desc:
            assert isinstance(desc, str)
        new = self.copy()
        new.loc = self.loc.next_loc()
        new.assign(lhs, rhs)
        return Transition(self, new, desc)

    def update_loc(self, newloc):
        new = self.copy()
        new.loc = newloc
        return new

    def use_next_loc(self):
        newloc = self.loc.next_loc()
        return self.update_loc(newloc)

    def has_returned(self):
        return self.return_rvalue is not None

    def get_gcc_loc(self):
        return self.loc.get_stmt().loc

class Transition:
    def __init__(self, src, dest, desc):
        assert isinstance(src, State)
        assert isinstance(dest, State)
        self.src = src
        self.dest = dest
        self.desc = desc

    def __repr__(self):
        return 'Transition(%r, %r)' % (self.dest, self.desc)

    def log(self, logger, indent):
        logger('desc: %r' % self.desc, indent)
        logger('dest:', indent)
        self.dest.log(logger, indent + 1)

class Trace:
    """A sequence of States and Transitions"""
    def __init__(self):
        self.states = []
        self.transitions = []
        self.err = None

    def add(self, transition):
        assert isinstance(transition, Transition)
        self.states.append(transition.dest)
        self.transitions.append(transition)
        return self

    def add_error(self, err):
        self.err = err

    def copy(self):
        t = Trace()
        t.states = self.states[:]
        t.transitions = self.transitions[:]
        t.err = self.err # FIXME: should this be a copy?
        return t

    def log(self, logger, name, indent):
        logger('%s:' % name, indent)
        for i, state in enumerate(self.states):
            logger('%i:' % i, indent + 1)
            state.log(logger, indent + 2)
        if self.err:
            logger('  Trace ended with error: %s' % self.err, indent + 1)

    def get_last_stmt(self):
        return self.states[-1].loc.get_stmt()

    def return_value(self):
        return self.states[-1].return_rvalue

    def final_references(self):
        return self.states[-1].owned_refs

def true_edge(bb):
    for e in bb.succs:
        if e.true_value:
            return e

def false_edge(bb):
    for e in bb.succs:
        if e.false_value:
            return e

class Resources:
    # Resource tracking for a state
    def __init__(self):
        # Resources that we've acquired:
        self._acquisitions = []

        # Resources that we've released:
        self._releases = []

    def copy(self):
        new = Resources()
        new._acquisitions = self._acquisitions[:]
        new._releases = self._releases[:]
        return new

    def acquire(self, resource):
        self._acquisitions.append(resource)

    def release(self, resource):
        self._releases.append(resource)

    def log(self, logger, indent):
        logger('resources:', indent)
        logger('acquisitions: %s' % self._acquisitions, indent + 1)
        logger('releases: %s' % self._releases, indent + 1)

def iter_traces(fun, stateclass, prefix=None):
    # Traverse the tree of traces of program state
    # FIXME: this code can't cope with loops yet
    log('iter_traces(%r, %r, %r)' % (fun, stateclass, prefix))
    if prefix is None:
        prefix = Trace()
        curstate = stateclass(Location.get_block_start(fun.cfg.entry),
                              None, None, None,
                              [],
                              Resources())
    else:
        curstate = prefix.states[-1]
        if curstate.has_returned():
            # This state has returned a value (and hence terminated):
            return [prefix]

    # We need the prevstate to handle Phi nodes
    if len(prefix.states) > 1:
        prevstate = prefix.states[-2]
    else:
        prevstate = None

    prefix.log(log, 'PREFIX', 1)
    log('  %s:%s' % (fun.decl.name, curstate.loc))
    try:
        transitions = curstate.get_transitions()
        assert isinstance(transitions, list)
    except PredictedError, err:
        # We're at a terminating state:
        err.loc = prefix.get_last_stmt().loc
        trace_with_err = prefix.copy()
        trace_with_err.add_error(err)
        trace_with_err.log(log, 'FINISHED TRACE WITH ERROR: %s' % err, 1)
        return [trace_with_err]

    log('transitions: %s' % transitions, 2)

    if len(transitions) > 0:
        result = []
        for transition in transitions:
            # Recurse:
            for trace in iter_traces(fun, stateclass, prefix.copy().add(transition)):
                result.append(trace)
        return result
    else:
        # We're at a terminating state:
        prefix.log(log, 'FINISHED TRACE', 1)
        return [prefix]

class StateGraph:
    """
    A graph of states, representing the various routes through a function,
    tracking state.

    For now, we give up when we encounter a loop, as an easy way to ensure
    termination of the analysis
    """
    def __init__(self, fun, logger, stateclass):
        assert isinstance(fun, gcc.Function)
        self.fun = fun
        self.states = []
        self.transitions = []
        self.stateclass = stateclass

        logger('StateGraph.__init__(%r)' % fun)

        # Recursively gather states:
        initial = stateclass(Location.get_block_start(fun.cfg.entry),
                             None, None, None,
                             [],
                             Resources())
        initial.init_for_function(fun)
        self.states.append(initial)
        self._gather_states(initial, logger)

    def _gather_states(self, curstate, logger):
        logger('  %s:%s' % (self.fun.decl.name, curstate.loc))
        try:
            transitions = curstate.get_transitions()
            #print transitions
            assert isinstance(transitions, list)
        except PredictedError, err:
            # We're at a terminating state:
            errstate = curstate.copy()
            transition = Transition(curstate, errstate, str(err))
            self.states.append(transition.dest)
            self.transitions.append(transition)
            return

        logger('transitions:', 2)
        for t in transitions:
            t.log(logger, 3)

        if len(transitions) > 0:
            for transition in transitions:
                # FIXME: what about loops???
                assert isinstance(transition, Transition)
                self.states.append(transition.dest)
                self.transitions.append(transition)

                if transition.dest.has_returned():
                    # This state has returned a value (and hence terminated)
                    continue

                # Recurse:
                self._gather_states(transition.dest, logger)
        else:
            # We're at a terminating state:
            logger('FINISHED TRACE')

    def get_prev_state(self, state):
        assert state in self.states
        for t in self.transitions:
            if t.dest == state:
                return t.src
        # Not found:
        return None

def extra_text(msg, indent):
    sys.stderr.write('%s%s\n' % ('  ' * indent, msg))

def describe_trace(trace):
    # Print more details about the path through the function that
    # leads to the error:
    awaiting_target = None
    for t in trace.transitions:
        log('transition: %s' % t)
        if t.desc:
            gcc.inform(t.src.loc.get_stmt().loc, 'when %s' % t.desc)
    for j in range(len(trace.states)-1):
        state = trace.states[j]
        nextstate = trace.states[j+1]
        stmt = state.loc.get_stmt()
        next_stmt = nextstate.loc.get_stmt()
        if state.loc.bb != nextstate.loc.bb:
            if stmt:
                extra_text('%s: taking %s path at %s'
                           % (stmt.loc,
                              nextstate.prior_bool,
                              get_src_for_loc(stmt.loc)), 1)
            first_loc_in_next_bb = get_first_loc_in_block(nextstate.loc.bb)
            if first_loc_in_next_bb:
                        extra_text('%s: reaching here %s'
                                   % (first_loc_in_next_bb,
                                      get_src_for_loc(first_loc_in_next_bb)),
                                   2)

