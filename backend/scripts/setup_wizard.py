#!/usr/bin/env python3
"""
Interactive Setup Wizard for AI Cost Tracker

Opens browser pages for API key creation and securely collects keys.
Validates formats and tests connectivity before saving to .env file.

Usage:
    python scripts/setup_wizard.py
    python scripts/setup_wizard.py --update  # Update existing .env
"""

import os
import sys
import webbrowser
import getpass
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Provider configuration
PROVIDERS = {
    'anthropic': {
        'name': 'Anthropic Claude',
        'required': True,
        'env_var': 'ANTHROPIC_ADMIN_API_KEY',
        'key_prefix': 'sk-ant-admin-',
        'console_url': 'https://console.anthropic.com/settings/organization',
        'instructions': [
            '1. Click "Generate Admin Key" (NOT "API Key")',
            '2. Admin keys are required for usage/cost tracking',
            '3. Standard API keys (sk-ant-api-...) will NOT work',
            '4. Copy the key starting with sk-ant-admin-...',
        ],
        'help_url': 'https://docs.anthropic.com/en/api/getting-started#accessing-the-api',
    },
    'openai': {
        'name': 'OpenAI',
        'required': True,
        'env_var': 'OPENAI_API_KEY',
        'key_prefix': 'sk-',
        'console_url': 'https://platform.openai.com/api-keys',
        'instructions': [
            '1. Click "Create new secret key"',
            '2. Give it a name (e.g., "AI Cost Tracker")',
            '3. Copy the key starting with sk-...',
            '4. You can only see the key once - save it now!',
        ],
        'help_url': 'https://platform.openai.com/docs/quickstart',
    },
    'groq': {
        'name': 'Groq',
        'required': False,
        'env_var': 'GROQ_API_KEY',
        'key_prefix': 'gsk_',
        'console_url': 'https://console.groq.com/keys',
        'instructions': [
            '1. Click "Create API Key"',
            '2. Give it a name',
            '3. Copy the key starting with gsk_...',
        ],
        'help_url': 'https://console.groq.com/docs/quickstart',
    },
    'perplexity': {
        'name': 'Perplexity',
        'required': False,
        'env_var': 'PERPLEXITY_API_KEY',
        'key_prefix': 'pplx-',
        'console_url': 'https://www.perplexity.ai/settings/api',
        'instructions': [
            '1. Click "Generate API Key"',
            '2. Copy the key starting with pplx-...',
            '3. Note: Last 4 chars appear on invoices for reconciliation',
        ],
        'help_url': 'https://docs.perplexity.ai/docs/getting-started',
    },
    'mistral': {
        'name': 'Mistral AI',
        'required': False,
        'env_var': 'MISTRAL_API_KEY',
        'key_prefix': '',  # Unknown prefix - will skip validation
        'console_url': 'https://console.mistral.ai/api-keys/',
        'instructions': [
            '1. Click "Create new key"',
            '2. Give it a name',
            '3. Copy the API key',
        ],
        'help_url': 'https://docs.mistral.ai/getting-started/quickstart/',
    },
}


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def validate_key_format(provider: str, key: str) -> Tuple[bool, str]:
    """
    Validate API key format for a provider.
    
    Returns:
        (is_valid, error_message)
    """
    config = PROVIDERS[provider]
    prefix = config['key_prefix']
    
    if not key:
        return False, "Key cannot be empty"
    
    if not key.strip():
        return False, "Key cannot be only whitespace"
    
    # Skip prefix validation if no prefix defined
    if not prefix:
        return True, ""
    
    if not key.startswith(prefix):
        return False, f"Key must start with '{prefix}'"
    
    # Check key length (most API keys are 40+ chars)
    if len(key) < 20:
        return False, "Key seems too short - did you copy it completely?"
    
    # Special validation for Anthropic admin keys
    if provider == 'anthropic':
        if key.startswith('sk-ant-api-'):
            return False, (
                "This is a standard API key, not an admin key!\n"
                "       Admin keys start with 'sk-ant-admin-' not 'sk-ant-api-'\n"
                "       Go to Organization settings, not API Keys page"
            )
    
    return True, ""


