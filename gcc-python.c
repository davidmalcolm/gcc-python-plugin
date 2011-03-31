#include <Python.h>
#include <gcc-plugin.h>

#include "gcc-python-closure.h"

int plugin_is_GPL_compatible;

#include "plugin-version.h"


#if GCC_PYTHON_TRACE_ALL_EVENTS
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
#endif /* GCC_PYTHON_TRACE_ALL_EVENTS */

//gcc_debug_callback(enum plugin_event event, void *gcc_data, void *user_data)

static void
gcc_python_callback_for_PLUGIN_PASS_EXECUTION(void *gcc_data, void *user_data)
{
  //gcc_data: struct opt_pass *pass
    struct opt_pass *pass = (struct opt_pass *)gcc_data;
    struct callback_closure *closure = (struct callback_closure *)user_data;
    PyObject *wrapped_gcc_data = NULL;
    PyObject *args = NULL;
    PyObject *result = NULL;

    PyGILState_STATE gstate;

    //printf("%s:%i:gcc_python_callback_for_PLUGIN_PASS_EXECUTION(%p, %p)\n", __FILE__, __LINE__, gcc_data, user_data);
    //printf("%s:%i:%p:%p\n", __FILE__, __LINE__, closure->callback, closure->data);

    assert(pass);
    assert(closure);

    //printf("%s:%i:gcc_python_callback_for_PLUGIN_PASS_EXECUTION bar\n", __FILE__, __LINE__);

    gstate = PyGILState_Ensure();

    //printf("%s:%i:gcc_python_callback_for_PLUGIN_PASS_EXECUTION foo\n", __FILE__, __LINE__);

    //PyObject_Print(closure->callback, stdout, 0);
    //PyObject_Print(closure->extraargs, stdout, 0);

    // FIXME: supply "pass" to the callback:
    // FIXME: for now, simply pass the address of "pass" as an int object (useless, really)
    wrapped_gcc_data = PyLong_FromLong((long)pass);
    if (!wrapped_gcc_data) {
        goto cleanup;
    }

    args = gcc_python_closure_make_args(closure, wrapped_gcc_data);
    if (!args) {
        goto cleanup;
    }
    result = PyObject_Call(closure->callback, args, NULL);

    // FIXME: the result is ignored
    // FIXME: exception handling?

cleanup:
    Py_XDECREF(wrapped_gcc_data);
    Py_XDECREF(args);
    Py_XDECREF(result);

    PyGILState_Release(gstate);
    return;


		       
}



static PyObject*
gcc_python_register_callback(PyObject *self, PyObject *args)
{
    int event;
    PyObject *callback = NULL;
    PyObject *extraargs = NULL;
    struct callback_closure *closure;

    if (!PyArg_ParseTuple(args, "iO|O:register_callback", &event, &callback, &extraargs)) {
        return NULL;
    }
    // FIXME: to be written
    //return NULL;
    printf("%s:%i:gcc_python_register_callback\n", __FILE__, __LINE__);

    closure = gcc_python_closure_new(callback, extraargs);
    if (!closure) {
        return PyErr_NoMemory();
    }

    switch ((enum plugin_event)event) {
    case PLUGIN_PASS_EXECUTION:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_PLUGIN_PASS_EXECUTION,
			  closure);
	break;

    default:
        PyErr_Format(PyExc_ValueError, "event type %i invalid (or not wired up yet)", event);
	return NULL;
    }
    //    register_callback(plugin_info->base_name, (enum plugin_event)event,
    //my_callback_for_##NAME, NULL);	      
    
    Py_RETURN_NONE;
    //return Py_BuildValue("i", numargs);
}

static PyMethodDef GccMethods[] = {
    {"register_callback", gcc_python_register_callback, METH_VARARGS,
     "Register a callback, to be called when various GCC events occur."},

    /* Sentinel: */
    {NULL, NULL, 0, NULL}
};

static struct 
{
    PyObject *module;
    PyObject *argument_dict;
    PyObject *argument_tuple;
} gcc_python_globals;

static int
gcc_python_init_gcc_module(struct plugin_name_args *plugin_info)
{
    int i;

    gcc_python_globals.module = Py_InitModule("gcc", GccMethods);
    if (!gcc_python_globals.module) {
        return 0;
    }

    /* Set up int constants for each of the enum plugin_event values: */
    #define DEFEVENT(NAME) \
       PyModule_AddIntMacro(gcc_python_globals.module, NAME);
    # include "plugin.def"
    # undef DEFEVENT

    gcc_python_globals.argument_dict = PyDict_New();
    if (!gcc_python_globals.argument_dict) {
        return 0;
    }

    gcc_python_globals.argument_tuple = PyTuple_New(plugin_info->argc);
    if (!gcc_python_globals.argument_tuple) {
        return 0;
    }

    /* PySys_SetArgvEx(plugin_info->argc, plugin_info->argv, 0); */
    for (i=0; i<plugin_info->argc; i++) {
	struct plugin_argument *arg = &plugin_info->argv[i];
        PyObject *key;
        PyObject *value;
	PyObject *pair;
      
	key = PyString_FromString(arg->key);
	if (arg->value) {
	    value = PyString_FromString(plugin_info->argv[i].value);
	} else {
  	    value = Py_None;
	}
        PyDict_SetItem(gcc_python_globals.argument_dict, key, value);
	// FIXME: ref counts?

	pair = Py_BuildValue("(s, s)", arg->key, arg->value);
	if (!pair) {
  	    return 1;
	}
        PyTuple_SetItem(gcc_python_globals.argument_tuple, i, pair);

    }
    PyModule_AddObject(gcc_python_globals.module, "argument_dict", gcc_python_globals.argument_dict);
    PyModule_AddObject(gcc_python_globals.module, "argument_tuple", gcc_python_globals.argument_tuple);

    /* Success: */
    return 1;
}

static void gcc_python_run_any_script(void)
{
    PyObject* script_name;
    FILE *fp;
  
    script_name = PyDict_GetItemString(gcc_python_globals.argument_dict, "script");
    if (!script_name) {
        return;
    }

    fp = fopen(PyString_AsString(script_name), "r");
    if (!fp) {
        fprintf(stderr,
		"Unable to read python script: %s\n",
		PyString_AsString(script_name));
	return;
    }
    PyRun_SimpleFile(fp, PyString_AsString(script_name));
    fclose(fp);
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
    PyEval_InitThreads();
  
    if (!gcc_python_init_gcc_module(plugin_info)) {
        return 1;
    }

    gcc_python_run_any_script();

    /* 
       Can we ever call Py_Finalize ?
       There doesn't seem to be an exit hook for a plugin
    */

    printf("%s:%i:got here\n", __FILE__, __LINE__);

#if GCC_PYTHON_TRACE_ALL_EVENTS
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
#endif /* GCC_PYTHON_TRACE_ALL_EVENTS */

    return 0;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
