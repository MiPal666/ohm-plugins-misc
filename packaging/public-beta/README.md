# Felis OHM A2DP Fix 0.3.1-1

Public beta with completed owner-device installation, reconnect/reboot/call
and removal QA on SFOS 5.2.0.22. Web/forum publication remains pending.

## Compatibility and changes

- Jolla Phone 2026, aarch64, Sailfish OS 5.2.0.20 or 5.2.0.22.
- Exact vendor `ohm-plugin-accessories`: `1.11.0-1.11.1.jolla`.
- Stock library SHA256:
  `3ca3739aadff088504357f9e5045c0a9d4eb361c74d611d8fcefb3e78c180f3a`.
- Clean PR library SHA256:
  `4226abfd91a0fb5df545b796d29d9c6d664cf872eba61c8415744b7d7e77b04a`.
- Same clean ARM64 library as public beta 0.3.0-1; no C changes or rebuild.
- Version 0.3.1 adds the exact 5.2.0.22 release to installation guards.
- Restore now checks OS/architecture/native package too, refusing unsupported
  systems after an OTA instead of risking an old-library restore.
- In-place package upgrades remain unsupported: remove the previous beta first.
- Standalone package; vendor OHM RPM records are not upgraded.

This is an experimental, unofficial system modification affecting audio and
calls. Keep SSH/root recovery access and the verified original library.
Remove the package before an OS upgrade. Do not bypass guards with force,
nodeps or noscripts options. A failed RPM scriptlet is not a transaction rollback.
If an OTA changes the system while installed, inspect the current files and
package scripts before any removal or restoration.

## Build

Run from the repository root, supplying the previously validated clean ELF:

```sh
sh packaging/public-beta/build.sh /absolute/path/to/libohm_accessories.so
```

The script checks the input hash and AArch64 ELF header, packages the prebuilt
library locally, and verifies the extracted library hash and helper contents.
A private rpmrc permits packaging ARM64 bytes on x86_64; it does not compile or
emulate ARM code, alter global RPM configuration, or install the package.
XZ compression keeps RPM feature requirements conservative for the target.
Binary and source RPMs appear under `RPMS/felis-ohm-public-beta-0.3.1/`.
The source RPM contains packaging inputs including the prebuilt ELF, rather
than a full OHM source tree. The implementation is in upstream PR #11:
https://github.com/sailfishos/ohm-plugins-misc/pull/11
Clean PR source commit: `fb663f56cfe5bf14e57bd8dd37d30f9ef3f91349`.

## Local checks

```sh
python3 -m unittest discover -s tests -p test_public_beta.py -v
```

Tests use isolated fixtures, mocked package/service commands and temporary
copies of the scripts. They cover both supported releases, rejected OS/arch/
native versions, in-place upgrades, unknown active bytes, symlinks, corrupt
backup/payload, activation restart failure and conservative restoration.
They do not replace actual RPM transaction and audio tests on the phone.

## Actual device observations, 27 October 2026

- SFOS 5.2.0.22 vendor package version and stock library hash exactly match .20.
- Vendor verification reports only the timestamp of `/usr/lib64/ohm` changed.
- The stock reconnect routing fault was reproduced on .22.
- Debug Fix 0.3 hash `ba38556e155150db851f09c8efd309dc42c584d8aaeb6c605bc55f8eaceada10`
  resolves its dependencies and runs on .22. Liberty 5 repeated reconnects,
  routing back to phone, reboot and repeat, calls with repeated Bluetooth/
  earpiece/speaker switches, and subsequent music playback passed.
- Clean public ELF and full RPM 0.3.0-1 transactions were tested on .20 in the
  previous session. RPM 0.3.1-1 itself has not been device-tested on .20.
- RPM 0.3.1-1 SHA256:
  `bd8ade5f348e128c0f623ead0945515df048016933a86d363f850ee1b46eb490`.
  Transfer to the phone was verified against this hash.
- On .22, installation through `pkcon install-local` passed. Package version
  0.3.1-1, active clean-library hash `4226abfd...`, protected original backup
  hash `3ca3739a...`, and active OHM were verified.
- The owner confirmed the requested clean-RPM reconnect, reboot and call/media
  routing tests passed with Liberty 5.
- Removal through `pkcon remove` passed: package absent, stock library restored
  with the exact original hash, protected backup retained with the same hash,
  and OHM active.
- Reinstallation passed. Final phone state: `felis-ohm-a2dp-fix-0.3.1-1.aarch64`
  installed, clean library hash `4226abfd...`, OHM active. No debug library active.

## Completed device QA procedure (reference)

1. Transfer the new RPM to the phone and verify its SHA256 against SHA256SUMS.
2. Restore the verified stock library using the already inspected
   `/usr/local/sbin/felis-ohm-restore`; verify stock hash and active OHM.
3. Install 0.3.1-1 through normal `pkcon install-local` and inspect the result.
4. Verify package version, active clean-library hash, protected original backup
   hash, and active `ohmd.service`.
5. Test repeated reconnects, reboot/reconnects, and calls/media routing.
6. Remove through normal `pkcon remove felis-ohm-a2dp-fix`; verify the package
   is absent, stock hash restored, backup retained, and OHM active.
7. Reinstall and verify package version, active clean-library hash and OHM.

## Remaining release work

Commit the packaging/test sources separately from the upstream C-only PR,
then prepare the website download/checksum/compatibility update and forum
announcement. No website or forum publication has been performed in this session.

No phone installation or web/forum publication is performed by the build.
