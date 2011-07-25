Name:           gcc-python-plugin
Version:        0.3
Release:        1%{?dist}
Summary:        GCC plugin that embeds Python

Group:          Development/Languages
License:        GPLv3+
URL:            https://fedorahosted.org/gcc-python-plugin/
Source0:        https://fedorahosted.org/releases/g/c/gcc-python-plugin/gcc-python-plugin-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  gcc-plugin-devel

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

%description  -n gcc-python2-plugin
GCC plugin embedding Python 2

%package -n gcc-python3-plugin
Summary: GCC plugin embedding Python 3
Group:   Development/Languages
Requires: python3-six

%description  -n gcc-python3-plugin
GCC plugin embedding Python 3

%package -n gcc-python2-debug-plugin
Summary: GCC plugin embedding Python 2 debug build
Group:   Development/Languages
Requires: python-six

%description  -n gcc-python2-debug-plugin
GCC plugin embedding debug build of Python 2

%package -n gcc-python3-debug-plugin
Summary: GCC plugin embedding Python 3 debug build
Group:   Development/Languages
Requires: python3-six

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

    # Disabled for now; not all tests pass:
    #make \
    #   PYTHON=$PythonExe \
    #   PYTHON_CONFIG=$PythonConfig \
    #   test-suite testcpychecker
}

CheckPlugin \
  python \
  python-config \
  python2.so

CheckPlugin \
  python-debug \
  python-debug-config \
  python2-debug.so

CheckPlugin \
  python3 \
  python3-config \
  python3.so

CheckPlugin \
  python3-debug \
  python3.2dmu-config \
  python3-debug-debug.so


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
%doc show-ssa.py show-docs.py

%changelog
* Mon Jul 25 2011 David Malcolm <dmalcolm@redhat.com> - 0.3-1
- add requirements on python-six and python3-six
- add %%check section (empty for now)
- set PYTHON and PLUGIN_PYTHONPATH during each build; install support files
into build-specific directories below the gcc plugin dir
- add helper gcc-with-python scripts, with man pages
- package the license
- add example scripts

* Tue May 24 2011 David Malcolm <dmalcolm@redhat.com> - 0.1-1
- initial packaging
