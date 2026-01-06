"""ZeroLaunch - minimal example implementation matching the example API.

This is a lightweight, dependency-free implementation intended to help
you design the public API. It supports filesystem collections (markdown
with front matter), simple templates, filters, a basic asset copy,
and simple sitemap/robots generation. Deploy methods are stubs that
print actions (do not perform network operations).
"""
from __future__ import annotations

import os
import shutil
import threading
import http.server
import socketserver
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any


class Plugin:
    def __init__(self, name: str, options: Optional[Dict[str, Any]] = None):
        self.name = name
        self.options = options or {}


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _parse_front_matter(text: str) -> (Dict[str, Any], str):
    """Parse a very small subset of YAML front matter.

    Expects front matter delimited by leading '---' and trailing '---'.
    Supports simple scalars and inline lists like [a, b].
    """
    text = text.lstrip('\ufeff')
    if text.startswith('---'):
        try:
            _, fm, rest = text.split('---', 2)
        except ValueError:
            return {}, text
        meta = {}
        for line in fm.splitlines():
            if not line.strip() or ':' not in line:
                continue
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            # list
            if val.startswith('[') and val.endswith(']'):
                items = [i.strip().strip("'\"") for i in val[1:-1].split(',') if i.strip()]
                meta[key] = items
            elif val.lower() in ('true', 'false'):
                meta[key] = val.lower() == 'true'
            else:
                # try int
                try:
                    meta[key] = int(val)
                except Exception:
                    meta[key] = val.strip().strip("'\"")
        return meta, rest.lstrip('\n')
    return {}, text


def _simple_markdown(md: str) -> str:
    """Tiny markdown -> HTML converter for headings and paragraphs."""
    lines = md.splitlines()
    out = []
    buf = []

    def flush():
        nonlocal buf
        if buf:
            out.append(f"<p>{'\n'.join(buf)}</p>")
            buf = []

    for line in lines:
        if line.startswith('# '):
            flush()
            out.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith('## '):
            flush()
            out.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.strip() == '':
            flush()
        else:
            buf.append(line)
    flush()
    return '\n'.join(out)


