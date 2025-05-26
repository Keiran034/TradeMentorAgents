from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict, List
import os
import re

# Set environment variables
os.environ["OPENAI_API_KEY"] = "dummy_key"  # Required by langchain-openai but not used with Ollama

# Configure LLM - Fix model provider specification
llm = ChatOpenAI(
    model="ollama/llama3.2:latest",  # Correctly specify ollama as the provider
    base_url="http://localhost:11434/v1"
)

# Define Agents with enhanced prompts
bullish_researcher = Agent(
    role='Bullish Investment Analyst',
    goal='Identify compelling buying opportunities based on news and counter bearish arguments with data-driven insights',
    backstory='''You are a former ARK Invest analyst who identified TSLA's 2019 breakout through supply chain analysis. 
    With 15+ years of experience in growth investing, you've developed an eye for spotting asymmetric risk/reward scenarios 
    with >3:1 payoff potential. You're known for your conviction and ability to see long-term value where others see risk.
    
    Your approach:
    1. You focus on positive signals in news and market data
    2. You identify companies with transformative technologies or market positions
    3. You can recognize patterns that suggest significant upside potential
    4. You present arguments with confidence backed by historical precedents
    5. You're skilled at refuting bearish arguments with data-driven counterpoints
    
    While you acknowledge risks, you believe that calculated risk-taking on high-conviction investments is the path to outperformance.''',
    llm=llm,
    verbose=True,
    memory=True,
    allow_delegation=False,
)

bearish_researcher = Agent(
    role='Bearish Risk Analyst',
    goal='Identify potential risks and valuation concerns based on news and challenge bullish narratives with historical precedents',
    backstory='''You are a Lehman Brothers survivor specializing in counterparty risk analysis during liquidity crunches.
    With 20+ years of experience navigating multiple market cycles, you've developed a finely-tuned radar for detecting 
    market euphoria, valuation disconnects, and hidden risks that others overlook.
    
    Your approach:
    1. You focus on risk factors often ignored in bullish narratives
    2. You examine valuation metrics with historical context
    3. You identify potential competitive threats and market shifts
    4. You present arguments with precision backed by historical parallels
    5. You're skilled at exposing the flaws in overly optimistic projections
    
    While you acknowledge growth opportunities, you believe that risk management and avoiding permanent capital loss 
    are essential to long-term investment success.''',
    llm=llm,
    verbose=True,
    memory=True,
    allow_delegation=False,
)

trader_agent = Agent(
    role='Trading Decision Strategist',
    goal='Synthesize conflicting analyses to make optimal risk-adjusted trading decisions',
    backstory='''You are a seasoned portfolio manager with experience at Goldman Sachs' SIGMA X trading desk,
    now enhanced with data science expertise. You've developed a systematic approach to evaluating conflicting
    investment theses and making decisive trading calls that balance opportunity and risk.
    
    Your approach:
    1. You objectively evaluate both bullish and bearish arguments
    2. You assign appropriate weights to different factors based on market context
    3. You maintain a probabilistic framework for decision-making
    4. You're skilled at detecting stronger arguments regardless of bias
    5. You translate qualitative insights into quantitative scores
    
    You believe that superior returns come from analytical rigor, emotional discipline, and making
    accurate probability-weighted decisions rather than seeking certainty.''',
    llm=llm,
    verbose=True,
    memory=True,
    allow_delegation=False,
)

# Define Tasks with clearer output structure requirements
bullish_analysis_task = Task(
    description='''Analyze the news content and identify all bullish signals that suggest buying. 
    Focus on growth potential, positive indicators, and favorable market conditions.
    Then, counter any bearish arguments with solid reasoning.
    
    Your analysis should cover:
    1. Key bullish signals in the news
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
    [Your final recommendation with conviction level]''',
    expected_output="A structured bullish analysis highlighting buying opportunities with strong counters to bearish arguments",
    agent=bullish_researcher,
    output_file="bullish_analysis.txt",
)

