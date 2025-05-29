from pydantic import BaseModel
from typing import Optional, Any, Dict, List, TypedDict, Union, Literal

class InputData(BaseModel):
    """输入数据模型"""
    type: str
    date: str
    data: Dict[str, Any]

class State(BaseModel):
    """状态模型"""
    inputs: List[InputData]
    analyses: List[str] = []
    trader_scores: List[float] = []
    debate_rounds: List[Dict[str, str]] = []
    decision: Optional[str] = None

class RequestBase(BaseModel):
    """基础请求模型"""
    request_id: Optional[str] = None
    data: List[InputData]

class ResponseBase(BaseModel):
    """基础响应模型"""
    status: str
    message: str
    data: Optional[State] = None 