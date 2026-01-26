"""Serve project documentation with Markdown rendering."""

from __future__ import annotations

import argparse
import http.server
import mimetypes
import sys
from email.utils import formatdate
from pathlib import Path
from typing import Final
from urllib.parse import unquote, urlparse

import markdown

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DOCS_ROOT: Final[Path] = PROJECT_ROOT / "docs"
MARKDOWN_EXTENSIONS: Final[list[str]] = ["fenced_code", "tables", "toc"]


def extract_title(markdown_text: str) -> str:
    """Extract a title from the first Markdown H1 line."""
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Documentation"


def render_markdown(
    markdown_text: str,
    title: str,
    source_path: Path,
    last_modified: str,
) -> bytes:
    """Render Markdown text into a full HTML page."""
    body_html = markdown.markdown(markdown_text, extensions=MARKDOWN_EXTENSIONS)
    css = """
    :root {
      color-scheme: dark;
    }
    body {
      margin: 0;
      padding: 0;
      font-family: "IBM Plex Sans", "Manrope", "Space Grotesk", "Segoe UI", sans-serif;
      line-height: 1.7;
      color: #f8f8f2;
      background: #1b1c20;
    }
    main {
      max-width: 920px;
      margin: 40px auto;
      padding: 34px 42px;
      background: #272822;
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
      border-radius: 14px;
      border: 1px solid #3e3f38;
    }
    h1, h2, h3, h4 {
      font-family: "Space Grotesk", "Segoe UI", "Helvetica Neue", sans-serif;
      letter-spacing: -0.01em;
      color: #f9f8f3;
    }
    h1 {
      margin-top: 0;
    }
    a {
      color: #66d9ef;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    pre, code {
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace;
      background: #1e1f1c;
      color: #f8f8f2;
    }
    pre {
      padding: 18px;
      border-radius: 10px;
      overflow-x: auto;
      border: 1px solid #3a3b34;
    }
    code {
      padding: 2px 6px;
      border-radius: 6px;
    }
    blockquote {
      margin: 16px 0;
      padding: 10px 18px;
      border-left: 4px solid #a6e22e;
      background: #20211c;
    }
    table {
      width: 100%%;
      border-collapse: collapse;
      margin: 16px 0;
    }
    th, td {
      border: 1px solid #3a3b34;
      padding: 10px 12px;
      text-align: left;
    }
    .meta {
      font-size: 0.9rem;
      color: #b7b8ae;
      margin-bottom: 24px;
    }
    @media (max-width: 720px) {
      main {
        margin: 16px;
        padding: 20px 22px;
      }
    }
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
  <main>
    <div class="meta">Source: {source_path.relative_to(DOCS_ROOT)}</div>
    {body_html}
  </main>
  <script>
    const lastModified = "{last_modified}";
    async function checkForUpdates() {{
      try {{
        const response = await fetch(window.location.href, {{
          method: "HEAD",
          cache: "no-store",
        }});
        const updated = response.headers.get("Last-Modified");
        if (updated && updated !== lastModified) {{
          window.location.reload();
        }}
      }} catch (error) {{
        // Ignore transient errors.
      }}
    }}
    setInterval(checkForUpdates, 2000);
  </script>
</body>
</html>
"""
    return html.encode("utf-8")


def format_http_date(timestamp: float) -> str:
    """Format a timestamp for HTTP headers."""
    return formatdate(timeval=timestamp, usegmt=True)


def resolve_url_path(url_path: str) -> Path | None:
    """Resolve a URL path to a safe filesystem path under DOCS_ROOT."""
    parsed = urlparse(url_path)
    raw_path = unquote(parsed.path).lstrip("/")
    candidate = (DOCS_ROOT / raw_path).resolve()
    if DOCS_ROOT not in candidate.parents and candidate != DOCS_ROOT:
        return None
    return candidate


