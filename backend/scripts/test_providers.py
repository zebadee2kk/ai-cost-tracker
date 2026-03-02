#!/usr/bin/env python3
"""
Provider connectivity diagnostic script.

Tests each configured AI provider service and reports status.
Run from the backend/ directory:

    python scripts/test_providers.py

Or with specific providers:

    python scripts/test_providers.py --providers openai anthropic

Environment variables checked:
    ANTHROPIC_API_KEY   (must be sk-ant-admin-...)
    OPENAI_API_KEY      (sk-...)
    GROQ_API_KEY        (gsk_...)
    PERPLEXITY_API_KEY  (pplx-...)
    MISTRAL_API_KEY     (any non-empty string)
"""

import argparse
import os
import sys
import textwrap
import time

# Ensure the backend/ directory is on the path so service imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── colour helpers ───────────────────────────────────────────────────────────
_USE_COLOUR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def red(t):    return _c("31", t)
def bold(t):   return _c("1", t)
def cyan(t):   return _c("36", t)


# ─── provider test helpers ────────────────────────────────────────────────────

def _test_anthropic(api_key: str) -> tuple[bool, str]:
    """Test Anthropic Admin API key."""
    from services.base_service import AuthenticationError, ServiceError

    if not api_key.startswith("sk-ant-admin"):
        return False, (
            f"Wrong key type: starts with '{api_key[:14]}...'\n"
            "   Anthropic requires an Admin API key (sk-ant-admin-).\n"
            "   Generate one at: Console → Settings → Organization → Admin API Keys"
        )

    try:
        from services.anthropic_service import AnthropicService
        svc = AnthropicService(api_key)
        ok = svc.validate_credentials()
        if ok:
            return True, "Admin API key valid"
        return False, "validate_credentials() returned False (check key permissions)"
    except AuthenticationError as exc:
        return False, f"Authentication error: {exc}"
    except ServiceError as exc:
        return False, f"Service error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"


def _test_openai(api_key: str) -> tuple[bool, str]:
    """Test OpenAI API key."""
    from services.base_service import AuthenticationError, ServiceError

    try:
        from services.openai_service import OpenAIService
        svc = OpenAIService(api_key)
        ok = svc.validate_credentials()
        if ok:
            return True, "API key valid"
        return False, "validate_credentials() returned False"
    except AuthenticationError as exc:
        return False, f"Authentication error: {exc}"
    except ServiceError as exc:
        return False, f"Service error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"


def _test_groq(api_key: str) -> tuple[bool, str]:
    """Test Groq API key."""
    from services.base_service import AuthenticationError, ServiceError

    if not api_key.startswith("gsk-"):
        return False, (
            f"Wrong key format: starts with '{api_key[:7]}...'\n"
            "   Groq keys start with 'gsk-'. Generate at: https://console.groq.com/keys"
        )

    try:
        from services.groq_service import GroqService
        svc = GroqService(api_key)
        ok = svc.validate_credentials()
        if ok:
            return True, "API key valid (model list endpoint reachable)"
        return False, "validate_credentials() returned False"
    except AuthenticationError as exc:
        return False, f"Authentication error: {exc}"
    except ServiceError as exc:
        return False, f"Service error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"


def _test_perplexity(api_key: str) -> tuple[bool, str]:
    """Test Perplexity API key."""
    from services.base_service import AuthenticationError, ServiceError

    if not api_key.startswith("pplx-"):
        return False, (
            f"Wrong key format: starts with '{api_key[:7]}...'\n"
            "   Perplexity keys start with 'pplx-'. Generate at: https://www.perplexity.ai/settings/api"
        )

    try:
        from services.perplexity_service import PerplexityService
        svc = PerplexityService(api_key)
        ok = svc.validate_credentials()
        if ok:
            return True, "API key valid (chat completions endpoint reachable)"
        return False, "validate_credentials() returned False"
    except AuthenticationError as exc:
        return False, f"Authentication error: {exc}"
    except ServiceError as exc:
        return False, f"Service error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"


