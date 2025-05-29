from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncGenerator, List
from ..models.base import RequestBase, ResponseBase, InputData
from debate.graph import TradingWorkflow
from debate.state import initialize_state
import json
import asyncio

router = APIRouter()

async def debate_stream(inputs: Dict[Any, Any]) -> AsyncGenerator[str, None]:
    """
    生成 debate 工作流的流式输出
    """
    try:
        # 初始化工作流
        workflow = TradingWorkflow(debug=False, max_rounds=4)
        
        # 准备初始状态
        initial_state = initialize_state(inputs)
        
        # 发送初始状态
        yield json.dumps({"type": "status", "message": "工作流已初始化"}) + "\n"
        
        # 创建一个事件循环来运行工作流
        loop = asyncio.get_event_loop()
        
        # 定义进度回调函数
        async def progress_callback(state):
            # 发送当前轮次信息
            if "debate_rounds" in state:
                current_round = len(state["debate_rounds"])
                yield json.dumps({
                    "type": "progress",
                    "round": current_round,
                    "total_rounds": 4,
                    "latest_analysis": state["debate_rounds"][-1] if state["debate_rounds"] else None
                }) + "\n"
        
        # 运行工作流并获取结果
        result = await loop.run_in_executor(None, workflow.app.invoke, initial_state)
        
        # 发送最终结果
        yield json.dumps({"type": "result", "data": result}) + "\n"
        
    except Exception as e:
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"

@router.post("/debate/stream")
async def run_debate_stream(inputs: Dict[Any, Any]):
    """
    运行 debate 工作流的流式端点
    
    接收任意格式的输入数据，并通过工作流处理，实时返回进度
    """
    return StreamingResponse(
        debate_stream(inputs),
        media_type="text/event-stream"
    )

@router.post("/debate")
async def run_debate(request: RequestBase):
    """
    运行 debate 工作流的端点
    
    Args:
        request: 包含输入数据的请求对象
    """
    try:
        # 初始化工作流
        workflow = TradingWorkflow(debug=False, max_rounds=4)
        
        # 准备初始状态
        initial_state = initialize_state(request.data)
        
        # 运行工作流
        result = workflow.app.invoke(initial_state)
        
        return ResponseBase(
            status="success",
            message="Debate workflow completed successfully",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debate/sample")
async def get_sample_inputs():
    """
    获取示例输入数据的端点
    """
    try:
        from debate.state import get_sample_inputs
        return get_sample_inputs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 