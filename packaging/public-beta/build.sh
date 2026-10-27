#!/bin/sh
# Package the validated prebuilt ARM64 ELF; no cross compilation is performed.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
LIB=${1:?Usage: build.sh /absolute/path/to/validated/libohm_accessories.so}
EXPECTED=4226abfd91a0fb5df545b796d29d9c6d664cf872eba61c8415744b7d7e77b04a
[ -f "$LIB" ] && [ ! -L "$LIB" ] || { echo 'Input must be a regular library' >&2; exit 1; }
[ "$(sha256sum "$LIB" | awk '{print $1}')" = "$EXPECTED" ] || { echo 'Unexpected library hash' >&2; exit 1; }
for tool in rpm rpmbuild rpm2cpio cpio readelf; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 1; }
done
readelf -h "$LIB" | grep -q 'Machine:.*AArch64' || { echo 'Expected AArch64 ELF' >&2; exit 1; }
TOP="$ROOT/RPMS/felis-ohm-public-beta-0.3.1"
mkdir -p "$TOP/SOURCES" "$TOP/SPECS" "$TOP/BUILD" "$TOP/BUILDROOT" "$TOP/RPMS" "$TOP/SRPMS" "$TOP/tmp"
cp "$LIB" "$TOP/SOURCES/libohm_accessories.so"
cp "$SCRIPT_DIR/felis-ohm-control.sh" "$TOP/SOURCES/"
cp "$SCRIPT_DIR/felis-ohm-a2dp-fix.spec" "$TOP/SPECS/"
# A local rpmrc permits packaging a prebuilt foreign-architecture ELF.
# This changes neither system RPM configuration nor the actual library.
RPM_CONFIG=$(rpm --eval '%{_rpmconfigdir}')
HOST_ARCH=$(uname -m)
printf 'buildarch_compat: %s: aarch64 noarch\n' "$HOST_ARCH" > "$TOP/prebuilt.rpmrc"
rpmbuild --rcfile "$RPM_CONFIG/rpmrc:$TOP/prebuilt.rpmrc" -ba --target aarch64 --define "_topdir $TOP" --define "_tmppath $TOP/tmp" --define '_binary_payload w2.xzdio' --define '_source_payload w2.xzdio' "$TOP/SPECS/felis-ohm-a2dp-fix.spec"
OUTPUT="$TOP/RPMS/aarch64/felis-ohm-a2dp-fix-0.3.1-1.aarch64.rpm"
CHECK_DIR=$(mktemp -d "$TOP/verify.XXXXXXXX")
trap 'rm -rf "$CHECK_DIR"' EXIT HUP INT TERM
(cd "$CHECK_DIR" && rpm2cpio "$OUTPUT" | cpio -id --quiet)
[ "$(sha256sum "$CHECK_DIR/usr/share/felis-ohm-a2dp-fix/libohm_accessories.so" | awk '{print $1}')" = "$EXPECTED" ] || { echo 'RPM changed library bytes' >&2; exit 1; }
cmp "$SCRIPT_DIR/felis-ohm-control.sh" "$CHECK_DIR/usr/libexec/felis-ohm-a2dp-fix"
rpm -K "$OUTPUT"
rpm -qp --queryformat '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' "$OUTPUT"
sha256sum "$OUTPUT"
