import gcc
import sys

def get_src_for_loc(loc):
    # Given a gcc.Location, get the source line as a string
    import linecache
    return linecache.getline(loc.file, loc.line).rstrip()

def check_pyargs(fun):
    def check_callsite(stmt):
        sys.stderr.write('got call at %s\n' % stmt.loc)
        sys.stderr.write('%s\n' % get_src_for_loc(stmt.loc))
        sys.stderr.write(str(stmt))
        sys.stderr.write('rhs: %r\n' % stmt.rhs)
        sys.stderr.write('rhs: %r\n' % [str(arg) for arg in stmt.rhs])
        for arg in stmt.rhs:
            sys.stderr.write('  arg: %s %r\n' % (arg, arg))
    
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if isinstance(stmt, gcc.GimpleCall):
                        #sys.stderr.write('stmt.fn: %s %r\n' % (stmt.fn, stmt.fn))
                        #sys.stderr.write('stmt.fndecl: %s %r\n' % (stmt.fndecl, stmt.fndecl))
                        if stmt.fndecl.name == 'PyArg_ParseTuple':
                            check_callsite(stmt)
                        #sys.stderr.write('GOT CALL\n')
                        
                        

def on_pass_execution(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name != '*warn_function_return':
        return

    sys.stderr.write('%s\n' % fun)
    if fun:
        check_pyargs(fun)
    
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
