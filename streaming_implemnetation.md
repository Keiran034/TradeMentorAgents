# 交易工作流流式输出实现说明

## 概述

本文档详细说明了为交易决策工作流实现的Agent级别流式输出功能。该实现基于LangGraph框架，提供了细粒度的实时事件流，让前端可以实时显示每个智能体的执行进度。

## 架构设计

### 1. 核心组件

```
TradingWorkflow (graph.py)
├── stream_run()              # 主要流式接口
├── _safe_stream_callback()   # 线程安全的事件发送
└── run()                     # 标准同步执行

Nodes (nodes.py)
├── StreamingCrew             # 支持流式的CrewAI包装
├── _send_stream_event()      # 节点级事件发送
├── prepare_inputs()          # 数据准备节点
├── run_analysis_round()      # 分析轮次节点
├── check_decision_criteria() # 决策检查节点
└── finalize_decision()       # 最终决策节点

FastAPI Routes (base.py)
├── agent_level_debate_stream() # 异步SSE生成器
├── run_debate_stream()         # 主流式端点
├── run_simple_debate_stream()  # 简化流式端点
└── test_stream_endpoint()      # 测试页面
```

### 2. 事件流架构

```
Client (Browser EventSource)
    ↓ HTTP GET/POST
FastAPI StreamingResponse
    ↓ SSE Format
agent_level_debate_stream()
    ↓ Async Queue
TradingWorkflow.stream_run()
    ↓ Thread Pool
Nodes._send_stream_event()
    ↓ Callback Chain
StreamingCrew.kickoff()
    ↓ LLM Calls
Individual Agent Events
```

## 实现详情

### 1. 流式事件类型

#### 工作流级别事件
- `workflow_start`: 工作流开始执行
- `workflow_complete`: 工作流成功完成
- `workflow_error`: 工作流执行错误
- `workflow_result`: 最终结果

#### 节点级别事件
- `prepare_inputs_start/complete`: 输入数据准备
- `analysis_round_start/complete`: 分析轮次执行
- `decision_criteria_check/result`: 决策条件检查
- `finalize_decision_start/complete`: 最终决策生成

#### Agent级别事件
- `agent_task_start`: 智能体任务开始
- `agent_task_complete`: 智能体任务完成
- `llm_call_start`: LLM调用开始
- `llm_call_complete`: LLM调用完成
- `llm_call_error`: LLM调用错误

#### 连接级别事件
- `connection_established`: 流式连接建立
- `heartbeat`: 连接保活心跳
- `stream_error`: 流式处理错误

### 2. 事件数据格式

每个事件遵循统一的格式：

```json
{
  "event": "event_type",
  "data": {
    "message": "人类可读的描述",
    "timestamp": 1234567890.123,
    "agent_role": "看多分析师",
    "task_name": "看多分析",
    "result_preview": "分析结果预览...",
    "score": 7.5,
    "round": 2,
    "...": "其他相关数据"
  },
  "timestamp": 1234567890.123
}
```

### 3. 线程安全设计

#### 问题
- CrewAI是同步执行的
- FastAPI需要异步响应
- 多个智能体可能并发执行

#### 解决方案
```python
# 1. 线程池执行同步工作流
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(workflow.run, inputs)

# 2. 异步队列传递事件
events_queue = asyncio.Queue()
done_event = asyncio.Event()

# 3. 线程安全的事件发送
def sync_runner():
    for event in workflow.stream_run(inputs):
        loop.call_soon_threadsafe(events_queue.put_nowait, event)

# 4. 异步事件消费
while not done_event.is_set():
    event = await asyncio.wait_for(events_queue.get(), timeout=0.5)
    yield f"data: {json.dumps(event)}\n\n"
```

### 4. SSE协议实现

#### 服务器端
```python
async def agent_level_debate_stream(inputs):
    # 标准SSE格式
    yield f"data: {json.dumps(event)}\n\n"
    
    # 设置正确的HTTP头
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "X-Accel-Buffering": "no"  # 禁用nginx缓冲
    }
```

#### 客户端 (JavaScript)
```javascript
const eventSource = new EventSource('/api/v1/debate/stream');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.event) {
        case 'agent_task_start':
            console.log(`${data.data.agent_role}开始执行`);
            break;
        case 'llm_call_complete':
            displayResult(data.data.result_preview);
            break;
        // ... 处理其他事件
    }
};
```

## API接口

### 1. 主要流式端点

#### POST `/api/v1/debate/stream`
接受任意格式的输入数据，返回SSE流。

**请求格式:**
```json
[
    {
        "type": "price_historical",
        "date": "2025-05-02",
        "data": {
            "symbol": "NVDA",
            "prices": [
                {"date": "2025-05-02", "close": 875.32, "volume": 25000000},
                {"date": "2025-05-01", "close": 870.15, "volume": 24500000}
            ]
        }
    },
    {
        "debate_round": 2
    }
]
```

