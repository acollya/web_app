#!/usr/bin/env python3
"""
Populate Secrets Manager with real credentials after first CDK deploy.

The CDK creates secrets with placeholder values — this script updates them
with real values from environment variables or interactive prompts.

Usage:
  # Interactive mode (prompts for each value):
  python scripts/setup_secrets.py --stage dev

  # From environment variables:
  OPENAI_KEY=sk-... STRIPE_KEY=sk_test_... python scripts/setup_secrets.py --stage dev
"""
import argparse
import json
import os

import boto3


def update_secret(client, secret_name: str, new_value: dict) -> None:
    try:
        client.put_secret_value(
            SecretId=secret_name,
            SecretString=json.dumps(new_value),
        )
        print(f"  ✓ Updated: {secret_name}")
    except Exception as e:
        print(f"  ✗ Failed to update {secret_name}: {e}")


def prompt(label: str, env_key: str = None, secret: bool = False) -> str:
    """Get value from env var, or prompt user."""
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    import getpass
    fn = getpass.getpass if secret else input
    return fn(f"  {label}: ").strip()


def main():
    parser = argparse.ArgumentParser(description="Populate Acollya secrets")
    parser.add_argument("--stage", required=True, choices=["dev", "prod"])
    parser.add_argument("--region", default="sa-east-1")
    args = parser.parse_args()

    client = boto3.client("secretsmanager", region_name=args.region)
    stage = args.stage

    print(f"\n=== Acollya Secrets Setup — {stage.upper()} ===")
    print("Leave blank to skip updating a secret.\n")

    # ── OpenAI ────────────────────────────────────────────────────────────────
    print("[ OpenAI ]")
    openai_key = prompt("API Key (sk-...)", "OPENAI_API_KEY", secret=True)
    if openai_key:
        update_secret(client, f"acollya/{stage}/openai", {
            "api_key": openai_key,
            "chat_model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-small",
            "max_tokens": "1024",
        })

    # ── Stripe ────────────────────────────────────────────────────────────────
    print("\n[ Stripe ]")
    stripe_key = prompt("Secret Key (sk_...)", "STRIPE_SECRET_KEY", secret=True)
    stripe_webhook = prompt("Webhook Secret (whsec_...)", "STRIPE_WEBHOOK_SECRET", secret=True)
    stripe_price_monthly = prompt("Monthly Price ID (price_...)", "STRIPE_PRICE_MONTHLY")
    stripe_price_yearly = prompt("Yearly Price ID (price_...)", "STRIPE_PRICE_YEARLY")
    if stripe_key:
        update_secret(client, f"acollya/{stage}/stripe", {
            "secret_key": stripe_key,
            "webhook_secret": stripe_webhook,
            "price_id_monthly": stripe_price_monthly,
            "price_id_yearly": stripe_price_yearly,
        })

    # ── Google OAuth ──────────────────────────────────────────────────────────
    print("\n[ Google OAuth ]")
    google_client_id = prompt("Client ID", "GOOGLE_CLIENT_ID")
    google_client_secret = prompt("Client Secret", "GOOGLE_CLIENT_SECRET", secret=True)
    if google_client_id:
        update_secret(client, f"acollya/{stage}/google-oauth", {
            "client_id": google_client_id,
            "client_secret": google_client_secret,
        })

    # ── JWT Keys (generate if not provided) ───────────────────────────────────
    print("\n[ JWT RS256 Keys ]")
    print("  Generating RS256 key pair...")
    import subprocess, tempfile, pathlib

    with tempfile.TemporaryDirectory() as tmp:
        priv = pathlib.Path(tmp) / "private.pem"
        pub = pathlib.Path(tmp) / "public.pem"
        subprocess.run(["openssl", "genrsa", "-out", str(priv), "2048"], check=True, capture_output=True)
        subprocess.run(["openssl", "rsa", "-in", str(priv), "-pubout", "-out", str(pub)], check=True, capture_output=True)
        private_key = priv.read_text()
        public_key = pub.read_text()

    update_secret(client, f"acollya/{stage}/jwt", {
        "private_key": private_key,
        "public_key": public_key,
        "algorithm": "RS256",
        "access_token_expire_minutes": "15",
        "refresh_token_expire_days": "30",
    })
    print("  ✓ RS256 key pair generated and stored")

    print(f"\n=== Secrets setup complete for {stage.upper()} ===")


if __name__ == "__main__":
    main()
