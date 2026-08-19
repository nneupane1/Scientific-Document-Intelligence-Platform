"""Initial scientific document metadata schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("sdr_path", sa.String(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=True)
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_table(
        "pages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("rendered_path", sa.String(1024)),
        sa.Column("result_path", sa.String(1024)),
        sa.Column("inspection", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "page_number", name="uq_pages_document_page"),
    )
    op.create_index("ix_pages_document_id", "pages", ["document_id"])
    op.create_table(
        "elements",
        sa.Column("id", sa.String(96), primary_key=True),
        sa.Column(
            "page_id", sa.String(64), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("element_type", sa.String(40), nullable=False),
        sa.Column("bbox", JSON_TYPE, nullable=False),
        sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("content", JSON_TYPE, nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("confidence_source", sa.String(80), nullable=False),
        sa.Column("provenance", JSON_TYPE, nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("warnings", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_elements_page_id", "elements", ["page_id"])
    op.create_index("ix_elements_element_type", "elements", ["element_type"])
    op.create_index("ix_elements_review_status", "elements", ["review_status"])
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(48), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("pages_completed", sa.Integer(), nullable=False),
        sa.Column("pages_total", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("details", JSON_TYPE, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_document_id", "jobs", ["document_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "processing_runs",
        sa.Column("id", sa.String(48), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pipeline_version", sa.String(40), nullable=False),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("git_commit", sa.String(64)),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("model_versions", JSON_TYPE, nullable=False),
        sa.Column("statistics", JSON_TYPE, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_processing_runs_document_id", "processing_runs", ["document_id"])


def downgrade() -> None:
    op.drop_table("processing_runs")
    op.drop_table("jobs")
    op.drop_table("elements")
    op.drop_table("pages")
    op.drop_table("documents")
