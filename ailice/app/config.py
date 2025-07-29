from typing import Dict, List, Optional, Any, Union, Annotated, Literal
from pydantic import BaseModel, field_validator, Field
from pydantic.networks import AnyUrl

class AiliceModelConfig(BaseModel):
     formatter: str
     contextWindow: int
     systemAsUser: bool
     
class AiliceWebProviderConfig(BaseModel):
    modelWrapper: str
    apikey: Optional[str] = None
    baseURL: Optional[Union[AnyUrl, str]] = None
    modelList: dict[str, AiliceModelConfig]
    
    @field_validator('baseURL')
    def validate_base_url(cls, v):
        if v == '':
            return v
        return v


class AiliceWebServiceConfig(BaseModel):
    protocol: Literal["aexp", "mcp"]
    addr: AnyUrl
    
class AiliceWebConfig(BaseModel):
    agentModelConfig: dict[str, str]
    models: dict[str, AiliceWebProviderConfig]
    temperature: Annotated[float, Field(ge=0.0)]
    contextWindowRatio: Annotated[float, Field(ge=0.0, le=1.0)]
    
    