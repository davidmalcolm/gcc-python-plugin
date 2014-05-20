/*
  Example of a historical reference-counting error:

  The code below was extracted from:
    https://github.com/lericson/pylibmc/blob/bc1787c3e74ddebb44736fc4eaf8333a2e51a80f/_pylibmcmodule.c

  TODO: does it find the bug?  can we simplify the code (e.g. just on the one function?)
  
  FIXME: don't add this: it adds a dependency on libmemcached
*/

/*
  Add this here to fool the test harness:
    #include <Python.h>
 */

/**
 * _pylibmc: hand-made libmemcached bindings for Python
 *
 * Copyright (c) 2008, Ludvig Ericson
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 * 
 *  - Redistributions of source code must retain the above copyright notice,
 *  this list of conditions and the following disclaimer.
 * 
 *  - Redistributions in binary form must reproduce the above copyright notice,
 *  this list of conditions and the following disclaimer in the documentation
 *  and/or other materials provided with the distribution.
 * 
 *  - Neither the name of the author nor the names of the contributors may be
 *  used to endorse or promote products derived from this software without
 *  specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include "_pylibmcmodule.h"

/* Extracted copy of PylibMC_Client_get_multi */
static PyObject *PylibMC_Client_get_multi(
        PylibMC_Client *self, PyObject *args, PyObject *kwds) {
    PyObject *key_seq, **key_objs, *retval = NULL;
    char **keys, *prefix = NULL;
    char *err_func = NULL;
    memcached_result_st *res, *results = NULL;
    int prefix_len = 0;
    Py_ssize_t i;
    PyObject *key_it, *ckey;
    size_t *key_lens;
    size_t nkeys, nresults = 0;
    memcached_return rc;

    static char *kws[] = { "keys", "key_prefix", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|s#:get_multi", kws,
            &key_seq, &prefix, &prefix_len))
        return NULL;

    if ((nkeys = (size_t)PySequence_Length(key_seq)) == -1)
        return NULL;

    /* Populate keys and key_lens. */
    keys = PyMem_New(char *, nkeys);
    key_lens = PyMem_New(size_t, nkeys);
    key_objs = PyMem_New(PyObject *, nkeys);
    if (!keys || !key_lens || !key_objs) {
        PyMem_Free(keys);
        PyMem_Free(key_lens);
        PyMem_Free(key_objs);
        return PyErr_NoMemory();
    }

    /* Clear potential previous exception, because we explicitly check for
     * exceptions as a loop predicate. */
    PyErr_Clear();

    /* Iterate through all keys and set lengths etc. */
    key_it = PyObject_GetIter(key_seq);
    i = 0;
    while ((ckey = PyIter_Next(key_it)) != NULL) {
        char *key;
        Py_ssize_t key_len;
        PyObject *rkey;

        assert(i < nkeys);

        if (PyErr_Occurred() || !_PylibMC_CheckKey(ckey)) {
            nkeys = i;
            goto earlybird;
        }

        PyString_AsStringAndSize(ckey, &key, &key_len);

        key_lens[i] = (size_t)(key_len + prefix_len);

        /* Skip empty keys */
        if (!key_lens[i])
            continue;

        /* determine rkey, the prefixed ckey */
        if (prefix != NULL) {
            rkey = PyString_FromStringAndSize(prefix, prefix_len);
            PyString_Concat(&rkey, ckey);
            if (rkey == NULL)
                goto earlybird;
            rkey = PyString_FromFormat("%s%s",
                    prefix, PyString_AS_STRING(ckey));
        } else {
            Py_INCREF(ckey);
            rkey = ckey;
        }
        Py_DECREF(ckey);

        keys[i] = PyString_AS_STRING(rkey);
        key_objs[i++] = rkey;
    }
    nkeys = i;
    Py_XDECREF(key_it);

    if (nkeys == 0) {
        retval = PyDict_New();
        goto earlybird;
    } else if (PyErr_Occurred()) {
        nkeys--;
        goto earlybird;
    }

    /* TODO Make an iterator interface for getting each key separately.
     *
     * This would help large retrievals, as a single dictionary containing all
     * the data at once isn't needed. (Should probably look into if it's even
     * worth it.)
     */
    Py_BEGIN_ALLOW_THREADS;
    rc = pylibmc_memcached_fetch_multi(self->mc,
                                       keys, nkeys, key_lens,
                                       &results, &nresults,
                                       &err_func);
    Py_END_ALLOW_THREADS;

    if (rc != MEMCACHED_SUCCESS) {
        PylibMC_ErrFromMemcached(self, err_func, rc);
        goto earlybird;
    }

    retval = PyDict_New();

    for (i = 0; i < nresults; i++) {
        PyObject *val, *key_obj;
        int rc;

        res = results + i;

        /* Explicitly construct a key string object so that NUL-bytes and the
         * likes can be contained within the keys (this is possible in the
         * binary protocol.) */
        key_obj = PyString_FromStringAndSize(memcached_result_key_value(res) + prefix_len,
                                             memcached_result_key_length(res) - prefix_len);
        if (key_obj == NULL)
            goto unpack_error;

        /* Parse out value */
        val = _PylibMC_parse_memcached_result(res);
        if (val == NULL)
            goto unpack_error;

        rc = PyDict_SetItem(retval, key_obj, val);
        Py_DECREF(key_obj);
        Py_DECREF(val);

        if (rc != 0)
            goto unpack_error;

        continue;

unpack_error:
            Py_DECREF(retval);
            break;
    }

earlybird:
    PyMem_Free(key_lens);
    PyMem_Free(keys);

    for (i = 0; i < nkeys; i++)
        Py_DECREF(key_objs[i]);
    PyMem_Free(key_objs);

    if (results != NULL) {
        for (i = 0; i < nresults && results != NULL; i++) {
            memcached_result_free(results + i);
        }
        PyMem_Free(results);
    }

    /* Not INCREFing because the only two outcomes are NULL and a new dict.
     * We're the owner of that dict already, so. */
    return retval;
}
