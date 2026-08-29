from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base for HTTP DTOs: camelCase JSON over snake_case Python fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
