"""
Compare two builds of the keystone library byte-for-byte on a corpus of
instructions, using the plugin's vendored Python bindings.

    python tests/keystone/regression.py <baseline library> <candidate library>

The corpus (tests/keystone/corpus) holds:

  x86_64-*.txt / arm64-*.txt   '<address>\t<instruction>' lines disassembled
                                from macOS system binaries with objdump
  cases.txt                     '<engine>\t<address>\t<instruction>' lines
                                covering every CPU the plugin supports
  hang.txt                      x86_64 inputs that must return (upstream
                                keystone loops forever on some of them)

Exits non-zero if any output differs or the candidate hangs.
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, 'corpus')
BINDINGS = os.path.join(HERE, '..', '..', 'plugins', 'patching', 'keystone')

# the file name the bindings load on each platform
LIB_NAMES = {'.dll': 'keystone.dll', '.dylib': 'libkeystone.dylib', '.so': 'libkeystone.so'}

ENGINES = {
    'x64':      ('KS_ARCH_X86', ['KS_MODE_64']),
    'x86':      ('KS_ARCH_X86', ['KS_MODE_32']),
    'x16':      ('KS_ARCH_X86', ['KS_MODE_16']),
    'arm':      ('KS_ARCH_ARM', ['KS_MODE_ARM']),
    'thumb':    ('KS_ARCH_ARM', ['KS_MODE_THUMB']),
    'a64':      ('KS_ARCH_ARM64', ['KS_MODE_LITTLE_ENDIAN']),
    'ppc32be':  ('KS_ARCH_PPC', ['KS_MODE_PPC32', 'KS_MODE_BIG_ENDIAN']),
    'ppc64le':  ('KS_ARCH_PPC', ['KS_MODE_PPC64', 'KS_MODE_LITTLE_ENDIAN']),
    'mips32be': ('KS_ARCH_MIPS', ['KS_MODE_MIPS32', 'KS_MODE_BIG_ENDIAN']),
    'mips64le': ('KS_ARCH_MIPS', ['KS_MODE_MIPS64', 'KS_MODE_LITTLE_ENDIAN']),
    'sparc32':  ('KS_ARCH_SPARC', ['KS_MODE_SPARC32', 'KS_MODE_BIG_ENDIAN']),
    'sparc64':  ('KS_ARCH_SPARC', ['KS_MODE_SPARC64', 'KS_MODE_BIG_ENDIAN']),
    'sysz':     ('KS_ARCH_SYSTEMZ', ['KS_MODE_BIG_ENDIAN']),
    'hexagon':  ('KS_ARCH_HEXAGON', ['KS_MODE_LITTLE_ENDIAN']),
    'evm':      ('KS_ARCH_EVM', []),
}

# runs in a child process per library, so each build gets its own copy of the bindings
WORKER = r'''
import sys, json
sys.path.insert(0, sys.argv[1])
import keystone as k

def engine(arch, modes):
    mode = 0
    for m in modes:
        mode |= getattr(k, m)
    return k.Ks(getattr(k, arch), mode)

def asm(ks, text, ea):
    try:
        enc, _ = ks.asm(text, ea, True)
        return enc.hex() if enc else ''
    except k.KsError as e:
        return 'ERR:%s' % e

jobs = json.loads(sys.stdin.read())
engines = {}
out = {}
for key, (arch, modes), ea, text in jobs:
    name = arch + '|'.join(modes)
    if name not in engines:
        engines[name] = engine(arch, modes)
    out[key] = asm(engines[name], text, ea)
json.dump(out, sys.stdout)
'''

HANG_WORKER = r'''
import sys
sys.path.insert(0, sys.argv[1])
import keystone as k
try:
    k.Ks(k.KS_ARCH_X86, k.KS_MODE_64).asm(sys.argv[2], 0, True)
except k.KsError:
    pass
'''

def stage(lib):
    """
    Copy the bindings and the given library into a temp dir, as the plugin ships them.
    """
    ext = os.path.splitext(lib)[1] if not '.so' in os.path.basename(lib) else '.so'
    root = tempfile.mkdtemp()
    dest = os.path.join(root, 'keystone')
    shutil.copytree(BINDINGS, dest, ignore=shutil.ignore_patterns('*.dll', '*.so', '*.dylib', '__pycache__'))
    shutil.copy(lib, os.path.join(dest, LIB_NAMES[ext]))
    return root

def load_jobs():
    jobs = []
    for name in sorted(os.listdir(CORPUS)):
        path = os.path.join(CORPUS, name)
        if name in ('hang.txt',):
            continue
        for line in open(path, encoding='utf-8'):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            if name == 'cases.txt':
                eng, ea, text = line.split('\t', 2)
            else:
                eng = 'x64' if name.startswith('x86_64') else 'a64'
                ea, text = line.split('\t', 1)
            text = text.replace('\t', ' ')
            jobs.append(('%s: %s %s @%s' % (name, eng, text, ea), ENGINES[eng], int(ea, 16), text))
    return jobs

def run(lib, jobs):
    root = stage(lib)
    r = subprocess.run([sys.executable, '-c', WORKER, root], input=json.dumps(jobs),
                       capture_output=True, text=True, timeout=1800)
    if r.returncode:
        sys.exit('%s: worker failed\n%s' % (lib, r.stderr))
    return json.loads(r.stdout)

def hangs(lib):
    root = stage(lib)
    hung = []
    for text in open(os.path.join(CORPUS, 'hang.txt'), encoding='utf-8'):
        text = text.rstrip('\n')
        try:
            subprocess.run([sys.executable, '-c', HANG_WORKER, root, text], capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            hung.append(text)
    return hung

def main():
    baseline, candidate = sys.argv[1], sys.argv[2]
    jobs = load_jobs()

    old = run(baseline, jobs)
    new = run(candidate, jobs)

    diff = [key for key, _, _, _ in jobs if old[key] != new[key]]
    assembled = sum(1 for v in old.values() if v and not v.startswith('ERR'))
    print('%d inputs (%d assembled by the baseline), %d differ' % (len(jobs), assembled, len(diff)))
    for key in diff[:50]:
        print('  %s\n    baseline:  %s\n    candidate: %s' % (key, old[key], new[key]))

    hung = hangs(candidate)
    print('hang inputs: %s' % ('none hang' if not hung else 'HANG on %r' % hung))

    if diff or hung:
        sys.exit(1)

if __name__ == '__main__':
    main()
