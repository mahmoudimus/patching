# Keystone Engine (Patching)

This plugin ships its own build of the [Keystone Engine](https://github.com/keystone-engine/keystone) rather than using the PyPI `keystone-engine` package. The PyPI package (0.9.2, 2020) has no Apple Silicon or Linux ARM builds, and it lacks fixes from [gaasedelen/keystone](https://github.com/gaasedelen/keystone) that the plugin relies on. One example: Keystone could loop forever on some invalid statements, and the patching dialog assembles on every keystroke.

## Contents

| File | Platform | SHA-256 |
|---|---|---|
| `libkeystone.dylib` | macOS (universal x86_64 + arm64) | `a2e43a1832999d8feba32f0da0977ca7594745c1f08ed09ee01841a0dc5cc426` |
| `libkeystone.so` | Linux x86_64 | `fab7cf0730e3ace1da3bb5d5ae40bc9d06e6ee0683ff88eddb26f978b6646832` |
| `keystone.dll` | Windows x86_64 | `84f132091b1cd5506d970f921b546d18064cb2d595531c75c7cfa60e41e2528f` |

The libraries, `COPYING` and `LICENSE.TXT` are byte-identical to the ones in the [v0.2.0 release](https://github.com/gaasedelen/patching/releases/tag/v0.2.0) of gaasedelen/patching (`patching_macos.zip`, `patching_linux.zip`, `patching_win32.zip`), built by gaasedelen/keystone's CI.

The Python bindings (`keystone.py`, `*_const.py`) come from the same release. One local change: the last-resort library search no longer uses `distutils`, which was removed in Python 3.12.

`keystone.py` tries each platform's library name in turn from this directory, so all three libraries can live side by side.

## Source

GPLv2 requires the corresponding source for these libraries to be available. It is pinned as a git submodule at [`third_party/keystone`](../../../third_party/keystone), pointing to [mahmoudimus/keystone](https://github.com/mahmoudimus/keystone), a fork of gaasedelen/keystone. The pinned commit is [`9ddb5e8`](https://github.com/mahmoudimus/keystone/commit/9ddb5e85b9507a98de3919ae24c18b02f8541442), also tagged `patching-v0.2.0`.

That commit is the head of gaasedelen/keystone's `master` (2024-11-23), the day before the v0.2.0 release that the libraries came from. It is inferred from those dates: the build is not bit-for-bit reproducible, and the CI records that produced it have expired.

As of 2026-09, upstream keystone-engine has not picked up gaasedelen's fixes. gaasedelen never opened a pull request, and upstream has not changed the affected files (`llvm/lib/MC/MCParser/AsmParser.cpp` and the X86 asm parser and code emitter) since the fork diverged. Upstream's last release is still 0.9.2 (2020).

The plugin never needs the submodule: `git clone` without `--recursive` is fine. Fetch the source with `git submodule update --init`.

## License

The Keystone engine libraries are licensed under GPLv2 (`COPYING`). The Python bindings are licensed under a BSD 3-clause license (`LICENSE.TXT`). Both files are redistributed unchanged. The rest of the plugin is MIT licensed, and upstream's release zips already shipped these same files alongside it.