def _test_mistral(api_key: str) -> tuple[bool, str]:
    """Test Mistral API key (if service is implemented)."""
    try:
        from services.mistral_service import MistralService  # noqa: F401
    except ImportError:
        return False, "MistralService not yet implemented (backend/services/mistral_service.py missing)"

    from services.base_service import AuthenticationError, ServiceError
    try:
        svc = MistralService(api_key)
        ok = svc.validate_credentials()
        if ok:
            return True, "API key valid"
        return False, "validate_credentials() returned False"
    except AuthenticationError as exc:
        return False, f"Authentication error: {exc}"
    except ServiceError as exc:
        return False, f"Service error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"


# ─── provider registry ────────────────────────────────────────────────────────

PROVIDERS = {
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "test_fn": _test_anthropic,
        "tracking": "pull (Admin API — usage endpoint)",
        "note": "Requires sk-ant-admin-... key (NOT a standard API key)",
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "test_fn": _test_openai,
        "tracking": "pull (billing/usage endpoint)",
        "note": None,
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        "test_fn": _test_groq,
        "tracking": "push (call_with_tracking — no usage API)",
        "note": "Key must start with gsk-",
    },
    "perplexity": {
        "env_var": "PERPLEXITY_API_KEY",
        "test_fn": _test_perplexity,
        "tracking": "push (call_with_tracking — no usage API)",
        "note": "Key must start with pplx-",
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
        "test_fn": _test_mistral,
        "tracking": "TBD — service not yet implemented",
        "note": None,
    },
}


# ─── main ─────────────────────────────────────────────────────────────────────

def run_tests(provider_names: list[str], verbose: bool = False) -> dict:
    results = {}
    for name in provider_names:
        cfg = PROVIDERS[name]
        api_key = os.environ.get(cfg["env_var"], "").strip()

        if not api_key:
            results[name] = ("skip", f"${cfg['env_var']} not set")
            continue

        print(f"  Testing {bold(name)} ... ", end="", flush=True)
        t0 = time.time()
        ok, msg = cfg["test_fn"](api_key)
        elapsed = time.time() - t0

        status = "ok" if ok else "fail"
        results[name] = (status, msg, elapsed)

        if ok:
            print(green(f"✓ ({elapsed:.2f}s)"))
        else:
            print(red("✗"))
        if verbose or not ok:
            for line in msg.splitlines():
                print(f"      {line}")

    return results


def print_summary(results: dict) -> int:
    """Print results table and return exit code (0=all ok, 1=failures)."""
    print()
    print(bold("─" * 56))
    print(bold(f"  {'Provider':<14} {'Status':<10} {'Detail'}"))
    print(bold("─" * 56))

    ok_count = fail_count = skip_count = 0
    for name, result in results.items():
        status = result[0]
        cfg = PROVIDERS[name]

        if status == "skip":
            icon = yellow("─ SKIP")
            detail = result[1]
            skip_count += 1
        elif status == "ok":
            icon = green("✓ OK")
            detail = result[1]
            ok_count += 1
        else:
            icon = red("✗ FAIL")
            detail = result[1].splitlines()[0]  # first line only in table
            fail_count += 1

        print(f"  {name:<14} {icon:<18} {detail}")

    print(bold("─" * 56))
    totals = []
    if ok_count:    totals.append(green(f"{ok_count} passed"))
    if fail_count:  totals.append(red(f"{fail_count} failed"))
    if skip_count:  totals.append(yellow(f"{skip_count} skipped (no key)"))
    print("  " + ", ".join(totals))
    print()

    if fail_count:
        print(bold(cyan("Troubleshooting tips:")))
        for name, result in results.items():
            if result[0] == "fail":
                print(f"  {bold(name)}:")
                for line in result[1].splitlines():
                    print(f"    {line}")
                note = PROVIDERS[name].get("note")
                if note:
                    print(f"    Note: {note}")
        print()

    return 1 if fail_count else 0


def main():
    parser = argparse.ArgumentParser(
        description="Test AI provider API connectivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python scripts/test_providers.py
              python scripts/test_providers.py --providers openai anthropic
              python scripts/test_providers.py --verbose
        """),
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=list(PROVIDERS),
        default=list(PROVIDERS),
        help="Providers to test (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full details for passing tests too",
    )
    args = parser.parse_args()

    print()
    print(bold("AI Cost Tracker — Provider Connectivity Tests"))
    print(f"  Providers: {', '.join(args.providers)}")
    print()

    results = run_tests(args.providers, verbose=args.verbose)
    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
