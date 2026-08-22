import pandera.polars as pa
from pandera.engines.polars_engine import String
import polars as pl

BAD_WORDS = ["test", "dummy", "fake", "sample", "xxx", "trap"]
BAD_PATTERN = r"(?i)\b(" + "|".join(BAD_WORDS) + r")\b"

class NameSchema(pa.DataFrameModel):
    account_id: int = pa.Field(nullable=False)
    address: str = pa.Field(nullable=False)

    name: String = pa.Field(
        str_matches=r"^[A-Z][a-zA-Z'\-]+(?: [A-Z][a-zA-Z'\-]+)*$",
        nullable=False,
        unique=False,
        description="Valid person name"
    )

    @pa.check("name")
    def no_forbidden_words(cls, data: pa.PolarsData) -> pl.LazyFrame:
        """Reject names that contain any forbidden test/dummy words."""
        return data.lazyframe.select(
            ~pl.col(data.key).str.contains(BAD_PATTERN)
        )

    class Config:
        strict = True
        coerce = True