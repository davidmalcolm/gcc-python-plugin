Name:           gcc-python-plugin
Version:        0.17
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

# pygments is used when running the selftests:
BuildRequires: python-pygments
BuildRequires: python3-pygments

# lxml is used when running the selftests:
BuildRequires: python-lxml
BuildRequires: python3-lxml

%global gcc_plugins_dir %(gcc --print-file-name=plugin)

%description
Plugins for embedding various versions of Python within GCC

%package -n gcc-python-plugin-c-api
Summary: Shared library to make it easier to write GCC plugins
Group:   Development/Languages

%description -n gcc-python-plugin-c-api
Shared library to make it easier to write GCC plugins

%package -n gcc-python2-plugin
Summary: GCC plugin embedding Python 2
Group:   Development/Languages
Requires: python-six
Requires: python-pygments
Requires: python-lxml
Requires: gcc-python-plugin-c-api%{?_isa} = %{version}-%{release}

%description  -n gcc-python2-plugin
GCC plugin embedding Python 2

%package -n gcc-python3-plugin
Summary: GCC plugin embedding Python 3
Group:   Development/Languages
Requires: python3-six
Requires: python3-pygments
Requires: python3-lxml
Requires: gcc-python-plugin-c-api%{?_isa} = %{version}-%{release}

%description  -n gcc-python3-plugin
GCC plugin embedding Python 3

%package -n gcc-python2-debug-plugin
Summary: GCC plugin embedding Python 2 debug build
Group:   Development/Languages
Requires: python-six
Requires: python-pygments
Requires: python-lxml
Requires: gcc-python-plugin-c-api%{?_isa} = %{version}-%{release}

%description  -n gcc-python2-debug-plugin
GCC plugin embedding debug build of Python 2

%package -n gcc-python3-debug-plugin
Summary: GCC plugin embedding Python 3 debug build
Group:   Development/Languages
Requires: python3-six
Requires: python3-pygments
Requires: python3-lxml
Requires: gcc-python-plugin-c-api%{?_isa} = %{version}-%{release}

%description  -n gcc-python3-debug-plugin
GCC plugin embedding debug build of Python 3

%package docs
Summary: API documentation for the GCC Python plugin
Group:   Development/Languages

%description docs
This package contains API documentation for the GCC Python plugin



%prep
%setup -q

# We will be building the plugin 4 times, each time against a different
# Python runtime
#
# The plugin doesn't yet cleanly support srcdir != builddir, so for now
# make 4 separate copies of the source, once for each build

PrepPlugin() {
    PluginName=$1

    BuildDir=../gcc-python-plugin-%{version}-building-for-$PluginName

    rm -rf $BuildDir
    cp -a . $BuildDir
}

PrepPlugin \
  python2

PrepPlugin \
  python2_debug

PrepPlugin \
  python3

PrepPlugin \
  python3_debug


%build

BuildPlugin() {
    PythonExe=$1
    PythonConfig=$2
    PluginDso=$3
    PluginName=$4

    BuildDir=../gcc-python-plugin-%{version}-building-for-$PluginName

    pushd $BuildDir
    make \
       %{?_smp_mflags} \
       PLUGIN_NAME=$PluginName \
       PLUGIN_DSO=$PluginDso \
       PYTHON=$PythonExe \
       PYTHON_CONFIG=$PythonConfig \
       PLUGIN_PYTHONPATH=%{gcc_plugins_dir}/$PluginName \
       plugin print-gcc-version
    popd
}

BuildPlugin \
  python \
  python-config \
  python2.so \
  python2

BuildPlugin \
  python-debug \
  python-debug-config \
  python2_debug.so \
  python2_debug

BuildPlugin \
  python3 \
  python3-config \
  python3.so \
  python3

BuildPlugin \
  python3-debug \
  /usr/bin/python3.?dm-config \
  python3_debug.so \
  python3_debug

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

    BuildDir=../gcc-python-plugin-%{version}-building-for-$PluginName

    pushd $BuildDir
    make install \
        DESTDIR=$RPM_BUILD_ROOT \
        PLUGIN_NAME=$PluginName \
        PLUGIN_DSO=$PluginDso
    popd

    # (doing the above actually installs each build's copy of libgccapi.so,
    # all to the same location, but they should all be identical, so that's
    # OK)
}

InstallPlugin \
  python \
  python-config \
  python2.so \
  python2

InstallPlugin \
  python-debug \
  python-debug-config \
  python2_debug.so \
  python2_debug

InstallPlugin \
  python3 \
  python3-config \
  python3.so \
  python3

InstallPlugin \
  python3-debug \
  python3.4dm-config \
  python3_debug.so \
  python3_debug


%clean
rm -rf $RPM_BUILD_ROOT

%check

CheckPlugin() {
    PythonExe=$1
    PythonConfig=$2
    PluginDso=$3
    PluginName=$4
    SelftestArgs=$5

    BuildDir=../gcc-python-plugin-%{version}-building-for-$PluginName

    pushd $BuildDir

    # Run the selftests:
    LD_LIBRARY_PATH=gcc-c-api \
    PLUGIN_NAME=$PluginName \
        $PythonExe run-test-suite.py $SelftestArgs

    LD_LIBRARY_PATH=gcc-c-api \
    PLUGIN_NAME=$PluginName \
        $PythonExe testcpychecker.py -v

    popd
}

# Selftest for python2 (optimized) build
# All tests ought to pass:
CheckPlugin \
  python \
  python-config \
  python2.so \
  python2 \
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
  python2_debug.so \
  python2_debug \
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
  python3 \
  "-x tests/cpychecker"

# Selftest for python3-debug build:
#   (shares the issues of the above)
CheckPlugin \
  python3-debug \
  python3.4dm-config \
  python3_debug.so \
  python3_debug \
  "-x tests/cpychecker"

%files -n gcc-python-plugin-c-api
%{gcc_plugins_dir}/libgcc-c-api.so

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
%{_bindir}/gcc-with-python2_debug
%{gcc_plugins_dir}/python2_debug.so
%{gcc_plugins_dir}/python2_debug
%doc %{_mandir}/man1/gcc-with-python2_debug.1.gz

%files -n gcc-python3-debug-plugin
%defattr(-,root,root,-)
%doc COPYING README.rst
%{_bindir}/gcc-with-python3_debug
%{gcc_plugins_dir}/python3_debug.so
%{gcc_plugins_dir}/python3_debug
%doc %{_mandir}/man1/gcc-with-python3_debug.1.gz

%files docs
%defattr(-,root,root,-)
%doc COPYING
%doc docs/_build/html
# Example scripts:
%doc examples

%changelog
* Mon Feb  6 2012 David Malcolm <dmalcolm@redhat.com> - 0.9-1
- 0.9

* Tue Jan 10 2012 David Malcolm <dmalcolm@redhat.com> - 0.8-1
- 0.8

* Tue Aug  2 2011 David Malcolm <dmalcolm@redhat.com> - 0.6-1
- 0.6

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
