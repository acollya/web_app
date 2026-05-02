#!/usr/bin/env python3
"""
Populate Secrets Manager with real credentials after first CDK deploy.

The CDK creates secrets with placeholder values ("{}") — this script updates
them with real values from environment variables or interactive prompts.

Usage:
  # Interactive mode (prompts for each value):
  python scripts/setup_secrets.py --stage dev

  # From environment variables (CI/CD):
  OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... \\
  STRIPE_SECRET_KEY=sk_test_... STRIPE_WEBHOOK_SECRET=whsec_... \\
  STRIPE_PRICE_MONTHLY=price_... STRIPE_PRICE_YEARLY=price_... \\
  GOOGLE_CLIENT_ID_IOS=... GOOGLE_CLIENT_ID_ANDROID=... \\
  REVENUE_CAT_API_KEY=... \\
  python scripts/setup_secrets.py --stage dev

Secrets managed by this script (mirrors SecretsStack):
  acollya/{stage}/jwt          — RS256 key pair + Google OAuth client IDs
  acollya/{stage}/openai       — OpenAI API key + model config
  acollya/{stage}/anthropic    — Anthropic API key + model config
  acollya/{stage}/stripe       — Stripe keys + price IDs
  acollya/{stage}/app-config   — Application config (trial, limits, RevenueCat)
"""
import argparse
import json
import os
import subprocess
import tempfile
import pathlib

import boto3


# ── Helpers ────────────────────────────────────────────────────────────────────

def update_secret(client, secret_name: str, new_value: dict) -> None:
    try:
        client.put_secret_value(
            SecretId=secret_name,
            SecretString=json.dumps(new_value),
        )
        print(f"  ✓ Updated: {secret_name}")
    except client.exceptions.ResourceNotFoundException:
        print(f"  ✗ Secret not found (CDK deploy ran?): {secret_name}")
    except Exception as e:
        print(f"  ✗ Failed to update {secret_name}: {e}")


def prompt(label: str, env_key: str = None, secret: bool = False, default: str = None) -> str:
    """Get value from env var, prompt user, or return default."""
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    import getpass
    hint = f" [{default}]" if default else ""
    fn = getpass.getpass if secret else input
    value = fn(f"  {label}{hint}: ").strip()
    return value or default or ""


def get_current_value(client, secret_name: str) -> dict:
    """Return current secret value, or {} if placeholder/missing."""
    try:
        resp = client.get_secret_value(SecretId=secret_name)
        return json.loads(resp["SecretString"])
    except Exception:
        return {}


def validate_all_populated(client, stage: str) -> list[str]:
    """Return list of secret names that are still empty placeholders ({})."""
    names = [
        f"acollya/{stage}/jwt",
        f"acollya/{stage}/openai",
        f"acollya/{stage}/anthropic",
        f"acollya/{stage}/stripe",
        f"acollya/{stage}/app-config",
    ]
    unpopulated = []
    for name in names:
        val = get_current_value(client, name)
        if not val or val == {}:
            unpopulated.append(name)
    return unpopulated


# ── Secret setup functions ─────────────────────────────────────────────────────

def setup_openai(client, stage: str) -> None:
    print("\n[ OpenAI ]")
    api_key = prompt("API Key (sk-...)", "OPENAI_API_KEY", secret=True)
    if not api_key:
        print("  — Skipped")
        return
    update_secret(client, f"acollya/{stage}/openai", {
        "api_key": api_key,
        "chat_model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small",
        "max_tokens": "1024",
    })


def setup_anthropic(client, stage: str) -> None:
    print("\n[ Anthropic ]")
    api_key = prompt("API Key (sk-ant-...)", "ANTHROPIC_API_KEY", secret=True)
    if not api_key:
        print("  — Skipped")
        return
    model = "claude-haiku-4-5-20251001" if stage != "prod" else "claude-haiku-4-5-20251001"
    update_secret(client, f"acollya/{stage}/anthropic", {
        "api_key": api_key,
        "chat_model": model,
    })


