Name:           felis-ohm-a2dp-fix
Version:        0.3.1
Release:        1
Summary:        Experimental Bluetooth A2DP reconnect fix for Jolla Phone 2026
License:        LGPL-2.1-only
URL:            https://github.com/sailfishos/ohm-plugins-misc/pull/11
BuildArch:      aarch64
Source0:        libohm_accessories.so
Source1:        felis-ohm-control.sh
AutoReqProv:     no
# Keep the prebuilt, QA-tested ELF byte-for-byte unchanged by brp-strip.
%global __os_install_post %{nil}
%global debug_package %{nil}

%description
EXPERIMENTAL AND UNSUPPORTED. Installs a known patched OHM accessories plugin
on Sailfish OS 5.2.0.20 or 5.2.0.22 aarch64. The script checks the exact native package
and original library hashes before activation; no other system packages are
upgraded. Remove before any Sailfish OS system update. Use entirely at your
own risk; system audio and telephone calls can be affected.

%prep
# Prebuilt ARM64 library from the validated public PR branch.

%build
# No compilation: safely package a previously compiled and tested .so.

%install
install -d %{buildroot}/usr/share/felis-ohm-a2dp-fix
install -d %{buildroot}/usr/libexec
install -m 0755 %{SOURCE0} %{buildroot}/usr/share/felis-ohm-a2dp-fix/libohm_accessories.so
install -m 0755 %{SOURCE1} %{buildroot}/usr/libexec/felis-ohm-a2dp-fix

%pre
# No in-place upgrades supported; uninstall and restore stock first.
if [ "$1" != 1 ]; then
    echo 'felis-ohm-a2dp-fix: package upgrades unsupported. Uninstall old beta first.' >&2
    exit 1
fi
[ -r /etc/os-release ] || exit 1
. /etc/os-release
if [ "${ID:-}" != sailfishos ] || { [ "${VERSION_ID:-}" != 5.2.0.20 ] && [ "${VERSION_ID:-}" != 5.2.0.22 ]; } || [ "$(uname -m)" != aarch64 ]; then
    echo 'felis-ohm-a2dp-fix: only Sailfish OS 5.2.0.20 or 5.2.0.22 aarch64 supported' >&2
    exit 1
fi
native=$(rpm -q --queryformat '%%{VERSION}-%%{RELEASE}' ohm-plugin-accessories 2>/dev/null) || exit 1
if [ "$native" != 1.11.0-1.11.1.jolla ]; then
    echo 'felis-ohm-a2dp-fix: native ohm-plugin-accessories version unsupported' >&2
    exit 1
fi
active=/usr/lib64/ohm/libohm_accessories.so
if [ ! -f "$active" ] || [ -L "$active" ] || [ "$(sha256sum "$active" | awk '{print $1}')" != 3ca3739aadff088504357f9e5045c0a9d4eb361c74d611d8fcefb3e78c180f3a ]; then
    echo 'felis-ohm-a2dp-fix: stock OHM library SHA256 mismatch. Restore stock before installation.' >&2
    exit 1
fi
backup=/var/lib/felis-ohm-a2dp-fix/libohm_accessories.so.original
if [ -e "$backup" ] && { [ ! -f "$backup" ] || [ -L "$backup" ] || [ "$(sha256sum "$backup" | awk '{print $1}')" != 3ca3739aadff088504357f9e5045c0a9d4eb361c74d611d8fcefb3e78c180f3a ]; }; then
    echo 'felis-ohm-a2dp-fix: unexpected previously saved original backup' >&2
    exit 1
fi
exit 0

%post
/usr/libexec/felis-ohm-a2dp-fix activate

%preun
if [ "$1" -eq 0 ]; then
    /usr/libexec/felis-ohm-a2dp-fix restore || exit 1
fi
exit 0

%files
%dir /usr/share/felis-ohm-a2dp-fix
/usr/share/felis-ohm-a2dp-fix/libohm_accessories.so
/usr/libexec/felis-ohm-a2dp-fix

%changelog
* Tue Oct 27 2026 Michal Kasik - 0.3.1-1
- Accept Sailfish OS 5.2.0.22 with the identical stock OHM build and hash.
- Keep the previously tested clean PR library unchanged.
- Check supported OS and native OHM package before restoring the backup.
