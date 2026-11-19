import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FakeOllama(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.respond({"models": [{"name": "salamandra-emprecoach:latest"},
                                 {"name": "qwen3-embedding:0.6b"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.embedding_requests += 1
        self.respond({"embeddings": [[1.0, 0.0] for _ in body["input"]]})

    def respond(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@unittest.skipUnless(sys.platform == "win32", "El lanzador es para Windows")
class LauncherTests(unittest.TestCase):
    def test_existing_models_start_web_and_index_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("app.py", "rag.py", "ingest.py", "requirements.txt", "Iniciar Virtual EmpreCoach.cmd"):
                shutil.copy(ROOT / name, root / name)
            for name in ("corpus", "static"):
                shutil.copytree(ROOT / name, root / name)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                web_port = sock.getsockname()[1]
            with http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama) as ollama:
                ollama.embedding_requests = 0
                thread = threading.Thread(target=ollama.serve_forever, daemon=True)
                thread.start()
                try:
                    script = (ROOT / "iniciar.ps1").read_text(encoding="utf-8")
                    script = script.replace("11434", str(ollama.server_port)).replace("5000", str(web_port))
                    script = script.replace("$ollama = Find-Ollama", "$ollama = $python[0]")
                    venv = str(Path(sys.executable)).replace("'", "''")
                    script = script.replace("$venvPython = Join-Path $PSScriptRoot '.venv\\Scripts\\python.exe'",
                                            f"$venvPython = '{venv}'")
                    script = script.replace(f"Start-Process 'http://127.0.0.1:{web_port}/'",
                                            "Write-Host 'Navegador simulado'")
                    script = script.replace("$server.WaitForExit()", "$server.Kill(); $server.WaitForExit()")
                    script = script.replace("if ($server.ExitCode -ne 0)", "if ($false)")
                    (root / "iniciar.ps1").write_text(script, encoding="utf-8")
                    app = root / "app.py"
                    app.write_text(app.read_text(encoding="utf-8").replace("port=5000", f"port={web_port}"),
                                   encoding="utf-8")
                    result = subprocess.run(
                        [os.environ["COMSPEC"], "/c", "Iniciar Virtual EmpreCoach.cmd"],
                        cwd=root, capture_output=True, text=True, timeout=120, env=os.environ.copy()
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("Web iniciada", result.stdout)
                    index = json.loads((root / "data" / "index.json").read_text(encoding="utf-8"))
                    self.assertEqual(index["model"], "qwen3-embedding:0.6b")
                    self.assertTrue(index["chunks"])
                    embedding_requests_after_ingest = ollama.embedding_requests

                    result = subprocess.run(
                        [os.environ["COMSPEC"], "/c", "Iniciar Virtual EmpreCoach.cmd"],
                        cwd=root, capture_output=True, text=True, timeout=120, env=os.environ.copy()
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("Reutilizando", result.stdout)
                    self.assertEqual(ollama.embedding_requests, embedding_requests_after_ingest)
                finally:
                    ollama.shutdown()
                    thread.join()


if __name__ == "__main__":
    unittest.main()
