"""
safe_gemini.py — Safe wrapper around the google-genai SDK.

Protections against API bans:
  1. RPM rate limiter    — stays under free-tier limit (default 10 RPM)
  2. Exponential backoff — retries 429 / 503 with increasing delays
  3. Response cache      — identical prompts reuse cached answers (saves quota)
  4. Token budget guard  — logs a warning if a prompt is suspiciously large
  5. Graceful fallback   — if all retries fail, raises GeminiFallbackError
                           so the caller can return a pre-baked response

Usage (in gemini_client.py):
    from services.safe_gemini import safe_generate, GeminiFallbackError

    try:
        text = safe_generate(prompt, json_mode=True, max_tokens=800)
    except GeminiFallbackError:
        return FALLBACK_RESPONSE
"""

import os
import time
import hashlib
import threading
import json
from collections import deque
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Config from .env ──────────────────────────────────────────────────────────

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME      = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
RPM_LIMIT       = int(os.getenv("GEMINI_RPM_LIMIT", "10"))
MAX_RETRIES     = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
OLLAMA_HOST     = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip("/")
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_MODEL    = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

# Warning threshold: log if prompt > this many chars (~50k tokens-ish)
TOKEN_BUDGET_CHARS = 40_000

# ── Sentinel exception ────────────────────────────────────────────────────────

class GeminiFallbackError(Exception):
    """Raised when all retries are exhausted — caller should use fallback."""
    pass

# ── Rate limiter (sliding-window, thread-safe) ────────────────────────────────

class _SlidingWindowRateLimiter:
    """
    Tracks call timestamps in the last 60 s.
    If we're at the limit, blocks until a slot opens.
    """
    def __init__(self, rpm: int):
        self._rpm   = rpm
        self._calls: deque = deque()
        self._lock  = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                # Drop timestamps older than 60 s
                while self._calls and now - self._calls[0] >= 60:
                    self._calls.popleft()

                if len(self._calls) < self._rpm:
                    self._calls.append(now)
                    return  # slot available

                # Need to wait — calculate how long
                oldest   = self._calls[0]
                wait_sec = 60 - (now - oldest) + 0.05   # small buffer

            print(f"[safe_gemini] RPM limit ({self._rpm}/min) reached — waiting {wait_sec:.1f}s")
            time.sleep(wait_sec)

_gemini_blocked_until = 0.0
_gemini_block_lock = threading.Lock()

_rate_limiter = _SlidingWindowRateLimiter(RPM_LIMIT)

# ── Response cache (in-process, keyed by prompt hash) ────────────────────────

_cache: dict[str, str] = {}
_cache_lock = threading.Lock()

def _cache_key(prompt: str, json_mode: bool, max_tokens: int) -> str:
    raw = f"{prompt}|{json_mode}|{max_tokens}|{MODEL_NAME}"
    return hashlib.sha256(raw.encode()).hexdigest()

def _get_cached(key: str) -> Optional[str]:
    with _cache_lock:
        return _cache.get(key)

def _set_cached(key: str, value: str):
    with _cache_lock:
        _cache[key] = value

def _get_ollama_model() -> Optional[str]:
    """Retrieve first available local model name from Ollama API if active."""
    import urllib.request
    import json
    try:
        req = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=1.0)
        data = json.loads(req.read().decode())
        models = data.get("models", [])
        if models:
            return models[0]["name"]
    except Exception:
        pass
    return None

def _generate_via_ollama(prompt: str, json_mode: bool, model_name: str) -> Optional[str]:
    """Post prompt to local Ollama server generation endpoint."""
    import urllib.request
    import json
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        if json_mode:
            payload["format"] = "json"
            
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30.0) as response:
            res_data = json.loads(response.read().decode())
            return res_data.get("response", "")
    except Exception as e:
        print(f"[safe_gemini] Ollama invocation failed: {e}")
        return None

def _generate_via_nvidia_nim(prompt: str, json_mode: bool) -> Optional[str]:
    """Query NVIDIA NIM API as a cloud fallback."""
    import urllib.request
    import json
    if not NVIDIA_API_KEY:
        return None
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        system_content = "You are a helpful analyst. Respond in valid JSON." if json_mode else "You are a helpful analyst."
        payload = {
            "model": NVIDIA_MODEL,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1000
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {NVIDIA_API_KEY}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30.0) as response:
            res_data = json.loads(response.read().decode())
            choices = res_data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"[safe_gemini] NVIDIA NIM invocation failed: {e}")
        return None

# ── Main safe wrapper ─────────────────────────────────────────────────────────

