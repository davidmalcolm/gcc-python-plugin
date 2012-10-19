/*
   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

#include <Python.h>
#include "gcc-python.h"

#include "gcc-python-closure.h"
#include "gcc-python-wrappers.h"

int plugin_is_GPL_compatible;

#include "plugin-version.h"

#include "cp/name-lookup.h" /* for global_namespace */
#include "tree.h"
#include "function.h"
#include "diagnostic.h"
#include "cgraph.h"
#include "opts.h"

/*
 * Use an unqualified name here and rely on dual search paths to let the
 * compiler find it.  This deals with c-pragma.h moving to a
 * subdirectory in newer versions of gcc.
 */
#include "c-pragma.h" /* for parse_in */

#if 0
#define LOG(msg) \
    (void)fprintf(stderr, "%s:%i:%s\n", __FILE__, __LINE__, (msg))
#else
#define LOG(msg) ((void)0);
#endif


#define GCC_PYTHON_TRACE_ALL_EVENTS 0
#if GCC_PYTHON_TRACE_ALL_EVENTS
static const char* event_name[] = {
#define DEFEVENT(NAME) \
  #NAME, 
# include "plugin.def"
# undef DEFEVENT
};

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

/*
  Weakly import parse_in; it will be non-NULL in the C and C++ frontend,
  but it's not available lto1 (link-time optimization)
*/
__typeof__ (parse_in) parse_in __attribute__ ((weak));

static PyObject*
gcc_python_define_macro(PyObject *self,
                        PyObject *args, PyObject *kwargs)
{
    const char *macro;
    char *keywords[] = {"macro",
                        NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "s:define_preprocessor_name", keywords,
                                     &macro)) {
        return NULL;
    }

    if (0) {
        fprintf(stderr, "gcc.define_macro(\"%s\")\n", macro);
    }

    if (!parse_in) {
        return PyErr_Format(PyExc_ValueError,
                            "gcc.define_macro(\"%s\") called without a compilation unit",
                            macro);
    }

    if (!gcc_python_is_within_event(NULL)) {
        return PyErr_Format(PyExc_ValueError,
                            "gcc.define_macro(\"%s\") called from outside an event callback",
                            macro);
    }

    cpp_define (parse_in, macro);

    Py_RETURN_NONE;
}

static PyObject *
gcc_python_set_location(PyObject *self, PyObject *args)
{
    PyGccLocation *loc_obj;
    if (!PyArg_ParseTuple(args,
                          "O!:set_location",
                          &gcc_LocationType, &loc_obj)) {
        return NULL;
    }

    input_location = loc_obj->loc;

    Py_RETURN_NONE;
}

