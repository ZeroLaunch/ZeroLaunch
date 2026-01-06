"""Comprehensive examples for a user-designed `zerolaunch` library.

This file is an extended example suite demonstrating many hypothetical
features you might implement in `zerolaunch`. It purposefully does not
implement the library; instead it shows snippets and full examples you
can copy into your docs. Run with `--show <name>` to print a named
example or `--all` to print everything.

Adjust API names to match your final design.
"""

from __future__ import annotations
import argparse
import textwrap
import json
import os
from typing import Dict

try:
	# If the real library exists, examples that run may use it.
	import zerolaunch
	ZEROLAUNCH_AVAILABLE = True
except Exception:
	zerolaunch = None
	ZEROLAUNCH_AVAILABLE = False


EXAMPLES: Dict[str, str] = {}


EXAMPLES['quick_start'] = textwrap.dedent('''
from zerolaunch import ZeroLaunch

cfg = {
	'site_name': 'My ZeroLaunch Site',
	'base_url': 'http://localhost:3000',
}

site = ZeroLaunch(src='site_src', dest='site_public', config=cfg)
site.build()
site.serve(port=3000, livereload=True)
''')


EXAMPLES['structures_and_fields'] = textwrap.dedent('''
from zerolaunch import Structure

# Define a rich 'post' structure (collection)
post = Structure('post')
post.add_field('id', type='int', primary=True)
post.add_field('title', type='string', required=True)
post.add_field('slug', type='string', index=True)
post.add_field('summary', type='string')
post.add_field('content', type='markdown')
post.add_field('created_at', type='datetime', default='now')
post.add_field('published', type='bool', default=False)
post.add_field('tags', type='list')

site.add_structure(post)
''')


EXAMPLES['multiple_renderers'] = textwrap.dedent('''
# Support multiple rendering engines
site.register_renderer('md', engine='markdown', options={'extensions': ['fenced_code', 'tables']})
site.register_renderer('rst', engine='docutils')
site.register_renderer('adoc', engine='asciidoc')

# Use them when creating pages
site.create_page(path='about.rst', content='''"""About"""\n\nAbout site in reStructuredText''', renderer='rst')
site.create_page(path='guide.adoc', content='= Guide\n... ', renderer='adoc')
''')


EXAMPLES['templates_filters_helpers'] = textwrap.dedent('''
# Templates and custom helpers/filters
site.add_template('base.html', open('layouts/base.html').read())

def excerpt(text, length=120):
	return text[:length].rsplit(' ', 1)[0] + '...'

site.register_filter('excerpt', excerpt)
''')


EXAMPLES['assets_pipeline'] = textwrap.dedent('''
# Asset pipeline examples
site.add_asset('styles/main.scss')
site.add_asset('scripts/app.ts')

# Compile SASS, transpile TypeScript, bundle and fingerprint
site.build_assets(
	pipeline=[
		{'task': 'sass', 'input': 'styles/main.scss', 'output': 'assets/main.css'},
		{'task': 'ts', 'input': 'scripts/app.ts', 'output': 'assets/app.js'},
		{'task': 'bundle', 'inputs': ['assets/app.js'], 'output': 'assets/bundle.js'},
		{'task': 'minify', 'inputs': ['assets/bundle.js'], 'output': 'assets/bundle.min.js'},
		{'task': 'fingerprint', 'inputs': ['assets/bundle.min.js'], 'output': 'assets/bundle.min.[hash].js'},
	]
)
''')


EXAMPLES['sitemap_and_robots'] = textwrap.dedent('''
# Sitemap and robots management
site.register_plugin('sitemap')

# Generate sitemap automatically during build
site.build()  # plugin creates sitemap.xml in output

# Manage robots.txt programmatically
site.set_robots(rules=[
	{'user_agent': '*', 'allow': '/', 'disallow': ['/admin']},
	{'user_agent': 'BadBot', 'disallow': ['/']}
])

# Or write custom robots content
site.write_robots('User-agent: *\nDisallow: /admin\n')
''')


EXAMPLES['rss_and_feed'] = textwrap.dedent('''
# Generate RSS and Atom feeds
site.register_plugin('rss', options={'limit': 20, 'collections': ['posts']})
site.build()  # rss.xml and atom.xml created
''')


EXAMPLES['pagination_and_collections'] = textwrap.dedent('''
# Pagination example
site.generate_collection_pages(collection='posts', template='posts_index.html', paginate=True, per_page=10)

# Taxonomies (tags/categories)
site.add_taxonomy('tags')
site.add_taxonomy('categories')

# Generate tag pages
site.generate_taxonomy_pages('tags', template='tag_list.html')
''')


EXAMPLES['i18n_and_translations'] = textwrap.dedent('''
# Internationalization
site.config['default_locale'] = 'en'
site.add_locale('es')
site.add_locale('fr')

# Create localized pages
site.create_page(path='index.en.md', content='# Hello')
site.create_page(path='index.es.md', content='# Hola')

# During build, outputs are placed in /en/, /es/ etc. or using subdomains
site.build(i18n=True)
''')


