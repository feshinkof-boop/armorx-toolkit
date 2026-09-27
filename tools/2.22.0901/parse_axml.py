#!/usr/bin/env python3
"""Minimal dependency-free Android binary XML (AXML) parser.

Usage: python3 scripts/parse_axml.py <file.apk|AndroidManifest.xml> [...]

Prints a human-readable XML-like dump. String values are resolved from the
chunk string pool; reference/boolean/int attrs are rendered as-is.
"""
import struct
import sys
import zipfile

RES_STRING_POOL = 0x0001
RES_XML_RESOURCE_MAP = 0x0180
RES_XML_START_ELEMENT = 0x0100
RES_XML_END_ELEMENT = 0x0101
RES_XML_CDATA = 0x0104

TYPE_REFERENCE = 0x01
TYPE_ATTRIBUTE = 0x02
TYPE_STRING = 0x03
TYPE_FLOAT = 0x04
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12


def parse_string_pool(data, off):
    ctype, header_size, chunk_size = struct.unpack_from('<HHI', data, off)
    assert ctype == RES_STRING_POOL
    string_count, style_count, flags, strings_start, styles_start = struct.unpack_from('<IIIII', data, off + 8)
    utf8 = (flags & (1 << 8)) != 0
    offsets = struct.unpack_from('<%dI' % string_count, data, off + header_size)
    out = []
    for o in offsets:
        p = off + strings_start + o
        try:
            if utf8:
                n = data[p]; p += 1
                if n & 0x80:
                    n = ((n & 0x7F) << 8) | data[p]; p += 1
                m = data[p]; p += 1
                if m & 0x80:
                    m = ((m & 0x7F) << 8) | data[p]; p += 1
                out.append(data[p:p + m].decode('utf-8', 'replace'))
            else:
                n = struct.unpack_from('<H', data, p)[0]; p += 2
                if n & 0x8000:
                    n = ((n & 0x7FFF) << 16) | struct.unpack_from('<H', data, p)[0]; p += 2
                out.append(data[p:p + n * 2].decode('utf-16-le', 'replace'))
        except Exception:
            out.append('<decode-error@%d>' % o)
    return out


def parse(data):
    strings = []
    items = []
    off = 8
    while off < len(data):
        ctype, header_size, chunk_size = struct.unpack_from('<HHI', data, off)
        if chunk_size == 0:
            break
        if ctype == RES_STRING_POOL:
            strings = parse_string_pool(data, off)
        elif ctype == RES_XML_START_ELEMENT:
            line, comment, ns, name, attr_start, attr_size, attr_count, id_idx, cls_idx, style_idx = \
                struct.unpack_from('<IIIIHHHHHH', data, off + 8)
            attrs = []
            for i in range(attr_count):
                ao = off + 8 + 8 + attr_start + i * attr_size
                ns_i, name_i, raw_i, typed, val = struct.unpack_from('<IIIII', data, ao)
                if typed == 0xFFFFFFFF:
                    v = strings[raw_i] if 0 <= raw_i < len(strings) else ''
                else:
                    vtype = (typed >> 24) & 0xFF
                    if vtype == TYPE_STRING:
                        v = strings[val] if val < len(strings) else hex(val)
                    elif vtype == TYPE_INT_BOOLEAN:
                        v = 'true' if val else 'false'
                    elif vtype == TYPE_REFERENCE:
                        v = '@0x%08x' % val
                    elif vtype == TYPE_ATTRIBUTE:
                        v = '?0x%08x' % val
                    elif vtype == TYPE_INT_DEC:
                        v = str(val if val < 0x80000000 else val - 0x100000000)
                    elif vtype == TYPE_INT_HEX:
                        v = '0x%08x' % val
                    elif vtype == TYPE_FLOAT:
                        v = str(struct.unpack('<f', struct.pack('<I', val))[0])
                    else:
                        v = 'type:0x%02x=0x%08x' % (vtype, val)
                nm = strings[name_i] if name_i < len(strings) else '?%d' % name_i
                nsn = strings[ns_i] if ns_i < len(strings) else ''
                attrs.append((nm, v, nsn))
            items.append(('start', strings[name] if name < len(strings) else '?%d' % name, attrs))
        elif ctype == RES_XML_END_ELEMENT:
            line, comment, ns, name = struct.unpack_from('<IIII', data, off + 8)
            items.append(('end', strings[name] if name < len(strings) else '?%d' % name, []))
        elif ctype == RES_XML_CDATA:
            line, comment, data_i, typed, val = struct.unpack_from('<IIIII', data, off + 4)
            items.append(('text', strings[data_i] if data_i < len(strings) else '', []))
        off += chunk_size
    return items


def render(items, indent='  '):
    lines = []
    depth = 0
    for kind, name, attrs in items:
        if kind == 'start':
            a = ' '.join('%s="%s"' % (att[0], att[1]) for att in attrs)
            lines.append(indent * depth + '<%s%s%s>' % (name, ' ' if a else '', a))
            depth += 1
        elif kind == 'end':
            depth = max(0, depth - 1)
            lines.append(indent * depth + '</%s>' % name)
        else:
            lines.append(indent * depth + name)
    return '\n'.join(lines)


def load(path):
    if path.endswith('.apk'):
        with zipfile.ZipFile(path) as z:
            return z.read('AndroidManifest.xml')
    return open(path, 'rb').read()


def main():
    for path in sys.argv[1:]:
        print('<!-- %s -->' % path)
        print(render(parse(load(path))))


if __name__ == '__main__':
    main()
