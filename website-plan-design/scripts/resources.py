#!/usr/bin/env python3
"""Read user-configured local resource indexes. No network, copying or design grading."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def contained(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Resource path leaves configured root')
    return path


def configuration(path=None):
    path = Path(path or os.environ.get('WEBSITE_RESOURCES_CONFIG') or
                Path.home() / '.codex/private-config/website-resources.json').resolve()
    if not path.is_file():
        return [], ['No local resource configuration; use accessible task references.']
    data = read(path)
    if data.get('schemaVersion') != 1:
        raise ValueError('Unsupported resource configuration version')
    sources = []
    for row in data.get('sources', []):
        if row.get('kind') not in ('design-md', 'motion-lab'):
            raise ValueError('Unknown resource kind')
        root = Path(os.path.expandvars(row['root'])).expanduser()
        root = root if root.is_absolute() else path.parent / root
        sources.append({**row, 'root': root.resolve()})
    if len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Source IDs must be unique')
    return sources, []


def entries(source):
    root, kind = source['root'], source['kind']
    if kind == 'design-md':
        manifest = read(root / 'spec-manifest.json')
        index_path = root / 'spec-analysis-index.json'
        index = read(index_path).get('records', {}) if index_path.is_file() else {}
        for item in manifest.get('entries', []):
            analysis = index.get(item['id'], {})
            yield {
                'id': source['id'] + ':' + item['id'], 'kind': kind,
                'title': item['title'], 'source': item.get('url'),
                'version': item.get('commit'), 'evidenceStatus': item.get('upstreamEvidenceStatus', 'unverified'),
                'summary': analysis.get('summary', ''), 'features': analysis.get('featureKeys', []),
                'limitations': ['Index is not original-site observation or permission to reuse assets.'],
                'license': None, 'raw': item, '_source': source,
            }
    else:
        catalog = read(root / 'library/catalog.json')
        for item in catalog.get('rows', []):
            yield {
                'id': source['id'] + ':' + item['id'], 'kind': kind,
                'title': item['name'], 'source': item.get('source') or None,
                'version': catalog.get('version'), 'evidenceStatus': item.get('layer'),
                'summary': ' / '.join(str(item.get(k, '')) for k in ('purpose', 'use', 'integration', 'cost', 'tech')),
                'features': [item.get('family', ''), item.get('group', '')],
                'limitations': [item.get('integration', ''), item.get('cost', ''), 'Project integration remains unverified.'],
                'license': item.get('license') or None, 'raw': item, '_source': source,
            }
        for name, purpose in {
            'header': '导航 菜单 navigation menu', 'dialog': '弹窗 对话框 modal dialog',
            'tabs': '标签 页签 tabs specification', 'form': '表单 询盘 form inquiry',
            'reveal': '显现 reveal scroll',
        }.items():
            yield {'id': source['id'] + ':component-' + name, 'kind': kind,
                   'title': name + ' independent component', 'source': None,
                   'version': read(root / 'site-kit/release.json').get('version'),
                   'evidenceStatus': 'independent-entry', 'summary': purpose,
                   'features': [name], 'limitations': ['Read site-kit guide and inspect implementation before reuse.'],
                   'license': None, 'raw': {'guide': 'site-kit/guide.html', 'component': name}, '_source': source}


def public(row):
    return {k: v for k, v in row.items() if k not in ('_source', 'raw')}


def search(sources, query, kind='all', limit=6):
    terms = set(re.findall(r'[\w-]+', query.casefold()))
    if not terms:
        raise ValueError('Query must contain words')
    candidates, warnings = [], []
    for source in sources:
        if kind != 'all' and source['kind'] != kind:
            continue
        try:
            for row in entries(source):
                title = (row['id'] + ' ' + row['title']).casefold()
                rest = (row['summary'] + ' ' + ' '.join(row['features'])).casefold()
                score = sum(4 * (t in title) + (t in rest) for t in terms)
                if score:
                    candidates.append({**public(row), 'metadataMatchScore': score})
        except (OSError, ValueError, KeyError) as error:
            warnings.append({'sourceId': source['id'], 'error': str(error)})
    return sorted(candidates, key=lambda r: (-r['metadataMatchScore'], r['id']))[:limit], warnings


def inspect(sources, identity, max_chars=16000):
    for source in sources:
        if not identity.startswith(source['id'] + ':'):
            continue
        for row in entries(source):
            if row['id'] != identity:
                continue
            item, root = row['raw'], source['root']
            result = {**public(row), 'metadata': item}
            relative = item.get('text') if source['kind'] == 'design-md' else item.get('guide')
            if relative:
                path = contained(root, relative)
                raw = path.read_bytes()
                text = raw.decode('utf-8-sig')
                digest = hashlib.sha256(raw).hexdigest()
                expected = item.get('sha256')
                result.update(text=text[:max_chars], truncated=len(text) > max_chars,
                              sha256=digest, sourceHashMatches=None if not expected else digest == expected)
                if expected and digest != expected:
                    result['limitations'].append('Source hash mismatch; recheck before adoption.')
                if '\ufffd' in text:
                    result['limitations'].append('Replacement characters found; source needs encoding review.')
            else:
                result['limitations'].append('Metadata only; open selected implementation and actual preview.')
            return result
    raise ValueError('Resource ID not found')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    find = sub.add_parser('search')
    find.add_argument('--query', required=True)
    find.add_argument('--kind', choices=['all', 'design-md', 'motion-lab'], default='all')
    find.add_argument('--limit', type=int, default=6)
    detail = sub.add_parser('inspect')
    detail.add_argument('--id', required=True)
    detail.add_argument('--max-chars', type=int, default=16000)
    args = parser.parse_args()
    try:
        sources, warnings = configuration(args.config)
        if args.command == 'doctor':
            checks = []
            for source in sources:
                try:
                    count = sum(1 for _ in entries(source))
                    checks.append({'sourceId': source['id'], 'kind': source['kind'], 'readable': True, 'entries': count})
                except (OSError, ValueError, KeyError) as error:
                    checks.append({'sourceId': source['id'], 'readable': False, 'error': str(error)})
            result = {'sources': checks, 'warnings': warnings, 'visualResearchPerformed': False}
        elif args.command == 'search':
            if not 1 <= args.limit <= 50:
                raise ValueError('limit must be 1..50')
            rows, errors = search(sources, args.query, args.kind, args.limit)
            result = {'candidates': rows, 'warnings': warnings + errors, 'selectionPerformed': False}
        else:
            if not 1 <= args.max_chars <= 100000:
                raise ValueError('max-chars must be 1..100000')
            result = inspect(sources, args.id, args.max_chars)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
