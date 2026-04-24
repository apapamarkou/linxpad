Name:           linxpad
Version:        1.0.0
Release:        1%{?dist}
Summary:        A macOS-style fullscreen application launcher for Linux

License:        GPL-3.0-or-later
URL:            https://github.com/apapamarkou/linxpad
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-pip
Requires:       python3 >= 3.11
Requires:       python3-pyqt6 >= 6.4
Requires:       python3-watchdog >= 3.0

%description
LinxPad is a macOS-style fullscreen application launcher for Linux,
supporting both X11 and Wayland sessions. It provides a full-screen
grid of application icons with folder grouping, drag-and-drop
reordering, multi-page navigation, integrated search, and a settings
panel for customisation.

%prep
%autosetup

%build
python3 -m pip install --no-build-isolation --prefix=%{buildroot}%{_prefix} .

%install
python3 -m pip install --no-build-isolation --root=%{buildroot} --prefix=%{_prefix} .
install -Dm644 src/linxpad/icons/linxpad.png        %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/linxpad.png
install -Dm644 src/linxpad/icons/linxpad-folder.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/linxpad-folder.png
install -Dm644 packaging/specs/linxpad.desktop      %{buildroot}%{_datadir}/applications/linxpad.desktop
install -Dm644 LICENSE                              %{buildroot}%{_datadir}/licenses/%{name}/LICENSE

%post
update-desktop-database %{_datadir}/applications &>/dev/null || :
gtk-update-icon-cache -f -t %{_datadir}/icons/hicolor &>/dev/null || :

%postun
update-desktop-database %{_datadir}/applications &>/dev/null || :
gtk-update-icon-cache -f -t %{_datadir}/icons/hicolor &>/dev/null || :

%files
%license LICENSE
%doc README.md
%{_bindir}/linxpad
%{python3_sitelib}/linxpad/
%{python3_sitelib}/linxpad-*.dist-info/
%{_datadir}/icons/hicolor/256x256/apps/linxpad.png
%{_datadir}/icons/hicolor/256x256/apps/linxpad-folder.png
%{_datadir}/applications/linxpad.desktop

%changelog
* Wed Jan 01 2025 Andrianos Papamarkou <andrianos@example.com> - 1.0.0-1
- Initial package release
