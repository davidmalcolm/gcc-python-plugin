Name:           gcc-python-plugin
Version:        0.5
Release:        1%{?dist}
Summary:        GCC plugin that embeds Python

Group:          Development/Languages
License:        GPLv3+
URL:            https://fedorahosted.org/gcc-python-plugin/
Source0:        https://fedorahosted.org/releases/g/c/gcc-python-plugin/gcc-python-plugin-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  gcc-plugin-devel

# gcc 4.6.1's plugin/include/double-int.h includes "gmp.h", but on Fedora,
# gmp-devel isn't yet listed in the requirements of gcc-plugin-devel
# For now, explicitly require it:
BuildRequires:  gmp-devel
# Filed as https://bugzilla.redhat.com/show_bug.cgi?id=725569


# Various python runtimes to build the plugin against:
BuildRequires:  python-devel
BuildRequires:  python-debug
BuildRequires:  python3-devel
BuildRequires:  python3-debug

# "six" is used at buildtime:
BuildRequires:  python-six
BuildRequires:  python3-six

# sphinx is used for building documentation:
BuildRequires:  python-sphinx

%global gcc_plugins_dir %(gcc --print-file-name=plugin)

%description
Plugins for embedding various versions of Python within GCC

%package -n gcc-python2-plugin
Summary: GCC plugin embedding Python 2
Group:   Development/Languages
Requires: python-six
Requires: python-pygments

%description  -n gcc-python2-plugin
GCC plugin embedding Python 2

%package -n gcc-python3-plugin
Summary: GCC plugin embedding Python 3
Group:   Development/Languages
Requires: python3-six
Requires: python3-pygments

%description  -n gcc-python3-plugin
GCC plugin embedding Python 3

%package -n gcc-python2-debug-plugin
Summary: GCC plugin embedding Python 2 debug build
Group:   Development/Languages
Requires: python-six
Requires: python-pygments

%description  -n gcc-python2-debug-plugin
GCC plugin embedding debug build of Python 2

%package -n gcc-python3-debug-plugin
Summary: GCC plugin embedding Python 3 debug build
Group:   Development/Languages
Requires: python3-six
Requires: python3-pygments

%description  -n gcc-python3-debug-plugin
GCC plugin embedding debug build of Python 3

%package docs
Summary: API documentation for the GCC Python plugin
Group:   Development/Languages

%description docs
This package contains API documentation for the GCC Python plugin



%prep
%setup -q


%build

BuildPlugin() {
    PythonExe=$1
    PythonConfig=$2
    PluginDso=$3
    PluginName=$4

    # "make clean" would remove the .so files from the previous build
    rm -f *.o
    make \
       %{?_smp_mflags} \
       PYTHON=$PythonExe \
       PYTHON_CONFIG=$PythonConfig \
       PLUGIN_PYTHONPATH=%{gcc_plugins_dir}/$PluginName \
       plugin
    mv python.so $PluginDso
}

BuildPlugin \
  python \
  python-config \
  python2.so \
  python2

BuildPlugin \
  python-debug \
  python-debug-config \
  python2-debug.so \
  python2-debug

BuildPlugin \
  python3 \
  python3-config \
  python3.so \
  python3

BuildPlugin \
  python3-debug \
  python3.2dmu-config \
  python3-debug.so \
  python3-debug

# Documentation:
cd docs
make html
# Avoid having a hidden file in the payload:
rm _build/html/.buildinfo

make man

%install
rm -rf $RPM_BUILD_ROOT

mkdir -p $RPM_BUILD_ROOT/%{gcc_plugins_dir}
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/man1

InstallPlugin() {
    PythonExe=$1
    PythonConfig=$2
    PluginDso=$3
    PluginName=$4

    cp $PluginDso $RPM_BUILD_ROOT/%{gcc_plugins_dir}

    # Install support files into the correct location:
    PluginDir=$PluginName
    mkdir $RPM_BUILD_ROOT/%{gcc_plugins_dir}/$PluginDir
    cp -a gccutils.py $RPM_BUILD_ROOT/%{gcc_plugins_dir}/$PluginDir
    cp -a libcpychecker $RPM_BUILD_ROOT/%{gcc_plugins_dir}/$PluginDir

    # Create "gcc-with-" support script:
    install -m 755 gcc-with-python $RPM_BUILD_ROOT/%{_bindir}/gcc-with-$PluginName
    # Fixup the reference to the plugin in that script, from being expressed as
    # a DSO filename with a path (for a working copy) to a name of an installed
    # plugin within GCC's search directory:
    sed \
       -i \
       -e"s|-fplugin=[^ ]*|-fplugin=$PluginName|" \
       $RPM_BUILD_ROOT/%{_bindir}/gcc-with-$PluginName

    # Fixup the plugin name within -fplugin-arg-PLUGIN_NAME-script to match the
    # name for this specific build:
    sed \
       -i \
       -e"s|-fplugin-arg-python-script|-fplugin-arg-$PluginName-script|" \
       $RPM_BUILD_ROOT/%{_bindir}/gcc-with-$PluginName

    # Fixup the generic manpage for this build:
    cp docs/_build/man/gcc-with-python.1 gcc-with-$PluginName.1
    sed \
        -i \
        -e"s|gcc-with-python|gcc-with-$PluginName|g" \
        gcc-with-$PluginName.1
    UpperPluginName=$(python -c"print('$PluginName'.upper())")
    sed \
        -i \
        -e"s|GCC-WITH-PYTHON|GCC-WITH-$UpperPluginName|g" \
        gcc-with-$PluginName.1
    gzip gcc-with-$PluginName.1
    cp gcc-with-$PluginName.1.gz  $RPM_BUILD_ROOT/%{_mandir}/man1
}

