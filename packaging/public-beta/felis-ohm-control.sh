#!/bin/sh
# Felis OHM Public Beta 0.3.1 – Sailfish OS 5.2.0.20 or 5.2.0.22 / aarch64
# Installed as /usr/libexec/felis-ohm-a2dp-fix by the standalone RPM.
set -eu
umask 077

ACTIVE=/usr/lib64/ohm/libohm_accessories.so
PAYLOAD=/usr/share/felis-ohm-a2dp-fix/libohm_accessories.so
STATE_DIR=/var/lib/felis-ohm-a2dp-fix
BACKUP="$STATE_DIR/libohm_accessories.so.original"
EXPECTED_ORIGINAL=3ca3739aadff088504357f9e5045c0a9d4eb361c74d611d8fcefb3e78c180f3a
EXPECTED_PATCH=4226abfd91a0fb5df545b796d29d9c6d664cf872eba61c8415744b7d7e77b04a

say() { printf '%s\n' "felis-ohm-a2dp-fix: $*" >&2; }
fail() { say "ERROR: $*"; exit 1; }
sha() { sha256sum "$1" | awk '{print $1}'; }
check_regular() { [ -f "$1" ] && [ ! -L "$1" ] || fail "Expected regular file: $1"; }
check_os() {
    [ -r /etc/os-release ] || fail '/etc/os-release is unavailable'
    # Trusted OS-provided shell variables; do not source an arbitrary user file.
    . /etc/os-release
    [ "${ID:-}" = sailfishos ] && { [ "${VERSION_ID:-}" = 5.2.0.20 ] || [ "${VERSION_ID:-}" = 5.2.0.22 ]; } || fail "Only Sailfish OS 5.2.0.20 or 5.2.0.22 is supported (found ${ID:-unknown} ${VERSION_ID:-unknown})"
    [ "$(uname -m)" = aarch64 ] || fail 'Only aarch64 is supported'
    native=$(rpm -q --queryformat '%{VERSION}-%{RELEASE}' ohm-plugin-accessories 2>/dev/null) || fail 'Original ohm-plugin-accessories package is missing'
    [ "$native" = 1.11.0-1.11.1.jolla ] || fail "Unsupported native OHM package: $native"
}
# Atomic replace on the same filesystem, never leave a half-written active .so.
replace() {
    src=$1
    tmp=$(mktemp "${ACTIVE}.felis.XXXXXXXX") || fail 'Cannot create temporary target file'
    if ! install -o root -g root -m 0755 "$src" "$tmp"; then
        rm -f "$tmp"
        fail 'Cannot stage replacement library'
    fi
    if ! mv -f "$tmp" "$ACTIVE"; then
        rm -f "$tmp"
        fail 'Cannot activate replacement library'
    fi
}
restart() {
    systemctl restart ohmd.service || fail 'ohmd restart failed; inspect journalctl -u ohmd.service'
    systemctl is-active --quiet ohmd.service || fail 'ohmd is not active after restart'
}

case "${1:-}" in
  check-install)
    check_os
    check_regular "$ACTIVE"
    current=$(sha "$ACTIVE")
    [ "$current" = "$EXPECTED_ORIGINAL" ] || fail 'Original OHM library does not match the known stock SHA256; restore stock library before installing'
    if [ -e "$BACKUP" ]; then
        check_regular "$BACKUP"
        [ "$(sha "$BACKUP")" = "$EXPECTED_ORIGINAL" ] || fail 'An existing original backup does not match expected SHA256'
    fi
    ;;
  activate)
    check_os
    check_regular "$ACTIVE"
    check_regular "$PAYLOAD"
    [ "$(sha "$PAYLOAD")" = "$EXPECTED_PATCH" ] || fail 'Packaged fixed library SHA256 mismatch'
    current=$(sha "$ACTIVE")
    [ "$current" = "$EXPECTED_ORIGINAL" ] || fail 'Refusing to replace unexpected OHM library'
    install -d -o root -g root -m 0700 "$STATE_DIR"
    if [ -e "$BACKUP" ]; then
        check_regular "$BACKUP"
        [ "$(sha "$BACKUP")" = "$EXPECTED_ORIGINAL" ] || fail 'Existing backup does not match known original'
    else
        tmp=$(mktemp "$STATE_DIR/.backup.XXXXXXXX") || fail 'Cannot create backup temp file'
        if ! install -o root -g root -m 0700 "$ACTIVE" "$tmp"; then
            rm -f "$tmp"
            fail 'Could not save original backup'
        fi
        if [ "$(sha "$tmp")" != "$EXPECTED_ORIGINAL" ]; then
            rm -f "$tmp"
            fail 'Original backup verification failed'
        fi
        mv "$tmp" "$BACKUP"
    fi
    replace "$PAYLOAD"
    if ! systemctl restart ohmd.service || ! systemctl is-active --quiet ohmd.service; then
        say 'OHM activation failed, trying to restore original library'
        replace "$BACKUP"
        systemctl restart ohmd.service || true
        fail 'Patch activation failed; original library restored; RPM may remain installed and should be removed'
    fi
    say 'Patch active. Verified original backup retained in /var/lib/felis-ohm-a2dp-fix/'
    ;;
  restore)
    # Never restore an old library over an unsupported system after an OTA.
    check_os
    check_regular "$ACTIVE"
    check_regular "$BACKUP"
    [ "$(sha "$BACKUP")" = "$EXPECTED_ORIGINAL" ] || fail 'Original backup corrupted; refusing uninstall'
    current=$(sha "$ACTIVE")
    if [ "$current" = "$EXPECTED_ORIGINAL" ]; then
        say 'Original library is already active; leaving it untouched'
    elif [ "$current" = "$EXPECTED_PATCH" ]; then
        replace "$BACKUP"
        say 'Original OHM library restored'
    else
        fail 'Active OHM library was changed by another update or modification; not overwriting it. Inspect before uninstall.'
    fi
    restart
    say 'Backup retained in /var/lib/felis-ohm-a2dp-fix/ for additional safety'
    ;;
  *)
    say 'Usage: felis-ohm-control.sh {check-install|activate|restore}'
    exit 2
    ;;
esac
