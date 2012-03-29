Proposed GCC plugin API
-----------------------

All public functions are declared with GCC_PUBLIC_API, any private
helper functions are declared with GCC_PRIVATE_API

Different plugins are likely to want different lifetime-management
policies for the wrapper objects: some plugins will want to
garbage-collect, others will want to reference-count, etc.

ence all types are "really" just pointers, but are hidden somewhat to
emphasize that you must collaborate with the GCC garbage collector.

Naming convention:  a GccSomethingI is a GCC "something" interface
e.g. GccGimplePhiI is an interface to a Gcc Gimple phi node.  All types
also have a standard varname (e.g. "edge" for a GccCfgEdgeI).  All
functions have a prefix relating to what they act on, e.g.:

All such interface types have a "MarkInUse" function, e.g.::

    GCC_PUBLIC_API(void)
    GccCfgBlockI_MarkInUse(GccCfgBlockI block);

If you're holding a pointer to one of these types, you *must* call this
when GCC's garbage collector runs.

Getters are named "TYPEPREFIX_GetATTR" e.g. "GccCfgBlockI_GetIndex"

Iterators follow a common pattern.  Here's one that iterates over all basic
blocks within a control flow graph::

      GCC_PUBLIC_API(bool)
      GccCfgI_ForEachBlock(GccCfgI cfg,
                           bool (*cb)(GccCfgBlockI block, void *user_data),
                           void *user_data);

The iteration terminates if the callback ever returns truth (allowing
it also to be used for a linear search).  The overall return value is truth
if any callback returned truth (implying there was an early exit), or false
if every callback returned falsehood (implying every element was visited).

TODO: how to arrange for your code to be called when the GC runs?

TODO: getting errors?
