"""Exercise the maintenance CLI without network calls or modifying the checkout."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'site'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '__pycache__', 'reports', 'tests'))
        self.before = (self.root / 'index.html').read_text()
        self.registry = json.loads((self.root / 'data/presence.json').read_text())

    def response(self, request, **kwargs):
        url = request.full_url
        if url.endswith('/data/presence.json'):
            return io.BytesIO(json.dumps(self.registry).encode())
        if '/author/' in url:
            return io.BytesIO(b'<a href="/articles/2026/11/20/refresh-regression">New writing fixture</a>')
        title = 'Attention Deficit' if 'attentiondeficit' in url else 'Alexa'
        return io.BytesIO(f'<rss><channel><title>{title}</title><item><title>Published episode fixture</title><link>https://example.com/episode</link><pubDate>Fri, 20 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'.encode())

    def cli(self, site='personal', unavailable=False):
        with patch.object(sys, 'argv', ['maintain-presence.py', '--site', site, '--refresh']), \
             patch('urllib.request.urlopen', side_effect=OSError('fixture source unavailable') if unavailable else self.response), \
             contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(self.root / 'scripts/maintain-presence.py'), run_name='__main__')

    def assert_personal(self):
        source = (self.root / 'index.html').read_text()
        self.assertNotIn('Latest episode', source)
        self.assertNotIn('Latest published episode', source)
        self.assertNotIn('presence:latest-', source)
        self.assertIn('New writing fixture', source)
        # Everything outside recent writing stays byte-for-byte unchanged.
        def without_writing(value):
            return value.split('<!-- presence:writing:start -->')[0] + value.split('<!-- presence:writing:end -->')[1]
        self.assertEqual(without_writing(source), without_writing(self.before))
        self.assertIn('src="https://anchor.fm/alexagriffith/embed"', source)
        self.assertIn('class="collapse show" id="redHatContent"', source)
        return source

    def test_valid_feeds_refresh_writing_without_episode_rows(self):
        self.cli()
        first = self.assert_personal()
        snapshot = json.loads((self.root / 'data/published.json').read_text())
        self.assertTrue(snapshot['alexas_input'])
        self.assertTrue(snapshot['attention'])
        self.cli()
        self.assertEqual(first, self.assert_personal())

    def test_saved_episode_snapshots_survive_unavailable_sources(self):
        self.cli()
        first = self.assert_personal()
        self.cli(unavailable=True)
        self.assertEqual(first, self.assert_personal())
        health = json.loads((self.root / 'reports/source-health.json').read_text())
        self.assertEqual(set(health['unverified_sources']), {'alexas_input', 'attention', 'writing'})

    def test_podcast_mode_still_refreshes_episodes(self):
        (self.root / 'data/site.json').write_text(json.dumps({'attention': {}, 'platforms': []}))
        self.cli('podcast')
        site = json.loads((self.root / 'data/site.json').read_text())
        self.assertEqual(site['latest_published']['title'], 'Published episode fixture')
        self.assertEqual(site['attention']['episodes'][0]['title'], 'Published episode fixture')
        self.assertEqual(site['writing'][0]['title'], 'New writing fixture')


if __name__ == '__main__':
    unittest.main()
