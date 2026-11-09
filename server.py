"""Serve the CampusMate browser app on this computer and open it."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import webbrowser

from tools import find_resource, load_knowledge


HOST = "127.0.0.1"
PORT = 8000
PROJECT_FOLDER = Path(__file__).resolve().parent
MODEL = "gemini-3.8-flash"
SEARCH_TOOL = {
    "type": "function",
    "name": "search_campus_resources",
    "description": (
        "Search CampusMate's official campus resource list for information that can answer "
        "a campus-related question. Use a short topic or keyword, such as tutoring, career, "
        "library, or health. Use this for every question about campus services or places."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "A short topic or keyword to search for in the campus resource list.",
            }
        },
        "required": ["topic"],
    },
}
SYSTEM_INSTRUCTION = (
    "You are CampusMate, a friendly campus guide. For every question about campus services, "
    "places, contacts, or hours, call search_campus_resources before answering. Use only "
    "the information returned by that search for campus-specific facts. If no resource "
    "matches, say CampusMate could not find that information and suggest a broader search. "
    "Do not invent services, locations, hours, or contacts. For general questions outside "
    "campus information, answer normally. For health questions, search for the Student "
    "Health Center and do not diagnose or give treatment instructions. Keep answers to "
    "three short sentences."
)


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

            self._start_event_stream()
            self._send_event({"type": "status", "message": "CampusMate is searching campus resources…"})

            client = genai.Client()
            history = [
                {
                    "type": "user_input",
                    "content": [{"type": "text", "text": question.strip()}],
                }
            ]
            interaction = client.interactions.create(
                model=MODEL,
                input=history,
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[SEARCH_TOOL],
                store=False,
            )
            history.extend(step.model_dump(exclude_none=True) for step in interaction.steps or [])

            function_calls = [
                step for step in interaction.steps or []
                if getattr(step, "type", None) == "function_call"
            ]

            if not function_calls:
                # General questions can be answered without consulting campus resources.
                if interaction.output_text:
                    self._send_event({"type": "text", "text": interaction.output_text})
                    self._send_event({"type": "done"})
                else:
                    self._send_event({"type": "error", "message": "Gemini returned no answer. Please try again."})
                return

            resources = load_knowledge()
            for call in function_calls:
                if call.name != "search_campus_resources":
                    continue
                topic = call.arguments.get("topic", "") if isinstance(call.arguments, dict) else ""
                matches = find_resource(resources, topic.strip()) if isinstance(topic, str) and topic.strip() else []
                result = {
                    "search_topic": topic,
                    "resources": [
                        {
                            "name": item.get("name", ""),
                            "description": item.get("description", ""),
                            "contact": item.get("contact", ""),
                        }
                        for item in matches
                    ],
                    "message": "No matching campus resources were found." if not matches else "Matching campus resources are listed above.",
                }
                history.append({
                    "type": "function_result",
                    "name": call.name,
                    "call_id": call.id,
                    "result": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                })

            self._send_event({"type": "status", "message": "Writing an answer from the search results…"})
            stream = client.interactions.create(
                model=MODEL,
                input=history,
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[SEARCH_TOOL],
                store=False,
                stream=True,
            )
            got_text = False
            for event in stream:
                delta = getattr(event, "delta", None)
                if event.event_type == "step.delta" and delta and getattr(delta, "type", None) == "text" and getattr(delta, "text", None):
                    self._send_event({"type": "text", "text": delta.text})
                    got_text = True
                elif event.event_type == "error":
                    self._send_event({"type": "error", "message": "Gemini couldn't finish the answer. Please try again."})
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
