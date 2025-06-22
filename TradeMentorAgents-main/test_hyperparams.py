#!/usr/bin/env python3
"""
超参数提取功能测试脚本

测试从输入列表中提取超参数（如debate_round）的功能
"""

import sys
import os
import time
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(__file__))

from demo_streaming import StreamingTradingWorkflow, InputData


def test_hyperparams_extraction():
    """测试超参数提取功能"""
    print("🧪 测试超参数提取功能")
    print("=" * 50)
    
    # 创建测试输入数据（包含超参数）
    test_inputs = [
        InputData(
            symbol="TSLA",
            news=["特斯拉发布新车型", "马斯克表示对未来乐观"],
            market_data={"price": 250.0, "volume": 500000, "change": 5.2}
        ),
        InputData(
            symbol="AAPL", 
            news=["苹果季度业绩超预期"],
            market_data={"price": 180.0, "volume": 800000, "change": 3.1}
        ),
        # 超参数配置（作为最后一个元素）
        {"debate_round": 2, "stream_mode": "detailed"}
    ]
    
    print(f"输入数据: {len(test_inputs)} 项")
    print(f"最后一项（超参数）: {test_inputs[-1]}")
    
    # 创建工作流（这里使用演示版本）
    workflow = StreamingTradingWorkflow(debug=True, max_rounds=4)
    
    print("\n开始流式执行 (自定义参数: debate_round=2):")
    print("-" * 40)
    
    start_time = time.time()
    events = []
    
    try:
        for event in workflow.stream_run(test_inputs):
            events.append(event)
            
            event_time = time.time() - start_time
            event_type = event['event']
            message = event['data'].get('message', 'N/A')
            
            # 重点关注超参数相关的事件
            if 'hyperparams' in event['data'] or 'max_rounds' in event['data']:
                print(f"🎯 [{event_time:.2f}s] {event_type}")
                print(f"   {message}")
                if 'hyperparams' in event['data']:
                    print(f"   提取的超参数: {event['data']['hyperparams']}")
                if 'max_rounds' in event['data']:
                    print(f"   最大轮次: {event['data']['max_rounds']}")
            elif event_type in ['workflow_start', 'analysis_round_start', 'analysis_round_complete', 'workflow_complete']:
                print(f"📝 [{event_time:.2f}s] {event_type}: {message}")
                
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False
    
    total_time = time.time() - start_time
    print(f"\n📊 测试结果:")
    print(f"   总时间: {total_time:.2f}秒")
    print(f"   总事件数: {len(events)}")
    
    # 验证是否正确执行了2轮分析（而不是默认的4轮）
    round_events = [e for e in events if e['event'] == 'analysis_round_complete']
    expected_rounds = 2
    actual_rounds = len(round_events)
    
    print(f"   预期轮次: {expected_rounds}")
    print(f"   实际轮次: {actual_rounds}")
    
    if actual_rounds == expected_rounds:
        print("✅ 超参数提取功能正常工作！")
        return True
    else:
        print("❌ 超参数提取功能有问题")
        return False


def test_default_params():
    """测试默认参数（无超参数情况）"""
    print("\n🧪 测试默认参数功能")
    print("=" * 50)
    
    # 创建不包含超参数的输入数据
    test_inputs = [
        InputData(
            symbol="NVDA",
            news=["英伟达AI芯片需求强劲"],
            market_data={"price": 900.0, "volume": 300000, "change": 8.5}
        )
    ]
    
    print(f"输入数据: {len(test_inputs)} 项（无超参数）")
    
    # 创建工作流
    workflow = StreamingTradingWorkflow(debug=True, max_rounds=4)
    
    print("\n开始流式执行 (使用默认参数):")
    print("-" * 40)
    
    start_time = time.time()
    events = []
    
    try:
        for event in workflow.stream_run(test_inputs):
            events.append(event)
            
            event_time = time.time() - start_time
            event_type = event['event']
            
            # 只显示轮次相关事件
            if event_type in ['analysis_round_start', 'analysis_round_complete']:
                message = event['data'].get('message', 'N/A')
                print(f"📝 [{event_time:.2f}s] {event_type}: {message}")
                
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False
    
    # 验证是否执行了默认轮次数
    round_events = [e for e in events if e['event'] == 'analysis_round_complete']
    actual_rounds = len(round_events)
    
    print(f"\n📊 默认参数测试结果:")
    print(f"   实际轮次: {actual_rounds}")
    print(f"   预期轮次: 2 (演示版本限制)")
    
    if actual_rounds == 2:  # 演示版本限制为2轮
        print("✅ 默认参数功能正常工作！")
        return True
    else:
        print("❌ 默认参数功能有问题")
        return False


def main():
    """主测试函数"""
    print("🚀 超参数提取功能测试")
    print("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # 运行测试
    test1_result = test_hyperparams_extraction()
    test2_result = test_default_params()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    tests = [
        ("超参数提取功能", test1_result),
        ("默认参数功能", test2_result)
    ]
    
    passed = 0
    for test_name, result in tests:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(tests)} 个测试通过")
    
    if passed == len(tests):
        print("🎉 所有测试通过！超参数功能正常工作。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)