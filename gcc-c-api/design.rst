Proposed GCC plugin C API
-------------------------

This is an API for GCC plugins written in C.

All public functions are declared with GCC_PUBLIC_API, any private
helper functions are declared with GCC_PRIVATE_API

Different plugins are likely to want different lifetime-management
policies for the wrapper objects: some plugins will want to
garbage-collect, others will want to reference-count, etc.

Hence all types are "really" just pointers, but are hidden somewhat to
emphasize that you must collaborate with the GCC garbage collector.

Naming convention:  a gcc_something is an interface to a GCC "something"
e.g. gcc_gimple_phi is an interface to a GCC gimple phi node.  All types
also have a standard varname (e.g. "edge" for a gcc_cfg_edge).  All
functions have a prefix relating to what they act on, e.g.:

    GCC_PUBLIC_API (int)
    gcc_cfg_block_get_index (gcc_cfg_block block);

All such interface types have a "mark_in_use" function, e.g.::

    GCC_PUBLIC_API (void)
    gcc_cfg_block_mark_in_use (gcc_cfg_block block);

If you're holding a pointer to one of these types, you *must* call this
when GCC's garbage collector runs.

Getters are named "TYPEPREFIX_get_ATTR" e.g. "gcc_cfg_block_get_index"

Iterators follow a common pattern.  Here's one that iterates over all basic
blocks within a control flow graph::

      GCC_PUBLIC_API (bool)
      gcc_cfg_for_each_block (gcc_cfg cfg,
                              bool (*cb) (gcc_cfg_block block, void *user_data),
                              void *user_data);

The iteration terminates if the callback ever returns truth (allowing
it also to be used for a linear search).  The overall return value is truth
if any callback returned truth (implying there was an early exit), or false
if every callback returned falsehood (implying every element was visited).


C-based class hierarchy
^^^^^^^^^^^^^^^^^^^^^^^
There is a "class hierarchy" to the types, but it is expressed in C.

There are explicit casting functions for every pair of types.  For example,
this function allows you to upcast a gcc_ssa_name to its parent class
gcc_tree::

  GCC_PUBLIC_API (gcc_tree)
  gcc_ssa_name_as_gcc_tree (gcc_ssa_name node);

and this function does the reverse, downcasting a gcc_tree to the more refined
class gcc_ssa_name::

  GCC_PUBLIC_API (gcc_ssa_name)
  gcc_tree_as_gcc_ssa_name (gcc_tree node);


XML hooks
^^^^^^^^^
The API is described in XML form, expressing the class hierarchy, along with
with the attributes that each class has.  This makes it easy to programatically
manipulate the API: every important platform can already handle XML.  The
header files for the API are generated from the XML description.  (This was
useful for generating all of the casting functions).

There is a RELAX-NG schema for the XML format.

(I also tried JSON, but XML ended up being clearer).

TODO: how to arrange for your code to be called when the GC runs?

TODO: getting errors?
