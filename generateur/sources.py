"""Assembler la constitution, les annexes et les documents d'appui liés."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\[([^]]+)\]\(([^)]+)\)')

def slug(title):
    return re.sub(r'[^\w\- ]', '', title.lower().replace('**', '')).replace(' ', '-')

def load_sources():
    paths = [ROOT / 'constitution-projet.md', *sorted((ROOT / 'annexes').glob('annexe-*.md'))]
    paths = [p.resolve() for p in paths]
    for path in paths:
        for match in LINK.finditer(path.read_text(encoding='utf-8-sig')):
            target = urlsplit(match[2])
            if target.scheme or target.netloc or not target.path:
                continue
            resolved = (path.parent / unquote(target.path)).resolve()
            if not resolved.is_relative_to(ROOT.resolve()):
                raise ValueError('Source hors du dépôt : ' + match[2])
            if not resolved.is_file():
                raise ValueError('Source introuvable : ' + match[2])
            if resolved.suffix == '.md' and resolved not in paths:
                paths.append(resolved)
    identifiers = {p: 'source-' + str(i) for i, p in enumerate(paths)}
    anchors, sources = {}, {}
    for path in paths:
        content = path.read_text(encoding='utf-8-sig')
        sources[path.relative_to(ROOT.resolve()).as_posix()] = content
        used = {}
        for line in content.splitlines():
            heading = re.match(r'^#+\s+(.+)', line)
            if heading:
                base = slug(heading[1]); n = used.get(base, 0); used[base] = n + 1
                key = base + ('-' + str(n) if n else '')
                anchors[(path, key)] = identifiers[path] + '-' + key
    original = sources['constitution-projet.md']
    status = next((l.strip('*') for l in original.splitlines() if l.startswith('**Projet ')), 'Projet non approuvé')
    parts = ['# Constitution du Fonds d’unité du 9e Escadron de génie', 'Version : ' + status]
    segments = []
    for path in paths:
        content = sources[path.relative_to(ROOT.resolve()).as_posix()]
        def rewrite(match):
            target = urlsplit(match[2])
            if target.scheme or target.netloc:
                return match[0]
            dest = (path.parent / unquote(target.path)).resolve() if target.path else path
            if dest not in identifiers:
                raise ValueError('Renvoi non exportable : ' + match[2])
            ident = anchors.get((dest, unquote(target.fragment))) if target.fragment else identifiers[dest]
            if not ident:
                raise ValueError('Ancre introuvable : ' + match[2])
            return '[' + match[1] + '](#' + ident + ')'
        lines = LINK.sub(rewrite, content).splitlines()
        marker = None; mapped = {}; used = {}
        for i, line in enumerate(lines):
            heading = re.match(r'^(#+)\s+(.+)', line)
            if not heading:
                continue
            base = slug(heading[2]); n = used.get(base, 0); used[base] = n + 1
            key = base + ('-' + str(n) if n else '')
            lines[i] = '#' + heading[1] + ' ' + heading[2]
            if marker is None:
                marker = lines[i]
            ids = [anchors[(path, key)]]
            if len(heading[1]) == 1:
                ids.append(identifiers[path])
            mapped['H:' + heading[2]] = ids
        if marker is None:
            raise ValueError('Titre manquant : ' + str(path))
        segments.append(dict(id=identifiers[path], titre=marker.lstrip('# '), marker=marker,
                             include_marker=True, shift=0, anchors=mapped,
                             source=path.relative_to(ROOT.resolve()).as_posix()))
        parts.append('\n'.join(lines))
    return '\n\n'.join(parts) + '\n', {'segments': segments}, sources
