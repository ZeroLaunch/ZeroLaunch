from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Tuple, cast


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------
class Plugin:
    """Simple plugin wrapper with a name and options.

    Plugins can be expanded later to include lifecycle hooks and
    initialization logic. Having `name` explicitly typed helps static
    checkers like Pylance understand usage such as `p.name`.
    """
    name: str
    options: Dict[str, Any]

    def __init__(self, name: str, options: Optional[Dict[str, Any]] = None):
        self.name = name
        self.options = options or {}

    def __repr__(self) -> str:
        return f"Plugin(name={self.name}, options={self.options})"


# ---------------------------------------------------------------------
# Front Matter
# ---------------------------------------------------------------------
def parse_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    """
    Minimal YAML-like front matter parser.
    Supports:
      - strings
      - ints
      - booleans
      - inline lists [a, b]
    """
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text

    try:
        _, fm, body = text.split("---", 2)
    except ValueError:
        return {}, text

    meta: Dict[str, Any] = {}
    for line in fm.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith("[") and value.endswith("]"):
            meta[key] = [
                v.strip().strip("'\"")
                for v in value[1:-1].split(",")
                if v.strip()
            ]
        elif value.lower() in ("true", "false"):
            meta[key] = value.lower() == "true"
        else:
            try:
                meta[key] = int(value)
            except ValueError:
                meta[key] = value.strip("'\"")

    return meta, body.lstrip("\n")


# ---------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------
def render_markdown(md: str) -> str:
    """
    Extremely small Markdown renderer (headings + paragraphs).
    """
    lines = md.splitlines()
    html: List[str] = []
    buffer: List[str] = []

    def flush() -> None:
        if buffer:
            html.append(f"<p>{' '.join(buffer)}</p>")
            buffer.clear()

    for line in lines:
        if line.startswith("# "):
            flush()
            html.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            flush()
            html.append(f"<h2>{line[3:].strip()}</h2>")
        elif not line.strip():
            flush()
        else:
            buffer.append(line.strip())

    flush()
    return "\n".join(html)


