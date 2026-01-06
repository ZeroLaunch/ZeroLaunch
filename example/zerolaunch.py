from zerolaunch import ZeroLaunch, Plugin

# --- Configuration
cfg = {
	'site_name': 'My ZeroLaunch Site',
	'base_url': 'https://example.com',
	'author': 'Alice',
}

site = ZeroLaunch(src='site_src', dest='site_public', config=cfg)

# --- Collections (Jekyll-style filesystem)
# Prefer simple filesystem collections using YAML front matter in Markdown files.
# Example layout:
# content/posts/2026-01-01-hello-world.md
# ---
# title: Hello World
# slug: hello-world
# tags: [intro, example]
# categories: [tutorial]
# date: 2026-01-01
# published: true
# ---
# Markdown body...

# Register two collections that read files from disk. The library should
# parse front matter keys (YAML/TOML) into metadata and treat the rest
# of the file as the page content.
site.add_collection('posts', path='content/posts', renderer='md')
site.add_collection('pages', path='content/pages', renderer='md')

# You can still programmatically create single pages if needed (optional):
# site.create_page(collection='posts', path='welcome.md', front_matter={...}, content='...')

# --- Renderers
site.register_renderer('md', engine='markdown', options={'extensions': ['fenced_code', 'tables', 'codehilite']})
site.register_renderer('rst', engine='docutils')
site.register_renderer('adoc', engine='asciidoc')

# --- Templates and helpers
site.add_template('base.html', open('layouts/base.html').read())
site.add_template('post.html', open('layouts/post.html').read())

def excerpt(text, length=140):
	return (text[:length].rsplit(' ', 1)[0] + '...') if len(text) > length else text

site.register_filter('excerpt', excerpt)

# --- Programmatic pages
site.create_page(
	collection='posts',
	path='hello-world.md',
	front_matter={
		'title': 'Hello World',
		'slug': 'hello-world',
		'author': 1,
		'tags': ['intro', 'example'],
		'published': True,
	},
	content='# Hello World\n\nThis is a sample post created via the API.'
)

# --- Static assets and pipeline
site.copy_static('static/')
site.add_asset('styles/main.scss')
site.add_asset('scripts/app.ts')
site.build_assets(pipeline=[
	{'task': 'sass', 'input': 'styles/main.scss', 'output': 'assets/main.css'},
	{'task': 'ts', 'input': 'scripts/app.ts', 'output': 'assets/app.js'},
	{'task': 'bundle', 'inputs': ['assets/app.js'], 'output': 'assets/bundle.js'},
	{'task': 'minify', 'inputs': ['assets/bundle.js'], 'output': 'assets/bundle.min.js'},
	{'task': 'fingerprint', 'inputs': ['assets/bundle.min.js'], 'output': 'assets/bundle.min.[hash].js'},
])

# --- Plugins: sitemap, rss, image optimization
site.register_plugin(Plugin('sitemap'))
site.register_plugin(Plugin('rss', options={'limit': 20, 'collections': ['posts']}))
site.register_plugin(Plugin('image-opt'))

# --- robots and redirects
site.write_robots('User-agent: *\nAllow: /\nDisallow: /admin\n')
site.add_redirect('/old-page.html', '/new-page.html', status=301)

# --- Taxonomies, pagination and indexes
site.add_taxonomy('tags')
site.add_taxonomy('categories')
site.generate_collection_pages(collection='posts', template='posts_index.html', paginate=True, per_page=10)
site.generate_taxonomy_pages('tags', template='tag_list.html')
site.generate_taxonomy_pages('categories', template='category_list.html')

# --- i18n
site.config['default_locale'] = 'en'
site.add_locale('es')
site.add_locale('fr')
site.create_page(path='index.en.md', content='# Hello')
site.create_page(path='index.es.md', content='# Hola')
site.build(i18n=True)

# --- Drafts and scheduled publishing
site.create_page(path='drafts/future.md', front_matter={'title': 'Future Post', 'date': '2099-01-01', 'published': False}, content='...')

# --- Hooks and pipeline
def before(site_obj):
	print('Running before build hook for', site_obj.config.get('site_name'))

site.register_hook('before_build', before)

# --- Deploy
site.build(output_format='static')
site.deploy(target='ftp', options={
	'host': 'ftp.example.com',
	'user': 'ftpuser',
	'password': 'your-password',
	'path': '/public_html',
})
site.deploy(target='sftp', options={
	'host': 'ssh.example.com',
	'user': 'deploy',
	'key': '~/.ssh/id_rsa',
	'path': '/var/www/site',
    'port': 2222
})

# --- Migrations and export
# site.import_from_wordpress(xml='wp-export.xml')
# site.import_from_hugo(dir='hugo_site')
# site.export_content(format='json', dest='backup/content.json')

# --- Headless API
# site.run_api(port=8081, auth={'token': 'secret'})

# --- Search index
# site.build_search_index(collections=['posts', 'pages'], output='search/index.json')
# site.push_search_index(provider='algolia', options={'app_id': 'XXX', 'api_key': 'YYY', 'index': 'my-site'})

# --- Image processing
# site.add_image('images/hero.jpg')
# site.process_images(rules=[{'resize': [800, 600], 'format': 'webp', 'quality': 80}, {'resize': [400, 300], 'format': 'jpeg'}])