def setup_stripe(client, stage: str) -> None:
    print("\n[ Stripe ]")
    secret_key = prompt("Secret Key (sk_live_... or sk_test_...)", "STRIPE_SECRET_KEY", secret=True)
    if not secret_key:
        print("  — Skipped")
        return
    webhook_secret = prompt("Webhook Secret (whsec_...)", "STRIPE_WEBHOOK_SECRET", secret=True)
    price_monthly  = prompt("Monthly Price ID (price_...)", "STRIPE_PRICE_MONTHLY")
    price_yearly   = prompt("Yearly Price ID (price_...)", "STRIPE_PRICE_YEARLY")
    update_secret(client, f"acollya/{stage}/stripe", {
        "secret_key": secret_key,
        "webhook_secret": webhook_secret,
        "monthly_price_id": price_monthly,
        "annual_price_id": price_yearly,
    })


def setup_app_config(client, stage: str) -> None:
    print("\n[ App Config ]")
    revenue_cat_key = prompt("RevenueCat API Key", "REVENUE_CAT_API_KEY", secret=True)
    if not revenue_cat_key:
        print("  — Skipped")
        return
    trial_days             = prompt("Trial days", default="14")
    free_msgs_per_day      = prompt("Free chat messages/day", default="20")
    premium_msgs_per_day   = prompt("Premium chat messages/day", default="9999")
    update_secret(client, f"acollya/{stage}/app-config", {
        "trial_days": trial_days,
        "free_chat_messages_per_day": free_msgs_per_day,
        "premium_chat_messages_per_day": premium_msgs_per_day,
        "revenue_cat_api_key": revenue_cat_key,
    })


def setup_jwt(client, stage: str) -> None:
    """Generate RS256 key pair and store with Google OAuth client IDs."""
    print("\n[ JWT RS256 Keys + Google OAuth Client IDs ]")

    # Google client IDs go here (not in a separate secret) per SecretsStack comment
    google_ios     = prompt("Google iOS Client ID", "GOOGLE_CLIENT_ID_IOS")
    google_android = prompt("Google Android Client ID", "GOOGLE_CLIENT_ID_ANDROID")

    print("  Generating RS256 key pair...")
    with tempfile.TemporaryDirectory() as tmp:
        priv = pathlib.Path(tmp) / "private.pem"
        pub  = pathlib.Path(tmp) / "public.pem"
        subprocess.run(
            ["openssl", "genrsa", "-out", str(priv), "2048"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["openssl", "rsa", "-in", str(priv), "-pubout", "-out", str(pub)],
            check=True, capture_output=True,
        )
        private_key = priv.read_text()
        public_key  = pub.read_text()

    google_client_ids = [gid for gid in [google_ios, google_android] if gid]

    update_secret(client, f"acollya/{stage}/jwt", {
        "private_key": private_key,
        "public_key": public_key,
        "algorithm": "RS256",
        "access_token_expire_minutes": "15",
        "refresh_token_expire_days": "30",
        "google_client_ids": google_client_ids,
    })
    print("  ✓ RS256 key pair generated and stored")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Populate Acollya Secrets Manager secrets")
    parser.add_argument("--stage", required=True, choices=["dev", "prod"])
    parser.add_argument("--region", default="sa-east-1")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only check which secrets are still empty placeholders, don't update",
    )
    args = parser.parse_args()

    client = boto3.client("secretsmanager", region_name=args.region)
    stage = args.stage

    if args.validate_only:
        print(f"\n=== Validating secrets — {stage.upper()} ===")
        unpopulated = validate_all_populated(client, stage)
        if unpopulated:
            print("Secrets still empty ({}):")
            for name in unpopulated:
                print(f"  ✗ {name}")
        else:
            print("All secrets are populated ✓")
        return

    print(f"\n=== Acollya Secrets Setup — {stage.upper()} ===")
    print("Leave blank to skip updating a secret.\n")

    setup_openai(client, stage)
    setup_anthropic(client, stage)
    setup_stripe(client, stage)
    setup_app_config(client, stage)
    setup_jwt(client, stage)

    print(f"\n=== Setup complete for {stage.upper()} ===")

    # Post-setup validation
    unpopulated = validate_all_populated(client, stage)
    if unpopulated:
        print("\n⚠️  The following secrets were skipped and remain empty:")
        for name in unpopulated:
            print(f"   {name}")
        print("Run this script again to populate them before deploying the app.")
    else:
        print("All secrets populated ✓ — safe to deploy.")


if __name__ == "__main__":
    main()
