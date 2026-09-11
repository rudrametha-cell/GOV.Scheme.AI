"""
app.py
-------
SchemeMatch AI - Flask Backend (single-command entry point)

Running this ONE file starts the ENTIRE application:
    1. Flask web server (frontend + backend)
    2. The scheme dataset (schemes.csv, loaded by matcher.py)
    3. The Python matching engine (matcher.py)
    4. The Java validation service (java/SchemeService.java) -
       auto-compiled and auto-started as a background process if a JDK
       is available. If Java cannot be started for any reason, the app
       logs a warning and keeps running in "fallback mode" using an
       equivalent Python validation routine - Java is never required
       for the website to work.

Run with:
    python app.py

Then open:
    http://127.0.0.1:5000
"""

from flask import Flask, render_template, request
import atexit
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
import urllib.error

import matcher

app = Flask(__name__,template_folder=".")

# ----------------------------------------------------------------------
# JAVA SERVICE LIFECYCLE MANAGEMENT
# ----------------------------------------------------------------------
# The Java component is OPTIONAL and self-managed. If it cannot be
# compiled/started, the app falls back to doing validation/normalization
# directly in Python so the MVP never breaks because of the Java service.

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JAVA_DIR = os.path.join(BASE_DIR, "java")
JAVA_SOURCE_FILE = os.path.join(JAVA_DIR, "SchemeService.java")
JAVA_CLASS_FILE = os.path.join(JAVA_DIR, "SchemeService.class")
JAVA_HOST = "127.0.0.1"
JAVA_PORT = 8080
JAVA_SERVICE_URL = f"http://{JAVA_HOST}:{JAVA_PORT}/validate"
JAVA_STATUS_URL = f"http://{JAVA_HOST}:{JAVA_PORT}/status"
JAVA_TIMEOUT_SECONDS = 1.5

_java_process = None
_java_status = "unavailable"   # "online" | "unavailable"
_java_status_note = "Not started yet."


