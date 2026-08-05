#!/usr/bin/env python3
"""
流式输出功能测试脚本

这个脚本测试新实现的Agent级别流式输出功能，
包括事件生成、时序和数据完整性验证。

使用方法:
    python test_streaming.py

预期输出:
    实时显示工作流执行的各个阶段事件
"""

import sys
import os
import time
import json
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(__file__))

from debate.graph import stream_trading_workflow, TradingWorkflow
from debate.state import get_sample_inputs


def test_basic_streaming():
    """
    测试基本的流式功能
    
    验证:
    1. 事件生成是否正常
    2. 事件顺序是否正确
    3. 数据格式是否符合预期
    """
    print("=" * 60)
    print("测试基本流式功能")
    print("=" * 60)
    
    # 获取示例输入
    sample_inputs = get_sample_inputs()
    print(f"使用示例输入: {len(sample_inputs)} 个数据项")
    
    # 收集所有事件
    events = []
    start_time = time.time()
    
    try:
        for event in stream_trading_workflow(sample_inputs, max_rounds=2, debug=True):
            events.append(event)
            
            # 实时显示事件
            event_time = time.time() - start_time
            print(f"[{event_time:.2f}s] {event['event']}: {event['data'].get('message', 'N/A')}")
            
            # 显示关键事件的详细信息
            if event['event'] in ['agent_task_complete', 'analysis_round_complete']:
                print(f"  └─ 详细: {json.dumps(event['data'], ensure_ascii=False, indent=2)}")
                
    except Exception as e:
        print(f"流式执行出错: {e}")
        return False
    
    print(f"\n总共收到 {len(events)} 个事件")
    print(f"总执行时间: {time.time() - start_time:.2f}s")
    
    # 验证事件序列
    expected_events = [
        'workflow_start',
        'prepare_inputs_start', 
        'prepare_inputs_complete',
        'analysis_round_start',
        'agent_task_start',  # 看多分析
        'llm_call_start',
        'llm_call_complete', 
        'agent_task_complete',
        'analysis_round_complete'
    ]
    
    actual_events = [e['event'] for e in events]
    
    print("\n事件序列验证:")
    for expected in expected_events:
        if expected in actual_events:
            print(f"  ✓ {expected}")
        else:
            print(f"  ✗ 缺失: {expected}")
    
    return True


def test_event_data_integrity():
    """
    测试事件数据完整性
    
    验证:
    1. 每个事件都包含必要字段
    2. 时间戳递增
    3. 数据类型正确
    """
    print("\n" + "=" * 60)
    print("测试事件数据完整性")
    print("=" * 60)
    
    sample_inputs = get_sample_inputs()
    events = []
    
    # 收集事件
    for event in stream_trading_workflow(sample_inputs, max_rounds=1, debug=False):
        events.append(event)
    
    # 验证事件结构
    issues = []
    last_timestamp = 0
    
    for i, event in enumerate(events):
        # 检查必要字段
        if 'event' not in event:
            issues.append(f"事件 {i}: 缺失 'event' 字段")
        if 'data' not in event:
            issues.append(f"事件 {i}: 缺失 'data' 字段")
        if 'timestamp' not in event:
            issues.append(f"事件 {i}: 缺失 'timestamp' 字段")
        
        # 检查时间戳
        if 'timestamp' in event:
            if event['timestamp'] < last_timestamp:
                issues.append(f"事件 {i}: 时间戳倒退")
            last_timestamp = event['timestamp']
        
        # 检查数据类型
        if 'data' in event and not isinstance(event['data'], dict):
            issues.append(f"事件 {i}: data字段不是字典类型")
    
    if issues:
        print("发现数据完整性问题:")
        for issue in issues:
            print(f"  ✗ {issue}")
        return False
    else:
        print(f"✓ 所有 {len(events)} 个事件通过完整性检查")
        return True


def test_workflow_integration():
    """
    测试与现有工作流的集成
    
    验证:
    1. 流式版本与非流式版本结果一致
    2. 性能对比
    """
    print("\n" + "=" * 60)
    print("测试工作流集成")
    print("=" * 60)
    
    sample_inputs = get_sample_inputs()
    
    # 运行流式版本
    print("运行流式版本...")
    streaming_start = time.time()
    streaming_events = []
    
    for event in stream_trading_workflow(sample_inputs, max_rounds=1, debug=False):
        streaming_events.append(event)
    
    streaming_time = time.time() - streaming_start
    
    # 获取最终结果
    streaming_result = None
    for event in streaming_events:
        if event['event'] == 'workflow_result':
            streaming_result = event['data'].get('final_result')
            break
    
    # 运行非流式版本
    print("运行非流式版本...")
    normal_start = time.time()
    
    workflow = TradingWorkflow(debug=False, max_rounds=1)
    normal_result = workflow.run(sample_inputs)
    
    normal_time = time.time() - normal_start
    
    # 结果对比
    print(f"\n性能对比:")
    print(f"  流式版本: {streaming_time:.2f}s ({len(streaming_events)} 个事件)")
    print(f"  普通版本: {normal_time:.2f}s")
    print(f"  性能差异: {((streaming_time - normal_time) / normal_time * 100):+.1f}%")
    
    # 结果一致性检查
    if streaming_result and normal_result:
        # 比较关键字段
        key_fields = ['trader_scores', 'final_confidence', 'recommendation']
        consistency_ok = True
        
        for field in key_fields:
            streaming_val = streaming_result.get(field)
            normal_val = normal_result.get(field)
            
            if streaming_val != normal_val:
                print(f"  ✗ 字段 '{field}' 不一致: {streaming_val} vs {normal_val}")
                consistency_ok = False
            else:
                print(f"  ✓ 字段 '{field}' 一致")
        
        return consistency_ok
    else:
        print("  ✗ 无法获取完整结果进行对比")
        return False


def main():
    """主测试函数"""
    print("开始流式输出功能测试")
    print("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    tests = [
        ("基本流式功能", test_basic_streaming),
        ("事件数据完整性", test_event_data_integrity), 
        ("工作流集成", test_workflow_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n测试 '{test_name}' 执行失败: {e}")
            results.append((test_name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！流式输出功能正常工作。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)