# ---------------------------------------------------------------------
# ZeroLaunch Core
# ---------------------------------------------------------------------
class ZeroLaunch:
    def __init__(
        self,
        src: str = "site_src",
        dest: str = "site_public",
        config: Optional[Dict[str, Any]] = None,
    ):
        self.src = Path(src)
        self.dest = Path(dest)
        self.config = config or {}

        self.collections: Dict[str, Dict[str, Any]] = {}
        self.renderers: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, str] = {}
        self.filters: Dict[str, Callable[..., Any]] = {}
        self.assets: List[str] = []
        self.plugins: List[Plugin] = []
        self.hooks: Dict[str, List[Callable[[ZeroLaunch], None]]] = {}
        self.taxonomies: List[str] = []

        ensure_dir(self.src)

    # -----------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------
    def add_collection(self, name: str, path: str, renderer: str = "md") -> None:
        self.collections[name] = {
            "path": Path(path),
            "renderer": renderer,
        }

    def generate_collection_pages(self, collection: str, template: str, paginate: bool = False, per_page: int = 10) -> None:
        """Generate index pages for a collection, with optional pagination.

        The `template` should be a template name previously registered
        via `add_template`. Templates can use the placeholders
        `{{ items }}` and `{{ title }}`. When `paginate=True` this will
        write `index.html`, `page2.html`, ... into the collection's
        output folder under `self.dest`.
        """
        coll = self.collections.get(collection)
        if not coll:
            return

        coll_path = self.src / coll["path"]
        items: List[Dict[str, Any]] = []
        for md in coll_path.rglob("*.md"):
            fm, _ = parse_front_matter(read_text(md))
            items.append({"path": md, "meta": fm})

        out = self.dest / collection
        ensure_dir(out)
        tpl = self.templates.get(template)

        def render_list(sub: List[Dict[str, Any]]) -> str:
            return (
                "<ul>"
                + "\n".join([
                    f"<li><a href='{i['path'].stem}.html'>{i['meta'].get('title','(untitled)')}</a></li>"
                    for i in sub
                ])
                + "</ul>"
            )

        if not paginate:
            content = render_list(items)
            if tpl:
                html = tpl.replace("{{ items }}", content).replace("{{ title }}", collection)
            else:
                html = content
            write_text(out / "index.html", html)
            return

        if per_page <= 0:
            per_page = 10
        total = len(items)
        pages = (total + per_page - 1) // per_page
        for p in range(1, pages + 1):
            start = (p - 1) * per_page
            sub = items[start : start + per_page]
            content = render_list(sub)

            nav = ""
            if pages > 1:
                parts: List[str] = []
                if p > 1:
                    prev = "index.html" if p - 1 == 1 else f"page{p-1}.html"
                    parts.append(f"<a href='{prev}'>Prev</a>")
                if p < pages:
                    nxt = f"page{p+1}.html"
                    parts.append(f"<a href='{nxt}'>Next</a>")
                nav = "<nav>" + " | ".join(parts) + "</nav>"

            if tpl:
                page_html = tpl.replace("{{ items }}", content).replace("{{ title }}", f"{collection} - page {p}") + nav
            else:
                page_html = content + nav

            fname = "index.html" if p == 1 else f"page{p}.html"
            write_text(out / fname, page_html)

    def register_renderer(
        self,
        ext: str,
        engine: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.renderers[ext] = {
            "engine": engine,
            "options": options or {},
        }

    def add_template(self, name: str, content: str) -> None:
        self.templates[name] = content

    def register_filter(self, name: str, fn: Callable[..., Any]) -> None:
        self.filters[name] = fn

    def register_plugin(self, plugin: Plugin) -> None:
        self.plugins.append(plugin)

    def register_hook(self, name: str, fn: Callable[[ZeroLaunch], None]) -> None:
        self.hooks.setdefault(name, []).append(fn)

    # -----------------------------------------------------------------
    # Content Creation
    # -----------------------------------------------------------------
    def create_page(
        self,
        collection: str,
        path: str,
        front_matter: Optional[Dict[str, Any]] = None,
        content: str = "",
    ) -> None:
        coll = self.collections.get(collection)
        base = self.src / (coll["path"] if coll else collection)
        ensure_dir(base)

        fm = ""
        if front_matter:
            lines = ["---"]
            for k, v in front_matter.items():
                if isinstance(v, list):
                    arr = cast(List[object], v)
                    lines.append(f"{k}: [{', '.join(str(el) for el in arr)}]")
                else:
                    lines.append(f"{k}: {v}")
            lines.append("---")
            fm = "\n".join(lines) + "\n"

        write_text(base / path, fm + content)

    # -----------------------------------------------------------------
    # Static / Assets
    # -----------------------------------------------------------------
    def copy_static(self, path: str) -> None:
        src = Path(path)
        dst = self.dest / src.name
        if not src.exists():
            return
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    def add_asset(self, path: str) -> None:
        self.assets.append(path)

    # -----------------------------------------------------------------
    # Robots & Redirects
    # -----------------------------------------------------------------
    def write_robots(self, content: str) -> None:
        write_text(self.dest / "robots.txt", content)

    def add_redirect(self, src: str, dst: str, status: int = 301) -> None:
        redirects = self.dest / "_redirects"
        line = f"{src} {dst} {status}\n"
        existing = redirects.read_text(encoding="utf-8") if redirects.exists() else ""
        write_text(redirects, existing + line)

    # -----------------------------------------------------------------
    # Taxonomy
    # -----------------------------------------------------------------
    def add_taxonomy(self, name: str) -> None:
        if name not in self.taxonomies:
            self.taxonomies.append(name)

    def generate_taxonomy_pages(self, taxonomy: str, template: str) -> None:
        """Generate pages for each term in a taxonomy (tags, categories).

        The `template` may use `{{ title }}` and `{{ items }}`.
        """
        coll = self.collections.get("posts")
        if not coll:
            return

        coll_path = self.src / coll["path"]
        tax_map: Dict[str, List[Dict[str, Any]]] = {}
        for md in coll_path.rglob("*.md"):
            fm, _ = parse_front_matter(read_text(md))
            vals = fm.get(taxonomy) or fm.get(taxonomy[:-1])
            if not vals:
                continue
            if isinstance(vals, str):
                vals = [vals]
            for v in vals:
                tax_map.setdefault(v, []).append({"path": md, "meta": fm})

        out_dir = self.dest / taxonomy
        ensure_dir(out_dir)
        tpl = self.templates.get(template)

        for name, items in tax_map.items():
            list_html = (
                "<ul>"
                + "\n".join([
                    f"<li><a href='../posts/{p['path'].stem}.html'>{p['meta'].get('title','(untitled)')}</a></li>"
                    for p in items
                ])
                + "</ul>"
            )
            if tpl:
                html = tpl.replace("{{ title }}", name).replace("{{ items }}", list_html)
            else:
                html = f"<h1>{name}</h1>\n" + list_html
            write_text(out_dir / f"{name}.html", html)
    
    # -----------------------------------------------------------------
    # Build Pipeline
    # -----------------------------------------------------------------
    def _run_hooks(self, name: str) -> None:
        for fn in self.hooks.get(name, []):
            fn(self)

    def _render_page(self, body: str, meta: Dict[str, Any]) -> str:
        html_body = render_markdown(body)
        default_template = "<html><head><title>{{ title }}</title></head><body>{{ content }}</body></html>"
        template = self.templates.get("post.html", default_template)
        return (
            template
            .replace("{{ content }}", html_body)
            .replace("{{ title }}", str(meta.get("title", "")))
        )

    def _build_collection(self, name: str, cfg: Dict[str, Any]) -> None:
        src_dir = self.src / cfg["path"]
        out_dir = self.dest / name
        ensure_dir(out_dir)

        for file in src_dir.rglob("*.md"):
            meta, body = parse_front_matter(read_text(file))
            html = self._render_page(body, meta)
            write_text(out_dir / f"{file.stem}.html", html)

    def _build_sitemap(self) -> None:
        urls = [
            f"<url><loc>/{p.relative_to(self.dest).as_posix()}</loc></url>"
            for p in self.dest.rglob("*.html")
        ]
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<urlset>\n"
            + "\n".join(urls)
            + "\n</urlset>"
        )
        write_text(self.dest / "sitemap.xml", xml)

    def build(self, output_format: str = "static") -> None:
        self._run_hooks("before_build")

        if self.dest.exists():
            shutil.rmtree(self.dest)
        ensure_dir(self.dest)

        for name, cfg in self.collections.items():
            self._build_collection(name, cfg)

        static_src = self.src / "static"
        if static_src.exists():
            shutil.copytree(static_src, self.dest / "static")

        if any(p.name == "sitemap" for p in self.plugins):
            self._build_sitemap()

        self._run_hooks("after_build")

    # -----------------------------------------------------------------
    # Deploy (Stub)
    # -----------------------------------------------------------------
    def deploy(self, target: str, options: Optional[Dict[str, Any]] = None) -> None:
        print(f"[ZeroLaunch] Deploy target={target}, options={options} (plugin stub)")
        
__all__ = ["ZeroLaunch", "Plugin"]
