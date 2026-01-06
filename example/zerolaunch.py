from zerolaunch import ZeroLaunch, Plugin

# --- Configuration
cfg = {
	'site_name': 'My ZeroLaunch Site',
	'base_url': 'https://example.com',
	'author': 'Alice',
}

site = ZeroLaunch(src='site_src', dest='site_public', config=cfg)

# --- Collections (Jekyll-style filesystem)
site.add_collection('posts', path='content/posts', renderer='md')
site.add_collection('pages', path='content/pages', renderer='md')

# --- Renderers
site.register_renderer('md', engine='markdown', options={'extensions': ['fenced_code', 'tables', 'codehilite']})
site.register_renderer('rst', engine='docutils')
site.register_renderer('adoc', engine='asciidoc')

# --- Templates
site.add_template('base.html', open('layouts/base.html').read())
site.add_template('post.html', open('layouts/post.html').read())

# --- Filters
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
