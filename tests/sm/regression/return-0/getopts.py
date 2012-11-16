"""
Seeing this error:

    tests/sm/regression/return-0/input.c:4:3: error: Unhandled Python exception raised calling 'execute' method
    Traceback (most recent call last):
      File "sm/__init__.py", line 53, in execute
        solve(ctxt, 'solution')
      File "sm/solver.py", line 586, in solve
        solution = ctxt.solve(name)
      File "sm/solver.py", line 544, in solve
        find_leaks(self)
      File "sm/leaks.py", line 59, in find_leaks
        retval_aliases = get_retval_aliases(ctxt, edge.dstnode)
      File "sm/leaks.py", line 33, in get_retval_aliases
        retval = retval.var
    AttributeError: 'gcc.IntegerCst' object has no attribute 'var'
with:
  -O2

With optimization, the return statement directly returns a constant, rather
than a temporary.
"""
print('-O2')
