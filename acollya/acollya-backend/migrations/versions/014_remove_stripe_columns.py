"""Remove Stripe-specific columns — app is now 100% mobile (RevenueCat for IAP).

Changes:
  1. users — drop stripe_customer_id column + index
  2. subscriptions — drop stripe_subscription_id + stripe_price_id columns
  3. subscriptions — change provider column server_default to 'revenue_cat'
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users: drop stripe_customer_id ───────────────────────────────────────
    op.drop_index("idx_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "stripe_customer_id")

    # ── subscriptions: drop Stripe-specific columns ───────────────────────────
    op.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_stripe_subscription_id_key")
    op.drop_column("subscriptions", "stripe_subscription_id")
    op.drop_column("subscriptions", "stripe_price_id")

    # ── subscriptions: update provider default ────────────────────────────────
    op.alter_column(
        "subscriptions", "provider",
        server_default=sa.text("'revenue_cat'"),
        existing_type=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "subscriptions", "provider",
        server_default=sa.text("'stripe'"),
        existing_type=sa.Text(),
        existing_nullable=False,
    )

    op.add_column(
        "subscriptions",
        sa.Column("stripe_price_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True, unique=True),
    )
    op.create_index(
        "subscriptions_stripe_subscription_id_key",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )

    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.Text(), nullable=True, unique=True),
    )
    op.create_index("idx_users_stripe_customer_id", "users", ["stripe_customer_id"])
