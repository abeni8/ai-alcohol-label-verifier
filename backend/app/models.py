from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Application(StrictModel):
    application_id: str = Field(default="Individual application", min_length=1, max_length=100)
    beverage_type: Literal["distilled_spirits", "wine", "malt_beverage"]
    imported: StrictBool = False
    brand_name: str = Field(min_length=1, max_length=200)
    class_type: str = Field(min_length=1, max_length=250)
    abv: str = Field(default="", max_length=12)
    net_contents: str = Field(min_length=1, max_length=60)
    producer_name: str = Field(min_length=1, max_length=250)
    producer_address: str = Field(min_length=1, max_length=400)
    country_of_origin: str = Field(default="", max_length=100)

    @field_validator("application_id", "brand_name", "class_type", "abv", "net_contents", "producer_name", "producer_address", "country_of_origin", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if not isinstance(value, str):
            raise ValueError("Enter a text value.")
        return value.strip()

    @field_validator("abv")
    @classmethod
    def check_abv(cls, value: str) -> str:
        if value:
            try:
                number = Decimal(value)
                if not number.is_finite() or not 0 <= number <= 100:
                    raise ValueError("ABV must be between 0 and 100.")
            except InvalidOperation as exc:
                raise ValueError("Enter a number such as 45, without a percent sign.") from exc
        return value

    @model_validator(mode="after")
    def category_requirements(self):
        if self.beverage_type == "distilled_spirits" and not self.abv:
            raise ValueError("Enter the expected alcohol percentage for distilled spirits.")
        if self.imported and not self.country_of_origin:
            raise ValueError("Enter the country of origin for an imported product.")
        return self


class Observation(StrictModel):
    value: str | None
    uncertain: bool
    image_indices: list[int]


class Extraction(StrictModel):
    brand_name: Observation
    class_type: Observation
    alcohol_content: Observation
    net_contents: Observation
    producer_name: Observation
    producer_address: Observation
    country_of_origin: Observation
    warning: Observation
    heading_bold: Literal["yes", "no", "uncertain"]
    body_not_bold: Literal["yes", "no", "uncertain"]
    warning_separate: Literal["yes", "no", "uncertain"]
    warning_legible: Literal["yes", "no", "uncertain"]
    issues: list[str]


class Check(StrictModel):
    key: str
    label: str
    expected: str
    observed: str
    status: Literal["match", "review", "not_checked"]
    reason: str
    image_indices: list[int] = Field(default_factory=list)


class Verification(StrictModel):
    application_id: str
    mode: Literal["demo", "openai"]
    model: str
    checks: list[Check]
    matches: int
    reviews: int
    not_checked: int
    elapsed_ms: float
    extraction_ms: float
    target_ms: int = 5000
    target_met: bool | None
    issues: list[str]
    filenames: list[str]
    policy_version: str
    warning_diff: list[dict[str, str]]
    limitations: list[str]