bearish_analysis_task = Task(
    description='''Analyze the news content and identify all bearish signals that suggest caution or selling.
    Focus on risks, negative indicators, and unfavorable market conditions.
    Then, counter any bullish arguments with solid reasoning.
    
    Your analysis should cover:
    1. Key risk factors in the news
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
    [Your final recommendation with conviction level]''',
    expected_output="A structured bearish analysis highlighting risks with strong counters to bullish arguments",
    agent=bearish_researcher,
    output_file="bearish_analysis.txt",
)

trader_decision_task = Task(
    description='''Evaluate the debate between bullish and bearish researchers and make a trading decision.
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
    Sizing: [FULL/HALF/QUARTER] position''',
    expected_output="A structured decision with numeric score, clear rationale, and specific action recommendation",
    agent=trader_agent,
    output_file="trader_decision.txt",
)

# Create LangGraph nodes
class State(TypedDict):
    news: Dict
    bullish_analysis: str
    bearish_analysis: str
    trader_score: int
    debate_round: int
    decision: str

class Nodes:
    def __init__(self):
        print("Initializing Trading Analysis Workflow")
    
    def get_news(self, state: State) -> State:
        """Fetch news data"""
        print("Fetching news data...")
        news = {
            'title': 'Jim Cramer Says "You Bet Against NVIDIA Corporation (NVDA) At Your Own Peril"',
            'url': 'https://finance.yahoo.com/news/jim-cramer-says-bet-against-115242723.html',
            'author': 'Syeda Seirut Javed',
            'date': '2025-05-02',
            'content': """We recently published an article titled Jim Cramer Listed 20 Best Performing Stocks of the Last 20 Years. In this article, we are going to take a look at where NVIDIA Corporation (NASDAQ:NVDA) stands against the other stocks.

Discussing two decades of Mad Money, Jim Cramer took a moment to highlight the top-performing stocks since the show's debut.

"This week we're celebrating the show's 20th anniversary, a little over a month late, but better late than never. Given that Mad Money's been on the air for more than two decades now, I think it's worth going over the best-performing stocks during that period."

READ ALSO Jim Cramer Recently Discussed These 9 Stocks and Jim Cramer Commented on These 8 Stocks Recently

He pointed out that while the broader markets have posted impressive long-term gains, the Dow rising 272%, the S&P 500 climbing 358%, and the Nasdaq 100 soaring 1,182%, the show's philosophy has not changed. He said, "I created this show because I believe you can beat the averages by doing the homework and picking great individual stocks." Two decades later, he feels even more strongly about that belief. According to him, investing in high-quality companies with long-term potential can outperform those indices.

"So, looking at every US-listed stock with a market cap of at least $1 billion and putting aside everything that came public after March 14th, 2005, the day of our first show, what are the biggest winners since Mad Money first went on the air? I've gotta tell you what, I love this list."

He also said the results were unexpected and would surprise viewers. Cramer framed these companies as real-world evidence of the show's long-held thesis, that investors who commit to studying individual businesses and hold onto strong performers over time can generate significant returns. Cramer noted that since Mad Money's launch in March 2005, "These winners really represent the core thesis of the show that you can make a killing by picking the right stocks, doing the homework and sticking with the great ones."

"Bottom line: When you look at the 10 best-performing stocks of the last 20-odd years, so many of these were gettable if you simply believed in your ability to pick stocks and stuck with them for the long haul."

Our Methodology
For this article, we compiled a list of 20 stocks that were discussed by Jim Cramer during the episodes of Mad Money aired on April 28 and 29. We listed the stocks in the order that Cramer mentioned them. We also provided hedge fund sentiment for each stock as of the fourth quarter of 2024, which was taken from Insider Monkey's database of over 1,000 hedge funds.

Why are we interested in the stocks that hedge funds pile into? The reason is simple: our research has shown that we can outperform the market by imitating the top stock picks of the best hedge funds. Our quarterly newsletter's strategy selects 14 small-cap and large-cap stocks every quarter and has returned 373.4% since May 2014, beating its benchmark by 218 percentage points (see more details here)."""
        }
        
        state["news"] = news
        state["debate_round"] = 0
        state["trader_score"] = 5  # Neutral starting score
        state["decision"] = ""
        
        print(f"News fetched: {news['title']}")
        return state
    
    def start_debate(self, state: State) -> State:
        """Start a debate round"""
        state["debate_round"] += 1
        print(f"Debate round {state['debate_round']} started")
        
        # Create Crew instance for debate
        crew = Crew(
            agents=[bullish_researcher, bearish_researcher],
            tasks=[bullish_analysis_task, bearish_analysis_task],
            verbose=True,
            process=Process.sequential  # Ensure sequential execution for proper debate flow
        )
        
        # Prepare news context
        news_context = f"""
        # FINANCIAL NEWS ANALYSIS
        
        ## NEWS DETAILS
        Title: {state['news']['title']}
        Date: {state['news']['date']}
        Author: {state['news']['author']}
        Source: {state['news']['url']}
        
        ## CONTENT
        {state['news']['content']}
        """
        
        # If not the first round, include previous analyses
        if state["debate_round"] > 1:
            context = f"""{news_context}
            
            ## PREVIOUS DEBATE ROUND {state['debate_round']-1}
            
            ### PREVIOUS BULLISH ANALYSIS
            {state.get('bullish_analysis', '')}
            
            ### PREVIOUS BEARISH ANALYSIS
            {state.get('bearish_analysis', '')}
            
            ### TRADER ASSESSMENT
            Previous Score: {state['trader_score']}/10
            """
        else:
            context = news_context
        
        # Execute debate tasks
        result = crew.kickoff(
            inputs={
                "news": context,
                "debate_round": state["debate_round"],
                "current_sentiment_score": state["trader_score"]
            }
        )
        
        # Fix: Correctly access results from CrewOutput for newer versions of CrewAI
        # Check if result is a dictionary or has tasks attribute
        if hasattr(result, 'tasks'):
            # New CrewAI output format
            bullish_result = None
            bearish_result = None
            
            # Loop through tasks to find the correct ones by task ID
            for task_output in result.tasks:
                if task_output.task.id == bullish_analysis_task.id:
                    bullish_result = task_output.output
                elif task_output.task.id == bearish_analysis_task.id:
                    bearish_result = task_output.output
            
            state["bullish_analysis"] = bullish_result
            state["bearish_analysis"] = bearish_result
        else:
            # Try dictionary format (older versions or alternative format)
            try:
                state["bullish_analysis"] = result.get("bullish_analysis_task") or result.get(str(bullish_analysis_task.id))
                state["bearish_analysis"] = result.get("bearish_analysis_task") or result.get(str(bearish_analysis_task.id))
            except:
                # Fallback: Try direct attribute access
                state["bullish_analysis"] = getattr(result, str(bullish_analysis_task.id), "No bullish analysis available")
                state["bearish_analysis"] = getattr(result, str(bearish_analysis_task.id), "No bearish analysis available")
        
        return state
    
    def decide_strategy(self, state: State) -> State:
        """Trader evaluates debate results and scores"""
        print("Trader evaluating debate results...")
        
        # Create Crew instance for decision
        crew = Crew(
            agents=[trader_agent],
            tasks=[trader_decision_task],
            verbose=True
        )
        
        # Prepare debate context for trader
        debate_context = f"""
        # INVESTMENT DECISION FRAMEWORK
        
        ## NEWS SUMMARY
        Title: {state['news']['title']}
        Date: {state['news']['date']}
        
        ## DEBATE ROUND {state['debate_round']} OF 4
        
        ### BULLISH ANALYSIS
        {state['bullish_analysis']}
        
        ### BEARISH ANALYSIS
        {state['bearish_analysis']}
        
        ## DECISION PARAMETERS
        - Current Debate Round: {state['debate_round']} of 4
        - Previous Score (if any): {state['trader_score']}
        - Score Range: 0 (Strong Sell) to 10 (Strong Buy)
        - Decision Thresholds:
          * Score ≥ 9: Immediate Buy
          * Score ≤ 1: Immediate Sell
          * After 4 rounds: Score ≥ 6 suggests Buy
          
        IMPORTANT: Your response MUST follow the exact format specified in your instructions, especially the "Score: X" line.
        """
        
        # Execute decision task
        result = crew.kickoff(inputs={"debate": debate_context})
        
        # Fix: Improved result access from CrewOutput
        result_text = ""
        # try:
        #     # 调试输出，查看result对象的类型和内容
        #     print(f"\nResult type: {type(result)}")
        #     print(f"Result attributes: {dir(result)}")
            
        #     if hasattr(result, 'tasks') and result.tasks:
        #         # New CrewAI output format
        #         print(f"Task count: {len(result.tasks)}")
        #         for i, task_output in enumerate(result.tasks):
        #             print(f"Task {i} ID: {task_output.task.id}, trader task ID: {trader_decision_task.id}")
        #             if hasattr(task_output, 'task') and task_output.task.id == trader_decision_task.id:
        #                 if hasattr(task_output, 'output'):
        #                     result_text = task_output.output
        #                     print("Found output via task.id match")
        #                     break
        #     elif hasattr(result, 'raw'):
        #         # Alternative CrewAI format
        #         print("Trying to access 'raw' attribute")
        #         raw_results = result.raw
        #         if isinstance(raw_results, dict):
        #             for key, value in raw_results.items():
        #                 print(f"Key in raw results: {key}")
        #                 if str(trader_decision_task.id) in key or "trader_decision" in key.lower():
        #                     result_text = value
        #                     print(f"Found output via raw key match: {key}")
        #                     break
        #     else:
        #         # Try dictionary format
        #         print("Trying dictionary access")
        #         try:
        #             # 尝试直接访问result中的键
        #             for key in dir(result):
        #                 if not key.startswith('_') and not callable(getattr(result, key)):
        #                     print(f"Checking key: {key}")
                    
        #             result_text = result.get("trader_decision_task") or result.get(str(trader_decision_task.id))
        #             if result_text:
        #                 print("Found output via get() method")
        #         except:
        #             # Fallback
        #             print("Dictionary access failed, trying attribute access")
        #             result_text = getattr(result, str(trader_decision_task.id), "")
        # except Exception as e:
        #     print(f"Error accessing result: {e}")
        
        # 如果所有方法都失败，则尝试访问result的字符串表示
        if not result_text:
            print("All output access methods failed, using result string representation")
            result_text = str(result)
        
        # Print the full text for debugging
        print("\n--- TRADER OUTPUT TEXT ---")
        print(result_text)
        print("-------------------------\n")
        
        # 使用增强的提取函数进行分数提取
        extracted_score = extract_score_from_text(result_text)
        state["trader_score"] = extracted_score
        print(f"Successfully extracted score: {extracted_score}")
        
        # Determine whether to make a decision based on score
        if state["trader_score"] >= 9:
            state["decision"] = "BUY"
            print(f"Decision made: BUY with high conviction (score: {state['trader_score']})")
        elif state["trader_score"] <= 1:
            state["decision"] = "SELL"
            print(f"Decision made: SELL with high conviction (score: {state['trader_score']})")
        elif state["debate_round"] >= 4:
            if state["trader_score"] >= 6:
                state["decision"] = "BUY"
            else:
                state["decision"] = "HOLD/SELL"
            print(f"Final decision after 4 rounds: {state['decision']} with score {state['trader_score']}")
        
        return state