static PyObject *
gcc_python_get_option_list(PyObject *self, PyObject *args)
{
    PyObject *result;
    int i;

    result = PyList_New(0);
    if (!result) {
	goto error;
    }

    for (i = 0; i < cl_options_count; i++) {
	PyObject *opt_obj = gcc_python_make_wrapper_opt_code((enum opt_code)i);
	if (!opt_obj) {
	    goto error;
	}
	if (-1 == PyList_Append(result, opt_obj)) {
	    Py_DECREF(opt_obj);
	    goto error;
	}
        Py_DECREF(opt_obj);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

static PyObject *
gcc_python_get_option_dict(PyObject *self, PyObject *args)
{
    PyObject *dict;
    size_t i;

    dict = PyDict_New();
    if (!dict) {
	goto error;
    }

    for (i = 0; i < cl_options_count; i++) {
	PyObject *opt_obj = gcc_python_make_wrapper_opt_code((enum opt_code)i);
        if (!opt_obj) {
	    goto error;
        }
        if (-1 == PyDict_SetItemString(dict,
                                       cl_options[i].opt_text,
                                       opt_obj)) {
	    Py_DECREF(opt_obj);
	    goto error;
	}
        Py_DECREF(opt_obj);
    }

    return dict;

 error:
    Py_XDECREF(dict);
    return NULL;
}

static PyObject *
gcc_python_get_parameters(PyObject *self, PyObject *args)
{
    PyObject *dict;
    size_t i;

    dict = PyDict_New();
    if (!dict) {
	goto error;
    }

    for (i = 0; i < get_num_compiler_params(); i++) {
        PyObject *param_obj = gcc_python_make_wrapper_param_num(i);
        if (!param_obj) {
	    goto error;
        }
        if (-1 == PyDict_SetItemString(dict,
                                       compiler_params[i].option,
                                       param_obj)) {
	    Py_DECREF(param_obj);
	    goto error;
	}
        Py_DECREF(param_obj);
    }

    return dict;

 error:
    Py_XDECREF(dict);
    return NULL;
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
        Py_DECREF(obj_var);
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

/*
  get_translation_units was made globally visible in gcc revision 164331:
    http://gcc.gnu.org/ml/gcc-cvs/2010-09/msg00625.html
    http://gcc.gnu.org/viewcvs?view=revision&revision=164331
*/
static PyObject *
gcc_python_get_translation_units(PyObject *self, PyObject *args)
{
    return VEC_tree_as_PyList(all_translation_units);
}

/* Weakly import global_namespace; it will be non-NULL for the C++ frontend: */
__typeof__ (global_namespace) global_namespace __attribute__ ((weak));

static PyObject *
gcc_python_get_global_namespace(PyObject *self, PyObject *args)
{
    /* (global_namespace will be NULL outside the C++ frontend, giving a
       result of None) */
    return gcc_python_make_wrapper_tree(global_namespace);
}

/* Dump files */

static PyObject *
gcc_python_dump(PyObject *self, PyObject *arg)
{
    PyObject *str_obj;
    /*
       gcc/output.h: declares:
           extern FILE *dump_file;
       This is NULL when not defined.
    */
    if (!dump_file) {
        /* The most common case; make it fast */
        Py_RETURN_NONE;
    }

    str_obj = PyObject_Str(arg);
    if (!str_obj) {
        return NULL;
    }

    /* FIXME: encoding issues */
    /* FIXME: GIL */
    if (!fwrite(gcc_python_string_as_string(str_obj),
                strlen(gcc_python_string_as_string(str_obj)),
                1,
                dump_file)) {
        Py_DECREF(str_obj);
        return PyErr_SetFromErrnoWithFilename(PyExc_IOError, dump_file_name);
    }

    Py_DECREF(str_obj);

    Py_RETURN_NONE;
}

static PyObject *
gcc_python_get_dump_file_name(PyObject *self, PyObject *noargs)
{
    /* gcc/tree-pass.h declares:
        extern const char *dump_file_name;
    */
    return gcc_python_string_or_none(dump_file_name);
}

static PyObject *
gcc_python_get_dump_base_name(PyObject *self, PyObject *noargs)
{
    /*
      The generated gcc/options.h has:
          #ifdef GENERATOR_FILE
          extern const char *dump_base_name;
          #else
            const char *x_dump_base_name;
          #define dump_base_name global_options.x_dump_base_name
          #endif
    */
    return gcc_python_string_or_none(dump_base_name);
}

static PyObject *
gcc_python_get_is_lto(PyObject *self, PyObject *noargs)
{
    /*
      The generated gcc/options.h has:
          #ifdef GENERATOR_FILE
          extern bool in_lto_p;
          #else
            bool x_in_lto_p;
          #define in_lto_p global_options.x_in_lto_p
          #endif
    */
    return PyBool_FromLong(in_lto_p);
}

static PyObject *
gcc_python_add_error(PyObject *self, PyObject *noargs)
{
    /* Fake an error, for working around bugs in GCC's error reporting
       e.g. http://gcc.gnu.org/bugzilla/show_bug.cgi?id=54962
     */
    errorcount++;
    Py_RETURN_NONE;
}


static PyMethodDef GccMethods[] = {
    {"register_attribute",
     (PyCFunction)gcc_python_register_attribute,
     (METH_VARARGS | METH_KEYWORDS),
     "Register an attribute."},

    {"register_callback",
     (PyCFunction)gcc_python_register_callback,
     (METH_VARARGS | METH_KEYWORDS),
     "Register a callback, to be called when various GCC events occur."},

    {"define_macro",
     (PyCFunction)gcc_python_define_macro,
     (METH_VARARGS | METH_KEYWORDS),
     "Pre-define a named value in the preprocessor."},

    /* Diagnostics: */
    {"permerror", gcc_python_permerror, METH_VARARGS,
     NULL},
    {"error",
     (PyCFunction)gcc_python_error,
     (METH_VARARGS | METH_KEYWORDS),
     ("Report an error\n"
      "FIXME\n")},
    {"warning",
     (PyCFunction)gcc_python_warning,
     (METH_VARARGS | METH_KEYWORDS),
     ("Report a warning\n"
      "FIXME\n")},
    {"inform",
     (PyCFunction)gcc_python_inform,
     (METH_VARARGS | METH_KEYWORDS),
     ("Report an information message\n"
      "FIXME\n")},
    {"set_location",
     (PyCFunction)gcc_python_set_location,
     METH_VARARGS,
     ("Temporarily set the default location for error reports\n")},

    /* Options: */
    {"get_option_list",
     gcc_python_get_option_list,
     METH_VARARGS,
     "Get all command-line options, as a list of gcc.Option instances"},

    {"get_option_dict",
     gcc_python_get_option_dict,
     METH_VARARGS,
     ("Get all command-line options, as a dict from command-line text strings "
      "to gcc.Option instances")},

    {"get_parameters", gcc_python_get_parameters, METH_VARARGS,
     "Get all tunable GCC parameters.  Returns a dictionary, mapping from"
     "option name -> gcc.Parameter instance"},

    {"get_variables", gcc_python_get_variables, METH_VARARGS,
     "Get all variables in this compilation unit as a list of gcc.Variable"},

    {"maybe_get_identifier", gcc_python_maybe_get_identifier, METH_VARARGS,
     "Get the gcc.IdentifierNode with this name, if it exists, otherwise None"},

    {"get_translation_units", gcc_python_get_translation_units, METH_VARARGS,
     "Get a list of all gcc.TranslationUnitDecl"},

    {"get_global_namespace", gcc_python_get_global_namespace, METH_VARARGS,
     "C++: get the global namespace (aka '::') as a gcc.NamespaceDecl"},

    /* Version handling: */
    {"get_plugin_gcc_version", gcc_python_get_plugin_gcc_version, METH_VARARGS,
     "Get the gcc.Version that this plugin was compiled with"},

    {"get_gcc_version", gcc_python_get_gcc_version, METH_VARARGS,
     "Get the gcc.Version for this version of GCC"},

    {"get_callgraph_nodes", gcc_python_get_callgraph_nodes, METH_VARARGS,
     "Get a list of all gcc.CallgraphNode instances"},

    /* Dump files */
    {"dump", gcc_python_dump, METH_O,
     "Dump str() of the argument to the current dump file (or silently discard it when no dump file is open)"},

    {"get_dump_file_name", gcc_python_get_dump_file_name, METH_NOARGS,
     "Get the name of the current dump file (or None)"},

    {"get_dump_base_name", gcc_python_get_dump_base_name, METH_NOARGS,
     "Get the base name used when writing dump files"},

    {"is_lto", gcc_python_get_is_lto, METH_NOARGS,
     "Determine whether or not we're being invoked during link-time optimization"},

    {"_add_error", gcc_python_add_error, METH_NOARGS,
     "Fake an error, for working around bugs in GCC's error reporting"},

    /* Garbage collection */
    {"_force_garbage_collection", gcc_python__force_garbage_collection, METH_VARARGS,
     "Forcibly trigger a single run of GCC's garbage collector"},

    {"_gc_selftest", gcc_python__gc_selftest, METH_VARARGS,
     "Run a garbage-collection selftest"},

    /* Sentinel: */
    {NULL, NULL, 0, NULL}
};

static struct 
{
    PyObject *module;
    PyObject *argument_dict;
    PyObject *argument_tuple;
} gcc_python_globals;

#if PY_MAJOR_VERSION == 3
static struct PyModuleDef gcc_module_def = {
    PyModuleDef_HEAD_INIT,
    "gcc",   /* name of module */
    NULL,
    -1,
    GccMethods
};
#endif

static PyMODINIT_FUNC PyInit_gcc(void)
{
#if PY_MAJOR_VERSION == 3
    PyObject *m;
    m = PyModule_Create(&gcc_module_def);
#else
    Py_InitModule("gcc", GccMethods);
#endif

#if PY_MAJOR_VERSION == 3
    return m;
#endif
}

static int
gcc_python_init_gcc_module(struct plugin_name_args *plugin_info)
{
    int i;

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

    /* Pass properties: */
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_gimple_any);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_gimple_lcf);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_gimple_leh);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_cfg);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_referenced_vars);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_ssa);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_no_crit_edges);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_rtl);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_gimple_lomp);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_cfglayout);
    PyModule_AddIntMacro(gcc_python_globals.module, PROP_gimple_lcx);

    /* Success: */
    return 1;
}

