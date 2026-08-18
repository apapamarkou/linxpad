Name:           linxpad
Version:        1.3.0
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
install -Dm644 src/linxpad/icons/linxpad.png      %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/linxpad.png
if [ -f src/linxpad/icons/linxpad-glow.png ]; then \
    install -Dm644 src/linxpad/icons/linxpad-glow.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/linxpad-glow.png; \
fi
install -Dm644 packaging/specs/linxpad.desktop    %{buildroot}%{_datadir}/applications/linxpad.desktop
install -Dm644 LICENSE                            %{buildroot}%{_datadir}/licenses/%{name}/LICENSE

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
%ghost %{_datadir}/icons/hicolor/256x256/apps/linxpad-glow.png
%{_datadir}/applications/linxpad.desktop

%changelog
* Wed Jan 01 2025 Andrianos Papamarkou <andrianos@example.com> - 1.3.0
- New application icon and alternative glow icon
- Removed linxpad-folder.png icon — folder icons now show a live preview collage of their contents
- AppImage fixes for Debian and Ubuntu
- Touchpad pinch-to-close gesture
- Added Ubuntu 26.04 package target
- Removed Flatpak packaging support
- Minor bug fixes

* Wed Jan 01 2025 Andrianos Papamarkou <andrianos@example.com> - 1.1.0
- Bug fix package release