**响应格式:** SSE流
```
data: {"event": "workflow_start", "data": {...}}

data: {"event": "agent_task_start", "data": {...}}

...
```

#### POST `/api/v1/debate/stream-simple`
兼容现有RequestBase格式的流式端点。

**请求格式:**
```json
{
  "data": [
    {"type": "news", "data": "...", "date": "2024-01-01"}
  ]
}
```

### 2. 测试和辅助端点

#### GET `/api/v1/debate/stream-test`
返回HTML测试页面，包含完整的JavaScript客户端实现。

#### GET `/api/v1/debate/sample`
返回示例输入数据，用于测试。

## 使用示例

### 1. Python客户端

```python
from debate.graph import stream_trading_workflow
from debate.state import get_sample_inputs

# 获取示例数据
inputs = get_sample_inputs()

# 流式执行
for event in stream_trading_workflow(inputs, max_rounds=4):
    print(f"[{event['event']}] {event['data'].get('message', '')}")
    
    if event['event'] == 'analysis_round_complete':
        print(f"第{event['data']['round']}轮完成，得分：{event['data']['score']}")
```

### 2. JavaScript前端

```javascript
// 建立SSE连接
const eventSource = new EventSource('/api/v1/debate/stream-simple', {
    method: 'POST',
    body: JSON.stringify({data: sampleInputs}),
    headers: {'Content-Type': 'application/json'}
});

// 处理实时事件
eventSource.addEventListener('analysis_round_complete', (event) => {
    const data = JSON.parse(event.data);
    updateProgressBar(data.data.round, data.data.score);
    displayAnalysis(data.data.bullish_analysis, data.data.bearish_analysis);
});

eventSource.addEventListener('workflow_complete', (event) => {
    const data = JSON.parse(event.data);
    showFinalRecommendation(data.data.recommendation);
    eventSource.close();
});
```

### 3. curl测试

```bash
# 测试流式端点
curl -N -X POST \
  -H "Content-Type: application/json" \
  -d '{"type":"news","data":"测试新闻","date":"2024-01-01"}' \
  http://localhost:8000/api/v1/debate/stream

# 获取示例数据
curl http://localhost:8000/api/v1/debate/sample
```

## 性能考虑

### 1. 内存使用
- 事件队列大小限制
- 及时清理已发送事件
- 避免大对象在事件中传递

### 2. 网络优化
- 事件数据压缩
- 合理的心跳间隔
- 连接超时处理

### 3. 并发处理
- 线程池大小配置
- 事件发送频率控制
- 错误隔离和恢复

## 测试

### 运行测试脚本
```bash
python test_streaming.py
```

### 测试覆盖
- 基本流式功能
- 事件数据完整性
- 与现有工作流的集成
- 性能对比

### 手动测试
1. 访问 `/api/v1/debate/stream-test`
2. 点击"开始流式分析"
3. 观察实时事件流
4. 验证最终结果

## 故障排除

### 常见问题

1. **事件不连续**
   - 检查线程池配置
   - 验证事件队列大小
   - 确认网络连接稳定

2. **连接中断**
   - 检查nginx配置（X-Accel-Buffering）
   - 验证防火墙设置
   - 增加心跳频率

3. **性能问题**
   - 减少事件详细程度
   - 优化LLM调用
   - 调整线程池大小

### 调试技巧

1. **启用调试模式**
```python
workflow = TradingWorkflow(debug=True, max_rounds=4)
```

2. **查看详细日志**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

3. **监控事件流**
```javascript
eventSource.addEventListener('heartbeat', (event) => {
    console.log('Connection alive:', new Date());
});
```

## 扩展建议

### 1. 功能增强
- 支持工作流暂停/恢复
- 实现事件重放功能
- 添加用户认证和授权
- 支持多工作流并行执行

### 2. 性能优化
- 实现事件批处理
- 添加客户端缓存
- 使用WebSocket替代SSE
- 实现负载均衡

### 3. 监控和观测
- 添加指标收集
- 实现分布式追踪
- 集成健康检查
- 添加性能监控

## 总结

本实现提供了完整的Agent级别流式输出功能，具有以下特点：

✅ **细粒度事件**: 支持从工作流到LLM调用的各级别事件
✅ **线程安全**: 正确处理同步/异步混合场景  
✅ **标准协议**: 基于SSE标准，浏览器原生支持
✅ **错误恢复**: 完善的错误处理和恢复机制
✅ **易于集成**: 兼容现有API和数据格式
✅ **测试完备**: 包含自动化测试和手动测试工具

该实现为用户提供了实时的、透明的工作流执行体验，大大提升了系统的可观测性和用户体验。