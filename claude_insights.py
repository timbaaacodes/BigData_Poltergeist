import os

# Try to import anthropic, but continue even if it fails
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic module not found. AI insights will not be available.")
    print("To enable AI insights, install the required packages:")
    print("  pip install anthropic python-dotenv")

# Try to import dotenv, but continue even if it fails
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv module not found. Will try to use environment variables directly.")

# Get Claude API key from environment variables
CLAUDE_API_KEY = "PLACE YOUR API KEY HERE"

# Uncomment and replace with your actual API key if needed
# CLAUDE_API_KEY = "sk-ant-your-actual-key-here"

def generate_insights(term, peak_months, total_results, peak_data=None):
    """
    Generate concise insights about why a search term was popular during specific time periods.
    
    Parameters:
    -----------
    term : str
        The search term used
    peak_months : dict
        Dictionary containing peak months data with date and count
    total_results : int
        Total number of results found
    peak_data : dict, optional
        Dictionary containing snippets for each peak period
        
    Returns:
    --------
    list
        List of insights generated
    """
    # Check if we're using Claude API or falling back to basic insights
    use_claude = ANTHROPIC_AVAILABLE and CLAUDE_API_KEY and not (
        CLAUDE_API_KEY.startswith("Claude API integration") or 
        CLAUDE_API_KEY.startswith("Unable to generate")
    )
    
    # If we can't use Claude, generate basic insights
    if not use_claude:
        return generate_basic_insights(term, peak_months, total_results)
    
    # Otherwise, try to use Claude for better insights
    try:
        # Get the insight as a single string
        insight = generate_claude_insights(term, peak_months, total_results, peak_data)
        
        # Return it as a single-item list (for compatibility with the template)
        return [insight]
    except Exception as e:
        print(f"Error calling Claude API: {str(e)}")
        # Fall back to basic insights if Claude fails
        return generate_basic_insights(term, peak_months, total_results)

def generate_basic_insights(term, peak_months, total_results):
    """Generate simple statistical insights without requiring Claude API."""
    insights = []
    
    # Format for 3 separate points
    if peak_months:
        # Get the top peak
        top_peak = peak_months.get(1, {})
        if top_peak:
            period_str = top_peak.get('date', '')
            count = top_peak.get('count', 0)
            
            # Create a formatted insight with header and 3 points
            insight = f"""**Peak in {period_str}**
1. The term '{term}' saw its highest popularity in {period_str} with {count} mentions.
2. Found a total of {total_results} mentions in the web archive.
3. Notable increase compared to typical monthly mentions."""
            
            insights.append(insight)
    else:
        insights.append(f"Found {total_results} mentions of '{term}' in the web archive with no significant peaks.")
    
    return insights

def generate_claude_insights(term, peak_months, total_results, peak_data=None):
    """Generate insights using Claude API with a focus on conciseness."""
    # Initialize the Claude API client
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    
    # Just look at the top peak for conciseness
    if not peak_months:
        return f"Found {total_results} mentions of '{term}' in the web archive."
    
    top_peak_id = 1  # The highest peak
    top_peak = peak_months.get(top_peak_id, {})
    period_str = top_peak.get('date', '')
    count = top_peak.get('count', 0)
    
    # Get snippets for this peak if available
    context_items = []
    if peak_data and top_peak_id in peak_data and 'snippets' in peak_data[top_peak_id]:
        snippets = peak_data[top_peak_id]['snippets']
        for i, snippet in enumerate(snippets[:5], 1):  # Limit to 5 snippets
            snippet_text = f"{snippet.get('title', 'No title')} - {snippet.get('snippet', 'No content')}"
            context_items.append(snippet_text)
    
    # Create a concise prompt
    if context_items:
        snippets_text = "\n".join(context_items)
        prompt = f"""
        The term "{term}" peaked during {period_str} with {count} mentions.
        
        Based on these snippets from {period_str}, briefly explain in 3 short points why this term peaked:
        
        {snippets_text}
        
        Be extremely concise. Your entire response must be under 150 words. Format EXACTLY like this:
        **Peak in {period_str}**
        1. [Short hypothesis why it peaked - one sentence]
        2. [Key event or context - one sentence]
        3. [How the term was discussed - one sentence]
        
        Each numbered point must be a complete sentence but should be as concise as possible.
        """
    else:
        prompt = f"""
        The term "{term}" peaked during {period_str} with {count} mentions.
        
        Based on your knowledge, briefly explain in 3 short points why this term might have peaked during this period.
        
        Be extremely concise. Your entire response must be under 150 words. Format EXACTLY like this:
        **Peak in {period_str}**
        1. [Short hypothesis why it peaked - one sentence]
        2. [Key event or context - one sentence]
        3. [How the term was discussed - one sentence]
        
        Each numbered point must be a complete sentence but should be as concise as possible.
        """
    
    # Call the Claude API for this specific peak
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=800,
        temperature=0.7,
        system="You are a concise historical analyst who explains search trends briefly with minimal text.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract insight
    return response.content[0].text.strip()