# Create workflow graph
def create_trading_workflow() -> StateGraph:
    """Create trading decision workflow"""
    nodes = Nodes()
    
    # Create workflow graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("get_news", nodes.get_news)
    workflow.add_node("start_debate", nodes.start_debate)
    workflow.add_node("decide_strategy", nodes.decide_strategy)
    
    # Set edges
    workflow.add_edge("get_news", "start_debate")
    workflow.add_edge("start_debate", "decide_strategy")
    
    # Add conditional edge: continue debate if no decision and rounds < 4
    def should_continue_debate(state: State) -> str:
        if state["decision"] or state["debate_round"] >= 4:
            return END
        else:
            return "start_debate"
    
    workflow.add_conditional_edges(
        "decide_strategy",
        should_continue_debate
    )
    
    # Set entry point
    workflow.set_entry_point("get_news")
    
    return workflow

# Run workflow
def run_trading_workflow():
    """Run trading decision workflow"""
    workflow = create_trading_workflow()
    app = workflow.compile()
    
    result = app.invoke({})
    
    print("\n=== Final Result ===")
    print(f"News: {result['news']['title']}")
    print(f"Debate Rounds: {result['debate_round']}")
    print(f"Final Score: {result['trader_score']}/10")
    print(f"Decision: {result['decision']}")
    
    return result

