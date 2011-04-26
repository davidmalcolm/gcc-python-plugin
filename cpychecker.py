import gcc
import sys

def log(msg):
    if 1:
        sys.stderr.write('%s\n' % msg)

def get_src_for_loc(loc):
    # Given a gcc.Location, get the source line as a string
    import linecache
    return linecache.getline(loc.file, loc.line).rstrip()

def check_pyargs(fun):
    def check_callsite(stmt):
        log('got call at %s' % stmt.loc)
        log(get_src_for_loc(stmt.loc))
        log('stmt: %r %s' % (stmt, stmt))
        log('args: %r' % stmt.args)
        for arg in stmt.args:
            log('  arg: %s %r' % (arg, arg))
    
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if isinstance(stmt, gcc.GimpleCall):
                        #log('stmt.fn: %s %r' % (stmt.fn, stmt.fn))
                        #log('stmt.fndecl: %s %r' % (stmt.fndecl, stmt.fndecl))
                        if stmt.fndecl.name == 'PyArg_ParseTuple':
                            check_callsite(stmt)

def on_pass_execution(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name != '*warn_function_return':
        return

    log(fun)
    if fun:
        check_pyargs(fun)
    
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
