# Multi-Agents API

这是 Multi-Agents 项目的 API 服务器。

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

启动服务器后，可以访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 基础端点

- GET /: 欢迎页面
- GET /health: 健康检查
- GET /api/v1/debate/sample: 获取示例输入数据
- POST /api/v1/debate: 运行 debate 工作流
- POST /api/v1/debate/stream: 运行 debate 工作流（流式输出）

### Debate 工作流端点

#### POST /api/v1/debate

运行 debate 工作流的端点。接受任意格式的输入数据，格式应与示例输入数据相似。

示例请求：
```bash
curl -X POST "http://localhost:8000/api/v1/debate" \
     -H "Content-Type: application/json" \
     -d '{
       "inputs": [
         {
           "type": "news",
           "date": "2025-05-02",
           "data": {
             "title": "示例新闻标题",
             "content": "示例新闻内容"
           }
         }
       ]
     }'
```

#### POST /api/v1/debate/stream

运行 debate 工作流的流式端点。实时返回工作流的进展状态。

示例请求：
```bash
curl -X POST "http://localhost:8000/api/v1/debate/stream" \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -d '{
       "inputs": [
         {
           "type": "news",
           "date": "2025-05-02",
           "data": {
             "title": "示例新闻标题",
             "content": "示例新闻内容"
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
// ...

// 最终结果
{"type": "result", "data": {...}}

// 如果发生错误
{"type": "error", "message": "错误信息"}
```

#### GET /api/v1/debate/sample

获取示例输入数据的端点，可用于了解正确的输入格式。

示例请求：
```bash
curl "http://localhost:8000/api/v1/debate/sample"
``` 