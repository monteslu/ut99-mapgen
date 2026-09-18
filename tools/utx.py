"""
utx.py - read texture names and sizes out of UE1 .utx packages.

A UE1 package is: header, then a name table, then export/import tables. Each
export points at a serialized object; for a Texture the USize/VSize live in its
property list. We only need names and dimensions (to scale texture mapping), so
this reads the tables and walks just far enough into each texture's properties.

Format reference: the 469 SDK's Core/Inc/UnLinker.h + UnObjBas.h.
"""

import os
import struct

# UE1 stores most counts/offsets as "compact indices": a variable-length signed
# integer where the first byte carries a sign bit and a continuation bit.
def _index(buf, pos):
    b = buf[pos]
    pos += 1
    neg = b & 0x80
    value = b & 0x3F
    if b & 0x40:
        shift = 6
        while True:
            b = buf[pos]
            pos += 1
            value |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                break
    return (-value if neg else value), pos


class Package:
    def __init__(self, path):
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]
        with open(path, "rb") as fh:
            self.buf = fh.read()
        self._parse()

    def _parse(self):
        b = self.buf
        tag, ver, lic = struct.unpack_from("<Ihh", b, 0)
        if tag != 0x9E2A83C1:
            raise ValueError(f"{self.path}: not an Unreal package")
        self.version = ver
        (flags, name_count, name_off, export_count, export_off,
         import_count, import_off) = struct.unpack_from("<7I", b, 8)

        # GUID + generations follow for version >= 68; we do not need them.
        self.names = []
        pos = name_off
        for _ in range(name_count):
            if ver < 64:                      # old: null-terminated
                end = b.index(b"\0", pos)
                self.names.append(b[pos:end].decode("latin-1"))
                pos = end + 1
            else:                             # new: length-prefixed
                ln = b[pos]
                pos += 1
                self.names.append(b[pos:pos + ln - 1].decode("latin-1"))
                pos += ln
            pos += 4                          # object flags

        self.exports = []
        pos = export_off
        for _ in range(export_count):
            cls, pos = _index(b, pos)
            sup, pos = _index(b, pos)
            pkg = struct.unpack_from("<i", b, pos)[0]; pos += 4
            nm, pos = _index(b, pos)
            eflags = struct.unpack_from("<I", b, pos)[0]; pos += 4
            size, pos = _index(b, pos)
            offset = 0
            if size > 0:
                offset, pos = _index(b, pos)
            self.exports.append({"class": cls, "name": self.names[nm],
                                 "size": size, "offset": offset})

        # An import records the class it is (ClassName) and what it is called
        # (ObjectName). An export's class field points here, so the name that
        # identifies "this export is a Texture" is the import's ObjectName.
        self.imports = []
        pos = import_off
        for _ in range(import_count):
            cp, pos = _index(b, pos)
            cn, pos = _index(b, pos)
            pkg = struct.unpack_from("<i", b, pos)[0]; pos += 4
            on, pos = _index(b, pos)
            self.imports.append(self.names[on])

    def _class_name(self, idx):
        """Export class refs are negative for imports, positive for exports."""
        if idx < 0:
            i = -idx - 1
            return self.imports[i] if i < len(self.imports) else ""
        if idx > 0:
            return self.exports[idx - 1]["name"]
        return ""

    def textures(self):
        """{name: (usize, vsize)} for every Texture export in the package."""
        out = {}
        for exp in self.exports:
            if self._class_name(exp["class"]) != "Texture":
                continue
            out[exp["name"]] = self._sizes(exp)
        return out

    def _sizes(self, exp):
        """Scan an export's property list for USize/VSize.

        Properties are (name-index, info-byte, [size], value) triples ending at
        a "None" name. We only decode enough to find the two ints we want, and
        fall back to 256x256 (the most common UT99 size) if the walk desyncs.
        """
        b = self.buf
        pos = exp["offset"]
        end = pos + exp["size"]
        found = {}
        try:
            while pos < end and len(found) < 2:
                nidx, pos = _index(b, pos)
                if nidx >= len(self.names):
                    break
                pname = self.names[nidx]
                if pname == "None":
                    break
                info = b[pos]; pos += 1
                ptype = info & 0x0F
                sz_code = (info >> 4) & 0x07

                if ptype == 10:                       # struct: skip its name
                    _, pos = _index(b, pos)
                if sz_code == 0:
                    size = 1
                elif sz_code == 1:
                    size = 2
                elif sz_code == 2:
                    size = 4
                elif sz_code == 3:
                    size = 12
                elif sz_code == 4:
                    size = 16
                elif sz_code == 5:
                    size = b[pos]; pos += 1
                elif sz_code == 6:
                    size = struct.unpack_from("<H", b, pos)[0]; pos += 2
                else:
                    size = struct.unpack_from("<I", b, pos)[0]; pos += 4
                if info & 0x80 and ptype != 3:        # array index byte
                    pos += 1

                if pname in ("USize", "VSize"):
                    if ptype == 2:                    # int
                        found[pname] = struct.unpack_from("<i", b, pos)[0]
                    elif ptype == 1:                  # byte
                        found[pname] = b[pos]
                pos += size
        except (IndexError, struct.error):
            pass
        return (found.get("USize", 256), found.get("VSize", 256))


def scan(textures_dir):
    """{package: {texture: (u, v)}} for every .utx in a directory."""
    out = {}
    for fn in sorted(os.listdir(textures_dir)):
        if not fn.lower().endswith(".utx"):
            continue
        try:
            pkg = Package(os.path.join(textures_dir, fn))
            out[pkg.name] = pkg.textures()
        except Exception:
            continue
    return out
