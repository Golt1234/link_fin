import pandera.polars as pa
from pandera.engines.polars_engine import String
import polars as pl

BAD_WORDS = ["test", "dummy", "fake", "sample", "xxx", "trap", "placeholder", "lorem", "ipsum"]
BAD_PATTERN = r"(?i)\b(" + "|".join(BAD_WORDS) + r")\b"

class AddressSchema(pa.DataFrameModel):
    account_id: int = pa.Field(nullable=False)
    name: str = pa.Field(nullable=False)

    address: String = pa.Field(
        str_length={"min_value": 8, "max_value": 200},
        str_matches=r".*\d+.*",
        nullable=False,
        description="Valid physical street address"
    )

    @pa.check("address")
    def no_forbidden_words(cls, data: pa.PolarsData) -> pl.LazyFrame:
        """Reject addresses that contain any forbidden placeholder/test words."""
        return data.lazyframe.select(
            ~pl.col(data.key).str.contains(BAD_PATTERN)
        )

    class Config:
        strict = True
        coerce = True