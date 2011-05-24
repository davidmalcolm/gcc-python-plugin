#include <Python.h>
#include "gcc-python.h"

#include "gcc-python-closure.h"
#include "gcc-python-wrappers.h"

int plugin_is_GPL_compatible;

#include "plugin-version.h"

#include "tree.h"
#include "function.h"
#include "diagnostic.h"
#include "cgraph.h"

#define GCC_PYTHON_TRACE_ALL_EVENTS 0
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
    However, it seems at this point to have initialized these:
      static const struct attribute_spec *attribute_tables[4];
      static htab_t attribute_hash;

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

  PLUGIN_FINISH_TYPE
    gcc_data=tree
    Called from c_parser_declspecs (parser=0x7fffef559730, specs=0x15296d0, scspec_ok=1 '\001', typespec_ok=1 '\001', start_attr_ok=<optimized out>, la=cla_nonabstract_decl) at ../../gcc/c-parser.c:2111

  PLUGIN_PRAGMA
    gcc_data=0x0
    Called from: init_pragma at ../../gcc/c-family/c-pragma.c:1321
    to  "Allow plugins to register their own pragmas."
*/

static void
trace_callback(enum plugin_event event, void *gcc_data, void *user_data)
{
    fprintf(stderr,
	    "%s:%i:trace_callback(%s, %p, %p)\n",
	    __FILE__, __LINE__, event_name[event], gcc_data, user_data);
    fprintf(stderr, "  cfun:%p\n", cfun);
}

#define DEFEVENT(NAME) \
static void trace_callback_for_##NAME(void *gcc_data, void *user_data) \
{ \
     trace_callback(NAME, gcc_data, user_data); \
}
# include "plugin.def"
# undef DEFEVENT
#endif /* GCC_PYTHON_TRACE_ALL_EVENTS */

static void
gcc_python_finish_invoking_callback(PyGILState_STATE gstate, PyObject *wrapped_gcc_data, void *user_data)
{
    struct callback_closure *closure = (struct callback_closure *)user_data;
    PyObject *args = NULL;
    PyObject *result = NULL;

    assert(closure);
    /* We take ownership of wrapped_gcc_data, which could also be NULL */

    if (!wrapped_gcc_data) {
        goto cleanup;
    }

    args = gcc_python_closure_make_args(closure, wrapped_gcc_data);
    if (!args) {
        goto cleanup;
    }
    result = PyObject_Call(closure->callback, args, NULL);

    if (!result) {
	PyErr_PrintEx(1);

	/* Treat an unhandled Python error as a fatal GCC-level error */
	fatal_error("Unhandled Python exception raised within callback");
    }

    // FIXME: the result is ignored

cleanup:
    Py_XDECREF(wrapped_gcc_data);
    Py_XDECREF(args);
    Py_XDECREF(result);

    PyGILState_Release(gstate);
}

static void
gcc_python_callback_for_tree(void *gcc_data, void *user_data)
{
    PyGILState_STATE gstate;
    tree t = (tree)gcc_data;

    gstate = PyGILState_Ensure();

    gcc_python_finish_invoking_callback(gstate, 
					gcc_python_make_wrapper_tree(t),
					user_data);
}

static void
gcc_python_callback_for_PLUGIN_PASS_EXECUTION(void *gcc_data, void *user_data)
{
    PyGILState_STATE gstate;
    struct opt_pass *pass = (struct opt_pass *)gcc_data;

    //printf("%s:%i:(%p, %p)\n", __FILE__, __LINE__, gcc_data, user_data);
    assert(pass);

    gstate = PyGILState_Ensure();

    gcc_python_finish_invoking_callback(gstate, 
					gcc_python_make_wrapper_pass(pass),
					user_data);
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

    //printf("%s:%i:gcc_python_register_callback\n", __FILE__, __LINE__);

    closure = gcc_python_closure_new(callback, extraargs);
    if (!closure) {
        return PyErr_NoMemory();
    }

    switch ((enum plugin_event)event) {
    case PLUGIN_PRE_GENERICIZE:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_tree,
			  closure);
	break;
	
    case PLUGIN_PASS_EXECUTION:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_PLUGIN_PASS_EXECUTION,
			  closure);
	break;

    case PLUGIN_FINISH_TYPE:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_tree,
			  closure);
	break;

    default:
        PyErr_Format(PyExc_ValueError, "event type %i invalid (or not wired up yet)", event);
	return NULL;
    }
    
    Py_RETURN_NONE;
}

static PyObject*
gcc_python_permerror(PyObject *self, PyObject *args)
{
    PyGccLocation *loc = NULL;
    char *msgid = NULL;
    PyObject *result_obj = NULL;
    bool result_b;

    if (!PyArg_ParseTuple(args,
			  "O!"
			  "s"
			  ":permerror",
			  &gcc_LocationType, &loc, 
			  &msgid)) {
        return NULL;
    }

    /* Invoke the GCC function: */
    result_b = permerror(loc->loc, msgid);

    result_obj = PyBool_FromLong(result_b);

    return result_obj;
}

