"""Enhance usage_records with rich provider metrics.

Revision ID: enhance_usage_v2
Revises: [auto-detect]
Create Date: 2026-03-02 15:20:00

This migration adds comprehensive metrics tracking for all AI providers:
- Token breakdown (input, output, cache)
- Model and service tier tracking
- Rate limit monitoring
- Performance metrics (response time, queue time)
- Provider-specific fields (workspaces, geo, search queries)

Approach: Additive migration (zero downtime)
- Adds new columns with defaults
- Preserves existing data
- Backfills where possible
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enhance_usage_v2'
down_revision = None  # Set to previous revision ID
branch_labels = None
depends_on = None


def upgrade():
    """Add new columns to usage_records table."""
    
    print("\n⚙️  Starting usage_records enhancement migration...")
    
    # ===================================================================
    # Token breakdown columns
    # ===================================================================
    print("➡️  Adding token breakdown columns...")
    op.add_column('usage_records', 
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('usage_records', 
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('usage_records', 
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'))
    
    # ===================================================================
    # Cache tracking (Anthropic, Google)
    # ===================================================================
    print("➡️  Adding cache tracking columns...")
    op.add_column('usage_records', 
        sa.Column('cache_creation_tokens', sa.Integer(), server_default='0'))
    op.add_column('usage_records', 
        sa.Column('cache_read_tokens', sa.Integer(), server_default='0'))
    
    # ===================================================================
    # Cost breakdown (structured JSON)
    # ===================================================================
    print("➡️  Adding cost breakdown column...")
    op.add_column('usage_records', 
        sa.Column('cost_breakdown', sa.JSON(), nullable=True))
    
    # ===================================================================
    # Model & configuration
    # ===================================================================
    print("➡️  Adding model tracking columns...")
    op.add_column('usage_records', 
        sa.Column('model_name', sa.String(100), nullable=True))
    op.add_column('usage_records', 
        sa.Column('model_version', sa.String(50), nullable=True))
    op.add_column('usage_records', 
        sa.Column('service_tier', sa.String(50), nullable=True))
    
    # ===================================================================
    # Request metadata
    # ===================================================================
    print("➡️  Adding request metadata columns...")
    op.add_column('usage_records', 
        sa.Column('request_id', sa.String(100), nullable=True))
    
    # ===================================================================
    # Rate limit tracking (OpenAI, Groq)
    # ===================================================================
    print("➡️  Adding rate limit tracking columns...")
    op.add_column('usage_records', 
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=True))
    op.add_column('usage_records', 
        sa.Column('rate_limit_tpm', sa.Integer(), nullable=True))
    op.add_column('usage_records', 
        sa.Column('rate_limit_remaining_requests', sa.Integer(), nullable=True))
    op.add_column('usage_records', 
        sa.Column('rate_limit_remaining_tokens', sa.Integer(), nullable=True))
    
    # ===================================================================
    # Performance metrics (Groq, timing)
    # ===================================================================
    print("➡️  Adding performance metric columns...")
    op.add_column('usage_records', 
        sa.Column('response_time_ms', sa.Float(), nullable=True))
    op.add_column('usage_records', 
        sa.Column('queue_time_ms', sa.Float(), nullable=True))
    
    # ===================================================================
    # Provider-specific fields
    # ===================================================================
    print("➡️  Adding provider-specific columns...")
    
    # Anthropic
    op.add_column('usage_records', 
        sa.Column('workspace_id', sa.String(100), nullable=True))
    op.add_column('usage_records', 
        sa.Column('api_key_id', sa.String(100), nullable=True))
    op.add_column('usage_records', 
        sa.Column('inference_geo', sa.String(50), nullable=True))
    
    # Perplexity
    op.add_column('usage_records', 
        sa.Column('search_queries', sa.Integer(), server_default='0'))
    op.add_column('usage_records', 
        sa.Column('reasoning_tokens', sa.Integer(), server_default='0'))
    op.add_column('usage_records', 
        sa.Column('citation_tokens', sa.Integer(), server_default='0'))
    
    # ===================================================================
    # Create indexes for performance
    # ===================================================================
    print("➡️  Creating indexes...")
    op.create_index('ix_usage_records_model_name', 'usage_records', ['model_name'])
    
    # ===================================================================
    # Backfill existing data
    # ===================================================================
    print("➡️  Backfilling existing records...")
    
    # Migrate tokens_used -> total_tokens for existing records
    op.execute("""
        UPDATE usage_records 
        SET total_tokens = tokens_used 
        WHERE total_tokens = 0 AND tokens_used > 0
    """)
    
    # Count updated records
    from sqlalchemy import text
    connection = op.get_bind()
    result = connection.execute(text(
        "SELECT COUNT(*) FROM usage_records WHERE total_tokens > 0"
    ))
    count = result.scalar()
    print(f"✅ Backfilled {count} existing records")
    
    print("✅ Migration upgrade complete!\n")


def downgrade():
    """Remove added columns (rollback)."""
    
    print("\n⚠️  Starting usage_records downgrade (rollback)...")
    
    # Drop indexes first
    print("➡️  Dropping indexes...")
    op.drop_index('ix_usage_records_model_name', table_name='usage_records')
    
    # Drop all new columns
    print("➡️  Dropping new columns...")
    columns_to_drop = [
        # Token breakdown
        'input_tokens', 'output_tokens', 'total_tokens',
        
        # Cache
        'cache_creation_tokens', 'cache_read_tokens',
        
        # Cost
        'cost_breakdown',
        
        # Model
        'model_name', 'model_version', 'service_tier',
        
        # Request
        'request_id',
        
        # Rate limits
        'rate_limit_rpm', 'rate_limit_tpm', 
        'rate_limit_remaining_requests', 'rate_limit_remaining_tokens',
        
        # Performance
        'response_time_ms', 'queue_time_ms',
        
        # Provider-specific
        'workspace_id', 'api_key_id', 'inference_geo',
        'search_queries', 'reasoning_tokens', 'citation_tokens',
    ]
    
    for col in columns_to_drop:
        try:
            op.drop_column('usage_records', col)
        except Exception as e:
            print(f"⚠️  Could not drop column {col}: {e}")
    
    print("✅ Migration downgrade complete!\n")
