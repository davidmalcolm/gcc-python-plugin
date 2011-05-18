# Sample python script, to be run by our gcc plugin (see "make test")
# Show the SSA form of each function, using GraphViz
import gcc
from gccutils import get_src_for_loc, cfg_to_dot, invoke_dot

def my_pass_execution_callback(*args, **kwargs):
    #print('my_pass_execution_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])
    (optpass, fun) = args
    if not optpass.properties_required & (1<<5):
        return
    if fun:
        print 'fun.cfg: %r' % fun.cfg
        if fun.cfg:
            #print help(fun.cfg)
            print 'fun.cfg.basic_blocks: %r' % fun.cfg.basic_blocks
            print 'fun.cfg.entry: %r' % fun.cfg.entry
            print 'fun.cfg.exit: %r' % fun.cfg.exit
            print 'fun.cfg.entry.succs: %r' % fun.cfg.entry.succs
            print 'fun.cfg.exit.preds: %r' % fun.cfg.exit.preds
            
            dot = cfg_to_dot(fun.cfg)
            print dot
            invoke_dot(dot)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      my_pass_execution_callback)