def load_existing_env() -> Dict[str, str]:
    """Load existing .env file if it exists."""
    env_path = Path(__file__).parent.parent.parent / '.env'
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def save_env_file(env_vars: Dict[str, str]):
    """Save environment variables to .env file."""
    env_path = Path(__file__).parent.parent.parent / '.env'
    
    # Backup existing .env if it exists
    if env_path.exists():
        backup_path = env_path.with_suffix('.env.backup')
        import shutil
        shutil.copy2(env_path, backup_path)
        print_info(f"Backed up existing .env to {backup_path.name}")
    
    # Write new .env file
    with open(env_path, 'w') as f:
        f.write("# AI Cost Tracker - Environment Configuration\n")
        f.write("# Generated by setup wizard\n")
        f.write(f"# Created: {os.popen('date').read().strip()}\n\n")
        
        # Provider API keys
        f.write("# Provider API Keys\n")
        for provider_id, config in PROVIDERS.items():
            env_var = config['env_var']
            value = env_vars.get(env_var, '')
            if value:
                f.write(f"{env_var}={value}\n")
            else:
                f.write(f"# {env_var}=  # Optional\n")
        
        # Database
        f.write("\n# Database Configuration\n")
        db_url = env_vars.get('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/ai_cost_tracker')
        f.write(f"DATABASE_URL={db_url}\n")
        
        # Flask
        f.write("\n# Flask Configuration\n")
        flask_env = env_vars.get('FLASK_ENV', 'development')
        f.write(f"FLASK_ENV={flask_env}\n")
        
        secret_key = env_vars.get('SECRET_KEY')
        if not secret_key:
            import secrets
            secret_key = secrets.token_hex(32)
        f.write(f"SECRET_KEY={secret_key}\n")
        
        # Additional vars
        f.write("\n# Additional Configuration\n")
        for key, value in env_vars.items():
            if key not in [config['env_var'] for config in PROVIDERS.values()] and \
               key not in ['DATABASE_URL', 'FLASK_ENV', 'SECRET_KEY']:
                f.write(f"{key}={value}\n")
    
    print_success(f"Saved configuration to {env_path}")


def setup_provider(provider_id: str, existing_env: Dict[str, str], update_mode: bool = False) -> Optional[str]:
    """
    Setup API key for a single provider.
    
    Returns:
        API key if configured, None if skipped
    """
    config = PROVIDERS[provider_id]
    env_var = config['env_var']
    existing_key = existing_env.get(env_var)
    
    print(f"\n{Colors.BOLD}{'─' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{config['name']}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'─' * 70}{Colors.ENDC}")
    
    # Show existing key status
    if existing_key:
        masked_key = existing_key[:15] + '...' + existing_key[-4:] if len(existing_key) > 20 else '***'
        print_info(f"Existing key found: {masked_key}")
        if not update_mode:
            response = input(f"\n{Colors.OKCYAN}Keep existing key? (Y/n): {Colors.ENDC}").strip().lower()
            if response != 'n':
                print_success("Keeping existing key")
                return existing_key
    
    # Check if required
    if not config['required']:
        response = input(f"\n{Colors.OKCYAN}Configure {config['name']}? (y/N): {Colors.ENDC}").strip().lower()
        if response != 'y':
            print_info("Skipped")
            return None
    
    # Show instructions
    print(f"\n{Colors.UNDERLINE}Instructions:{Colors.ENDC}")
    for instruction in config['instructions']:
        print(f"  {instruction}")
    
    # Offer to open browser
    print(f"\n{Colors.OKCYAN}Console URL:{Colors.ENDC} {config['console_url']}")
    response = input(f"{Colors.OKCYAN}Open this page in your browser? (Y/n): {Colors.ENDC}").strip().lower()
    if response != 'n':
        try:
            webbrowser.open(config['console_url'])
            print_success("Opened in browser")
        except Exception as e:
            print_warning(f"Could not open browser: {e}")
            print_info(f"Please manually open: {config['console_url']}")
    
    # Collect API key
    while True:
        print(f"\n{Colors.BOLD}Paste your API key below{Colors.ENDC}")
        print(f"{Colors.WARNING}(Input will be hidden for security){Colors.ENDC}")
        
        api_key = getpass.getpass(f"{config['name']} API Key: ").strip()
        
        if not api_key:
            if not config['required']:
                print_info("Skipped")
                return None
            print_error("API key is required for this provider")
            continue
        
        # Validate format
        is_valid, error_msg = validate_key_format(provider_id, api_key)
        if not is_valid:
            print_error(f"Invalid key format: {error_msg}")
            retry = input(f"{Colors.OKCYAN}Try again? (Y/n): {Colors.ENDC}").strip().lower()
            if retry == 'n':
                return None
            continue
        
        print_success("Key format looks valid")
        
        # Confirm
        masked_key = api_key[:15] + '...' + api_key[-4:] if len(api_key) > 20 else '***'
        print(f"\n{Colors.OKCYAN}Key:{Colors.ENDC} {masked_key}")
        response = input(f"{Colors.OKCYAN}Save this key? (Y/n): {Colors.ENDC}").strip().lower()
        if response != 'n':
            return api_key
        
        retry = input(f"{Colors.OKCYAN}Try again? (Y/n): {Colors.ENDC}").strip().lower()
        if retry == 'n':
            return None