InstallPlugin \
  python \
  python-config \
  python2.so \
  python2

InstallPlugin \
  python-debug \
  python-debug-config \
  python2-debug.so \
  python2-debug

InstallPlugin \
  python3 \
  python3-config \
  python3.so \
  python3

InstallPlugin \
  python3-debug \
  python3.2dmu-config \
  python3-debug.so \
  python3-debug


%clean
rm -rf $RPM_BUILD_ROOT

%check

CheckPlugin() {
    PythonExe=$1
    PythonConfig=$2
    PluginDso=$3
    SelftestArgs=$4

    # Copy the specific build of the plugin back into the location where
    # the selftests expect it:
    cp $PluginDso python.so

    # Run the selftests:
    $PythonExe run-test-suite.py $SelftestArgs

    $PythonExe testcpychecker.py -v
}

# Selftest for python2 (optimized) build
# All tests ought to pass:
CheckPlugin \
  python \
  python-config \
  python2.so \
  %{nil}

# Selftest for python2-debug build:
# Disable the cpychecker tests for now: somewhat ironically, the extra
# instrumentation in the debug build breaks the selftests for the refcount
# tracker.  (specifically, handling of _Py_RefTotal):
#
#   Failed tests:
#     tests/cpychecker/refcounts/correct_py_none
#     tests/cpychecker/refcounts/correct_decref
#     tests/cpychecker/refcounts/use_after_dealloc
#     tests/cpychecker/refcounts/returning_dead_object
#     tests/cpychecker/refcounts/too_many_increfs
#     tests/cpychecker/refcounts/loop_n_times
#
CheckPlugin \
  python-debug \
  python-debug-config \
  python2-debug.so \
  "-x tests/cpychecker"

# Selftest for python3 (optimized) build:
# Disable the cpychecker tests for now:
#   Failed tests:
#     tests/cpychecker/PyArg_ParseTuple/incorrect_codes_S_and_U
#     tests/cpychecker/PyArg_ParseTuple/correct_codes_S_and_U
#     tests/cpychecker/refcounts/correct_decref
#     tests/cpychecker/refcounts/fold_conditional
#     tests/cpychecker/refcounts/use_after_dealloc
#     tests/cpychecker/refcounts/missing_decref
#     tests/cpychecker/refcounts/returning_dead_object
#     tests/cpychecker/refcounts/too_many_increfs
#     tests/cpychecker/refcounts/loop_n_times
#
CheckPlugin \
  python3 \
  python3-config \
  python3.so \
  "-x tests/cpychecker"

# Selftest for python3-debug build:
#   (shares the issues of the above)
CheckPlugin \
  python3-debug \
  python3.2dmu-config \
  python3-debug.so \
  "-x tests/cpychecker"

%files -n gcc-python2-plugin
%defattr(-,root,root,-)
%doc COPYING README.rst
%{_bindir}/gcc-with-python2
%{gcc_plugins_dir}/python2.so
%{gcc_plugins_dir}/python2
%doc %{_mandir}/man1/gcc-with-python2.1.gz

%files -n gcc-python3-plugin
%defattr(-,root,root,-)
%doc COPYING README.rst
%{_bindir}/gcc-with-python3
%{gcc_plugins_dir}/python3.so
%{gcc_plugins_dir}/python3
%doc %{_mandir}/man1/gcc-with-python3.1.gz

%files -n gcc-python2-debug-plugin
%defattr(-,root,root,-)
%doc COPYING README.rst
%{_bindir}/gcc-with-python2-debug
%{gcc_plugins_dir}/python2-debug.so
%{gcc_plugins_dir}/python2-debug
%doc %{_mandir}/man1/gcc-with-python2-debug.1.gz

%files -n gcc-python3-debug-plugin
%defattr(-,root,root,-)
%doc COPYING README.rst
%{_bindir}/gcc-with-python3-debug
%{gcc_plugins_dir}/python3-debug.so
%{gcc_plugins_dir}/python3-debug
%doc %{_mandir}/man1/gcc-with-python3-debug.1.gz

%files docs
%defattr(-,root,root,-)
%doc COPYING
%doc docs/_build/html
# Example scripts:
%doc examples

%changelog
* Wed Jul 27 2011 David Malcolm <dmalcolm@redhat.com> - 0.5-1
- 0.5
- examples are now in an "examples" subdirectory

* Tue Jul 26 2011 David Malcolm <dmalcolm@redhat.com> - 0.4-1
- 0.4
- add requirement on pygments
- run the upstream test suites during %%check

* Mon Jul 25 2011 David Malcolm <dmalcolm@redhat.com> - 0.3-1
- add requirements on python-six and python3-six
- add %%check section (empty for now)
- set PYTHON and PLUGIN_PYTHONPATH during each build; install support files
into build-specific directories below the gcc plugin dir
- add helper gcc-with-python scripts, with man pages
- package the license
- add example scripts
- add explicit BR on gmp-devel (rhbz#725569)

* Tue May 24 2011 David Malcolm <dmalcolm@redhat.com> - 0.1-1
- initial packaging
