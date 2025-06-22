#!/usr/bin/env python3
"""
交易决策工作流 - 简化流式实现
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Generator, Optional, Callable

from .state import State, InputData, initialize_state
from .nodes import Nodes


class TradingWorkflow:
    """
    基于CrewAI的交易决策工作流
    
    整合多个智能体进行交易分析，支持多轮辩论和最终决策生成。
    包含完整的流式输出支持。
    """
    
    def __init__(self, debug: bool = False, max_rounds: int = 4, stream_callback: Optional[Callable] = None):
        """
        初始化交易工作流
        
        Args:
            debug: 是否启用调试模式
            max_rounds: 最大分析轮次
            stream_callback: 流式回调函数
        """
        self.debug = debug
        self.max_rounds = max_rounds
        self.stream_callback = stream_callback
        self.nodes = Nodes(debug=debug, stream_callback=stream_callback)
        self._lock = threading.Lock()
        
        if self.debug:
            print("交易决策工作流初始化完成")
    
    def _safe_stream_callback(self, event_type: str, data: Dict[str, Any]) -> None:
        """线程安全的流式回调函数"""
        if self.stream_callback:
            with self._lock:
                try:
                    enhanced_data = {
                        **data,
                        "timestamp": time.time()
                    }
                    self.stream_callback(event_type, enhanced_data)
                except Exception as e:
                    if self.debug:
                        print(f"流式回调失败: {e}")

    def run(self, inputs: List[InputData]) -> State:
        """
        运行交易决策工作流（非流式版本）
        
        Args:
            inputs: 输入数据列表
                   
        Returns:
            State: 包含完整决策结果的状态字典
        """
        # 发送工作流开始事件
        if self.stream_callback:
            self._safe_stream_callback("workflow_start", {
                "message": "开始运行交易决策工作流",
                "input_count": len(inputs),
                "max_rounds": self.max_rounds
            })

        # 初始化状态
        state = initialize_state(inputs)
            
        if self.debug:
            print("开始运行交易决策工作流")
            
        try:
            # 步骤1: 准备输入
            state = self.nodes.prepare_inputs(state)
            
            # 步骤2: 分析循环
            while True:
                # 执行分析轮次
                state = self.nodes.run_analysis_round(state)
                
                # 检查是否继续
                decision = self.nodes.check_decision_criteria(state)
                if decision == "end":
                    break
            
            # 步骤3: 最终决策
            state = self.nodes.finalize_decision(state)
            
            # 发送工作流完成事件
            if self.stream_callback:
                self._safe_stream_callback("workflow_complete", {
                    "message": "交易决策工作流完成",
                    "final_confidence": state.get("final_confidence", 5.0),
                    "recommendation": state.get("recommendation", "观望"),
                    "total_rounds": len(state.get("debate_rounds", [])),
                    "success": True
                })
            
            if self.debug:
                print("交易决策工作流完成")
                
            return state
            
        except Exception as e:
            # 发送错误事件
            if self.stream_callback:
                self._safe_stream_callback("workflow_error", {
                    "message": "工作流执行失败",
                    "error": str(e),
                    "success": False
                })
            
            if self.debug:
                print(f"工作流执行失败: {e}")
            
            raise

    def stream_run(self, inputs: List[InputData]) -> Generator[Dict[str, Any], None, None]:
        """
        流式运行交易决策工作流
        
        Args:
            inputs: 输入数据列表
            
        Yields:
            Dict[str, Any]: 流式事件，包含event, data, timestamp字段
        """
        # 事件收集器
        events = []
        
        def event_collector(event_type: str, data: Dict[str, Any]) -> None:
            events.append({
                "event": event_type,
                "data": data,
                "timestamp": time.time()
            })
        
        # 创建带事件收集的工作流
        temp_workflow = TradingWorkflow(
            debug=self.debug,
            max_rounds=self.max_rounds,
            stream_callback=event_collector
        )
        
        # 在线程中运行工作流
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(temp_workflow.run, inputs)
        
        # 实时产生事件
        last_event_count = 0
        while not future.done():
            if len(events) > last_event_count:
                for event in events[last_event_count:]:
                    yield event
                last_event_count = len(events)
            time.sleep(0.1)  # 短暂休眠
        
        # 产生剩余事件
        for event in events[last_event_count:]:
            yield event
        
        # 获取最终结果
        try:
            result = future.result()
            yield {
                "event": "workflow_result",
                "data": {
                    "final_result": result,
                    "success": True
                },
                "timestamp": time.time()
            }
        except Exception as e:
            yield {
                "event": "workflow_result", 
                "data": {
                    "error": str(e),
                    "success": False
                },
                "timestamp": time.time()
            }
        finally:
            executor.shutdown(wait=False)


# 便利函数
def stream_trading_workflow(
    inputs: List[InputData], 
    max_rounds: int = 4,
    debug: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """
    便利函数：创建并运行流式交易工作流
    
    Args:
        inputs: 输入数据列表
        max_rounds: 最大分析轮次 
        debug: 是否启用调试模式
        
    Yields:
        Dict[str, Any]: 流式事件
    """
    workflow = TradingWorkflow(debug=debug, max_rounds=max_rounds)
    yield from workflow.stream_run(inputs)


def run_trading_workflow(
    inputs: List[InputData],
    max_rounds: int = 4, 
    debug: bool = False
) -> State:
    """
    便利函数：创建并运行交易工作流（非流式版本）
    
    Args:
        inputs: 输入数据列表
        max_rounds: 最大分析轮次
        debug: 是否启用调试模式
        
    Returns:
        State: 工作流执行结果
    """
    workflow = TradingWorkflow(debug=debug, max_rounds=max_rounds)
    return workflow.run(inputs) 