from crewai import Task
from debate.agents import bullish_researcher, bearish_researcher, trader_agent
from textwrap import dedent

class TradingTasks:
    def bullish_analysis_task(self, inputs=None, previous_round=None, bearish_analysis=None):
        """创建看多分析任务
        
        Args:
            inputs: 输入数据
            previous_round: 前一轮次号码（如果有）
            bearish_analysis: 前一轮看空分析（如果有）
            
        Returns:
            配置好的Task对象
        """
        description = dedent(f"""
            Analyze the inputs content and identify all bullish signals that suggest buying. 
            Focus on growth potential, positive indicators, and favorable market conditions.
            Then, counter any bearish arguments with solid reasoning.
            
            Here is the inputs to analyze:
            {inputs}
            """)
            
        # 如果有前一轮分析，添加相关内容
        if previous_round and bearish_analysis:
            description += dedent(f"""
                
                Your analysis should also address the following bearish analysis from round {previous_round}:
                
                BEARISH ANALYSIS:
                {bearish_analysis}
                """)
            
        description += dedent("""
            
            Your analysis should cover:
            1. Key bullish signals in the inputs
            2. Historical precedents that support your view
            3. Potential catalysts for upside
            4. Valuation considerations that support buying
            5. Counterarguments to bearish concerns
            
            Your analysis must be structured, data-driven, and persuasive. Include specific facts and figures where possible.
            
            FORMAT YOUR RESPONSE AS FOLLOWS:
            
            ## BULLISH ANALYSIS
            [Your detailed bullish analysis with specific points]
            
            ## COUNTER TO BEARISH PERSPECTIVE
            [Your specific counters to bearish arguments]
            
            ## CONCLUSION
            [Your final recommendation with conviction level]
            """)
            
        return Task(
            description=description,
            expected_output="A structured bullish analysis highlighting buying opportunities with strong counters to bearish arguments",
            agent=bullish_researcher,
            output_file="debate/output/bullish_analysis.txt",
        )
    
    def bearish_analysis_task(self, inputs=None, previous_round=None, bullish_analysis=None):
        """创建看空分析任务
        
        Args:
            inputs: 输入数据
            previous_round: 前一轮次号码（如果有）
            bullish_analysis: 前一轮看多分析（如果有）
            
        Returns:
            配置好的Task对象
        """
        description = dedent(f"""
            Analyze the inputs content and identify all bearish signals that suggest caution or selling.
            Focus on risks, negative indicators, and unfavorable market conditions.
            Then, counter any bullish arguments with solid reasoning.
            
            Here is the inputs content to analyze:
            {inputs}
            """)
            
        # 如果有前一轮分析，添加相关内容
        if previous_round and bullish_analysis:
            description += dedent(f"""
                
                Your analysis should also address the following bullish analysis from round {previous_round}:
                
                BULLISH ANALYSIS:
                {bullish_analysis}
                """)
            
        description += dedent("""
            
            Your analysis should cover:
            1. Key risk factors in the inputs
            2. Historical precedents that support your cautious view
            3. Potential catalysts for downside
            4. Valuation considerations that suggest overvaluation
            5. Counterarguments to bullish optimism
            
            Your analysis must be structured, data-driven, and persuasive. Include specific facts and figures where possible.
            
            FORMAT YOUR RESPONSE AS FOLLOWS:
            
            ## BEARISH ANALYSIS
            [Your detailed bearish analysis with specific points]
            
            ## COUNTER TO BULLISH PERSPECTIVE
            [Your specific counters to bullish arguments]
            
            ## CONCLUSION
            [Your final recommendation with conviction level]
            """)
            
        return Task(
            description=description,
            expected_output="A structured bearish analysis highlighting risks with strong counters to bullish arguments",
            agent=bearish_researcher,
            output_file="debate/output/bearish_analysis.txt",
        )
    
    def trader_decision_task(self, inputs=None, previous_round=None, bullish_analysis=None, bearish_analysis=None):
        """创建交易决策任务
        
        Args:
            inputs: 输入数据
            previous_round: 前一轮次号码（如果有）
            bullish_analysis: 看多分析（如果有）
            bearish_analysis: 看空分析（如果有）
            
        Returns:
            配置好的Task对象
        """
        description = dedent(f"""
            Evaluate the debate between bullish and bearish researchers and make a trading decision.
            
            Here is the inputs content that was analyzed:
            {inputs}
            """)
            
        # 添加轮次信息（如果有）
        if previous_round:
            description += dedent(f"""
                
                This is round {previous_round} of the debate.
                """)
            
        # 添加分析内容（如果有）
        if bullish_analysis:
            description += dedent(f"""
                
                BULLISH ANALYSIS:
                {bullish_analysis}
                """)
            
        if bearish_analysis:
            description += dedent(f"""
                
                BEARISH ANALYSIS:
                {bearish_analysis}
                """)
        
        description += dedent("""
            
            Assign a score from 0 to 10, where:
            - 0-1: Strong sell recommendation
            - 2-4: Moderate sell/avoid recommendation
            - 5: Neutral stance
            - 6-8: Moderate buy recommendation
            - 9-10: Strong buy recommendation
            
            Your evaluation should:
            1. Assess the strength of arguments from both sides
            2. Identify which side presented more compelling evidence
            3. Consider the quality of counterarguments
            4. Evaluate risk/reward ratio based on both perspectives
            5. Determine appropriate position sizing if any
            
            Note: Score >= 9 or <= 1 should result in immediate action. Score >= 6 after all debate rounds suggests buying.
            
            IMPORTANT: You MUST use EXACTLY THE FORMAT below, including the headings and exact formatting of the Score line.
            
            FORMAT YOUR RESPONSE AS FOLLOWS:
            
            ## ASSESSMENT OF BULLISH ARGUMENTS
            [Evaluation of key bullish points]
            
            ## ASSESSMENT OF BEARISH ARGUMENTS
            [Evaluation of key bearish points]
            
            ## DECISION RATIONALE
            [Detailed explanation of your decision-making process]
            
            ## SCORE AND RECOMMENDATION
            Score: [NUMBER]
            Action: [BUY/SELL/HOLD]
            Conviction: [HIGH/MEDIUM/LOW]
            Sizing: [FULL/HALF/QUARTER] position
            """)
            
        return Task(
            description=description,
            expected_output="A structured decision with numeric score, clear rationale, and specific action recommendation",
            agent=trader_agent,
            output_file="debate/output/trader_decision.txt",
        )


# 创建任务生成器实例
trading_tasks = TradingTasks()

# 导出基础任务（用于向后兼容，实际运行时应直接使用TradingTasks实例创建任务）
bullish_analysis_task = trading_tasks.bullish_analysis_task()
bearish_analysis_task = trading_tasks.bearish_analysis_task()
trader_decision_task = trading_tasks.trader_decision_task() 