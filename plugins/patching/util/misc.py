import os

#------------------------------------------------------------------------------
# Plugin Util
#------------------------------------------------------------------------------

PLUGIN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def plugin_resource(resource_name):
    """
    Return the full path for a given plugin resource file.
    """
    return os.path.join(
        PLUGIN_PATH,
        "ui",
        "resources",
        resource_name
    )

#------------------------------------------------------------------------------
# Misc / OS Util
#------------------------------------------------------------------------------

def is_file_locked(filepath):
    """
    Checks to see if a file is locked. Performs three checks

        1. Checks if the file even exists

        2. Attempts to open the file for reading. This will determine if the
           file has a write lock. Write locks occur when the file is being
           edited or copied to, e.g. a file copy destination

        3. Attempts to rename the file. If this fails the file is open by some
           other process for reading. The file can be read, but not written to
           or deleted.

    Not perfect, but it doesn't have to be. Source: https://stackoverflow.com/a/63761161
    """
    if not (os.path.exists(filepath)):
        return False

    try:
        f = open(filepath, 'r')
        f.close()
    except IOError:
        return True

    try:
        os.rename(filepath, filepath)
        return False
    except WindowsError:
        return True

#------------------------------------------------------------------------------
# macOS Util
#------------------------------------------------------------------------------

# thin (32/64bit, either endian) and fat Mach-O header magics
MACHO_MAGICS = [b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe']
FAT_MAGICS = [b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca']

def is_macho(filepath):
    """
    Return True if the given file appears to be a (thin or fat) Mach-O.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
    except OSError:
        return False

    magic = header[:4]
    if magic in MACHO_MAGICS:
        return True

    #
    # 0xCAFEBABE is shared with Java class files, where the next field is
    # the class file version (45+) rather than a small fat arch count
    #

    if magic in FAT_MAGICS and len(header) == 8:
        byteorder = 'big' if magic == FAT_MAGICS[0] else 'little'
        return int.from_bytes(header[4:], byteorder) < 45

    return False

def resign_macho(filepath):
    """
    Make a patched Mach-O runnable again on macOS.

    Patching a Mach-O invalidates its code signature, and Apple Silicon will
    refuse to run a binary with an invalid (or missing) signature. So we clear
    the quarantine attribute and replace the signature with an ad-hoc one.

    Returns True if the file was re-signed.
    """
    import sys
    import subprocess

    if sys.platform != 'darwin' or not is_macho(filepath):
        return False

    def run(*args):
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            return subprocess.CompletedProcess(args, -1, '', str(e))

    # the attribute may not exist, so failure here is fine
    run('xattr', '-d', 'com.apple.quarantine', filepath)

    #
    # try to keep the original entitlements (eg. JIT), falling back to a
    # plain ad-hoc signature if they cannot be carried over
    #

    result = run('codesign', '--force', '--sign', '-', '--preserve-metadata=entitlements', filepath)
    if result.returncode != 0:
        result = run('codesign', '--force', '--sign', '-', filepath)

    if result.returncode != 0:
        print("[Patching] Failed to re-sign '%s': %s" % (filepath, result.stderr.strip()))
        print("[Patching] To run it, re-sign it manually: codesign --force --sign - '%s'" % filepath)
        return False

    print("[Patching] Re-signed '%s' with an ad-hoc signature" % filepath)
    return True
