print('-O2')

# With optimization, the whole of test() goes away, and hence we get no error
# message
#
# Specifically, what's happening is dead-code elimination (the "cddce" pass
# in tree-ssa-dce.c)
# Invoking gcc with -fdump-tree-all-details shows this within input.c.031t.cddce1:
#   Eliminating unnecessary statements:
#   Deleting : free (ptr_1);
#
#   Deleting : free (ptr_1);
#
#   Deleting : ptr_1 = malloc (512);
#
# and the whole of the function has been optimized away before the analysis
# pass sees it
