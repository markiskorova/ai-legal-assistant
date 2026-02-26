# Generated manually for PR-1.5 pgvector bootstrap.

from django.db import migrations


VECTOR_DIM = 1536


def enable_pgvector(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION review_finding_embedding_input(
                summary text,
                explanation text,
                evidence text
            )
            RETURNS text
            LANGUAGE SQL
            IMMUTABLE
            AS $$
              SELECT trim(BOTH E'\n' FROM concat_ws(
                E'\n',
                COALESCE(summary, ''),
                COALESCE(explanation, ''),
                COALESCE(evidence, '')
              ));
            $$;
            """
        )
        cursor.execute(
            f"ALTER TABLE review_finding ADD COLUMN IF NOT EXISTS embedding_vector vector({VECTOR_DIM})"
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS review_finding_embedding_vector_ivfflat_idx
            ON review_finding
            USING ivfflat (embedding_vector vector_cosine_ops)
            WITH (lists = 100)
            """
        )


def disable_pgvector(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS review_finding_embedding_vector_ivfflat_idx")
        cursor.execute("ALTER TABLE review_finding DROP COLUMN IF EXISTS embedding_vector")
        cursor.execute(
            """
            DROP FUNCTION IF EXISTS review_finding_embedding_input(
                text,
                text,
                text
            )
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("review", "0009_finding_embedding_finding_recommendation"),
    ]

    operations = [
        migrations.RunPython(enable_pgvector, disable_pgvector),
    ]