static PyObject *
gcc_python_get_variables(PyObject *self, PyObject *args)
{
    PyObject *result;
    struct varpool_node *n;

    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    for (n = varpool_nodes; n; n = n->next) {
	PyObject *obj_var = gcc_python_make_wrapper_variable(n);
	if (!obj_var) {
	    goto error;
	}
	if (-1 == PyList_Append(result, obj_var)) {
	    Py_DECREF(obj_var);
	    goto error;
	}
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

static PyObject *
gcc_python_maybe_get_identifier(PyObject *self, PyObject *args)
{
    const char *str;
    tree t;

    if (!PyArg_ParseTuple(args,
			  "s:maybe_get_identifier",
			  &str)) {
	return NULL;
    }

    t = maybe_get_identifier(str);
    return gcc_python_make_wrapper_tree(t);
}

static PyObject *
gcc_python_get_translation_units(PyObject *self, PyObject *args)
{
    return VEC_tree_as_PyList(all_translation_units);
}


static PyMethodDef GccMethods[] = {
    {"register_callback", gcc_python_register_callback, METH_VARARGS,
     "Register a callback, to be called when various GCC events occur."},
    
    {"permerror", gcc_python_permerror, METH_VARARGS,
     NULL},

    {"get_variables", gcc_python_get_variables, METH_VARARGS,
     "Get all variables in this compilation unit as a list of gcc.Variable"},

    {"maybe_get_identifier", gcc_python_maybe_get_identifier, METH_VARARGS,
     "Get the gcc.IdentifierNode with this name, if it exists, otherwise None"},

    {"get_translation_units", gcc_python_get_translation_units, METH_VARARGS,
     "Get a list of all gcc.TranslationUnitDecl"},

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
      
	key = gcc_python_string_from_string(arg->key);
	if (arg->value) {
            value = gcc_python_string_from_string(plugin_info->argv[i].value);
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

    fp = fopen(gcc_python_string_as_string(script_name), "r");
    if (!fp) {
        fprintf(stderr,
		"Unable to read python script: %s\n",
                gcc_python_string_as_string(script_name));
	exit(1);
    }
    PyRun_SimpleFile(fp, gcc_python_string_as_string(script_name));
    fclose(fp);
}



int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version)
{
    if (!plugin_default_version_check (version, &gcc_version)) {
        return 1;
    }

    //printf("%s:%i:plugin_init\n", __FILE__, __LINE__);

    Py_Initialize();
    PyEval_InitThreads();
  
    if (!gcc_python_init_gcc_module(plugin_info)) {
        return 1;
    }

    /* Init other modules */
    /* FIXME: properly integrate them within the module hierarchy */

    autogenerated_cfg_init_types();  /* FIXME: error checking! */
    autogenerated_function_init_types();  /* FIXME: error checking! */
    autogenerated_gimple_init_types();  /* FIXME: error checking! */
    autogenerated_location_init_types();  /* FIXME: error checking! */
    autogenerated_pass_init_types();  /* FIXME: error checking! */
    autogenerated_pretty_printer_init_types();  /* FIXME: error checking! */
    autogenerated_tree_init_types(); /* FIXME: error checking! */
    autogenerated_variable_init_types(); /* FIXME: error checking! */



    autogenerated_cfg_add_types(gcc_python_globals.module);
    autogenerated_function_add_types(gcc_python_globals.module);
    autogenerated_gimple_add_types(gcc_python_globals.module);
    autogenerated_location_add_types(gcc_python_globals.module);
    autogenerated_pass_add_types(gcc_python_globals.module);
    autogenerated_pretty_printer_add_types(gcc_python_globals.module);
    autogenerated_tree_add_types(gcc_python_globals.module);
    autogenerated_variable_add_types(gcc_python_globals.module);


    //    inittree();

    gcc_python_run_any_script();

    /* 
       Can we ever call Py_Finalize ?
       There doesn't seem to be an exit hook for a plugin
    */

    //printf("%s:%i:got here\n", __FILE__, __LINE__);

#if GCC_PYTHON_TRACE_ALL_EVENTS
#define DEFEVENT(NAME) \
    if (NAME != PLUGIN_PASS_MANAGER_SETUP &&         \
        NAME != PLUGIN_INFO &&                       \
	NAME != PLUGIN_REGISTER_GGC_ROOTS &&         \
	NAME != PLUGIN_REGISTER_GGC_CACHES) {        \
    register_callback(plugin_info->base_name, NAME,  \
		      trace_callback_for_##NAME, NULL); \
    }
# include "plugin.def"
# undef DEFEVENT
#endif /* GCC_PYTHON_TRACE_ALL_EVENTS */

    return 0;
}

PyObject *
gcc_python_string_or_none(const char *str_or_null)
{
    if (str_or_null) {
	return gcc_python_string_from_string(str_or_null);
    } else {
	Py_RETURN_NONE;
    }
}


/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
