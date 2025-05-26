# 交易决策工作流系统

这是一个基于LangGraph和CrewAI框架的多智能体交易决策系统，可以根据输入的金融新闻内容，通过专业智能体的分析和辩论，做出买入或卖出的投资决策建议。

## 系统架构

该系统采用了现代的多智能体协作框架和图状态流设计：

- **LangGraph状态图**：使用有向图模型管理工作流状态和转换逻辑
- **CrewAI智能体**：利用专业化的智能体团队完成不同阶段的分析任务
- **函数式状态处理**：通过纯函数处理状态转换，确保可测试性和可预测性

### LangGraph工作流

工作流基于LangGraph的StateGraph实现，包含以下关键节点：

1. **prepare_news**：准备新闻数据（入口点）
2. **run_analysis_round**：执行分析辩论轮次
3. **check_decision_criteria**：条件决策点（继续辩论或结束）
4. **finalize_decision**：确定最终交易决策

```
prepare_news → run_analysis_round ↔ [条件] → finalize_decision
```

## 项目结构

```
.
├── crew/                  # 核心模块
│   ├── __init__.py        # 包初始化文件
│   ├── agents.py          # 智能体定义
│   ├── graph.py           # LangGraph状态图定义
│   ├── nodes.py           # 图节点处理逻辑
│   ├── state.py           # 状态类型和管理
│   └── tasks.py           # 任务定义
├── run_example.py         # 示例运行脚本
└── README.md              # 项目说明
```

## 智能体团队

系统包含三个专业智能体，各有不同的角色和目标：

1. **看多分析师 (Bullish Researcher)**
   - 专注于寻找投资机会和积极信号
   - 提供成长潜力、市场前景等方面的分析
   - 反驳看空论点

2. **看空分析师 (Bearish Researcher)**
   - 专注于识别风险和潜在问题
   - 提供估值分析、风险评估等
   - 挑战乐观预期和看多论点

3. **交易决策者 (Trader Agent)**
   - 综合分析双方观点，做出平衡的决策
   - 给出0-10分的投资评分和明确的行动建议
   - 权衡风险与收益，确定投资决策

## 环境准备

### 系统要求

- Python 3.8+
- 本地大语言模型（通过Ollama）或OpenAI API接口

### 安装依赖

```bash
# 安装核心依赖
pip install crewai langgraph langchain-openai

# 如果使用本地模型，安装Ollama（以macOS为例）
brew install ollama
# 启动Ollama服务
ollama serve
# 拉取模型（例如llama3）
ollama run llama3.2:latest
```

### 配置

如果使用OpenAI API，需要设置环境变量：

```bash
export OPENAI_API_KEY="你的API密钥"
```

如果使用本地模型，需要在代码中配置：

```python
llm = ChatOpenAI(
    model="ollama/llama3.2:latest",
    base_url="http://localhost:11434/v1"
)
```

## 使用方法

### 运行示例

使用样例新闻运行:

```bash
python run_example.py
```

使用自定义新闻文件运行:

```bash
python run_example.py news.txt
```

开启调试模式:

```bash
python run_example.py --debug
```

设置辩论回合数:

```bash
python run_example.py --rounds 2
```

### 结果解读

系统会给出0-10分的投资评分：

- **0-1**: 强烈卖出建议
- **2-4**: 中度卖出/避免建议
- **5**: 中性立场
- **6-8**: 中度买入建议
- **9-10**: 强烈买入建议

完整结果将保存到`trading_result.json`文件中。

## 代码集成

可以在自己的Python代码中直接使用该工作流:

```python
from crew.graph import TradingWorkflow

# 初始化工作流
workflow = TradingWorkflow(debug=True, max_rounds=2)

# 准备初始状态
initial_state = {
    "news": "您的新闻内容",
    "analyses": [],
    "trader_scores": [],
    "debate_rounds": [],
    "decision": None
}

# 运行工作流
result = workflow.app.invoke(initial_state)

# 获取决策和得分
decision = result["decision"]
score = result["trader_scores"][-1]

print(f"决策得分: {score}")
```

## 核心设计理念

### 状态管理

系统使用TypedDict定义明确的状态结构，确保类型安全：

```python
class State(TypedDict):
    news: str
    analyses: List[str]
    trader_scores: List[float]
    debate_rounds: List[Dict[str, str]]
    decision: Optional[str]
```

### 节点处理

所有节点都是纯函数，接收状态并返回更新后的状态，避免副作用：

