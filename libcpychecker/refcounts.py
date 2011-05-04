import gcc

from gccutils import cfg_to_dot, invoke_dot

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

class Operations:
    def __init__(self, fun):
        self.fun = fun

        self.assigns_to_count = []
        self.assigns_to_objptr = []
        self.returns_of_objptr = []

        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    # log(stmt)
                    # log(repr(stmt))
                    if stmt_is_assignment_to_count(stmt):
                        log('%s: assignment to count: %s' % (stmt.loc, stmt))
                        self.assigns_to_count.append(stmt)
                    if stmt_is_assignment_to_objptr(stmt):
                        log('%s: assignment to objptr: %s' % (stmt.loc, stmt))
                        self.assigns_to_objptr.append(stmt)
                    if stmt_is_return_of_objptr(stmt):
                        log('%s: return of objptr: %s' % (stmt.loc, stmt))
                        log('stmt.retval: %s' % stmt.retval)
                        self.returns_of_objptr.append(stmt)

        log(self.returns_of_objptr)
        log(self.assigns_to_count)

        # Highly-simplistic first pass at refcount tracking:
        if len(self.returns_of_objptr) > 0:
            if self.assigns_to_count == []:
                # We're returning a PyObject *, but not modifying a refcount
                # FIXME: if we're calling various APIs, this would affect the count
                # Otherwise, this is a bug:
                for r in self.returns_of_objptr:
                    if r.loc:
                        gcc.permerror(r.loc, 'return of PyObject* without Py_INCREF()')

def check_refcounts(fun):
    ops = Operations(fun)
     
    if 0:
        dot = cfg_to_dot(fun.cfg)
        invoke_dot(dot)


        
