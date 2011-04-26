import gcc
import sys

def check_pyargs(fun):
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if isinstance(stmt, gcc.GimpleCall):
                        sys.stderr.write(str(stmt))
                        sys.stderr.write('GOT CALL TO %s %r\n' % (stmt.fn, stmt.fn))
                        sys.stderr.write('rhs: %r\n' % stmt.rhs)
                        sys.stderr.write('rhs: %r\n' % [str(arg) for arg in stmt.rhs])
                        
                        for arg in stmt.rhs:
                            sys.stderr.write('  arg: %s %r\n' % (arg, arg))
                        
                        

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
