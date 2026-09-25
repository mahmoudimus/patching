# Keystone Engine (Patching)

This plugin ships its own build of the [Keystone Engine](https://github.com/keystone-engine/keystone) rather than using the PyPI `keystone-engine` package. The PyPI package (0.9.2, 2020) has no Apple Silicon or Linux ARM builds, and it lacks fixes from [gaasedelen/keystone](https://github.com/gaasedelen/keystone) that the plugin relies on. One example: Keystone could loop forever on some invalid statements, and the patching dialog assembles on every keystroke.

## Contents

| File | Platform | Runtime requirements | SHA-256 |
|---|---|---|---|
| `libkeystone.dylib` | macOS (universal x86_64 + arm64) | macOS 11+ | `2350e2d71fcbca23978729187392ec904e47ab7f0ec768a5bd066b067d90298f` |
| `libkeystone.so` | Linux x86_64 | glibc 2.17+ (built on manylinux2014) | `111a5f6d05478864b2ed02344d5c5d5f75d37325b141c447472d9447ba1bd4dc` |
| `keystone.dll` | Windows x86_64 | none beyond `KERNEL32.dll` (static C runtime) | `172cfe29791a669819c2af966019ae2740a6a72eb4d4e0fb4a9a43634ed3743c` |

The libraries are the assets of the [`patching-v0.5.0`](https://github.com/mahmoudimus/keystone/releases/tag/patching-v0.5.0) release of mahmoudimus/keystone. They were built from [`c8cf85e`](https://github.com/mahmoudimus/keystone/commit/c8cf85e05fac86de72f9987d5c2549a2ea339216) by that repository's `patching-libs.yml` workflow in [this run](https://github.com/mahmoudimus/keystone/actions/runs/36188440047), which smoke tests each library before publishing it with `SHA256SUMS`.

Before they were vendored, the [Keystone regression test](https://github.com/mahmoudimus/patching-ng/actions/runs/36188950471) (`tests/keystone/regression.py`) compared them with the previous libraries, from gaasedelen/patching v0.2.0, on Linux, macOS and Windows. The output was byte-for-byte identical on all 18,048 inputs, and none of the inputs that hang upstream Keystone hung. The x86_64 half of the macOS library was also checked the same way under Rosetta.

The Python bindings (`keystone.py`, `*_const.py`), `COPYING` and `LICENSE.TXT` come from the [v0.2.0 release](https://github.com/gaasedelen/patching/releases/tag/v0.2.0) of gaasedelen/patching. They use the same API version (0.9) as the new libraries. One local change: the last-resort library search no longer uses `distutils`, which was removed in Python 3.12.

`keystone.py` tries each platform's library name in turn from this directory, so all three libraries can live side by side.

## Source

GPLv2 requires the corresponding source for these libraries to be available. It is pinned as a git submodule at [`third_party/keystone`](../../../third_party/keystone), at [`c8cf85e`](https://github.com/mahmoudimus/keystone/commit/c8cf85e05fac86de72f9987d5c2549a2ea339216), the exact commit the libraries were built from.

That source is [mahmoudimus/keystone](https://github.com/mahmoudimus/keystone), a fork of [gaasedelen/keystone](https://github.com/gaasedelen/keystone), which is in turn a fork of [keystone-engine/keystone](https://github.com/keystone-engine/keystone). It combines:

* gaasedelen's fixes: an infinite loop on some invalid statements, RIP-relative `movabs` loads and stores, and the number radix after setting the syntax
* upstream keystone-engine's `master` ([merged](https://github.com/mahmoudimus/keystone/commit/c0b646f)), including its CMake 4 / GCC 15 / MSVC build fixes and RISC-V support
* the CI build of these libraries

As of 2026-09, upstream keystone-engine has not picked up gaasedelen's fixes. gaasedelen never opened a pull request, and upstream has not changed the affected files (`llvm/lib/MC/MCParser/AsmParser.cpp` and the X86 asm parser and code emitter) since the fork diverged. Upstream's last release is still 0.9.2 (2020).

The previous libraries came from gaasedelen's v0.2.0 release, almost certainly built from gaasedelen/keystone [`9ddb5e8`](https://github.com/mahmoudimus/keystone/commit/9ddb5e85b9507a98de3919ae24c18b02f8541442) (tagged `patching-v0.2.0` in mahmoudimus/keystone). That source no longer configures with CMake 4.

The plugin never needs the submodule: `git clone` without `--recursive` is fine. Fetch the source with `git submodule update --init`.

## License

The Keystone engine libraries are licensed under GPLv2 (`COPYING`). The Python bindings are licensed under a BSD 3-clause license (`LICENSE.TXT`). Both files are redistributed unchanged. The rest of the plugin is MIT licensed, and gaasedelen's release zips already shipped Keystone alongside it.