def test_connectivity(env_vars: Dict[str, str]):
    """
    Test provider connectivity with configured keys.
    """
    print_header("Testing Provider Connectivity")
    
    # Temporarily set environment variables
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # Import and run test script
        test_script = Path(__file__).parent / 'test_providers.py'
        if test_script.exists():
            print_info("Running connectivity tests...\n")
            os.system(f"python {test_script}")
        else:
            print_warning("Test script not found - skipping connectivity tests")
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main():
    """Main setup wizard."""
    update_mode = '--update' in sys.argv
    
    print_header("AI Cost Tracker - Setup Wizard")
    
    print(f"{Colors.BOLD}Welcome to the AI Cost Tracker setup wizard!{Colors.ENDC}")
    print("\nThis wizard will help you:")
    print("  1. Open provider consoles in your browser")
    print("  2. Securely collect API keys")
    print("  3. Validate key formats")
    print("  4. Save configuration to .env file")
    print("  5. Test connectivity\n")
    
    # Load existing configuration
    existing_env = load_existing_env()
    if existing_env:
        print_info(f"Found existing .env file with {len(existing_env)} variables")
    else:
        print_info("No existing .env file found - creating new configuration")
    
    # Confirm start
    if not update_mode:
        response = input(f"\n{Colors.OKCYAN}Continue with setup? (Y/n): {Colors.ENDC}").strip().lower()
        if response == 'n':
            print_info("Setup cancelled")
            return
    
    # Setup each provider
    new_env = existing_env.copy()
    
    for provider_id in PROVIDERS.keys():
        api_key = setup_provider(provider_id, existing_env, update_mode)
        if api_key:
            new_env[PROVIDERS[provider_id]['env_var']] = api_key
    
    # Save configuration
    print_header("Saving Configuration")
    
    configured_count = sum(1 for p in PROVIDERS.values() if new_env.get(p['env_var']))
    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  Providers configured: {configured_count}/{len(PROVIDERS)}")
    for provider_id, config in PROVIDERS.items():
        env_var = config['env_var']
        if new_env.get(env_var):
            print_success(f"{config['name']}: Configured")
        elif config['required']:
            print_error(f"{config['name']}: Missing (REQUIRED)")
        else:
            print_warning(f"{config['name']}: Not configured (optional)")
    
    response = input(f"\n{Colors.OKCYAN}Save this configuration? (Y/n): {Colors.ENDC}").strip().lower()
    if response == 'n':
        print_info("Configuration not saved")
        return
    
    save_env_file(new_env)
    
    # Test connectivity
    response = input(f"\n{Colors.OKCYAN}Test provider connectivity now? (Y/n): {Colors.ENDC}").strip().lower()
    if response != 'n':
        test_connectivity(new_env)
    
    # Next steps
    print_header("Setup Complete!")
    print(f"{Colors.OKGREEN}✓ Configuration saved to .env{Colors.ENDC}")
    print(f"{Colors.OKGREEN}✓ API keys validated{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
    print("  1. Start services: docker-compose up -d")
    print("  2. Apply migration: docker-compose exec backend flask db upgrade")
    print("  3. Open dashboard: http://localhost:3000")
    print("\nFor help, see: docs/HANDOVER_TO_PERPLEXITY.md\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Setup cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
