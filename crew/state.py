from typing import TypedDict, List, Dict, Any, Optional

# Define state structure for the workflow
class State(TypedDict):
    news: str
    analyses: List[str]
    trader_scores: List[float]
    debate_rounds: List[Dict[str, str]]
    decision: Optional[str]

# Helper functions for state manipulation if needed
def initialize_state() -> State:
    """Initialize the state for the trading workflow.
    
    Returns:
        A new state dictionary with default values.
    """
    return {
        "news": "",
        "analyses": [],
        "trader_scores": [],
        "debate_rounds": [],
        "decision": None
    }

def get_sample_news() -> str:
    """Get a sample news article for testing.
    
    Returns:
        A sample news text.
    """
    return {
            'title': 'Jim Cramer Says "You Bet Against NVIDIA Corporation (NVDA) At Your Own Peril"',
            'url': 'https://finance.yahoo.com/news/jim-cramer-says-bet-against-115242723.html',
            'author': 'Syeda Seirut Javed',
            'date': '2025-05-02',
            'content': """
            We recently published an article titled Jim Cramer Listed 20 Best Performing Stocks of the Last 20 Years. In this article, we are going to take a look at where NVIDIA Corporation (NASDAQ:NVDA) stands against the other stocks.

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