static void gcc_python_run_any_command(void)
{
    PyObject* command_obj; /* borrowed ref */
    int result;
    const char *command_str;

    command_obj = PyDict_GetItemString(gcc_python_globals.argument_dict, "command");
    if (!command_obj) {
        return;
    }

    command_str = gcc_python_string_as_string(command_obj);

    if (0) {
        fprintf(stderr, "Running: %s\n", command_str);
    }

    result = PyRun_SimpleString(command_str);
    if (-1 == result) {
        /* Error running the python command */
        Py_Finalize();
        exit(1);
    }
}

static void gcc_python_run_any_script(void)
{
    PyObject* script_name;
    FILE *fp;
    int result;
  
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
    result = PyRun_SimpleFile(fp, gcc_python_string_as_string(script_name));
    fclose(fp);
    if (-1 == result) {
        /* Error running the python script */
        Py_Finalize();
        exit(1);
    }
}

int
setup_sys(struct plugin_name_args *plugin_info)
{
    /*

     * Sets up "sys.plugin_full_name" as plugin_info->full_name.  This is the
     path to the plugin (as specified with -fplugin=)

     * Sets up "sys.plugin_base_name" as plugin_info->base_name.  This is the
     short name, of the plugin (filename without .so suffix)

     * Add the directory containing the plugin to "sys.path", so that it can
     find modules relative to itself without needing PYTHONPATH to be set up.
     (sys.path has already been initialized by the call to Py_Initialize)

     * If PLUGIN_PYTHONPATH is defined, add it to "sys.path"

    */
    int result = 0; /* failure */
    PyObject *full_name = NULL;
    PyObject *base_name = NULL;
    const char *program =
      "import sys;\n"
      "import os;\n"
      "sys.path.append(os.path.abspath(os.path.dirname(sys.plugin_full_name)))\n";

    /* Setup "sys.plugin_full_name" */
    full_name = gcc_python_string_from_string(plugin_info->full_name);
    if (!full_name) {
        goto error;
    }
    if (-1 == PySys_SetObject("plugin_full_name", full_name)) {
        goto error;
    }

    /* Setup "sys.plugin_base_name" */
    base_name = gcc_python_string_from_string(plugin_info->base_name);
    if (!base_name) {
        goto error;
    }
    if (-1 == PySys_SetObject("plugin_base_name", base_name)) {
        goto error;
    }

    /* Add the plugin's path to sys.path */
    if (-1 == PyRun_SimpleString(program)) {
        goto error;
    }

#ifdef PLUGIN_PYTHONPATH
    {
        /*
           Support having multiple builds of the plugin installed independently
           of each other, by supporting each having a directory for support
           files e.g. gccutils, libcpychecker, etc

           We do this by seeing if PLUGIN_PYTHONPATH was defined in the
           compile, and if so, adding it to sys.path:
        */
        const char *program2 =
            "import sys;\n"
            "import os;\n"
            "sys.path.append('" PLUGIN_PYTHONPATH "')\n";

        if (-1 == PyRun_SimpleString(program2)) {
            goto error;
        }
    }
#endif

    /* Success: */
    result = 1;

 error:
    Py_XDECREF(full_name);
    Py_XDECREF(base_name);
    return result;
}

