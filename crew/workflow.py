import os
from typing import List, Dict, Any, Optional
import json
from copy import deepcopy

from crewai import Crew, Process, Task
from langchain_openai import ChatOpenAI

from crew.state import State, initialize_state, get_sample_news
from crew.agents import bullish_researcher, bearish_researcher, trader_agent
from crew.tasks import bullish_analysis_task, bearish_analysis_task, trader_decision_task

class TradingWorkflow:
    def __init__(
        self, 
        state: Optional[State] = None, 
        max_rounds: int = 1,
        debug: bool = False
    ):
        """Initialize the trading workflow.
        
        Args:
            state: Initial state dictionary. If None, a new state will be initialized.
            max_rounds: Maximum number of debate rounds.
            debug: Whether to enable debug mode.
        """
        self.state = state if state else initialize_state()
        self.max_rounds = max_rounds
        self.debug = debug
        
        # 初始化任务，但不立即配置crew
        # 我们将在每轮动态创建任务的副本
        self.base_bullish_task = bullish_analysis_task
        self.base_bearish_task = bearish_analysis_task
        self.base_trader_task = trader_decision_task
    
    def set_news(self, news_text: str) -> None:
        """Set the news text for analysis.
        
        Args:
            news_text: The news text to analyze.
        """
        self.state["news"] = news_text
    
    def extract_score_from_decision(self, decision_text: str) -> float:
        """Extract the score from the trader's decision text.
        
        Args:
            decision_text: The decision text from the trader agent.
            
        Returns:
            The extracted score as a float.
        """
        try:
            # Look for "Score: X" in the decision text
            lines = decision_text.split("\n")
            for line in lines:
                if line.strip().startswith("Score:"):
                    # Extract the score value
                    score_part = line.strip().split("Score:")[1].strip()
                    # Take the first word and convert to float
                    score = float(score_part.split()[0])
                    return score
        except Exception as e:
            if self.debug:
                print(f"Error extracting score: {e}")
            return 5.0  # Default to neutral if extraction fails
        
        # If no score found, default to neutral
        return 5.0
    
    def create_round_tasks(self, round_num: int) -> List[Task]:
        """为当前回合创建任务，并传入必要的上下文
        
        Args:
            round_num: 当前回合数
            
        Returns:
            为本回合配置的任务列表
        """
        news_content = self.state["news"]
        
        # 创建任务的副本，以便我们可以修改它们
        bullish_task = deepcopy(self.base_bullish_task)
        bearish_task = deepcopy(self.base_bearish_task)
        trader_task = deepcopy(self.base_trader_task)
        
        # 更新任务的上下文
        bullish_context = {"NEWS_CONTENT": news_content}
        bearish_context = {"NEWS_CONTENT": news_content}
        trader_context = {"NEWS_CONTENT": news_content}
        
        # 如果不是第一回合，添加前一轮的分析结果
        if round_num > 0:
            bullish_analysis = self.state["analyses"][-2]
            bearish_analysis = self.state["analyses"][-1]
            
            bullish_context["PREVIOUS_ROUND"] = round_num
            bullish_context["BEARISH_ANALYSIS"] = bearish_analysis
            
            bearish_context["PREVIOUS_ROUND"] = round_num
            bearish_context["BULLISH_ANALYSIS"] = bullish_analysis
            
            trader_context["PREVIOUS_ROUND"] = round_num
        
        # 设置任务的上下文
        bullish_task.context = bullish_context
        bearish_task.context = bearish_context
        trader_task.context = trader_context
        
        return [bullish_task, bearish_task, trader_task]
    
    def run(self) -> Dict[str, Any]:
        """Run the trading workflow.
        
        Returns:
            The final state dictionary.
        """
        if not self.state["news"]:
            # Use sample news if none provided
            self.state["news"] = get_sample_news()
        
        current_round = 0
        final_decision = None
        
        while current_round < self.max_rounds:
            if self.debug:
                print(f"执行第 {current_round + 1} 轮分析...")
            
            # 为当前回合创建任务
            round_tasks = self.create_round_tasks(current_round)
            
            # 为当前回合配置crew
            crew = Crew(
                agents=[bullish_researcher, bearish_researcher, trader_agent],
                tasks=round_tasks,
                process=Process.sequential,
                verbose=self.debug,
            )
            
            # 运行本回合的crew
            results = crew.kickoff()
            
            # 处理结果
            self.state["analyses"].append(results[0])  # Bullish analysis
            self.state["analyses"].append(results[1])  # Bearish analysis
            
            decision_text = results[2]
            self.state["debate_rounds"].append({
                "bullish_analysis": results[0],
                "bearish_analysis": results[1],
                "trader_decision": decision_text
            })
            
            # 提取分数
            score = self.extract_score_from_decision(decision_text)
            self.state["trader_scores"].append(score)
            
            # 保存最终决策
            final_decision = decision_text
            
            # 检查是否应该根据分数立即做出决策
            if score >= 9 or score <= 1:
                if self.debug:
                    print(f"根据较极端的分数 {score} 立即做出决策")
                break
                
            current_round += 1
        
        # 设置最终决策
        self.state["decision"] = final_decision
        
        return self.state
        

def run_trading_workflow(
    news_text: Optional[str] = None, 
    max_rounds: int = 1,
    debug: bool = False
) -> Dict[str, Any]:
    """Run the trading workflow with optional news text.
    
    Args:
        news_text: The news text to analyze. If None, sample news will be used.
        max_rounds: Maximum number of debate rounds.
        debug: Whether to enable debug mode.
        
    Returns:
        The final state dictionary.
    """
    workflow = TradingWorkflow(max_rounds=max_rounds, debug=debug)
    
    if news_text:
        workflow.set_news(news_text)
        
    return workflow.run() 