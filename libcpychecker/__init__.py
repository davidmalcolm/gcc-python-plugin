import gcc

from PyArg_ParseTuple import check_pyargs, log

def on_pass_execution(optpass, fun):
    # Only run in one pass
    # FIXME: should we be adding our own pass for this?
    if optpass.name != '*warn_function_return':
        return

    log(fun)
    if fun:
        check_pyargs(fun)

def main():
    gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                          on_pass_execution)