/*
  Wired up to PLUGIN_FINISH, this callback handles finalization for the plugin:
*/
void
on_plugin_finish(void *gcc_data, void *user_data)
{
    /*
       Clean up the python runtime.

       For python 3, this flushes buffering of sys.stdout and sys.stderr
    */
    Py_Finalize();
}

extern int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version) __attribute__((nonnull));

int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version)
{
    LOG("plugin_init started");

    if (!plugin_default_version_check (version, &gcc_version)) {
        return 1;
    }

#if PY_MAJOR_VERSION >= 3
    /*
      Python 3 added internal buffering to sys.stdout and sys.stderr, but this
      leads to unpredictable interleavings of messages from gcc, such as from calling
      gcc.warning() vs those from python scripts, such as from print() and
      sys.stdout.write()

      Suppress the buffering, to better support mixed gcc/python output:
    */
    Py_UnbufferedStdioFlag = 1;
#endif

    PyImport_AppendInittab("gcc", PyInit_gcc);

    LOG("calling Py_Initialize...");

    Py_Initialize();

    LOG("Py_Initialize finished");

    gcc_python_globals.module = PyImport_ImportModule("gcc");

    PyEval_InitThreads();
  
    if (!gcc_python_init_gcc_module(plugin_info)) {
        return 1;
    }

    if (!setup_sys(plugin_info)) {
        return 1;
    }

    /* Init other modules */
    gcc_python_wrapper_init();

    /* FIXME: properly integrate them within the module hierarchy */

    gcc_python_version_init(version);

    autogenerated_callgraph_init_types();  /* FIXME: error checking! */
    autogenerated_cfg_init_types();  /* FIXME: error checking! */
    autogenerated_function_init_types();  /* FIXME: error checking! */
    autogenerated_gimple_init_types();  /* FIXME: error checking! */
    autogenerated_location_init_types();  /* FIXME: error checking! */
    autogenerated_option_init_types();  /* FIXME: error checking! */
    autogenerated_parameter_init_types();  /* FIXME: error checking! */
    autogenerated_pass_init_types();  /* FIXME: error checking! */
    autogenerated_pretty_printer_init_types();  /* FIXME: error checking! */
    autogenerated_rtl_init_types(); /* FIXME: error checking! */
    autogenerated_tree_init_types(); /* FIXME: error checking! */
    autogenerated_variable_init_types(); /* FIXME: error checking! */



    autogenerated_callgraph_add_types(gcc_python_globals.module);
    autogenerated_cfg_add_types(gcc_python_globals.module);
    autogenerated_function_add_types(gcc_python_globals.module);
    autogenerated_gimple_add_types(gcc_python_globals.module);
    autogenerated_location_add_types(gcc_python_globals.module);
    autogenerated_option_add_types(gcc_python_globals.module);
    autogenerated_parameter_add_types(gcc_python_globals.module);
    autogenerated_pass_add_types(gcc_python_globals.module);
    autogenerated_pretty_printer_add_types(gcc_python_globals.module);
    autogenerated_rtl_add_types(gcc_python_globals.module);
    autogenerated_tree_add_types(gcc_python_globals.module);
    autogenerated_variable_add_types(gcc_python_globals.module);


    /* Register at-exit finalization for the plugin: */
    register_callback(plugin_info->base_name, PLUGIN_FINISH,
                      on_plugin_finish, NULL);

    gcc_python_run_any_command();
    gcc_python_run_any_script();

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

    LOG("init_plugin finished");

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
  "double_int" is declared in gcc/double-int.h as a pair of HOST_WIDE_INT.
  These in turn are defined in gcc/hwint.h as a #define to one of "long",
  "long long", or "__int64".

  It appears that they can be interpreted as either "unsigned" or "signed"

  How to convert this to other types?
  We "cheat", and take it through the decimal representation, then convert
  from decimal.  This is probably slow, but is (I hope) at least correct.
*/
void
gcc_python_double_int_as_text(double_int di, bool is_unsigned,
                              char *out, int bufsize)
{
    FILE *f;
    assert(out);
    assert(bufsize > 256); /* FIXME */

    out[0] = '\0';
    f = fmemopen(out, bufsize, "w");
    dump_double_int (f, di, is_unsigned);
    fclose(f);
}

PyObject *
gcc_python_int_from_double_int(double_int di, bool is_unsigned)
{
    PyObject *long_obj;
#if PY_MAJOR_VERSION < 3
    long long_val;
    int overflow;
#endif
    char buf[512]; /* FIXME */
    gcc_python_double_int_as_text(di, is_unsigned, buf, sizeof(buf));

    long_obj = PyLong_FromString(buf, NULL, 10);
    if (!long_obj) {
        return NULL;
    }
#if PY_MAJOR_VERSION >= 3
    return long_obj;
#else
    long_val = PyLong_AsLongAndOverflow(long_obj, &overflow);
    if (overflow) {
        /* Doesn't fit in a PyIntObject; use the PyLongObject: */
        return long_obj;
    } else {
        /* Fits in a PyIntObject: use that */
        PyObject *int_obj = PyInt_FromLong(long_val);
        if (!int_obj) {
            return long_obj;
        }
        Py_DECREF(long_obj);
        return int_obj;
    }
#endif
}

/*
   GCC's headers "poison" strdup to make it unavailable, so we provide our own.

   The buffer is allocated using PyMem_Malloc
*/
char *
gcc_python_strdup(const char *str)
{
    char *result;
    char *dst;

    result = (char*)PyMem_Malloc(strlen(str) + 1);

    if (!result) {
        return NULL;
    }

    dst = result;
    while (*str) {
        *(dst++) = *(str++);
    }
    *dst = '\0';

    return result;
}

void gcc_python_print_exception(const char *msg)
{
    /* Handler for Python exceptions */
    assert(msg);

    /*
       Emit a gcc error, using GCC's "input_location"

       Typically, by the time our code is running, that's generally just the
       end of the source file.

       The value is saved and restored whenever calling into Python code, and
       within passes is initialized to the top of the function; it can be
       temporarily overridden using gcc.set_location()
    */
    error_at(input_location, "%s", msg);

    /* Print the traceback: */
    PyErr_PrintEx(1);
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
