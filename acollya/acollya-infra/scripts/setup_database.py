#!/usr/bin/env python3
"""
Post-deploy database setup script.

Run ONCE after first CDK deploy to:
  1. Enable pgvector extension
  2. Run Alembic migrations
  3. Verify connectivity

Usage:
  python scripts/setup_database.py --stage dev
  python scripts/setup_database.py --stage prod --region sa-east-1

Requirements:
  pip install boto3 psycopg2-binary alembic
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import boto3
import psycopg2

BACKEND_DIR = Path(__file__).parent.parent.parent / "acollya-backend"


def get_db_secret(stage: str, region: str) -> dict:
    print(f"Fetching DB credentials from Secrets Manager (stage={stage})...")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=f"acollya/{stage}/db-credentials")
    return json.loads(response["SecretString"])


def get_db_host(stage: str, region: str) -> str:
    print(f"Fetching DB endpoint from CloudFormation outputs...")
    cf = boto3.client("cloudformation", region_name=region)
    response = cf.describe_stacks(StackName=f"AcollyaDatabase-{stage}")
    outputs = response["Stacks"][0]["Outputs"]
    for output in outputs:
        if output["OutputKey"] == "DbEndpoint":
            return output["OutputValue"]
    raise ValueError(f"DbEndpoint not found in AcollyaDatabase-{stage} outputs")


def enable_extensions(conn) -> None:
    print("Enabling PostgreSQL extensions...")
    with conn.cursor() as cur:
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    print("  ✓ uuid-ossp enabled")
    print("  ✓ vector (pgvector) enabled")


def run_migrations(stage: str, db_host: str, secret: dict) -> None:
    print("Running Alembic migrations...")
    db_url = (
        f"postgresql+psycopg2://{secret['username']}:{secret['password']}"
        f"@{db_host}:5432/acollya"
        f"?sslmode=require"
    )
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env={
            **__import__("os").environ,
            "STAGE": stage,
            "DB_HOST": db_host,
            "DB_USER": secret["username"],
            "DB_PASSWORD": secret["password"],
        },
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Migration failed:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout)
    print("  ✓ Migrations applied")


def main():
    parser = argparse.ArgumentParser(description="Acollya post-deploy DB setup")
    parser.add_argument("--stage", required=True, choices=["dev", "prod"])
    parser.add_argument("--region", default="sa-east-1")
    parser.add_argument("--skip-extensions", action="store_true")
    parser.add_argument("--skip-migrations", action="store_true")
    args = parser.parse_args()

    print(f"\n=== Acollya Database Setup — {args.stage.upper()} ===\n")

    secret = get_db_secret(args.stage, args.region)
    db_host = get_db_host(args.stage, args.region)

    print(f"Connecting to {db_host}...")
    conn = psycopg2.connect(
        host=db_host,
        port=5432,
        dbname="acollya",
        user=secret["username"],
        password=secret["password"],
        sslmode="require",
    )
    print("  ✓ Connected\n")

    if not args.skip_extensions:
        enable_extensions(conn)

    conn.close()

    if not args.skip_migrations:
        run_migrations(args.stage, db_host, secret)

    print("\n=== Setup complete! ===")
    print(f"  DB Host:  {db_host}")
    print(f"  Stage:    {args.stage}")
    print("\nNext steps:")
    print("  1. Populate secrets: python scripts/setup_secrets.py --stage dev")
    print("  2. Start local dev:  cd ../acollya-backend && uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
