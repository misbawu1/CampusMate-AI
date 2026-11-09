"""Serve the CampusMate browser app on this computer and open it."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import webbrowser


HOST = "127.0.0.1"
PORT = 8000
PROJECT_FOLDER = Path(__file__).resolve().parent


class CampusMateHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ask":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "The question could not be read."})
            return

        if content_length < 1 or content_length > 10000:
            self._send_json(400, {"error": "Please send a shorter question."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "The question could not be read."})
            return

        question = payload.get("question", "") if isinstance(payload, dict) else ""
        if not isinstance(question, str) or not question.strip():
            self._send_json(400, {"error": "Type a question first."})
            return
        if len(question) > 1000:
            self._send_json(400, {"error": "Please keep your question under 1,000 characters."})
            return

        if not os.environ.get("GEMINI_API_KEY"):
            self._send_json(
                503,
                {"error": "Gemini key not available. Close and reopen VS Code, then start CampusMate again."},
            )
            return

        try:
            from google import genai

            with (PROJECT_FOLDER / "knowledge.json").open(encoding="utf-8") as file:
                resources = json.load(file)

            prompt = (
                "You are CampusMate, a friendly guide to campus resources. "
                "Answer using only the campus resource information below. "
                "Keep answers to three short sentences. "
                "Do not invent services, locations, hours, or contact details. "
                "If the information does not answer the question, say what is missing "
                "and suggest the closest listed resource. For health questions, do not "
                "diagnose or give treatment instructions; point the student to the "
                "Student Health Center.\n\n"
                f"Campus resource information:\n{json.dumps(resources, ensure_ascii=False)}\n\n"
                f"Student question: {question.strip()}"
            )
            self._start_event_stream()
            self._send_event({"type": "status", "message": "Gemini is preparing an answer…"})

            client = genai.Client()
            stream = client.interactions.create(
                model="gemini-3.8-flash",
                input=prompt,
                store=False,
                stream=True,
            )
            got_text = False
            for event in stream:
                delta = getattr(event, "delta", None)
                if (
                    event.event_type == "step.delta"
                    and delta
                    and getattr(delta, "type", None) == "text"
                    and getattr(delta, "text", None)
                ):
                    self._send_event({"type": "text", "text": delta.text})
                    got_text = True
                elif event.event_type == "error":
                    self._send_event({"type": "error", "message": "Gemini couldn't answer. Please try again."})
                    return

            if got_text:
                self._send_event({"type": "done"})
            else:
                self._send_event({"type": "error", "message": "Gemini returned no answer. Please try again."})
        except Exception as error:
            print(f"Gemini request failed: {type(error).__name__}")
            self._send_event({"type": "error", "message": "CampusMate couldn't get an AI answer. Check the VS Code terminal and try again."})

    def _start_event_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _send_event(self, payload):
        message = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.wfile.write(b"data: " + message + b"\n\n")
        self.wfile.flush()

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    handler = partial(CampusMateHandler, directory=str(PROJECT_FOLDER))
    try:
        server = ThreadingHTTPServer((HOST, PORT), handler)
    except OSError:
        server = ThreadingHTTPServer((HOST, 0), handler)
    address = f"http://{HOST}:{server.server_port}/"
    print(f"CampusMate is open at {address}")
    print("Keep this window open while you use CampusMate. Press Ctrl+C to stop it.")
    threading.Timer(0.7, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCampusMate server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
