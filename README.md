# CampusMate

A beginner-friendly campus guide with a browser resource search, an optional Gemini AI question box, and a small Python command-line version.

## Open the browser app

1. Open this folder in VS Code.
2. Choose **Terminal → New Terminal**.
3. Install the browser AI dependency by running `python -m pip install -r requirements.txt`.
4. Run `python server.py`.
5. CampusMate opens in your browser at `http://127.0.0.1:8000`.
6. Keep the terminal open while you use the site. Press **Ctrl+C** there when you are finished.

If Windows does not recognize `python` in an already-open terminal, open a new terminal or restart VS Code. As a fallback, run `& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m pip install -r requirements.txt` and then `& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" server.py` in PowerShell.

## Ask CampusMate with Gemini

1. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey).
2. Add it to Windows as a user environment variable named `GEMINI_API_KEY`. Do not put the key in `app.js` or share it.
3. Close and reopen VS Code so the server can read the new variable.
4. Install the dependency and start `server.py` using the steps above.

The AI question box uses the resources in `knowledge.json` as its reference and asks Gemini not to invent campus details. Answers stream onto the page as Gemini generates them; this reduces the wait before you see the first words, though it does not guarantee a shorter total response time. The regular keyword search works separately. Gemini API usage may be subject to account limits and billing.

The browser search and command-line version use the same `knowledge.json` campus information. The browser AI feature uses Google's `google-genai` Python package; the command-line search still uses only the Python standard library.

## How it is organized

- `index.html` provides the page structure.
- `styles.css` controls the colors, layout, and responsive appearance.
- `app.js` loads campus data, filters results, and sends AI questions to the Python server.
- `server.py` serves the browser files and sends AI questions to Gemini.
- `main.py` remains a simple command-line version for practicing Python.
- `tools.py` contains reusable functions for loading and searching information.
- `knowledge.json` stores campus resources separately from the code.
- `requirements.txt` records the Gemini SDK needed for the browser AI feature.
