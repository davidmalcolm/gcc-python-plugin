Name:           gcc-python-plugin
Version:        0.1
Release:        1%{?dist}
Summary:        GCC plugin that embeds Python

Group:          Development/Languages
License:        GPLv3
URL:            FIXME
Source0:        gcc-python-plugin-0.1.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  gcc-plugin-devel
BuildRequires:  python-devel
BuildRequires:  python-debug
BuildRequires:  python3-devel
BuildRequires:  python3-debug

%global gcc_plugins_dir %(gcc --print-file-name=plugin)

%description
Plugins for embedding various versions of Python within GCC

%package -n gcc-python2-plugin
Summary: GCC plugin embedding Python 2
Group:   Development/Languages

%description  -n gcc-python2-plugin
GCC plugin embedding Python 2

%package -n gcc-python3-plugin
Summary: GCC plugin embedding Python 3
Group:   Development/Languages

%description  -n gcc-python3-plugin
GCC plugin embedding Python 3

%package -n gcc-python2-debug-plugin
Summary: GCC plugin embedding Python 2 debug build
Group:   Development/Languages

%description  -n gcc-python2-debug-plugin
GCC plugin embedding debug build of Python 2

%package -n gcc-python3-debug-plugin
Summary: GCC plugin embedding Python 3 debug build
Group:   Development/Languages

%description  -n gcc-python3-debug-plugin
GCC plugin embedding debug build of Python 3




%prep
# FIXME: tarball generation
%setup -q -n gcc-python-clean


%build

BuildPlugin() {
    Config=$1
    PluginName=$2

    # "make clean" would remove the .so files from the previous build
    rm -f *.o    
    make %{?_smp_mflags} PYTHON_CONFIG=$Config plugin
    mv python.so $PluginName
}

BuildPlugin \
  python-config \
  python2.so

BuildPlugin \
  python-debug-config \
  python2-debug.so

BuildPlugin \
  python3-config \
  python3.so

#BuildPlugin \
#  python3-debug-config \
#  python3.so


%install
rm -rf $RPM_BUILD_ROOT
#make install DESTDIR=$RPM_BUILD_ROOT

mkdir -p $RPM_BUILD_ROOT/%{gcc_plugins_dir}

for plugin in python2.so python2-debug.so python3.so ;
do
    cp $plugin $RPM_BUILD_ROOT/%{gcc_plugins_dir}
done
# FIXME: we also need the support code (gccutils.py)

%clean
rm -rf $RPM_BUILD_ROOT


%files -n gcc-python2-plugin
%defattr(-,root,root,-)
%doc README.rst
%{gcc_plugins_dir}/python2.so

%files -n gcc-python3-plugin
%defattr(-,root,root,-)
%doc README.rst
%{gcc_plugins_dir}/python3.so

%files -n gcc-python2-debug-plugin
%defattr(-,root,root,-)
%doc README.rst
%{gcc_plugins_dir}/python2-debug.so

%files -n gcc-python3-debug-plugin
%defattr(-,root,root,-)
%doc README.rst
#%{gcc_plugins_dir}/python3-debug.so



%changelog
* Tue May 24 2011 David Malcolm <dmalcolm@redhat.com> - 0.1-1
- initial packaging
