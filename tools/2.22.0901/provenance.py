#!/usr/bin/env python3
"""Reproducible Phase-1 provenance extraction for the MYGT 4.0.8 bundle.

Reads BIGBIGWON-4.0.8.apkm (APKM = zip of split APKs), verifies SHA-256 of the
bundle and of every contained APK, and emits:
    hashes.json, package-metadata.json, apk-layout.txt, signing-certificate.txt

Usage:
    python3 scripts/provenance.py <apkm> <outdir>
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def collect_layout(apk_path):
    """Return a compact listing of an APK: entry count, top-level dirs, key entries."""
    out = {'entries': 0, 'native_libs': [], 'dex': [], 'assets_top': {}, 'resources_arsc': None,
           'android_manifest_sha256': None, 'certificates': []}
    with zipfile.ZipFile(apk_path) as z:
        infos = z.infolist()
        out['entries'] = len(infos)
        for i in infos:
            n = i.filename
            if n.endswith('.so'):
                out['native_libs'].append({'name': n, 'size': i.file_size,
                                           'sha256': sha256_bytes(z.read(n))})
            elif n.endswith('.dex'):
                out['dex'].append({'name': n, 'size': i.file_size,
                                   'sha256': sha256_bytes(z.read(n))})
            elif n == 'resources.arsc':
                out['resources_arsc'] = sha256_bytes(z.read(n))
            elif n == 'AndroidManifest.xml':
                out['android_manifest_sha256'] = sha256_bytes(z.read(n))
            elif n.startswith('META-INF/') and n.endswith(('.RSA', '.DSA', '.EC')):
                out['certificates'].append({'name': n, 'sha256': sha256_bytes(z.read(n)),
                                            'size': i.file_size})
            elif n.startswith('assets/'):
                top = '/'.join(n.split('/')[:2])
                e = out['assets_top'].setdefault(top, {'files': 0, 'bytes': 0})
                e['files'] += 1
                e['bytes'] += i.file_size
    out['assets_top'] = {k: v for k, v in sorted(out['assets_top'].items())}
    return out


def cert_info(apk_path):
    """Extract the signer PKCS#7 certificate(s) via openssl."""
    info = {}
    with zipfile.ZipFile(apk_path) as z:
        sigs = [n for n in z.namelist() if n.startswith('META-INF/') and n.endswith(('.RSA', '.DSA', '.EC'))]
        if not sigs:
            return info
        name = sigs[0]
        info['pkcs7_entry'] = name
        data = z.read(name)
        info['pkcs7_sha256'] = sha256_bytes(data)
        tmp = '/tmp/_cert_prov.p7'
        pem = '/tmp/_cert_prov.pem'
        open(tmp, 'wb').write(data)
        with open(pem, 'wb') as f:
            subprocess.run(['openssl', 'pkcs7', '-inform', 'DER', '-in', tmp, '-print_certs', '-outform', 'PEM'],
                           stdout=f, stderr=subprocess.DEVNULL)
        for args in (['-subject', '-issuer', '-serial', '-dates', '-fingerprint', '-sha256'],
                     ['-subject', '-issuer', '-serial', '-dates', '-fingerprint', '-sha1']):
            r = subprocess.run(['openssl', 'x509', '-in', pem, '-noout'] + args,
                               capture_output=True, text=True)
            key = 'sha256' if 'sha256' in args else 'sha1'
            info['x509_' + key] = r.stdout.strip().splitlines()
        info['pem'] = open(pem).read()
    return info


def main():
    apkm = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    apks_dir = os.path.join(outdir, 'apks')
    os.makedirs(apks_dir, exist_ok=True)

    # 1. extract (preserving the original untouched)
    with zipfile.ZipFile(apkm) as z:
        names = z.namelist()
        z.extractall(apks_dir)

    hashes = {'apkm': {'path': os.path.abspath(apkm), 'size': os.path.getsize(apkm),
                       'sha256': sha256_file(apkm), 'members': names}, 'apks': {}}
    layout = {}
    for n in sorted(names):
        p = os.path.join(apks_dir, n)
        hashes['apks'][n] = {'size': os.path.getsize(p), 'sha256': sha256_file(p)}
        layout[n] = collect_layout(p)

    meta = {'extracted_at': datetime.now(timezone.utc).isoformat(), 'apkm_sha256': hashes['apkm']['sha256']}
    base = os.path.join(apks_dir, 'base.apk')
    if os.path.exists(base):
        try:
            from loguru import logger
            logger.disable('androguard')
        except Exception:
            pass
        from androguard.core.apk import APK
        a = APK(base)

        def g(name, *args):
            fn = getattr(a, name, None)
            if fn is None:
                return None
            try:
                return fn(*args)
            except Exception as e:  # noqa: BLE001
                return 'ERR:%s' % e

        meta.update({
            'package': g('get_package'),
            'version_code': g('get_androidversion_code'),
            'version_name': g('get_androidversion_name'),
            'app_label': g('get_app_name'),
            'min_sdk': g('get_min_sdk_version'),
            'target_sdk': g('get_target_sdk_version'),
            'effective_target_sdk': g('get_effective_target_sdk_version'),
            'permissions': sorted(g('get_permissions') or []),
            'activities': sorted(g('get_activities') or []),
            'services': sorted(g('get_services') or []),
            'providers': sorted(g('get_providers') or []),
            'receivers': sorted(g('get_receivers') or []),
            'main_activity': g('get_main_activity'),
            'libraries': g('get_libraries'),
            'features': g('get_features'),
            'is_signed': g('is_signed'),
            'signature_names': g('get_signature_names'),
            'is_flutter_app': True,
        })
        open(os.path.join(outdir, 'AndroidManifest.base.xml'), 'w').write(a.get_android_manifest_axml().get_xml().decode('utf-8', 'replace'))

    json.dump(hashes, open(os.path.join(outdir, 'hashes.json'), 'w'), indent=2)
    json.dump(meta, open(os.path.join(outdir, 'package-metadata.json'), 'w'), indent=2)
    with open(os.path.join(outdir, 'apk-layout.txt'), 'w') as f:
        for n, l in layout.items():
            f.write('== %s\n' % n)
            f.write('  entries: %d\n' % l['entries'])
            for lib in l['native_libs']:
                f.write('  lib %-40s %10d  %s\n' % (lib['name'], lib['size'], lib['sha256']))
            for d in l['dex']:
                f.write('  dex %-40s %10d  %s\n' % (d['name'], d['size'], d['sha256']))
            for k, v in l['assets_top'].items():
                f.write('  assets %-38s %6d files %10d bytes\n' % (k, v['files'], v['bytes']))
            if l['resources_arsc']:
                f.write('  resources.arsc %s\n' % l['resources_arsc'])
            if l['certificates']:
                for c in l['certificates']:
                    f.write('  cert %-36s %10d  %s\n' % (c['name'], c['size'], c['sha256']))
            f.write('\n')
    with open(os.path.join(outdir, 'signing-certificate.txt'), 'w') as f:
        for n in sorted(names):
            ci = cert_info(os.path.join(apks_dir, n))
            f.write('== %s\n%s\n\n' % (n, json.dumps(ci, indent=2)))
    print(json.dumps({'apkm_sha256': hashes['apkm']['sha256'],
                      'package': meta.get('package'), 'version': meta.get('version_name'),
                      'min_sdk': meta.get('min_sdk'), 'target_sdk': meta.get('target_sdk')}, indent=2))


if __name__ == '__main__':
    main()
