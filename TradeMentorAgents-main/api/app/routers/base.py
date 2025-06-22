from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncGenerator, List
from ..models.base import RequestBase, ResponseBase, InputData
import sys
import os
import json
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from debate.graph import TradingWorkflow, stream_trading_workflow
from debate.state import initialize_state

router = APIRouter()

async def agent_level_debate_stream(inputs: List[Dict[Any, Any]]) -> AsyncGenerator[str, None]:
    """
    生成Agent级别的交易工作流流式输出
    
    Args:
        inputs: 输入数据列表，应包含交易分析所需的数据，最后一个元素可以是超参数配置
        
    Yields:
        str: SSE格式的事件流，每行格式为 "data: {json_event}\n\n"
        
    Note:
        提供细粒度的流式输出，包括：
        - 工作流生命周期事件
        - 每个智能体的任务开始/完成
        - LLM调用的开始/完成  
        - 每轮分析的详细进度
        - 决策检查和最终结果
        
    Events:
        - workflow_start: 工作流开始
        - prepare_inputs_*: 输入准备阶段
        - analysis_round_start: 分析轮次开始
        - agent_task_start: 智能体任务开始
        - llm_call_start: LLM调用开始
        - llm_call_complete: LLM调用完成
        - agent_task_complete: 智能体任务完成
        - analysis_round_complete: 分析轮次完成
        - decision_criteria_*: 决策检查
        - finalize_decision_*: 最终决策
        - workflow_complete: 工作流完成
        - workflow_error: 工作流错误
    """
    try:
        # 发送初始连接确认
        yield f"data: {json.dumps({'event': 'connection_established', 'data': {'message': '流式连接已建立', 'timestamp': time.time()}}, ensure_ascii=False)}\n\n"
        
        # 在线程池中运行流式工作流
        loop = asyncio.get_event_loop()
        
        # 提取最大轮次参数（如果有的话）
        max_rounds = 1  # 默认值
        if isinstance(inputs, list) and len(inputs) > 0:
            # 检查最后一个元素是否包含超参数
            last_item = inputs[-1] if inputs else {}
            if isinstance(last_item, dict) and 'debate_round' in last_item:
                max_rounds = last_item['debate_round']
        elif isinstance(inputs, dict) and 'debate_round' in inputs:
            max_rounds = inputs['debate_round']
        
        # 使用更直接的方法：在executor中运行生成器
        with ThreadPoolExecutor(max_workers=1) as executor:
            # 创建工作流实例，使用提取的max_rounds
            workflow = TradingWorkflow(debug=False, max_rounds=max_rounds)
            
            # 异步迭代流式事件
            async def async_stream_wrapper():
                """异步包装器，将同步生成器转换为异步"""
                for event in workflow.stream_run(inputs):
                    yield event
            
            # 由于我们需要在executor中运行，我们采用不同的策略
            events_queue = asyncio.Queue()
            done_event = asyncio.Event()
            
            def sync_runner():
                """同步运行器，将事件放入队列"""
                try:
                    # 使用已经创建的workflow实例
                    for event in workflow.stream_run(inputs):
                        # 这里我们需要线程安全的方式
                        loop.call_soon_threadsafe(events_queue.put_nowait, event)
                    loop.call_soon_threadsafe(done_event.set)
                except Exception as e:
                    error_event = {
                        "event": "workflow_error",
                        "data": {"error": str(e), "timestamp": time.time()}
                    }
                    loop.call_soon_threadsafe(events_queue.put_nowait, error_event)
                    loop.call_soon_threadsafe(done_event.set)
            
            # 在executor中启动同步运行器
            future = executor.submit(sync_runner)
            
            # 异步产生事件
            while not done_event.is_set():
                try:
                    # 等待事件，设置超时避免无限等待
                    event = await asyncio.wait_for(events_queue.get(), timeout=0.5)
                    # 格式化为SSE格式
                    event_json = json.dumps(event, ensure_ascii=False)
                    yield f"data: {event_json}\n\n"
                except asyncio.TimeoutError:
                    # 超时时发送心跳
                    heartbeat = {
                        "event": "heartbeat",
                        "data": {"timestamp": time.time()}
                    }
                    yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
            
            # 处理队列中剩余的事件
            while not events_queue.empty():
                try:
                    event = events_queue.get_nowait()
                    event_json = json.dumps(event, ensure_ascii=False)
                    yield f"data: {event_json}\n\n"
                except:
                    break
        
    except Exception as e:
        # 发送错误事件
        error_event = {
            "event": "stream_error",
            "data": {
                "error": str(e),
                "message": "流式输出发生错误",
                "timestamp": time.time()
            }
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

@router.post("/debate/stream")
async def run_debate_stream(inputs: List[Dict[Any, Any]]):
    """
    运行交易工作流的Agent级别流式端点
    
    Args:
        inputs: 输入数据列表，包含交易分析所需的数据
               格式: [{"type": "price_historical", "data": "...", "date": "2024-01-01"}, {...}, {"debate_round": 3}]
               
    Returns:
        StreamingResponse: SSE流式响应，包含实时的工作流执行事件
        
    Note:
        这是主要的流式API端点，提供Agent级别的细粒度事件流。
        客户端可以通过EventSource API接收实时更新。
        
    Response Format:
        每个事件的格式为:
        ```
        data: {"event": "event_type", "data": {...}, "timestamp": 1234567890}
        
        ```
    """
    return StreamingResponse(
        agent_level_debate_stream(inputs),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive", 
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )

@router.post("/debate")
async def run_debate(request: RequestBase):
    """
    运行 debate 工作流的端点
    
    Args:
        request: 包含输入数据的请求对象
    """
    try:
        # 提取最大轮次参数
        max_rounds = 4  # 默认值
        inputs = request.data
        if isinstance(inputs, list) and len(inputs) > 0:
            last_item = inputs[-1] if inputs else {}
            if isinstance(last_item, dict) and 'debate_round' in last_item:
                max_rounds = last_item['debate_round']
        
        # 初始化工作流
        workflow = TradingWorkflow(debug=False, max_rounds=max_rounds)
        
        # 运行工作流（使用新的run方法）
        result = workflow.run(inputs)
        
        return ResponseBase(
            status="success",
            message="Debate workflow completed successfully",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debate/stream-simple")
async def run_simple_debate_stream(request: RequestBase):
    """
    简化的流式端点（兼容现有请求格式）
    
    Args:
        request: 标准请求对象，包含data字段
        
    Returns:
        StreamingResponse: SSE流式响应
        
    Note:
        这个端点兼容现有的RequestBase格式，
        是对标准流式端点的包装
    """
    return StreamingResponse(
        agent_level_debate_stream(request.data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/debate/sample")
async def get_sample_inputs():
    """
    获取示例输入数据的端点
    
    Returns:
        Dict: 示例输入数据，可直接用于测试工作流
        
    Note:
        返回的数据格式符合InputData的要求，
        包含type、data和date字段
    """
    try:
        from debate.state import get_sample_inputs
        return get_sample_inputs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/debate/stream-test")
async def test_stream_endpoint():
    """
    流式端点测试页面
    
    Returns:
        str: HTML测试页面，包含JavaScript客户端代码
        
    Note:
        提供一个简单的HTML页面来测试流式功能，
        包含EventSource客户端实现和事件显示
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>交易工作流流式测试</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .event { 
                margin: 10px 0; 
                padding: 10px; 
                border-left: 3px solid #007bff; 
                background-color: #f8f9fa; 
            }
            .error { border-left-color: #dc3545; background-color: #f8d7da; }
            .success { border-left-color: #28a745; background-color: #d4edda; }
            #events { max-height: 600px; overflow-y: auto; }
            button { padding: 10px 20px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>交易工作流流式测试</h1>
        <button onclick="startStream()">开始流式分析</button>
        <button onclick="stopStream()">停止流式</button>
        <button onclick="clearEvents()">清空事件</button>
        
        <h2>实时事件流</h2>
        <div id="events"></div>
        
        <script>
            let eventSource = null;
            
            function startStream() {
                if (eventSource) {
                    eventSource.close();
                }
                
                // 获取示例数据并启动流式分析
                fetch('/api/v1/debate/sample')
                    .then(response => response.json())
                    .then(sampleData => {
                        // 使用POST方式创建EventSource（需要特殊处理）
                        const url = '/api/v1/debate/stream?' + new URLSearchParams({
                            data: JSON.stringify(sampleData)
                        });
                        
                        eventSource = new EventSource(url);
                        
                        eventSource.onmessage = function(event) {
                            try {
                                const data = JSON.parse(event.data);
                                displayEvent(data);
                            } catch (e) {
                                displayEvent({
                                    event: 'parse_error',
                                    data: { error: 'Failed to parse: ' + event.data }
                                });
                            }
                        };
                        
                        eventSource.onerror = function(event) {
                            displayEvent({
                                event: 'connection_error',
                                data: { error: 'Connection error', timestamp: Date.now() / 1000 }
                            }, true);
                        };
                        
                        displayEvent({
                            event: 'client_start',
                            data: { message: '开始连接流式端点...', timestamp: Date.now() / 1000 }
                        });
                    })
                    .catch(error => {
                        displayEvent({
                            event: 'fetch_error', 
                            data: { error: error.message, timestamp: Date.now() / 1000 }
                        }, true);
                    });
            }
            
            function stopStream() {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                    displayEvent({
                        event: 'client_stop',
                        data: { message: '流式连接已关闭', timestamp: Date.now() / 1000 }
                    });
                }
            }
            
            function clearEvents() {
                document.getElementById('events').innerHTML = '';
            }
            
            function displayEvent(event, isError = false) {
                const eventsDiv = document.getElementById('events');
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event' + (isError ? ' error' : '');
                
                if (event.event === 'workflow_complete' || event.event === 'workflow_result') {
                    eventDiv.className += ' success';
                }
                
                const timestamp = new Date(event.data?.timestamp * 1000 || Date.now()).toLocaleTimeString();
                eventDiv.innerHTML = `
                    <strong>[${timestamp}] ${event.event}</strong><br>
                    <pre>${JSON.stringify(event.data, null, 2)}</pre>
                `;
                
                eventsDiv.appendChild(eventDiv);
                eventsDiv.scrollTop = eventsDiv.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content) 