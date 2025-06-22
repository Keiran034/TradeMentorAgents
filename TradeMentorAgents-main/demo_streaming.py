#!/usr/bin/env python3
"""
流式输出演示脚本

演示Agent级别的流式输出实现概念，
不依赖于CrewAI等外部库，纯Python实现。
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Generator, Optional, Callable
import json


# 模拟输入数据结构
class InputData:
    def __init__(self, symbol: str, news: List[str], market_data: Dict[str, Any]):
        self.symbol = symbol
        self.news = news
        self.market_data = market_data
        self.timestamp = time.time()


# 模拟状态字典
State = Dict[str, Any]


def get_sample_inputs():
    """获取示例输入数据"""
    return [
        InputData(
            symbol="AAPL",
            news=[
                "苹果公司发布新款iPhone，预计销量将大幅增长",
                "苹果股价受到市场关注，分析师普遍看好"
            ],
            market_data={
                "price": 150.25,
                "volume": 1000000,
                "change": 2.5
            }
        )
    ]


class StreamingAgent:
    """模拟的流式智能体"""
    
    def __init__(self, role: str, stream_callback: Optional[Callable] = None):
        self.role = role
        self.stream_callback = stream_callback
    
    def _send_event(self, event_type: str, data: Dict[str, Any]):
        """发送流式事件"""
        if self.stream_callback:
            self.stream_callback(event_type, {
                **data,
                "agent_role": self.role,
                "timestamp": time.time()
            })
    
    def execute_task(self, task_description: str, inputs: List[InputData]) -> str:
        """执行任务并发送流式事件"""
        # 发送任务开始事件
        self._send_event("agent_task_start", {
            "message": f"{self.role} 开始分析",
            "task_description": task_description
        })
        
        # 模拟LLM调用开始
        self._send_event("llm_call_start", {
            "message": f"{self.role} 开始LLM调用",
            "input_symbols": [inp.symbol for inp in inputs]
        })
        
        # 模拟处理时间
        time.sleep(1.0 + len(inputs) * 0.5)  # 根据输入数量调整处理时间
        
        # 生成模拟结果
        if "看多" in self.role:
            result = f"基于最新消息，{inputs[0].symbol}表现出积极信号，建议关注买入机会。当前价格{inputs[0].market_data['price']}具有上涨潜力。"
            confidence_score = 7.5
        elif "看空" in self.role:
            result = f"从风险控制角度，{inputs[0].symbol}存在一些不确定因素，建议谨慎观望。当前估值可能偏高。"
            confidence_score = 6.0
        else:  # 交易员
            result = f"综合多空双方观点，{inputs[0].symbol}建议采取中性偏多策略，设置止损位并关注市场变化。"
            confidence_score = 7.0
        
        # 发送LLM调用完成事件
        self._send_event("llm_call_complete", {
            "message": f"{self.role} LLM调用完成",
            "result_preview": result[:100] + "..." if len(result) > 100 else result,
            "confidence_score": confidence_score
        })
        
        # 发送任务完成事件
        self._send_event("agent_task_complete", {
            "message": f"{self.role} 分析完成",
            "result": result,
            "confidence_score": confidence_score,
            "success": True
        })
        
        return result


class StreamingTradingWorkflow:
    """流式交易决策工作流"""
    
    def __init__(self, debug: bool = False, max_rounds: int = 4, stream_callback: Optional[Callable] = None):
        self.debug = debug
        self.max_rounds = max_rounds
        self.stream_callback = stream_callback
        self._lock = threading.Lock()
        
        # 创建智能体
        self.bullish_agent = StreamingAgent("看多研究员", stream_callback)
        self.bearish_agent = StreamingAgent("看空研究员", stream_callback)
        self.trader_agent = StreamingAgent("交易员", stream_callback)
        
        if debug:
            print("交易决策工作流初始化完成")
    
    def _safe_stream_callback(self, event_type: str, data: Dict[str, Any]) -> None:
        """线程安全的流式回调"""
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
    
    def run(self, inputs: List[InputData]) -> Dict[str, Any]:
        """运行工作流"""
        # 发送工作流开始事件
        self._safe_stream_callback("workflow_start", {
            "message": "开始运行交易决策工作流",
            "input_count": len(inputs),
            "max_rounds": self.max_rounds
        })
        
        # 初始化状态
        state = {
            "inputs": inputs,
            "debate_rounds": [],
            "trader_scores": [],
            "final_confidence": 5.0,
            "recommendation": "观望"
        }
        
        try:
            # 步骤1: 准备输入
            self._safe_stream_callback("prepare_inputs_start", {
                "message": "开始准备输入数据"
            })
            
            # 模拟数据准备
            time.sleep(0.2)
            
            self._safe_stream_callback("prepare_inputs_complete", {
                "message": "输入数据准备完成",
                "input_count": len(inputs)
            })
            
            # 步骤2: 分析轮次
            for round_num in range(1, min(self.max_rounds + 1, 3)):  # 限制为2轮以加快演示
                self._safe_stream_callback("analysis_round_start", {
                    "message": f"开始第{round_num}轮分析",
                    "round": round_num
                })
                
                # 看多分析
                bullish_result = self.bullish_agent.execute_task(
                    f"对{inputs[0].symbol}进行看多分析", inputs
                )
                
                # 看空分析
                bearish_result = self.bearish_agent.execute_task(
                    f"对{inputs[0].symbol}进行看空分析", inputs
                )
                
                # 交易员决策
                trader_result = self.trader_agent.execute_task(
                    f"基于多空观点对{inputs[0].symbol}做出交易决策", inputs
                )
                
                # 记录本轮结果
                round_data = {
                    "round": round_num,
                    "bullish_analysis": bullish_result,
                    "bearish_analysis": bearish_result,
                    "trader_decision": trader_result,
                    "timestamp": time.time()
                }
                
                state["debate_rounds"].append(round_data)
                state["trader_scores"].append(7.0 + round_num * 0.2)  # 模拟递增的信心分数
                
                self._safe_stream_callback("analysis_round_complete", {
                    "message": f"第{round_num}轮分析完成",
                    "round": round_num,
                    "score": state["trader_scores"][-1]
                })
                
                # 检查是否继续
                if round_num >= 2:  # 演示中限制为2轮
                    self._safe_stream_callback("decision_criteria_result", {
                        "message": "决策检查: 分析充分，准备结束",
                        "decision": "end",
                        "current_round": round_num
                    })
                    break
                else:
                    self._safe_stream_callback("decision_criteria_result", {
                        "message": "决策检查: 继续下一轮分析",
                        "decision": "continue", 
                        "current_round": round_num
                    })
            
            # 步骤3: 最终决策
            self._safe_stream_callback("finalize_decision_start", {
                "message": "开始确定最终交易决策"
            })
            
            # 计算最终结果
            avg_score = sum(state["trader_scores"]) / len(state["trader_scores"])
            if avg_score >= 7.5:
                recommendation = "买入"
            elif avg_score <= 5.5:
                recommendation = "卖出"
            else:
                recommendation = "观望"
            
            state["final_confidence"] = avg_score
            state["recommendation"] = recommendation
            
            self._safe_stream_callback("finalize_decision_complete", {
                "message": "最终交易决策已确定",
                "final_confidence": state["final_confidence"],
                "recommendation": state["recommendation"]
            })
            
            # 发送工作流完成事件
            self._safe_stream_callback("workflow_complete", {
                "message": "交易决策工作流完成",
                "final_confidence": state["final_confidence"],
                "recommendation": state["recommendation"],
                "total_rounds": len(state["debate_rounds"]),
                "success": True
            })
            
            return state
            
        except Exception as e:
            # 发送错误事件
            self._safe_stream_callback("workflow_error", {
                "message": "工作流执行失败",
                "error": str(e),
                "success": False
            })
            raise
    
    def stream_run(self, inputs: List[InputData]) -> Generator[Dict[str, Any], None, None]:
        """流式运行工作流"""
        # 事件收集器
        events = []
        
        def event_collector(event_type: str, data: Dict[str, Any]) -> None:
            events.append({
                "event": event_type,
                "data": data,
                "timestamp": time.time()
            })
        
        # 创建带事件收集的工作流
        temp_workflow = StreamingTradingWorkflow(
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


def main():
    """主演示函数"""
    print("🚀 流式交易决策工作流演示")
    print("=" * 60)
    
    # 获取示例数据
    sample_inputs = get_sample_inputs()
    print(f"输入数据: {sample_inputs[0].symbol} - {len(sample_inputs[0].news)} 条新闻")
    
    # 创建工作流
    workflow = StreamingTradingWorkflow(debug=True, max_rounds=2)
    
    print("\n开始流式执行:")
    print("-" * 40)
    
    # 收集所有事件用于分析
    all_events = []
    start_time = time.time()
    
    try:
        for event in workflow.stream_run(sample_inputs):
            all_events.append(event)
            
            # 实时显示重要事件
            event_time = time.time() - start_time
            event_type = event['event']
            message = event['data'].get('message', 'N/A')
            
            # 格式化输出
            if event_type in ['workflow_start', 'workflow_complete', 'workflow_error']:
                print(f"\n🔥 [{event_time:.2f}s] {event_type.upper()}")
                print(f"   {message}")
            elif event_type.endswith('_start'):
                print(f"\n⏳ [{event_time:.2f}s] {message}")
            elif event_type.endswith('_complete'):
                print(f"✅ [{event_time:.2f}s] {message}")
                if 'confidence_score' in event['data']:
                    print(f"   信心分数: {event['data']['confidence_score']}")
            elif event_type == 'llm_call_start':
                agent_role = event['data'].get('agent_role', 'Unknown')
                print(f"🤖 [{event_time:.2f}s] {agent_role} - {message}")
            elif event_type == 'llm_call_complete':
                agent_role = event['data'].get('agent_role', 'Unknown')
                preview = event['data'].get('result_preview', '')
                print(f"✨ [{event_time:.2f}s] {agent_role} - {message}")
                print(f"   预览: {preview}")
            elif event_type == 'workflow_result':
                success = event['data'].get('success', False)
                if success:
                    result = event['data']['final_result']
                    print(f"\n🎯 最终结果:")
                    print(f"   推荐: {result['recommendation']}")
                    print(f"   信心度: {result['final_confidence']:.1f}/10")
                    print(f"   分析轮次: {len(result['debate_rounds'])}")
    
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        return 1
    
    # 统计分析
    total_time = time.time() - start_time
    print(f"\n📊 执行统计:")
    print(f"   总时间: {total_time:.2f}秒")
    print(f"   总事件数: {len(all_events)}")
    
    # 事件类型统计
    event_types = {}
    for event in all_events:
        event_type = event['event']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print(f"   事件类型分布:")
    for event_type, count in sorted(event_types.items()):
        print(f"     {event_type}: {count}")
    
    print("\n✅ 流式输出演示完成！")
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 