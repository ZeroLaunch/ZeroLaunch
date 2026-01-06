from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Tuple


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
        self.filters: Dict[str, Callable] = {}
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

    def register_filter(self, name: str, fn: Callable) -> None:
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
                    lines.append(f"{k}: [{', '.join(map(str, v))}]")
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

    # -----------------------------------------------------------------
    # Build Pipeline
    # -----------------------------------------------------------------
    def _run_hooks(self, name: str) -> None:
        for fn in self.hooks.get(name, []):
            fn(self)

    def _render_page(self, body: str, meta: Dict[str, Any]) -> str:
        html_body = render_markdown(body)
        template = self.templates.get(
            "post.html",
            "<html><head><title>{{ title }}</title></head><body>{{ content }}</body></html>",
        )
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
