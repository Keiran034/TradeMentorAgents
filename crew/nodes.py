from typing import Dict, Any, List, Literal, Union, cast
import re

from crewai import Crew, Process, Task, Agent
from copy import deepcopy

from crew.state import State, get_sample_news
from crew.agents import bullish_researcher, bearish_researcher, trader_agent
from crew.tasks import TradingTasks

class Nodes:
    def __init__(self, debug: bool = False):
        """初始化节点处理类
        
        Args:
            debug: 是否启用调试模式
        """
        self.debug = debug
        # 初始化任务生成器
        self.tasks = TradingTasks()
    
    def _run_task(self, agent: Agent, task: Task, task_name: str) -> str:
        """运行单个任务并返回结果
        
        Args:
            agent: 要使用的智能体
            task: 要运行的任务
            task_name: 任务名称（用于调试信息）
            
        Returns:
            任务结果文本
        """
        if self.debug:
            print(f"运行{task_name}...")
            
        # 创建Crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=self.debug
        )
        
        # 运行并获取结果
        result = str(crew.kickoff())
        
        # 检查结果格式
        output_filename = f"{task_name.lower().replace(' ', '_')}.txt"
        if result and output_filename in result:
            result = f"{task_name}完成，但结果格式不正确"
            
        if self.debug:
            print(f"{task_name}完成")
            
        return result
    
    def prepare_news(self, state: State) -> State:
        """准备新闻数据，如果没有则使用样例新闻
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        if not state["news"]:
            if self.debug:
                print("使用样例新闻进行分析")
            state["news"] = get_sample_news()['content']
        
        return state
    
    def run_analysis_round(self, state: State) -> State:
        """运行一轮分析
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        # 获取当前轮次
        current_round = len(state["debate_rounds"])
        
        if self.debug:
            print(f"执行第 {current_round + 1} 轮分析...")
            
        news_content = state["news"]
        
        # 第一步：运行看多分析
        # 获取前轮分析（如果有）
        previous_bearish = None
        if current_round > 0:
            previous_bearish = state["analyses"][-1]  # 上一轮的看空分析
            
        # 创建看多任务
        bullish_task = self.tasks.bullish_analysis_task(
            news_content=news_content,
            previous_round=current_round if current_round > 0 else None,
            bearish_analysis=previous_bearish
        )
        
        # 运行任务并获取结果
        bullish_result = self._run_task(bullish_researcher, bullish_task, "看多分析")
            
        # 存入状态
        state["analyses"].append(bullish_result)
            
        # 第二步：运行看空分析
        # 创建看空任务
        bearish_task = self.tasks.bearish_analysis_task(
            news_content=news_content,
            previous_round=current_round if current_round > 0 else None,
            bullish_analysis=bullish_result  # 使用刚生成的看多分析
        )
        
        # 运行任务并获取结果
        bearish_result = self._run_task(bearish_researcher, bearish_task, "看空分析")
            
        # 存入状态
        state["analyses"].append(bearish_result)
            
        # 第三步：运行交易决策
        # 创建交易决策任务
        trader_task = self.tasks.trader_decision_task(
            news_content=news_content,
            previous_round=current_round if current_round > 0 else None,
            bullish_analysis=bullish_result,
            bearish_analysis=bearish_result
        )
        
        # 运行任务并获取结果
        trader_result = self._run_task(trader_agent, trader_task, "交易决策")
        
        # 添加辩论轮次记录
        state["debate_rounds"].append({
            "bullish_analysis": bullish_result,
            "bearish_analysis": bearish_result,
            "trader_decision": trader_result
        })
        
        # 提取分数
        score = self.extract_score_from_decision(trader_result)
        state["trader_scores"].append(score)
        
        # 设置最新决策
        state["decision"] = trader_result
        
        if self.debug:
            print(f"第 {current_round + 1} 轮分析完成，得分：{score}")
        
        return state
    
    def extract_score_from_decision(self, decision_text: str) -> float:
        """从交易决策文本中提取分数
        
        Args:
            decision_text: 决策文本
            
        Returns:
            提取的分数，如果无法提取则返回5.0（中性）
        """
        if not decision_text:
            if self.debug:
                print("决策文本为空")
            return 5.0
            
        if self.debug:
            print("尝试从以下文本中提取分数：")
            print(decision_text[:200] + "..." if len(decision_text) > 200 else decision_text)
        
        # 存储所有可能的分数
        potential_scores = []
        
        # 模式1：标准格式 "Score: X"
        try:
            lines = decision_text.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("Score:"):
                    # 提取分数值
                    score_part = line.split("Score:")[1].strip()
                    # 取第一个单词并转换为浮点数
                    score = float(score_part.split()[0].replace(',', '.'))
                    potential_scores.append(score)
                    if self.debug:
                        print(f"从'Score:'行提取到分数: {score}")
        except Exception as e:
            if self.debug:
                print(f"标准格式提取出错: {e}")
        
        # 模式2：使用正则表达式寻找"Score: X"或"Score: X/10"格式
        try:
            pattern1 = r'Score:\s*(\d+(?:\.\d+)?)\s*(?:/10)?'
            matches = re.findall(pattern1, decision_text, re.IGNORECASE)
            for match in matches:
                try:
                    score = float(match.replace(',', '.'))
                    if 0 <= score <= 10:
                        potential_scores.append(score)
                        if self.debug:
                            print(f"从正则表达式1提取到分数: {score}")
                except:
                    pass
        except Exception as e:
            if self.debug:
                print(f"正则表达式1提取出错: {e}")
        
        # 模式3：查找"X out of 10"或"X/10"格式
        try:
            pattern2 = r'(\d+(?:\.\d+)?)\s*(?:out of|\/)\s*10'
            matches = re.findall(pattern2, decision_text, re.IGNORECASE)
            for match in matches:
                try:
                    score = float(match.replace(',', '.'))
                    if 0 <= score <= 10:
                        potential_scores.append(score)
                        if self.debug:
                            print(f"从正则表达式2提取到分数: {score}")
                except:
                    pass
        except Exception as e:
            if self.debug:
                print(f"正则表达式2提取出错: {e}")
        
        # 模式4：在"SCORE AND RECOMMENDATION"部分后的第一个数字
        try:
            pattern3 = r'SCORE AND RECOMMENDATION.*?(\d+(?:\.\d+)?)'
            match = re.search(pattern3, decision_text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    score = float(match.group(1).replace(',', '.'))
                    if 0 <= score <= 10:
                        potential_scores.append(score)
                        if self.debug:
                            print(f"从'SCORE AND RECOMMENDATION'部分提取到分数: {score}")
                except:
                    pass
        except Exception as e:
            if self.debug:
                print(f"正则表达式3提取出错: {e}")
        
        # 如果有多个候选分数，优先选择在[0-10]范围内的
        valid_scores = [s for s in potential_scores if 0 <= s <= 10]
        
        if valid_scores:
            # 如果有多个有效分数，取最可能的一个（通常是第一个找到的）
            final_score = valid_scores[0]
            if self.debug:
                print(f"最终选择的分数: {final_score}")
            return final_score
            
        if self.debug:
            print("未能提取到有效分数，使用默认值5.0")
        
        # 默认返回中性分数
        return 5.0
    
    def check_decision_criteria(self, state: State) -> Literal["continue", "end"]:
        """检查是否应该结束辩论
        
        Args:
            state: 当前状态
            
        Returns:
            "continue" 继续辩论，"end" 结束辩论
        """
        # 如果没有分数，继续辩论
        if not state["trader_scores"]:
            return "continue"
        
        # 获取最新分数
        current_score = state["trader_scores"][-1]
        
        # 如果分数极端（<=1或>=9），立即结束
        if current_score <= 1 or current_score >= 9:
            if self.debug:
                print(f"根据极端分数 {current_score} 结束辩论")
            return "end"
        
        # 如果已经进行了足够多的回合，结束辩论
        if len(state["debate_rounds"]) >= 4:
            if self.debug:
                print("已达到最大辩论回合数，结束辩论")
            return "end"
        
        # 否则继续辩论
        return "continue"
    
    def finalize_decision(self, state: State) -> State:
        """最终确定交易决策
        
        Args:
            state: 当前状态
            
        Returns:
            最终状态
        """
        if not state["trader_scores"]:
            if self.debug:
                print("未进行任何分析，无法做出决策")
            return state
        
        final_score = state["trader_scores"][-1]
        
        # 最终决策已经在run_analysis_round中设置
        if self.debug:
            print(f"最终决策分数：{final_score}")
            if final_score >= 8:
                print("强烈建议: 买入")
            elif final_score >= 6:
                print("建议: 买入")
            elif final_score <= 2:
                print("强烈建议: 卖出")
            elif final_score <= 4:
                print("建议: 卖出")
            else:
                print("建议: 持有/观望")
        
        return state 