EXAMPLES['drafts_scheduling'] = textwrap.dedent('''
# Drafts and scheduled publishing
site.create_page(path='drafts/future.md', front_matter={'title':'Future', 'date':'2099-01-01', 'published':False}, content='...')

# Build with drafts included
site.build(include_drafts=True)

# Or only publish scheduled pages whose date <= now
site.build(publish_scheduled=True)
''')


EXAMPLES['preview_and_live_reload'] = textwrap.dedent('''
# Preview server with live reload
site.serve(port=3000, livereload=True, open_browser=True)

# Serve over HTTPS for testing
site.serve(port=3443, tls={'cert': 'cert.pem', 'key': 'key.pem'})
''')


EXAMPLES['programmatic_generation'] = textwrap.dedent('''
# Generate pages from external data sources (JSON/CSV/API)
import csv

with open('data/posts.csv') as fh:
	reader = csv.DictReader(fh)
	for row in reader:
		site.create_page(
			collection='posts',
			path=f"posts/{row['slug']}.md",
			front_matter={'title': row['title'], 'date': row['date']},
			content=row['body_markdown']
		)
''')


EXAMPLES['search_index'] = textwrap.dedent('''
# Build a client-side search index (lunr.js) or push to Algolia
site.build_search_index(collections=['posts', 'pages'], output='search/index.json')

# Optionally push to Algolia
site.push_search_index(provider='algolia', options={'app_id':'XXX','api_key':'YYY','index':'my-site'})
''')


EXAMPLES['image_processing'] = textwrap.dedent('''
# Responsive image generation and optimization
site.add_image('images/hero.jpg')
site.process_images(rules=[{'resize':[800,600], 'format':'webp', 'quality':80}, {'resize':[400,300], 'format':'jpeg'}])

# Use helper in templates: responsive_image('hero.jpg')
''')


EXAMPLES['deploy_examples'] = textwrap.dedent('''
# Deployment examples
site.build()
site.deploy(target='s3', options={'bucket':'my-bucket', 'region':'us-east-1'})

# Or deploy via rsync
site.deploy(target='rsync', options={'host':'example.com', 'dest':'/var/www/site'})
''')


EXAMPLES['ci_cd'] = textwrap.dedent('''
# CI pipeline snippet (GitHub Actions)
name: Build and Deploy
on: [push]
jobs:
  build:
	runs-on: ubuntu-latest
	steps:
	  - uses: actions/checkout@v2
	  - name: Set up Python
		uses: actions/setup-python@v2
		with:
		  python-version: '3.11'
	  - name: Install deps
		run: pip install zerolaunch
	  - name: Build
		run: zerolaunch build
	  - name: Deploy
		run: zerolaunch deploy --target s3 --bucket my-bucket
''')


EXAMPLES['hooks_and_plugins'] = textwrap.dedent('''
# Hooks and plugin examples
def on_before_build(site):
	print('About to build', site.config.get('site_name'))

site.register_hook('before_build', on_before_build)

# Plugin example
site.register_plugin('minify-html')
''')


EXAMPLES['robots_and_redirects'] = textwrap.dedent('''
# Manage robots.txt and redirects
site.write_robots('User-agent: *\nAllow: /\nDisallow: /admin')

# Programmatic redirects
site.add_redirect('/old-page.html', '/new-page.html', status=301)
''')


EXAMPLES['headless_mode_and_api'] = textwrap.dedent('''
# Headless mode: expose content as JSON for a frontend app
site.run_api(port=8081, auth={'token':'secret'})

# Sample API call: GET /api/posts -> JSON list of posts
''')


EXAMPLES['migration_examples'] = textwrap.dedent('''
# Content migration helpers
site.import_from_wordpress(xml='wp-export.xml')
site.import_from_hugo(dir='hugo_site')

# Export content as JSON for backup
site.export_content(format='json', dest='backup/content.json')
''')


def print_example(name: str) -> None:
	if name not in EXAMPLES:
		print(f"Unknown example '{name}'. Available: {', '.join(EXAMPLES.keys())}")
		return
	print(f"\n=== Example: {name} ===\n")
	print(EXAMPLES[name])


def main():
	parser = argparse.ArgumentParser(description='Print expanded zerolaunch examples')
	parser.add_argument('--show', '-s', help='Show a named example')
	parser.add_argument('--all', '-a', action='store_true', help='Show all examples')
	args = parser.parse_args()

	if args.all:
		for k in EXAMPLES:
			print_example(k)
		return

	if args.show:
		print_example(args.show)
		return

	print('Available examples:')
	for k in EXAMPLES:
		print(' -', k)
	print('\nRun `python zerolaunch.py --show structures_and_fields` to print one.')


if __name__ == '__main__':
	main()
