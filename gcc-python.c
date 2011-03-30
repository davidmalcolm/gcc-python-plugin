#include <Python.h>
#include <gcc-plugin.h>

int plugin_is_GPL_compatible;

#include "plugin-version.h"

static const char* event_name[] = {
#define DEFEVENT(NAME) \
  #NAME, 
# include "plugin.def"
# undef DEFEVENT
};

/*
  Notes on the passes

  As of 2011-03-30, http://gcc.gnu.org/onlinedocs/gccint/Plugins.html doesn't
  seem to document the type of the gcc_data passed to each callback.

  For reference, with gcc-4.6.0-0.15.fc15.x86_64 the types seem to be as
  follows:

  PLUGIN_ATTRIBUTES:
    gcc_data=0x0
    Called from: init_attributes () at ../../gcc/attribs.c:187

  PLUGIN_PRAGMAS:
    gcc_data=0x0
    Called from: c_common_init () at ../../gcc/c-family/c-opts.c:1052

  PLUGIN_START_UNIT:
    gcc_data=0x0
    Called from: compile_file () at ../../gcc/toplev.c:573

  PLUGIN_PRE_GENERICIZE
    gcc_data is:  tree fndecl;
    Called from: finish_function () at ../../gcc/c-decl.c:8323

  PLUGIN_OVERRIDE_GATE
    gcc_data:
      &gate_status
      bool gate_status;
    Called from : execute_one_pass (pass=0x1011340) at ../../gcc/passes.c:1520

  PLUGIN_PASS_EXECUTION
    gcc_data: struct opt_pass *pass
    Called from: execute_one_pass (pass=0x1011340) at ../../gcc/passes.c:1530

  PLUGIN_ALL_IPA_PASSES_START
    gcc_data=0x0
    Called from: ipa_passes () at ../../gcc/cgraphunit.c:1779

  PLUGIN_EARLY_GIMPLE_PASSES_START
    gcc_data=0x0
    Called from: execute_ipa_pass_list (pass=0x1011fa0) at ../../gcc/passes.c:1927

  PLUGIN_EARLY_GIMPLE_PASSES_END
    gcc_data=0x0
    Called from: execute_ipa_pass_list (pass=0x1011fa0) at ../../gcc/passes.c:1930

  PLUGIN_ALL_IPA_PASSES_END
    gcc_data=0x0
    Called from: ipa_passes () at ../../gcc/cgraphunit.c:1821

  PLUGIN_ALL_PASSES_START
    gcc_data=0x0
    Called from: tree_rest_of_compilation (fndecl=0x7ffff16b1f00) at ../../gcc/tree-optimize.c:420

  PLUGIN_ALL_PASSES_END
    gcc_data=0x0
    Called from: tree_rest_of_compilation (fndecl=0x7ffff16b1f00) at ../../gcc/tree-optimize.c:425

  PLUGIN_FINISH_UNIT
    gcc_data=0x0
    Called from: compile_file () at ../../gcc/toplev.c:668

  PLUGIN_FINISH
    gcc_data=0x0
    Called from: toplev_main (argc=17, argv=0x7fffffffdfc8) at ../../gcc/toplev.c:1970

*/

static void
my_callback(enum plugin_event event, void *gcc_data, void *user_data)
{
  printf("%s:%i:my_callback(%s, %p, %p)\n", __FILE__, __LINE__, event_name[event], gcc_data, user_data);
}

#define DEFEVENT(NAME) \
static void my_callback_for_##NAME(void *gcc_data, void *user_data) \
{ \
     my_callback(NAME, gcc_data, user_data); \
}
# include "plugin.def"
# undef DEFEVENT

static PyObject*
gcc_python_register_callback(PyObject *self, PyObject *args)
{
    // FIXME: to be written
    // if(!PyArg_ParseTuple(args, ":numargs"))
    //return NULL;
    printf("%s:%i:gcc_python_register_callback\n", __FILE__, __LINE__);
    Py_RETURN_NONE;
    //return Py_BuildValue("i", numargs);
}

static PyMethodDef GccMethods[] = {
    {"register_callback", gcc_python_register_callback, METH_VARARGS,
     "Register a callback, to be called when various GCC events occur."},

    /* Sentinel: */
    {NULL, NULL, 0, NULL}
};

static int
gcc_python_init_gcc_module(struct plugin_name_args *plugin_info)
{
    PyObject *gcc_module;

    gcc_module = Py_InitModule("gcc", GccMethods);
    if (!gcc_module) {
        return 0;
    }

#define DEFEVENT(NAME) \
    PyModule_AddIntMacro(gcc_module, NAME);
# include "plugin.def"
# undef DEFEVENT


    /* Success: */
    return 1;
}

int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version)
{
    if (!plugin_default_version_check (version, &gcc_version)) {
        return 1;
    }

    printf("%s:%i:plugin_init\n", __FILE__, __LINE__);

    Py_Initialize();

    if (!gcc_python_init_gcc_module(plugin_info)) {
        return 1;
    }

    PyRun_SimpleString("from time import time,ctime\n"
		       "print 'Today is',ctime(time())\n");
    PyRun_SimpleString("import gcc; help(gcc)\n");
    PyRun_SimpleString("import gcc; gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION)\n");
    Py_Finalize();

    printf("%s:%i:got here\n", __FILE__, __LINE__);

#define DEFEVENT(NAME) \
    if (NAME != PLUGIN_PASS_MANAGER_SETUP &&         \
        NAME != PLUGIN_INFO &&                       \
	NAME != PLUGIN_REGISTER_GGC_ROOTS &&         \
	NAME != PLUGIN_REGISTER_GGC_CACHES) {        \
    register_callback(plugin_info->base_name, NAME,  \
		      my_callback_for_##NAME, NULL); \
    }
# include "plugin.def"
# undef DEFEVENT

    return 0;
}
