import gcc
import sys

def check_pyargs(fun):
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    sys.stderr.write(str(stmt))
                    if isinstance(stmt, gcc.GimpleCall):
                        sys.stderr.write('GOT CALL TO %s\n' % stmt.fn)
                        

def on_pass_execution(optpass, fun):
    sys.stderr.write('%s\n' % fun)
    if fun:
        check_pyargs(fun)

    #
    #   sys.stderr.write(str(dir(optpass)))
    #    sys.exit(1)
    
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
