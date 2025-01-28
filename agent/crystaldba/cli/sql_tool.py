from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

import sqlalchemy
from attrs import define
from attrs import field

from crystaldba.shared.base_sql_driver import BaseSqlDriver

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


@define
class LocalSqlDriver:
    engine_url: str | sqlalchemy.URL = field(kw_only=True)
    create_engine_params: dict[str, Any] = field(factory=dict, kw_only=True)
    _engine: Engine = field(default=None, kw_only=True, alias="engine", metadata={"serializable": False})

    @property
    def engine(self) -> Engine:
        return sqlalchemy.create_engine(self.engine_url, **self.create_engine_params)

    def local_execute_query_raw(self, query: str) -> list[dict[str, Any]] | None:
        with self.engine.connect() as con:
            try:
                results = con.execute(sqlalchemy.text(query))
                if not results.returns_rows:
                    return None
                return [dict(result._mapping) for result in results]  # pyright: ignore[reportPrivateUsage]
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Error: client sql execution error {e!r}")
                raise

    def execute_query(self, query: str) -> list[BaseSqlDriver.RowResult] | None:
        raw_results = self.local_execute_query_raw(query)
        if raw_results is None:
            return None
        return [BaseSqlDriver.RowResult(cells=row) for row in raw_results]

    def get_table_schema(self, table_name: str, schema: str | None = None) -> str | None:
        try:
            if schema is not None and table_name.startswith(f"{schema}."):
                table_name = table_name[len(schema) + 1 :]
            table = sqlalchemy.Table(table_name, sqlalchemy.MetaData(), schema=schema, autoload_with=self.engine)
            res = str([(c.name, c.type) for c in table.columns])
            return res
        except sqlalchemy.exc.NoSuchTableError:
            return None