def safe_generate(
    prompt: str,
    json_mode: bool = True,
    max_tokens: int = 1000,
    use_cache: bool = True,
) -> str:
    """
    Calls Gemini safely. Falls back to local Ollama if running, then to NVIDIA NIM, then to pre-baked static data.
    """
    # Cache check
    key = _cache_key(prompt, json_mode, max_tokens)
    if use_cache:
        cached = _get_cached(key)
        if cached is not None:
            print("[safe_gemini] Cache hit - skipping API call")
            return cached

    with _gemini_block_lock:
        is_gemini_blocked = time.time() < _gemini_blocked_until

    if not GEMINI_API_KEY or is_gemini_blocked:
        if is_gemini_blocked:
            print("[safe_gemini] Gemini API is currently blocked (Circuit Breaker active due to previous 429 quota errors). Direct failover routing triggered.")
        # 1. Try NVIDIA NIM fallback
        if NVIDIA_API_KEY:
            print(f"[safe_gemini] Pivoting to NVIDIA NIM Cloud API: '{NVIDIA_MODEL}'...")
            response_text = _generate_via_nvidia_nim(prompt, json_mode)
            if response_text:
                if use_cache:
                    _set_cached(key, response_text)
                return response_text

        # 2. Try Ollama fallback
        ollama_model = _get_ollama_model()
        if ollama_model:
            print(f"[safe_gemini] Pivoting to local Ollama model: '{ollama_model}'...")
            response_text = _generate_via_ollama(prompt, json_mode, ollama_model)
            if response_text:
                if use_cache:
                    _set_cached(key, response_text)
                return response_text

        raise GeminiFallbackError("No active Gemini API key or fallbacks (NVIDIA NIM/Ollama) available.")

    # Token budget guard
    if len(prompt) > TOKEN_BUDGET_CHARS:
      print(f"[safe_gemini] [WARNING] Large prompt: {len(prompt):,} chars - consider trimming")

    # Lazy-init client
    from google import genai
    from google.genai import types as genai_types
    client = genai.Client(api_key=GEMINI_API_KEY)

    config_kwargs = {
        "max_output_tokens": max_tokens,
        "temperature": 0.3,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    config = genai_types.GenerateContentConfig(**config_kwargs)

    # Retry loop with exponential backoff
    base_delay = 2.0   # seconds
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _rate_limiter.acquire()   # block if at RPM limit

            print(f"[safe_gemini] Calling {MODEL_NAME} (attempt {attempt}/{MAX_RETRIES})")
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            if use_cache:
                _set_cached(key, text)
            return text

        except Exception as e:
            err_str = str(e).lower()
            is_retriable = any(code in err_str for code in [
                "429", "rate", "quota", "503", "overloaded",
                "resource exhausted", "unavailable"
            ])
            
            # Check if this is a permanent quota limit (limit: 0 or perday)
            is_permanent_quota_exhaust = "limit: 0" in err_str or "perday" in err_str

            if is_permanent_quota_exhaust:
                print(f"[safe_gemini] Quota permanently exhausted (limit: 0 / perday). Skipping remaining retries and pivoting immediately!")
                is_retriable = False

            if is_retriable and attempt < MAX_RETRIES:
                # Default exponential backoff
                delay = base_delay * (2 ** (attempt - 1))   # 2s, 4s, 8s ...
                
                # Parse retryDelay from Gemini error if available
                import re
                match = re.search(r"(?:retry in|retrydelay:?\s*'?)\s*(\d+(\.\d+)?)s?", err_str)
                if match:
                    try:
                        delay = float(match.group(1))
                        print(f"[safe_gemini] Parsed dynamic retry delay from API: {delay:.1f}s")
                    except ValueError:
                        pass
                
                print(f"[safe_gemini] Retriable error (attempt {attempt}): {e} - retrying in {delay:.1f}s")
                time.sleep(delay)
                continue

            # Non-retriable or final attempt - Try NVIDIA NIM and Ollama fallbacks first before raising error
            print(f"[safe_gemini] [ERROR] Failed after {attempt} attempt(s): {e}")
            
            # Activate Circuit Breaker on 429 / Quota exhausted errors to avoid retrying on future calls
            err_str = str(e).lower()
            if any(code in err_str for code in ["429", "quota", "resource exhausted"]):
                with _gemini_block_lock:
                    global _gemini_blocked_until
                    _gemini_blocked_until = time.time() + 300.0   # Block for 5 minutes
                    print("[safe_gemini] Circuit Breaker activated! Gemini API calls will be blocked and automatically routed to fallbacks for the next 5 minutes.")

            if NVIDIA_API_KEY:
                print(f"[safe_gemini] Gemini API error. Pivoting to NVIDIA NIM Cloud API: '{NVIDIA_MODEL}'...")
                response_text = _generate_via_nvidia_nim(prompt, json_mode)
                if response_text:
                    if use_cache:
                        _set_cached(key, response_text)
                    return response_text
            
            ollama_model = _get_ollama_model()
            if ollama_model:
                print(f"[safe_gemini] Gemini API error. Pivoting to local Ollama model: '{ollama_model}'...")
                response_text = _generate_via_ollama(prompt, json_mode, ollama_model)
                if response_text:
                    if use_cache:
                        _set_cached(key, response_text)
                    return response_text
                    
            raise GeminiFallbackError(str(e)) from e

    raise GeminiFallbackError("Exhausted all retries")


def get_status() -> dict:
    """Return current rate-limiter and cache stats (for health endpoint)."""
    with _rate_limiter._lock:
        now = time.monotonic()
        recent = [t for t in _rate_limiter._calls if now - t < 60]
        calls_last_min = len(recent)

    with _cache_lock:
        cache_size = len(_cache)

    return {
        "model": MODEL_NAME,
        "rpm_limit": RPM_LIMIT,
        "calls_last_minute": calls_last_min,
        "cache_entries": cache_size,
        "api_key_configured": bool(GEMINI_API_KEY),
    }
