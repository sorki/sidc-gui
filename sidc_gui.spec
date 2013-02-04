Name:           sidc-gui
Version:        0.4
Release:        1%{?dist}
Summary:        Sudden ionospheric disturbance collector (sidc) GUI

Group:          Applications/Communications
License:        BSD
URL:            http://github.com/sorki/sidc-gui
Source0:        http://sources.48.io/sid/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-devel
BuildRequires:  desktop-file-utils

Requires:       python
Requires:       python-psutil
Requires:       wxPython
Requires:       python-matplotlib-wx

%description
This application allows user to monitor sidc daemon
and view live graphs of recorded data.

%prep
%setup -q

%build
%{__python} setup.py build

%install
%{__python} setup.py install --skip-build --root %{buildroot}
mkdir -p %{buildroot}%{_datadir}/pixmaps/
cp sidc_gui.svg %{buildroot}%{_datadir}/pixmaps/
desktop-file-install \
  --dir=%{buildroot}%{_datadir}/applications \
  sidc_gui.desktop

%files
%doc README.rst
%doc AUTHORS
%doc LICENSE
%doc CHANGES
%{_bindir}/sidc_gui
%{python_sitelib}/*
%{_datadir}/pixmaps/sidc_gui.svg
%{_datadir}/applications/sidc_gui.desktop

%changelog
* Mon Jan 04 2013 Richard Marko <rmarko@fedoraproject.org> - 0.4-1
- Version bump

* Wed Dec 12 2012 Richard Marko <rmarko@fedoraproject.org> - 0.3-1
- Initial packaging attempt
