from zerolaunch import ZeroLaunch, Structure, Field, Page, Template, Plugin

site = ZeroLaunch(src='site_src', dest='site_public', config={
	'site_name': 'My ZeroLaunch Site',
	'base_url': 'http://localhost:3000'
})

post = Structure('post')
post.add_field('id', type='int', primary=True)
post.add_field('title', type='string', required=True)
post.add_field('slug', type='string', index=True)
post.add_field('description', type='string')
post.add_field('content', type='markdown')
post.add_field('created_at', type='datetime', default='now')
post.add_field('tags', type='list')

author = Structure('author')
author.add_field('id', type='int', primary=True)
author.add_field('name', type='string')
author.add_field('bio', type='string')

site.add_structure(post)
site.add_structure(author)

site.add_template('base.html', open('layouts/base.html').read())
site.add_template('post.html', open('layouts/post.html').read())

site.create_page(
	collection='posts',
	path='hello-world.md',
	front_matter={
		'title': 'Hello World',
		'slug': 'hello-world',
		'author': 1,
		'tags': ['intro', 'example']
	},
	content="# Hello World\n\nThis is a sample post created via the API."
)

site.copy_static('static/')

site.register_plugin(Plugin('sitemap'))
site.register_plugin(Plugin('rss', options={'limit': 20}))

site.serve(port=3000, livereload=True)

site.build(output_format='static')
# site.deploy(target='ftp', ...)