# 改进score提取函数
def extract_score_from_text(text):
    """Enhanced function to extract score from Trader's output text"""
    print("Extracting score from text...")
    if not text or len(text) < 10:
        print("Text is empty or too short")
        return None
    
    print(f"Text snippet to analyze: {text[:200]}...")  # Print first 200 chars for debugging
    
    # Store all potential scores found
    potential_scores = []
    
    # Pattern 1: Look for "Score: X" format (most common)
    pattern1 = r'Score:\s*(\d+)'
    matches = re.findall(pattern1, text, re.IGNORECASE)
    if matches:
        print(f"Found 'Score: X' match: {matches}")
        potential_scores.extend([int(score) for score in matches if 0 <= int(score) <= 10])
    
    # # Pattern 2: Look for "Score of X/10" format
    # pattern2 = r'Score of (\d+)(?:/10)?'
    # matches = re.findall(pattern2, text, re.IGNORECASE)
    # print(f"Pattern 2 matches: {matches}")
    # potential_scores.extend([int(score) for score in matches if 0 <= int(score) <= 10])
    
    # # Pattern 3: Look for "X out of 10" format
    # pattern3 = r'(\d+)\s*(?:out of|\/)\s*10'
    # matches = re.findall(pattern3, text, re.IGNORECASE)
    # print(f"Pattern 3 matches: {matches}")
    # potential_scores.extend([int(score) for score in matches if 0 <= int(score) <= 10])
    
    # # Pattern 4: Look for score after section heading
    # pattern4 = r'(?:##|SCORE)[^\d]*?(\d+)'
    # matches = re.findall(pattern4, text, re.IGNORECASE | re.DOTALL)
    # print(f"Pattern 4 matches: {matches}")
    # potential_scores.extend([int(score) for score in matches if 0 <= int(score) <= 10])

    # # Pattern 5: Direct number after score keyword
    # pattern5 = r'score.*?(\d+)'
    # matches = re.findall(pattern5, text, re.IGNORECASE)
    # print(f"Pattern 5 matches: {matches}")
    # potential_scores.extend([int(score) for score in matches if 0 <= int(score) <= 10])
    
    # # Pattern 6: Just look for any number between 0-10 in the "SCORE AND RECOMMENDATION" section
    # pattern6 = r'SCORE AND RECOMMENDATION[^0-9]*(\d+)'
    # matches = re.findall(pattern6, text, re.IGNORECASE | re.DOTALL)
    # print(f"Pattern 6 matches: {matches}")
    # potential_scores.extend([int(score) for score in matches if 0 <= int(score) <= 10])
    
    # If we found any valid scores, return the first one
    if potential_scores:
        print(f"Extracted score(s): {potential_scores}, using {potential_scores[0]}")
        return potential_scores[0]
    
    print("No score found through regex patterns.")
    return None

if __name__ == "__main__":
    run_trading_workflow() 