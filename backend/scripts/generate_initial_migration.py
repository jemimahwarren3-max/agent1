"""One-off helper: emits a raw-SQL alembic migration body from the current
SQLAlchemy metadata, since autogenerate needs a live DB connection to diff
against and none is available in this environment. Regenerate with this
script if you add tables before ever running against a real Postgres;
once you've run `alembic upgrade head` against a real DB at least once,
use `alembic revision --autogenerate` normally from then on.
"""

from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from app.db.session import Base
from app import models  # noqa: F401

dialect = postgresql.dialect()


def main() -> None:
    seen_enums: set[str] = set()
    enum_lines = []
    for table in Base.metadata.sorted_tables:
        for col in table.columns:
            enum_type = col.type
            name = getattr(enum_type, "name", None)
            if name and hasattr(enum_type, "enums") and name not in seen_enums:
                seen_enums.add(name)
                values = ", ".join(f"'{v}'" for v in enum_type.enums)
                enum_lines.append(f'    op.execute("CREATE TYPE {name} AS ENUM ({values})")')

    table_lines = []
    drop_lines = []
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
        indented = "\n".join("    " + line for line in ddl.splitlines())
        table_lines.append(f'    op.execute("""\n{indented}\n    """)')
        drop_lines.append(f'    op.execute("DROP TABLE IF EXISTS {table.name} CASCADE")')

    drop_enum_lines = [f'    op.execute("DROP TYPE IF EXISTS {name} CASCADE")' for name in seen_enums]

    upgrade_body = "\n\n".join(enum_lines + table_lines)
    downgrade_body = "\n\n".join(list(reversed(drop_lines)) + drop_enum_lines)

    print("# ---- paste into the migration's upgrade()/downgrade() ----")
    print("def upgrade() -> None:")
    print(upgrade_body)
    print()
    print("def downgrade() -> None:")
    print(downgrade_body)


if __name__ == "__main__":
    main()