def find_target_path(candidate: Path) -> Path | None:
    """Find a concrete file path for a candidate URL path."""
    if candidate == DOCS_ROOT:
        readme = DOCS_ROOT / "README.md"
        return readme if readme.exists() else None

    if candidate.exists() and candidate.is_dir():
        for name in ("index.md", "README.md"):
            entry = candidate / name
            if entry.exists():
                return entry
        return None

    if candidate.exists() and candidate.is_file():
        return candidate

    if candidate.suffix == "":
        md_candidate = candidate.with_suffix(".md")
        if md_candidate.exists():
            return md_candidate

    return None


class DocsRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler that renders Markdown files."""

    def do_GET(self) -> None:  # noqa: N802
        """Serve Markdown or static assets for GET requests."""
        candidate = resolve_url_path(self.path)
        if candidate is None:
            self.send_error(400, "Invalid path")
            return

        target = find_target_path(candidate)
        if target is None:
            self.send_error(404, "Not found")
            return

        if target.suffix.lower() == ".md":
            self.serve_markdown(target)
            return

        self.serve_static(target)

    def do_HEAD(self) -> None:  # noqa: N802
        """Serve headers for GET requests."""
        candidate = resolve_url_path(self.path)
        if candidate is None:
            self.send_error(400, "Invalid path")
            return

        target = find_target_path(candidate)
        if target is None:
            self.send_error(404, "Not found")
            return

        if target.suffix.lower() == ".md":
            payload, last_modified = self.build_markdown_payload(target)
            self.send_response(200)
            self.send_common_headers(
                content_type="text/html; charset=utf-8",
                content_length=len(payload),
                last_modified=last_modified,
            )
            self.end_headers()
            return

        self.send_response(200)
        self.send_common_headers(
            content_type=self.get_content_type(target),
            content_length=target.stat().st_size,
            last_modified=format_http_date(target.stat().st_mtime),
        )
        self.end_headers()

    def serve_markdown(self, path: Path) -> None:
        """Render and serve a Markdown file."""
        payload, last_modified = self.build_markdown_payload(path)
        self.send_response(200)
        self.send_common_headers(
            content_type="text/html; charset=utf-8",
            content_length=len(payload),
            last_modified=last_modified,
        )
        self.end_headers()
        self.wfile.write(payload)

    def serve_static(self, path: Path) -> None:
        """Serve a static file."""
        data = path.read_bytes()
        self.send_response(200)
        self.send_common_headers(
            content_type=self.get_content_type(path),
            content_length=len(data),
            last_modified=format_http_date(path.stat().st_mtime),
        )
        self.end_headers()
        self.wfile.write(data)

    def build_markdown_payload(self, path: Path) -> tuple[bytes, str]:
        """Build the HTML payload and last-modified value for Markdown."""
        markdown_text = path.read_text(encoding="utf-8")
        title = extract_title(markdown_text)
        last_modified = format_http_date(path.stat().st_mtime)
        payload = render_markdown(markdown_text, title, path, last_modified)
        return payload, last_modified

    def get_content_type(self, path: Path) -> str:
        """Infer the Content-Type for a path."""
        content_type, _ = mimetypes.guess_type(path.name)
        return content_type or "application/octet-stream"

    def send_common_headers(
        self,
        *,
        content_type: str,
        content_length: int,
        last_modified: str,
    ) -> None:
        """Send shared headers for responses."""
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Last-Modified", last_modified)
        self.send_header("Cache-Control", "no-store")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Log requests with a shorter format."""
        message = format % args
        sys.stderr.write(f"{self.address_string()} - {message}\n")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the docs server."""
    parser = argparse.ArgumentParser(description="Serve docs with Markdown rendering.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    return parser.parse_args()


def main() -> None:
    """Start the docs HTTP server."""
    args = parse_args()
    server_address = (args.host, args.port)
    httpd = http.server.ThreadingHTTPServer(server_address, DocsRequestHandler)
    print(f"Serving docs at http://{args.host}:{args.port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
