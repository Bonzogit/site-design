import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from resources import configuration, contained, inspect, search


class ResourcesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'original.txt').write_text('Original measured rule', encoding='utf-8')
        raw = (self.root / 'original.txt').read_bytes()
        self.item = {'id': 'hardware', 'title': 'Hardware', 'text': 'original.txt', 'url': 'https://example.org/reference', 'sha256': hashlib.sha256(raw).hexdigest()}
        self.write()
        self.sources = [{'id': 'fixture', 'kind': 'design-md', 'root': self.root}]

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        (self.root / 'spec-manifest.json').write_text(json.dumps({'entries': [self.item]}), encoding='utf-8')

    def test_search_returns_traceable_candidate(self):
        rows, warnings = search(self.sources, 'hardware')
        self.assertEqual(rows[0]['id'], 'fixture:hardware')
        self.assertEqual(rows[0]['source'], self.item['url'])
        self.assertFalse(warnings)

    def test_inspect_detects_changed_source(self):
        self.assertTrue(inspect(self.sources, 'fixture:hardware')['sourceHashMatches'])
        (self.root / 'original.txt').write_text('Changed source', encoding='utf-8')
        self.assertFalse(inspect(self.sources, 'fixture:hardware')['sourceHashMatches'])

    def test_escape_rejected(self):
        with self.assertRaises(ValueError):
            contained(self.root, '../outside.txt')
        self.item['text'] = '../outside.txt'
        self.write()
        with self.assertRaises(ValueError):
            inspect(self.sources, 'fixture:hardware')

    def test_missing_configuration_is_explicit(self):
        sources, warnings = configuration(self.root / 'missing.json')
        self.assertFalse(sources)
        self.assertTrue(warnings)

    def test_relative_roots_use_configuration_location(self):
        path = self.root / 'config.json'
        path.write_text(json.dumps({'schemaVersion': 1, 'sources': [{'id': 'a', 'kind': 'design-md', 'root': '.'}]}), encoding='utf-8')
        self.assertEqual(configuration(path)[0][0]['root'], self.root.resolve())

    def test_missing_library_preserves_warning(self):
        self.sources[0]['root'] = self.root / 'missing'
        rows, warnings = search(self.sources, 'hardware')
        self.assertFalse(rows)
        self.assertTrue(warnings)


if __name__ == '__main__':
    unittest.main()
