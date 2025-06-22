from typing import Dict, Any, List, Literal, Union, cast, Optional, Callable
import re
import time
import json
from threading import Lock

from crewai import Crew, Process, Task, Agent
from copy import deepcopy

from debate.state import State, get_sample_inputs
from debate.agents import bullish_researcher, bearish_researcher, trader_agent
from debate.tasks import TradingTasks


class StreamingTaskExecutor:
    """
    流式任务执行器
    
    包装CrewAI的执行逻辑，添加流式事件发送功能。
    使用组合模式而不是继承，避免CrewAI构造函数的兼容性问题。
    """
    
    def __init__(self, stream_callback: Optional[Callable] = None, 
                 task_name: str = "", agent_role: str = ""):
        """
        初始化流式任务执行器
        
        Args:
            stream_callback: 流式回调函数，用于发送事件
                           签名：callback(event_type: str, data: Dict[str, Any]) -> None
            task_name: 当前执行的任务名称，用于事件标识
            agent_role: 当前执行的智能体角色，用于事件标识
        """
        self.stream_callback = stream_callback
        self.task_name = task_name
        self.agent_role = agent_role
        self._lock = Lock()  # 确保线程安全
    
    def _send_stream_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        发送流式事件到客户端
        
        Args:
            event_type: 事件类型标识符
            data: 事件数据字典
            
        Returns:
            None
            
        Note:
            使用线程锁确保并发安全，避免多个智能体同时发送事件时的竞争条件
        """
        if self.stream_callback:
            with self._lock:
                try:
                    # 添加通用的元数据
                    enhanced_data = {
                        **data,
                        "agent_role": self.agent_role,
                        "task_name": self.task_name,
                        "timestamp": time.time()
                    }
                    self.stream_callback(event_type, enhanced_data)
                except Exception as e:
                    # 静默处理流式回调错误，避免影响主要业务逻辑
                    print(f"流式事件发送失败: {e}")
    
    def execute_task(self, agent: Agent, task: Task, debug: bool = False) -> str:
        """
        执行任务并发送流式事件
        
        Args:
            agent: CrewAI智能体实例
            task: CrewAI任务实例
            debug: 是否启用调试模式
            
        Returns:
            str: 任务执行结果
            
        Note:
            在任务执行的关键节点发送流式事件
        """
        # 发送LLM调用开始事件
        self._send_stream_event("llm_call_start", {
            "message": f"开始LLM调用: {self.task_name}",
            "description": task.description[:200] + "..." if len(task.description) > 200 else task.description
        })
        
        # 执行原始的CrewAI逻辑
        try:
            # 创建标准的Crew实例
            crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=debug
            )
            
            result = crew.kickoff()
            result_str = str(result)
            
            # 发送LLM调用完成事件
            result_preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
            self._send_stream_event("llm_call_complete", {
                "message": f"LLM调用完成: {self.task_name}",
                "result_preview": result_preview,
                "result_length": len(result_str)
            })
            
            return result_str
            
        except Exception as e:
            # 发送错误事件
            self._send_stream_event("llm_call_error", {
                "message": f"LLM调用失败: {self.task_name}",
                "error": str(e)
            })
            raise


class Nodes:
    """
    工作流节点处理类
    
    负责处理LangGraph工作流中的各个节点，包括数据准备、分析轮次执行、
    决策标准检查和最终决策确定。支持流式输出和调试模式。
    """
    
    def __init__(self, debug: bool = False, stream_callback: Optional[Callable] = None):
        """
        初始化节点处理类
        
        Args:
            debug: 是否启用调试模式，True时会打印详细的执行信息
            stream_callback: 流式回调函数，用于实时发送执行进度
                           签名：callback(event_type: str, data: Dict[str, Any]) -> None
        """
        self.debug = debug
        self.stream_callback = stream_callback
        self.tasks = TradingTasks()
        
        if self.debug:
            print("节点处理类初始化完成")
    
    def _send_stream_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        安全地发送流式事件
        
        Args:
            event_type: 事件类型，如'task_start', 'task_complete'等
            data: 事件数据字典
            
        Returns:
            None
            
        Note:
            包装了错误处理，确保流式事件发送失败不会影响主要业务逻辑
        """
        if self.stream_callback:
            try:
                enhanced_data = {
                    **data,
                    "timestamp": time.time(),
                    "source": "nodes"
                }
                self.stream_callback(event_type, enhanced_data)
            except Exception as e:
                if self.debug:
                    print(f"流式事件发送失败: {e}")
    
    def _run_task(self, agent: Agent, task: Task, task_name: str) -> str:
        """
        运行单个智能体任务并返回结果
        
        Args:
            agent: CrewAI智能体实例，包含角色、目标和LLM配置
            task: CrewAI任务实例，包含任务描述和期望输出
            task_name: 任务名称，用于日志和流式事件标识
            
        Returns:
            str: 任务执行结果的字符串表示
            
        Note:
            使用StreamingTaskExecutor来支持流式输出，会发送任务开始、
            LLM调用和任务完成等事件
        """
        # 发送任务开始事件
        self._send_stream_event("agent_task_start", {
            "agent_role": agent.role,
            "task_name": task_name,
            "task_description": task.description[:100] + "..." if len(task.description) > 100 else task.description
        })
        
        if self.debug:
            print(f"运行{task_name}...")
            
        # 创建流式任务执行器
        executor = StreamingTaskExecutor(
            stream_callback=self.stream_callback,
            task_name=task_name,
            agent_role=agent.role
        )
        
        # 运行任务并获取结果
        try:
            result = executor.execute_task(agent, task, debug=self.debug)
            
            # 验证结果格式
            output_filename = f"{task_name.lower().replace(' ', '_')}.txt"
            if result and output_filename in result:
                result = f"{task_name}完成，但结果格式不正确"
            
            # 发送任务完成事件
            self._send_stream_event("agent_task_complete", {
                "agent_role": agent.role,
                "task_name": task_name,
                "result": result,
                "result_length": len(result),
                "success": True
            })
            
            if self.debug:
                print(f"{task_name}完成")
                
            return result
            
        except Exception as e:
            # 发送任务失败事件
            self._send_stream_event("agent_task_error", {
                "agent_role": agent.role,
                "task_name": task_name,
                "error": str(e),
                "success": False
            })
            
            if self.debug:
                print(f"{task_name}失败: {e}")
                
            # 重新抛出异常，让上层处理
            raise
    
    # def prepare_news(self, state: State) -> State:
    #     """准备新闻数据，如果没有则使用样例新闻
        
    #     Args:
    #         state: 当前状态
            
    #     Returns:
    #         更新后的状态
    #     """
    #     if not state["news"]:
    #         if self.debug:
    #             print("使用样例新闻进行分析")
    #         state["news"] = get_sample_news()['content']
        
    #     return state
    def prepare_inputs(self, state: State) -> State:
        """
        准备分析输入数据节点
        
        Args:
            state: LangGraph状态字典，包含以下键：
                  - inputs: 输入数据列表，可能为空
                  - 其他工作流状态数据
            
        Returns:
            State: 更新后的状态字典，确保inputs字段包含有效数据
            
        Note:
            如果state["inputs"]为空，则使用样例数据填充。
            这是工作流的入口节点，会发送准备开始和完成事件。
            同时会从输入列表的最后一个元素提取超参数（如debate_round）。
        """
        self._send_stream_event("prepare_inputs_start", {
            "message": "开始准备输入数据",
            "has_inputs": bool(state.get("inputs"))
        })
        
        if not state["inputs"]:
            if self.debug:
                print("使用样例输入进行分析")
            state["inputs"] = get_sample_inputs()
        

        # 提取超参数：检查输入列表的最后一个元素是否为配置字典
        if state["inputs"] and len(state["inputs"]) > 0:
            last_item = state["inputs"][-1]
            
            # 检查最后一个元素是否包含超参数
            if isinstance(last_item, dict) and 'debate_round' in last_item:
                # 提取超参数
                hyperparams = state["inputs"].pop()  # 移除超参数项
                
                # 设置工作流参数
                if 'debate_round' in hyperparams:
                    state['max_rounds'] = hyperparams['debate_round']
                    if self.debug:
                        print(f"从输入中提取到max_rounds: {hyperparams['debate_round']}")
                
                # 可以添加其他超参数的处理
                # if 'stream_mode' in hyperparams:
                #     state['stream_mode'] = hyperparams['stream_mode']
                
                self._send_stream_event("hyperparams_extracted", {
                    "message": "从输入中提取到超参数",
                    "hyperparams": hyperparams,
                    "max_rounds": state.get('max_rounds', 4)
                })
        
        # 确保至少有一些输入数据
        if not state["inputs"]:
            if self.debug:
                print("提取超参数后无输入数据，使用样例数据")
            # 重新获取样例数据，但不包含超参数
            sample_inputs = get_sample_inputs()
            # 过滤掉超参数项
            state["inputs"] = [item for item in sample_inputs if not (isinstance(item, dict) and 'debate_round' in item)]
            
        self._send_stream_event("prepare_inputs_complete", {
            "message": "输入数据准备完成",
            "input_count": len(state["inputs"]) if state["inputs"] else 0,
            "max_rounds": state.get('max_rounds', 4)
        })
        
        return state
    
    def run_analysis_round(self, state: State) -> State:
        """
        执行一轮分析辩论节点
        
        Args:
            state: 当前工作流状态，包含：
                  - inputs: 输入数据列表
                  - debate_rounds: 已完成的辩论轮次列表
                  - analyses: 分析结果列表
                  - trader_scores: 交易员评分列表
            
        Returns:
            State: 更新后的状态，新增：
                  - 一轮辩论结果（看多、看空、交易决策）
                  - 新的交易员评分
                  - 更新的最新决策
                  
        Note:
            每轮包含三个步骤：
            1. 看多分析师分析
            2. 看空分析师分析
            3. 交易员决策
            
            每个步骤都会发送相应的流式事件
        """
        # 获取当前轮次
        current_round = len(state["debate_rounds"])
        
        # 发送轮次开始事件
        self._send_stream_event("analysis_round_start", {
            "round": current_round + 1,
            "total_rounds_so_far": current_round,
            "message": f"开始第{current_round + 1}轮分析"
        })
        
        if self.debug:
            print(f"执行第 {current_round + 1} 轮分析...")
            
        inputs = state["inputs"]
        
        # 第一步：运行看多分析
        # 获取前轮分析（如果有）
        previous_bearish = None
        if current_round > 0:
            previous_bearish = state["analyses"][-1]  # 上一轮的看空分析
            
        # 创建看多任务
        bullish_task = self.tasks.bullish_analysis_task(
            inputs=inputs,
            previous_round=current_round if current_round > 0 else None,
            bearish_analysis=previous_bearish
        )
        
        # 运行看多分析任务
        bullish_result = self._run_task(bullish_researcher, bullish_task, "看多分析")
        state["analyses"].append(bullish_result)
            
        # 第二步：运行看空分析
        # 创建看空任务
        bearish_task = self.tasks.bearish_analysis_task(
            inputs=inputs,
            previous_round=current_round if current_round > 0 else None,
            bullish_analysis=bullish_result  # 使用刚生成的看多分析
        )
        
        # 运行看空分析任务
        bearish_result = self._run_task(bearish_researcher, bearish_task, "看空分析")
        state["analyses"].append(bearish_result)
            
        # 第三步：运行交易决策
        # 创建交易决策任务
        trader_task = self.tasks.trader_decision_task(
            inputs=inputs,
            previous_round=current_round if current_round > 0 else None,
            bullish_analysis=bullish_result,
            bearish_analysis=bearish_result
        )
        
        # 运行交易决策任务
        trader_result = self._run_task(trader_agent, trader_task, "交易决策")
        
        # 添加辩论轮次记录
        round_data = {
            "bullish_analysis": bullish_result,
            "bearish_analysis": bearish_result,
            "trader_decision": trader_result
        }
        state["debate_rounds"].append(round_data)
        
        # 提取分数
        score = self.extract_score_from_decision(trader_result)
        state["trader_scores"].append(score)
        
        # 设置最新决策
        state["decision"] = trader_result
        
        # 发送轮次完成事件
        self._send_stream_event("analysis_round_complete", {
            "round": current_round + 1,
            "bullish_analysis": bullish_result,
            "bearish_analysis": bearish_result,
            "trader_decision": trader_result,
            "score": score,
            "total_rounds": len(state["debate_rounds"]),
            "message": f"第{current_round + 1}轮分析完成，得分：{score}"
        })
        
        if self.debug:
            print(f"第 {current_round + 1} 轮分析完成，得分：{score}")
        
        return state
    
    def extract_score_from_decision(self, decision_text: str) -> float:
        """
        从交易决策文本中提取数值分数
        
        Args:
            decision_text: 交易员生成的决策文本，应包含1-10的评分
            
        Returns:
            float: 提取的分数值，范围[0-10]，如果无法提取则返回5.0（中性）
            
        Note:
            使用多种正则表达式模式来匹配不同格式的分数表示：
            - "Score: X"
            - "X out of 10"
            - "X/10"
            - "SCORE AND RECOMMENDATION"部分的数字
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
        """
        检查辩论终止条件的决策节点
        
        Args:
            state: 当前工作流状态，必须包含：
                  - trader_scores: 交易员评分列表
                  - debate_rounds: 辩论轮次列表
            
        Returns:
            Literal["continue", "end"]: 
                - "continue": 继续下一轮辩论
                - "end": 终止辩论，进入最终决策阶段
                
        Note:
            终止条件（满足任一条件即终止）：
            1. 分数极端（≤1 或 ≥9）：表示观点已经很明确
            2. 达到最大轮次（4轮）：避免无限循环
            
            会发送决策检查事件通知当前的检查结果
        """
        # 发送决策检查开始事件
        self._send_stream_event("decision_criteria_check", {
            "message": "检查辩论终止条件",
            "current_rounds": len(state["debate_rounds"]),
            "has_scores": bool(state.get("trader_scores"))
        })
        
        # 如果没有分数，继续辩论
        if not state["trader_scores"]:
            self._send_stream_event("decision_criteria_result", {
                "decision": "continue",
                "reason": "尚无评分，继续辩论",
                "current_rounds": len(state["debate_rounds"])
            })
            return "continue"
        
        # 获取最新分数
        current_score = state["trader_scores"][-1]
        
        # 如果分数极端（<=1或>=9），立即结束
        if current_score <= 1 or current_score >= 9:
            self._send_stream_event("decision_criteria_result", {
                "decision": "end",
                "reason": f"分数极端 ({current_score})，辩论结束",
                "current_score": current_score,
                "current_rounds": len(state["debate_rounds"])
            })
            if self.debug:
                print(f"根据极端分数 {current_score} 结束辩论")
            return "end"
        
        # 如果已经进行了足够多的回合，结束辩论
        max_rounds = state.get('max_rounds', 4)  # 从状态中获取最大轮次，默认4轮
        if len(state["debate_rounds"]) >= max_rounds:
            self._send_stream_event("decision_criteria_result", {
                "decision": "end", 
                "reason": f"达到最大轮次 ({max_rounds}轮)，辩论结束",
                "current_score": current_score,
                "current_rounds": len(state["debate_rounds"]),
                "max_rounds": max_rounds
            })
            if self.debug:
                print(f"已达到最大辩论回合数({max_rounds})，结束辩论")
            return "end"
        
        # 否则继续辩论
        self._send_stream_event("decision_criteria_result", {
            "decision": "continue",
            "reason": f"当前分数 {current_score}，轮次 {len(state['debate_rounds'])}，继续辩论",
            "current_score": current_score,
            "current_rounds": len(state["debate_rounds"])
        })
        return "continue"
    
    def finalize_decision(self, state: State) -> State:
        """
        确定最终交易决策的收尾节点
        
        Args:
            state: 当前工作流状态，包含：
                  - trader_scores: 所有轮次的交易员评分列表
                  - decision: 最新的交易决策文本
                  - debate_rounds: 所有辩论轮次的完整记录
            
        Returns:
            State: 最终状态，新增：
                  - final_confidence: 最终置信度分数（基于最后一轮分数）
                  - recommendation: 基于分数的具体投资建议
                  
        Note:
            这是工作流的最后一个节点，负责：
            1. 生成最终投资建议（买入/卖出/持有）
            2. 设置置信度分数
            3. 发送工作流完成事件
        """
        # 发送最终决策开始事件
        self._send_stream_event("finalize_decision_start", {
            "message": "开始确定最终交易决策",
            "total_rounds": len(state["debate_rounds"]),
            "total_scores": len(state["trader_scores"])
        })
        
        if not state["trader_scores"]:
            # 没有分析分数的情况
            state["final_confidence"] = 5.0
            state["recommendation"] = "持有/观望"
            
            self._send_stream_event("finalize_decision_complete", {
                "message": "未进行分析，建议观望",
                "final_confidence": 5.0,
                "recommendation": "持有/观望",
                "reason": "无可用分析数据"
            })
            
            if self.debug:
                print("未进行任何分析，无法做出决策")
            return state
        
        # 使用最后一轮的分数作为最终置信度
        final_score = state["trader_scores"][-1]
        state["final_confidence"] = final_score
        
        # 根据分数生成投资建议
        if final_score >= 8:
            state["recommendation"] = "强烈建议: 买入"
        elif final_score >= 6:
            state["recommendation"] = "建议: 买入"
        elif final_score <= 2:
            state["recommendation"] = "强烈建议: 卖出"
        elif final_score <= 4:
            state["recommendation"] = "建议: 卖出"
        else:
            state["recommendation"] = "建议: 持有/观望"
        
        # 发送最终决策完成事件
        self._send_stream_event("finalize_decision_complete", {
            "message": "最终交易决策已确定",
            "final_confidence": final_score,
            "recommendation": state["recommendation"],
            "final_decision": state.get("decision", ""),
            "total_rounds": len(state["debate_rounds"]),
            "all_scores": state["trader_scores"],
            "average_score": sum(state["trader_scores"]) / len(state["trader_scores"])
        })
        
        if self.debug:
            print(f"最终决策分数：{final_score}")
            print(f"投资建议：{state['recommendation']}")
        
        return state 