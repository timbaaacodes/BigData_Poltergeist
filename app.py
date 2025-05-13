import matplotlib
matplotlib.use("Agg")
from flask import Flask, render_template, request, redirect, url_for
import matplotlib.pyplot as plt
import io
import base64
from arquivo_scraper import analyze_search_term
from claude_insights import generate_insights  # Import the Claude insights function

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form.get("searchterm", "").strip()
        if not user_input:
            return render_template("index.html", error="Please enter a search term.")
        return redirect(url_for("chart", term=user_input))
    return render_template("index.html")

@app.route("/chart")
def chart():
    term = request.args.get("term", "")
    if not term:
        return redirect(url_for("index"))
    
    try:
        # Get analysis results from arquivo.pt
        results = analyze_search_term(term, start_year=2000, max_results=300)
        
        # Check if we have an error
        if results.get('error'):
            return render_template("chart.html", 
                                  year_chart_url=None, 
                                  month_chart_url=None,
                                  term=term, 
                                  error=results['error'])
        
        # Extract chart URLs
        year_chart_url = results.get('year_chart')
        month_chart_url = results.get('month_chart')
        
        # Get peak months and content data
        peak_months = results.get('peak_months', {})
        peak_data = results.get('peak_data', {})
        total_results = results.get('total_results', 0)
        
        # Generate AI insights using Claude with content snippets
        ai_insights = generate_insights(term, peak_months, total_results, peak_data)
        
        # If Claude API fails or returns empty insights, fall back to basic insights
        if not ai_insights or ai_insights[0].startswith("Claude API integration is not configured") or ai_insights[0].startswith("Unable to generate AI insights"):
            # Simple insights based on peak data
            insights = []
            if peak_months:
                top_peak = peak_months.get(1, {})
                if top_peak:
                    insights.append(f"The term '{term}' saw its highest popularity in {top_peak['date']} with {top_peak['count']} mentions.")
                
                # Add insight about total results
                if total_results > 0:
                    insights.append(f"Found a total of {total_results} mentions of '{term}' in the web archive.")
                
                # Add more detailed insight if we have multiple peaks
                if len(peak_months) >= 2:
                    insights.append(f"Notable peaks for '{term}' occurred in {', '.join([data['date'] for i, data in peak_months.items()])}")
            
            # If we don't have enough insights, add a generic one
            if len(insights) < 1:
                insights.append(f"The data shows how '{term}' has been documented on the web over time.")
            
            ai_powered = False
        else:
            # Use Claude's AI-generated insights
            insights = ai_insights
            ai_powered = True
        
        return render_template("chart.html", 
                              year_chart_url=year_chart_url,
                              month_chart_url=month_chart_url, 
                              term=term, 
                              insights=insights,
                              total_results=total_results,
                              ai_powered=ai_powered)  # Flag to indicate AI-powered insights
        
    except Exception as e:
        return render_template("chart.html", 
                              year_chart_url=None,
                              month_chart_url=None, 
                              term=term, 
                              error=str(e))

if __name__ == "__main__":
    app.run(debug=True)