class ZeroLaunch:
    def __init__(self, src: str = 'site_src', dest: str = 'site_public', config: Optional[Dict] = None):
        self.src = Path(src)
        self.dest = Path(dest)
        self.config = config or {}

        self.collections: Dict[str, Dict[str, Any]] = {}
        self.renderers: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, str] = {}
        self.filters: Dict[str, Callable] = {}
        self.assets: List[str] = []
        self.plugins: List[Plugin] = []
        self.hooks: Dict[str, List[Callable]] = {}
        self.taxonomies: List[str] = []

        _ensure_dir(self.src)

    # Collections
    def add_collection(self, name: str, path: str, renderer: str = 'md'):
        self.collections[name] = {'path': Path(path), 'renderer': renderer}

    # Renderers
    def register_renderer(self, ext: str, engine: str = 'markdown', options: Optional[Dict] = None):
        self.renderers[ext] = {'engine': engine, 'options': options or {}}

    # Templates
    def add_template(self, name: str, content: str):
        self.templates[name] = content

    # Filters/helpers
    def register_filter(self, name: str, fn: Callable):
        self.filters[name] = fn

    # Page creation (programmatic)
    def create_page(self, collection: str, path: str, front_matter: Optional[Dict] = None, content: str = ''):
        coll = self.collections.get(collection)
        if not coll:
            # create collection on-demand under src
            coll_path = self.src / collection
        else:
            coll_path = self.src / coll['path']
        _ensure_dir(coll_path)
        file_path = coll_path / path
        fm = ''
        if front_matter:
            fm_lines = ['---']
            for k, v in front_matter.items():
                if isinstance(v, list):
                    fm_lines.append(f"{k}: [{', '.join(map(str, v))}]")
                else:
                    fm_lines.append(f"{k}: {v}")
            fm_lines.append('---')
            fm = '\n'.join(fm_lines) + '\n'
        file_path.write_text(fm + content, encoding='utf-8')

    def copy_static(self, path: str):
        src = Path(path)
        dst = self.dest / src.name
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    def add_asset(self, path: str):
        self.assets.append(path)

    def build_assets(self, pipeline: List[Dict[str, Any]]):
        out_dir = self.dest / 'assets'
        _ensure_dir(out_dir)
        for asset in self.assets:
            src = Path(asset)
            if src.exists():
                shutil.copy(src, out_dir / src.name)

    def register_plugin(self, plugin: Any):
        if isinstance(plugin, Plugin):
            self.plugins.append(plugin)
        else:
            self.plugins.append(Plugin(str(plugin)))

    def write_robots(self, content: str):
        _ensure_dir(self.dest)
        (self.dest / 'robots.txt').write_text(content, encoding='utf-8')

    def add_redirect(self, src: str, dst: str, status: int = 301):
        _ensure_dir(self.dest)
        f = self.dest / '_redirects'
        line = f"{src} {dst} {status}\n"
        f.write_text((f.read_text() if f.exists() else '') + line, encoding='utf-8')

    def add_taxonomy(self, name: str):
        if name not in self.taxonomies:
            self.taxonomies.append(name)

    def generate_collection_pages(self, collection: str, template: str, paginate: bool = False, per_page: int = 10):
        coll = self.collections.get(collection)
        if not coll:
            return
        coll_path = self.src / coll['path']
        items = []
        for md in coll_path.rglob('*.md'):
            raw = md.read_text(encoding='utf-8')
            meta, _ = _parse_front_matter(raw)
            items.append({'path': md, 'meta': meta})
        body = '<ul>' + '\n'.join([f"<li><a href='{i['path'].stem}.html'>{i['meta'].get('title','(untitled)')}</a></li>" for i in items]) + '</ul>'
        out = self.dest / collection
        _ensure_dir(out)
        (out / 'index.html').write_text(body, encoding='utf-8')

    def generate_taxonomy_pages(self, taxonomy: str, template: str):
        coll = self.collections.get('posts')
        if not coll:
            return
        coll_path = self.src / coll['path']
        tax_map: Dict[str, List[Dict[str, Any]]] = {}
        for md in coll_path.rglob('*.md'):
            raw = md.read_text(encoding='utf-8')
            meta, _ = _parse_front_matter(raw)
            vals = meta.get(taxonomy) or meta.get(taxonomy[:-1])  # tags vs tag
            if not vals:
                continue
            if isinstance(vals, str):
                vals = [vals]
            for v in vals:
                tax_map.setdefault(v, []).append({'path': md, 'meta': meta})
        out_dir = self.dest / taxonomy
        _ensure_dir(out_dir)
        for name, items in tax_map.items():
            body = f"<h1>{name}</h1>\n<ul>" + '\n'.join([f"<li><a href='../posts/{p['path'].stem}.html'>{p['meta'].get('title')}</a></li>" for p in items]) + '</ul>'
            (out_dir / f"{name}.html").write_text(body, encoding='utf-8')

    def register_hook(self, name: str, fn: Callable):
        self.hooks.setdefault(name, []).append(fn)

    def _run_hooks(self, name: str):
        for fn in self.hooks.get(name, []):
            try:
                fn(self)
            except Exception:
                pass

    def build(self, **kwargs):
        self._run_hooks('before_build')
        if self.dest.exists():
            shutil.rmtree(self.dest)
        _ensure_dir(self.dest)

        for coll_name, coll in self.collections.items():
            src_dir = self.src / coll['path']
            if not src_dir.exists():
                continue
            out_dir = self.dest / coll_name
            _ensure_dir(out_dir)
            for md in src_dir.rglob('*.md'):
                raw = md.read_text(encoding='utf-8')
                meta, body = _parse_front_matter(raw)
                html_body = _simple_markdown(body)
                tpl = self.templates.get('post.html') or '<html><body>{{ content }}</body></html>'
                html = tpl.replace('{{ content }}', html_body)
                html = html.replace('{{ title }}', meta.get('title', ''))
                out_file = out_dir / f"{md.stem}.html"
                out_file.write_text(html, encoding='utf-8')

        static_src = self.src / 'static'
        if static_src.exists():
            shutil.copytree(static_src, self.dest / 'static')

        if any(p.name == 'sitemap' for p in self.plugins):
            urls = []
            for html in self.dest.rglob('*.html'):
                rel = html.relative_to(self.dest).as_posix()
                urls.append(rel)
            sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset>\n' + '\n'.join([f"<url><loc>/{u}</loc></url>" for u in urls]) + '\n</urlset>'
            (self.dest / 'sitemap.xml').write_text(sitemap, encoding='utf-8')

        self._run_hooks('after_build')

    def build_search_index(self, collections: List[str], output: str):
        idx = []
        for coll in collections:
            c = self.collections.get(coll)
            if not c:
                continue
            for md in (self.src / c['path']).rglob('*.md'):
                raw = md.read_text(encoding='utf-8')
                meta, body = _parse_front_matter(raw)
                idx.append({'path': str(md), 'title': meta.get('title'), 'body': body})
        outp = self.dest / output
        _ensure_dir(outp.parent)
        outp.write_text(json.dumps(idx), encoding='utf-8')

    def push_search_index(self, provider: str, options: Dict[str, Any]):
        print(f"Pushing search index to {provider} (stub)")

    def add_image(self, path: str):
        self.add_asset(path)

    def process_images(self, rules: List[Dict[str, Any]]):
        print('Processing images (stub)')

    def run_api(self, port: int = 8081, auth: Optional[Dict[str, Any]] = None):
        posts = []
        coll = self.collections.get('posts')
        if coll:
            for md in (self.src / coll['path']).rglob('*.md'):
                raw = md.read_text(encoding='utf-8')
                meta, body = _parse_front_matter(raw)
                posts.append({'meta': meta, 'body': body})

        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith('/api/posts'):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(posts).encode('utf-8'))
                    return
                return super().do_GET()

        def serve():
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(f"API serving on http://localhost:{port}")
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    pass

        t = threading.Thread(target=serve, daemon=True)
        t.start()

    def deploy(self, target: str, options: Optional[Dict[str, Any]] = None):
        print(f"Deploying to {target} with options: {options} (stub) - implement real deploy in plugins")

    def export_content(self, format: str = 'json', dest: Optional[str] = None):
        destp = Path(dest or (self.dest / 'export.json'))
        _ensure_dir(destp.parent)
        out = []
        coll = self.collections.get('posts')
        if coll:
            for md in (self.src / coll['path']).rglob('*.md'):
                raw = md.read_text(encoding='utf-8')
                meta, body = _parse_front_matter(raw)
                out.append({'meta': meta, 'body': body})
        destp.write_text(json.dumps(out), encoding='utf-8')


__all__ = ['ZeroLaunch', 'Plugin']
