import http.server
import socketserver
import os
import argparse


def run_server(port=8000, directory="."):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def do_GET(self):
            # If requesting a Markdown file without ?raw=true, serve the HTML wrapper
            if self.path.endswith(".md") and "raw=true" not in self.path:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                # HTML Wrapper with marked.js and GitHub Markdown CSS
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Markdown Preview</title>
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown-light.min.css">
                    <style>
                        body { box-sizing: border-box; min-width: 200px; max-width: 980px; margin: 0 auto; padding: 45px; }
                        @media (max-width: 767px) { body { padding: 15px; } }
                        .markdown-body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif; }
                    </style>
                </head>
                <body>
                    <a href="javascript:history.back()" style="display:inline-block; margin-bottom:20px; text-decoration:none; color:#0969da;">&larr; Back</a>
                    <article class="markdown-body" id="content">Loading...</article>
                    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
                    <script>
                        // Fetch the raw markdown content with a cache-busting timestamp
                        fetch(window.location.pathname + '?raw=true&t=' + new Date().getTime())
                            .then(response => response.text())
                            .then(text => {
                                document.getElementById('content').innerHTML = marked.parse(text);
                            })
                            .catch(err => {
                                document.getElementById('content').innerHTML = '<p style="color:red">Error loading markdown file.</p>';
                                console.error(err);
                            });
                    </script>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
            else:
                # Serve the raw file (or directory listing) normally
                super().do_GET()

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving directory '{directory}' at http://localhost:{port}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple Documentation Server")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to serve on (default: 8000)"
    )
    parser.add_argument(
        "--dir", type=str, default="docs", help="Directory to serve (default: docs)"
    )

    args = parser.parse_args()

    # Verify directory exists
    if not os.path.isdir(args.dir):
        print(f"Error: Directory '{args.dir}' not found.")
        exit(1)

    run_server(args.port, args.dir)
