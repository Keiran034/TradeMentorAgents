#!/usr/bin/env python3

import os
import sys
import json
from crew.graph import TradingWorkflow

def main():
    # 设置日志等级
    debug = "--debug" in sys.argv
    
    # 如果提供了新闻文件路径，读取新闻内容
    news_text = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        news_file = sys.argv[1]
        try:
            with open(news_file, "r", encoding="utf-8") as f:
                news_text = f.read()
            print(f"读取到新闻内容，长度: {len(news_text)} 字符")
        except Exception as e:
            print(f"读取新闻文件时出错: {e}")
            sys.exit(1)
    
    # 设置最大回合数
    max_rounds = 4  # 默认4轮
    for i, arg in enumerate(sys.argv):
        if arg == "--rounds" and i + 1 < len(sys.argv):
            try:
                max_rounds = int(sys.argv[i + 1])
            except ValueError:
                print(f"无效的回合数: {sys.argv[i + 1]}")
                sys.exit(1)
    
    print(f"开始运行交易工作流 (调试模式: {debug}, 最大回合数: {max_rounds})")
    
    # 初始化工作流
    workflow = TradingWorkflow(debug=debug, max_rounds=max_rounds)
    
    # 准备初始状态
    initial_state = {
        "news": news_text if news_text else "",
        "analyses": [],
        "trader_scores": [],
        "debate_rounds": [],
        "decision": None
    }
    
    # 运行工作流
    result = workflow.app.invoke(initial_state)
    
    # 保存结果到文件
    with open("trading_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 输出决策
    print("\n====== 交易决策 ======")
    print(result["decision"])
    
    # 输出决策建议
    if result["trader_scores"]:
        score = result["trader_scores"][-1]
        print("\n最终得分:", score)
        
        if score >= 8:
            print("\n强烈建议: 买入")
        elif score >= 6:
            print("\n建议: 买入")
        elif score <= 2:
            print("\n强烈建议: 卖出")
        elif score <= 4:
            print("\n建议: 卖出")
        else:
            print("\n建议: 持有/观望")
    
    print(f"\n完整结果已保存至 trading_result.json")

if __name__ == "__main__":
    main() 