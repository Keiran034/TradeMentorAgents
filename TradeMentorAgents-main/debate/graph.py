from typing import Dict, Any, Optional, List, TypedDict, Literal, Union, cast
import json

from langgraph.graph import StateGraph, START, END

from debate.state import State, initialize_state, InputData
from debate.nodes import Nodes

class TradingWorkflow:
    def __init__(self, debug: bool = False, max_rounds: int = 4):
        """初始化交易决策工作流
        
        Args:
            debug: 是否启用调试模式
            max_rounds: 最大辩论回合数
        """
        self.debug = debug
        self.max_rounds = max_rounds
        
        # 初始化节点处理类
        self.nodes = Nodes(debug=debug)
        
        # 创建状态图
        workflow = StateGraph(State)
        
        # 添加节点
        workflow.add_node("prepare_inputs", self.nodes.prepare_inputs)
        workflow.add_node("run_analysis_round", self.nodes.run_analysis_round)
        workflow.add_node("finalize_decision", self.nodes.finalize_decision)
        
        # 设置入口点
        workflow.set_entry_point("prepare_inputs")
        
        # 添加边和条件边
        workflow.add_edge("prepare_inputs", "run_analysis_round")
        workflow.add_conditional_edges(
            "run_analysis_round",
            self.nodes.check_decision_criteria,
            {
                "continue": "run_analysis_round",
                "end": "finalize_decision"
            }
        )
        workflow.add_edge("finalize_decision", END)
        
        # 编译工作流
        self.app = workflow.compile()
    
    def run(self, inputs: List[InputData]) -> Dict[str, Any]:
        """运行交易决策工作流
        
        Args:
            inputs: 输入数据列表，每个元素包含类型、数据和日期
            
        Returns:
            最终状态
        """
        # 初始化状态
        state = initialize_state(inputs)
            
        if self.debug:
            print("开始运行交易决策工作流")
            
        # 运行工作流
        result = self.app.invoke(state)
        
        if self.debug:
            print("交易决策工作流完成")
            
        return result


def run_trading_workflow(
    inputs: List[InputData], 
    max_rounds: int = 4,
    debug: bool = False
) -> Dict[str, Any]:
    """运行交易决策工作流
    
    Args:
        inputs: 输入数据列表，每个元素包含类型、数据和日期
        max_rounds: 最大辩论回合数
        debug: 是否启用调试模式
        
    Returns:
        最终状态
    """
    workflow = TradingWorkflow(debug=debug, max_rounds=max_rounds)
    return workflow.app.invoke(initialize_state(inputs)) 