def _is_port_open(host, port, timeout=0.4):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_java_service():
    """
    Best-effort, non-blocking startup of the Java validation service.
    Order of operations:
      1. If something is already answering on port 8080, reuse it.
      2. Otherwise, look for javac/java on PATH.
      3. Compile SchemeService.java if SchemeService.class is missing
         or older than the source file.
      4. Launch it as a background subprocess.
      5. Poll briefly to confirm it actually came up.
    Any failure at any step is caught and logged - the Flask app keeps
    running in fallback mode regardless.
    """
    global _java_process, _java_status, _java_status_note

    if _is_port_open(JAVA_HOST, JAVA_PORT):
        _java_status = "online"
        _java_status_note = "Java service already running - reused existing instance."
        print("[Java] Detected an existing service on port 8080 - reusing it.")
        return

    javac_path = shutil.which("javac")
    java_path = shutil.which("java")

    if not java_path:
        _java_status = "unavailable"
        _java_status_note = "Java runtime not found on PATH. Running in fallback mode."
        print(f"[Java] {_java_status_note}")
        return

    needs_compile = (
        not os.path.exists(JAVA_CLASS_FILE)
        or os.path.getmtime(JAVA_SOURCE_FILE) > os.path.getmtime(JAVA_CLASS_FILE)
    )

    if needs_compile:
        if not javac_path:
            _java_status = "unavailable"
            _java_status_note = "JDK (javac) not found - cannot compile Java service. Running in fallback mode."
            print(f"[Java] {_java_status_note}")
            return
        print("[Java] Compiling SchemeService.java ...")
        try:
            compile_result = subprocess.run(
                [javac_path, "SchemeService.java"],
                cwd=JAVA_DIR,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if compile_result.returncode != 0:
                _java_status = "unavailable"
                _java_status_note = "Java compilation failed. Running in fallback mode."
                print(f"[Java] Compilation error:\n{compile_result.stderr}")
                return
            print("[Java] Compilation successful.")
        except (OSError, subprocess.SubprocessError) as exc:
            _java_status = "unavailable"
            _java_status_note = "Could not run javac. Running in fallback mode."
            print(f"[Java] {_java_status_note} ({exc})")
            return

    print("[Java] Starting SchemeService ...")
    try:
        _java_process = subprocess.Popen(
            [java_path, "SchemeService"],
            cwd=JAVA_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _java_status = "unavailable"
        _java_status_note = "Could not launch the Java process. Running in fallback mode."
        print(f"[Java] {_java_status_note} ({exc})")
        return

    # Give the JVM a moment to boot, then confirm it is actually listening.
    for _ in range(10):
        time.sleep(0.3)
        if _is_port_open(JAVA_HOST, JAVA_PORT):
            _java_status = "online"
            _java_status_note = "Java validation service is online."
            print(f"[Java] Service is up at http://{JAVA_HOST}:{JAVA_PORT}")
            return

    _java_status = "unavailable"
    _java_status_note = "Java process started but did not respond in time. Running in fallback mode."
    print(f"[Java] {_java_status_note}")


def stop_java_service():
    """Terminate the background Java process (if we started one) on shutdown."""
    if _java_process is not None and _java_process.poll() is None:
        print("[Java] Shutting down Java service ...")
        _java_process.terminate()
        try:
            _java_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _java_process.kill()


atexit.register(stop_java_service)

VALID_GENDERS = {"Female", "Male", "Other"}
VALID_CATEGORIES = {"SC", "ST", "OBC", "General"}
VALID_BUSINESS_TYPES = {
    "Tailoring", "Food Business", "Retail", "Manufacturing", "Agriculture",
    "Handicraft", "Services", "Technology", "Other"
}
VALID_STAGES = {"New Business", "Existing Business", "Expansion"}
VALID_STATES = {
    "Gujarat", "Maharashtra", "Rajasthan", "Delhi", "Uttar Pradesh",
    "Madhya Pradesh", "Karnataka", "Tamil Nadu", "West Bengal", "Other"
}


def python_fallback_validate(profile):
    """Basic validation/normalization used if the Java service is unavailable."""
    errors = []

    if profile["gender"] not in VALID_GENDERS:
        errors.append("Invalid gender value.")
    if profile["category"] not in VALID_CATEGORIES:
        errors.append("Invalid category value.")
    if profile["business_type"] not in VALID_BUSINESS_TYPES:
        errors.append("Invalid business type value.")
    if profile["business_stage"] not in VALID_STAGES:
        errors.append("Invalid business stage value.")
    if profile["state"] not in VALID_STATES:
        errors.append("Invalid state value.")
    if profile["age"] < 18 or profile["age"] > 100:
        errors.append("Age must be between 18 and 100.")
    if profile["income"] < 0:
        errors.append("Income cannot be negative.")
    if profile["funding_required"] < 0:
        errors.append("Funding required cannot be negative.")

    return {"valid": len(errors) == 0, "errors": errors, "source": "python-fallback"}


def call_java_validation_service(profile):
    """
    Try to call the Java validation microservice (java/SchemeService.java).
    If it is not running, silently fall back to Python validation so the
    demo never breaks. This keeps Java "meaningfully included" without
    creating a hard dependency.
    """
    try:
        payload = json.dumps(profile).encode("utf-8")
        req = urllib.request.Request(
            JAVA_SERVICE_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=JAVA_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
            result["source"] = "java-service"
            return result
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # Java service not running or unreachable -> fall back to Python.
        return python_fallback_validate(profile)


def build_profile_from_form(form):
    """Extract and lightly clean the submitted form data into a profile dict."""
    def to_int(value, default=0):
        try:
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    return {
        "age": to_int(form.get("age")),
        "gender": (form.get("gender") or "").strip(),
        "category": (form.get("category") or "").strip(),
        "state": (form.get("state") or "").strip(),
        "income": to_int(form.get("income")),
        "business_type": (form.get("business_type") or "").strip(),
        "business_stage": (form.get("business_stage") or "").strip(),
        "funding_required": to_int(form.get("funding_required")),
    }


def get_system_status():
    """
    Returns a small status dict used to power the "SYSTEM STATUS" card
    on the About section. Reflects the real, current state of each part
    of the architecture - not hard-coded values.
    """
    try:
        dataset_loaded = len(matcher.load_schemes()) > 0
    except Exception:
        dataset_loaded = False

    return {
        "python_backend": True,          # If this code is running, Flask is online.
        "matching_engine": dataset_loaded,
        "java_service": _java_status,    # "online" or "unavailable"
        "java_note": _java_status_note,
        "dataset_loaded": dataset_loaded,
    }


@app.route("/")
def home():
    return render_template("index.html", system_status=get_system_status())


@app.route("/match", methods=["POST"])
def match():
    profile = build_profile_from_form(request.form)

    # Basic required-field check first (friendly message, no blank screens).
    required = ["gender", "category", "state", "business_type", "business_stage"]
    missing = [field for field in required if not profile.get(field)]

    if missing or profile["age"] <= 0:
        return render_template(
            "index.html",
            error_message="Please complete the highlighted fields so we can generate better recommendations.",
            profile=profile,
            system_status=get_system_status(),
        )

    validation = call_java_validation_service(profile)

    if not validation.get("valid", True):
        return render_template(
            "index.html",
            error_message="Please complete the highlighted fields so we can generate better recommendations.",
            profile=profile,
            system_status=get_system_status(),
        )

    recommendations = matcher.get_recommendations(profile)

    return render_template(
        "results.html",
        profile=profile,
        recommendations=recommendations,
        validation_source=validation.get("source", "python-fallback"),
        has_matches=len(recommendations) > 0,
        system_status=get_system_status(),
    )


@app.route("/api/status")
def api_status():
    """JSON endpoint so the status card can refresh itself without a page reload."""
    return json.dumps(get_system_status())


@app.errorhandler(500)
def handle_server_error(_error):
    """Never show a raw Python traceback to the user - show a friendly card instead."""
    return render_template(
        "error.html",
        message="Something went wrong while processing your request. Please try again.",
    ), 500


if __name__ == "__main__":
    print("=" * 56)
    print(" SchemeMatch AI - starting complete application ...")
    print("=" * 56)

    start_java_service()

    print("-" * 56)
    print(" SchemeMatch AI")
    print(" Running at http://127.0.0.1:5000")
    print(f" Java validation service: {_java_status.upper()} ({_java_status_note})")
    print("-" * 56)

    # use_reloader=False is intentional: it prevents Flask's debug reloader
    # from spawning a second process, which would try to start a second
    # Java service and duplicate everything above.
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)