```python
def run_analysis_round(state: State) -> State:
    # 处理逻辑
    return updated_state
```

### 任务生成

使用函数式方法动态生成任务，提高灵活性：

```python
def bullish_analysis_task(news_content, previous_round=None, bearish_analysis=None):
    # 创建任务逻辑
    return Task(...)
```

## 自定义和扩展

### 修改智能体行为

编辑`agents.py`文件中的智能体定义：

```python
bullish_researcher = Agent(
    role='Bullish Investment Analyst',
    goal='识别投资机会并反驳看空论点',
    backstory='...',
    llm=llm
)
```

### 调整任务描述

在`tasks.py`中修改任务生成函数：

```python
def trader_decision_task(news_content, bullish_analysis, bearish_analysis):
    # 自定义任务描述和参数
    return Task(...)
```

### 更改工作流逻辑

修改`graph.py`中的条件边和状态转换逻辑：

```python
workflow.add_conditional_edges(
    "run_analysis_round",
    nodes.check_decision_criteria,
    {
        "continue": "run_analysis_round",
        "end": "finalize_decision"
    }
)
```

## 注意事项

- 系统需要较强的语言模型才能获得高质量分析，推荐使用Llama 3或强于它的模型
- 分析质量取决于输入新闻的质量和相关性，高质量的金融新闻会带来更准确的结果
- 投资决策仅供参考，不应完全依赖算法结果进行实际投资
- 如果使用本地模型，确保Ollama服务正在运行且已加载相应模型

## 输入新闻样例

```python
{
  'title': 'Jim Cramer Says "You Bet Against NVIDIA Corporation (NVDA) At Your Own Peril"',
  'url': 'https://finance.yahoo.com/news/jim-cramer-says-bet-against-115242723.html',
  'author': 'Syeda Seirut Javed',
  'date': '2025-05-02',
  'content': """We recently published an article titled Jim Cramer Listed 20 Best Performing Stocks of the Last 20 Years. In this article, we are going to take a look at where NVIDIA Corporation (NASDAQ:NVDA) stands against the other stocks.

  Discussing two decades of Mad Money, Jim Cramer took a moment to highlight the top-performing stocks since the show's debut.

  "This week we're celebrating the show's 20th anniversary, a little over a month late, but better late than never. Given that Mad Money's been on the air for more than two decades now, I think it's worth going over the best-performing stocks during that period."

  READ ALSO Jim Cramer Recently Discussed These 9 Stocks and Jim Cramer Commented on These 8 Stocks Recently

  He pointed out that while the broader markets have posted impressive long-term gains, the Dow rising 272%, the S&P 500 climbing 358%, and the Nasdaq 100 soaring 1,182%, the show's philosophy has not changed. He said, "I created this show because I believe you can beat the averages by doing the homework and picking great individual stocks." Two decades later, he feels even more strongly about that belief. According to him, investing in high-quality companies with long-term potential can outperform those indices.

  "So, looking at every US-listed stock with a market cap of at least $1 billion and putting aside everything that came public after March 14th, 2005, the day of our first show, what are the biggest winners since Mad Money first went on the air? I've gotta tell you what, I love this list."

  He also said the results were unexpected and would surprise viewers. Cramer framed these companies as real-world evidence of the show's long-held thesis, that investors who commit to studying individual businesses and hold onto strong performers over time can generate significant returns. Cramer noted that since Mad Money's launch in March 2005, "These winners really represent the core thesis of the show that you can make a killing by picking the right stocks, doing the homework and sticking with the great ones."

  "Bottom line: When you look at the 10 best-performing stocks of the last 20-odd years, so many of these were gettable if you simply believed in your ability to pick stocks and stuck with them for the long haul."

  Our Methodology
  For this article, we compiled a list of 20 stocks that were discussed by Jim Cramer during the episodes of Mad Money aired on April 28 and 29. We listed the stocks in the order that Cramer mentioned them. We also provided hedge fund sentiment for each stock as of the fourth quarter of 2024, which was taken from Insider Monkey's database of over 1,000 hedge funds.

  Why are we interested in the stocks that hedge funds pile into? The reason is simple: our research has shown that we can outperform the market by imitating the top stock picks of the best hedge funds. Our quarterly newsletter's strategy selects 14 small-cap and large-cap stocks every quarter and has returned 373.4% since May 2014, beating its benchmark by 218 percentage points (see more details here)."""
}
```
