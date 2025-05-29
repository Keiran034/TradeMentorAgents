# Multi-Agents API

这是 Multi-Agents 项目的 API 服务器，用于提供智能交易分析和决策服务。

## 安装

1. 创建虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 运行服务器

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动服务器后，可以访问以下地址查看详细的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点说明

### 基础端点

- `GET /`: 欢迎页面
- `GET /health`: 健康检查
- `GET /api/v1/debate/sample`: 获取示例输入数据
- `POST /api/v1/debate`: 运行 debate 工作流（同步响应）
- `POST /api/v1/debate/stream`: 运行 debate 工作流（流式输出）

### 输入数据格式

API 接受的输入数据格式如下：

```json
{
    "request_id": "optional_request_id",
    "data": [
        {
            "type": "news",
            "date": "2024-03-20",
            "data": {
                "title": "新闻标题",
                "content": "新闻内容"
            }
        }
    ]
}
```

### 使用示例

#### 1. 获取示例输入数据

```bash
curl "http://localhost:8000/api/v1/debate/sample"
```

#### 2. 运行 Debate 工作流（同步）

```bash
curl -X POST "http://localhost:8000/api/v1/debate" \
     -H "Content-Type: application/json" \
     -d '{
       "data": [
         {
           "type": "news",
           "date": "2024-03-20",
           "data": {
             "title": "市场分析新闻",
             "content": "详细的市场分析内容..."
           }
         }
       ]
     }'
```

响应格式：
```json
{
    "status": "success",
    "message": "Debate workflow completed successfully",
    "data": {
        "inputs": [...],
        "analyses": [...],
        "trader_scores": [...],
        "debate_rounds": [...],
        "decision": "最终决策"
    }
}
```

#### 3. 运行 Debate 工作流（流式输出）

```bash
curl -X POST "http://localhost:8000/api/v1/debate/stream" \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -d '{
       "data": [
         {
           "type": "news",
           "date": "2024-03-20",
           "data": {
             "title": "市场分析新闻",
             "content": "详细的市场分析内容..."
           }
         }
       ]
     }'
```

流式响应格式：
```jsonc
// 初始化状态
{"type": "status", "message": "工作流已初始化"}

// 进度更新
{"type": "progress", "round": 1, "total_rounds": 4, "latest_analysis": {...}}
{"type": "progress", "round": 2, "total_rounds": 4, "latest_analysis": {...}}

// 最终结果
{"type": "result", "data": {...}}

// 如果发生错误
{"type": "error", "message": "错误信息"}
```

## 错误处理

API 使用标准的 HTTP 状态码进行错误响应：

- 200: 请求成功
- 400: 请求格式错误
- 500: 服务器内部错误

错误响应格式：
```json
{
    "detail": "错误描述信息"
}
```

## 注意事项

1. 所有时间格式应使用 ISO 格式：YYYY-MM-DD
2. 请确保输入数据的完整性和准确性
3. 对于流式输出，请确保客户端支持 Server-Sent Events (SSE) 