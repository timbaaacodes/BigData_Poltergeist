import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import datetime
import io
import base64
import numpy as np
from matplotlib.ticker import MaxNLocator

def fetch_arquivo_data(term, start_year=2000, max_results=1000, items_per_site=50):
    """
    Fetch data from Arquivo.pt for a given search term
    
    Parameters:
    -----------
    term : str
        The term to search for
    start_year : int
        The year to start searching from
    max_results : int
        Maximum number of results to fetch
    items_per_site : int
        Maximum number of items to return per site
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame containing the search results
    """
    # Maximum items allowed per request
    max_items_per_request = 100
    
    # Create URLs for API requests with pagination
    all_urls = []
    
    # Generate paginated URLs
    for offset in range(0, max_results, max_items_per_request):
        all_urls.append(
            f'https://arquivo.pt/textsearch?q={term}&maxItems={max_items_per_request}&offset={offset}'
            f'&prettyPrint=false&dedupValue={items_per_site}&from={start_year}'
        )
    
    # Process all URLs and collect results
    all_items = []
    
    for url in all_urls:
        try:
            # Fetch data from URL
            response = requests.get(url)
            response.raise_for_status()
            json_data = response.json()
            
            # Extract response items
            if 'response_items' in json_data and json_data['response_items']:
                all_items.extend(json_data['response_items'])
                print(f"Retrieved {len(json_data['response_items'])} items from {url[:50]}...")
            else:
                print(f"No items found for URL: {url[:50]}...")
                
        except Exception as e:
            print(f"Error fetching {url[:50]}...: {str(e)}")
    
    # Convert to DataFrame if we have data
    if all_items:
        df = pd.DataFrame(all_items)
        return df
    else:
        return pd.DataFrame()  # Return empty DataFrame if no results

def parse_tstamp(ts):
    """Convert arquivo.pt timestamp format to datetime, with error handling"""
    if pd.isna(ts):  # Handle NaN/None values
        return None
    
    try:
        ts_str = str(ts).strip()
        # Check exact format - must be 14 digits
        if not ts_str.isdigit() or len(ts_str) != 14:
            return None
        
        year = int(ts_str[0:4])
        month = int(ts_str[4:6])
        day = int(ts_str[6:8])
        hour = int(ts_str[8:10])
        minute = int(ts_str[10:12])
        second = int(ts_str[12:14])
        
        # Validate ranges to avoid invalid dates
        if not (1000 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= 31 and
                0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            return None
            
        return datetime(year, month, day, hour, minute, second)
    except Exception as e:
        print(f"Error parsing timestamp {ts}: {e}")
        return None

def create_visualizations(df, term):
    """
    Create visualizations based on the search data
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing the search results
    term : str
        The search term used
        
    Returns:
    --------
    dict
        Dictionary containing the visualization results
    """
    result = {
        'year_chart': None,
        'month_chart': None,
        'peak_months': {},
        'peak_data': {},  # Will contain the actual content snippets for each peak
        'total_results': len(df),
        'error': None
    }
    
    if 'tstamp' not in df.columns or len(df) == 0:
        result['error'] = "No timestamp data found in search results."
        return result
    
    # Convert tstamp to datetime
    df['datetime'] = df['tstamp'].apply(parse_tstamp)
    
    # Drop rows with invalid dates
    df = df.dropna(subset=['datetime'])
    
    if len(df) == 0:
        result['error'] = "No valid timestamp data found in search results."
        return result
    
    # Generate month chart with enhanced styling
    try:
        # Extract yearmonth for grouping
        df['yearmonth'] = df['datetime'].dt.strftime('%Y-%m')
        
        # Group by yearmonth and count occurrences
        monthly_counts = df.groupby('yearmonth').size().reset_index(name='count')
        
        # Add date column for sorting and plotting
        monthly_counts['date'] = pd.to_datetime(monthly_counts['yearmonth'])
        monthly_counts = monthly_counts.sort_values('date')
        
        # Create clean plot with no styles that might add grid lines
        plt.style.use('default')
        
        # Create figure with high resolution and aspect ratio similar to example
        fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
        
        # Create gradient color for area under the curve
        gradient_color = '#1f77b4'  # Base blue color
        
        # Plot the line with a thicker, professional line style
        line = ax.plot(monthly_counts['date'], monthly_counts['count'], 
                      marker='o', 
                      linestyle='-', 
                      linewidth=3,
                      markersize=8,
                      color=gradient_color)
        
        # Fill area under the curve with gradient
        x = monthly_counts['date']
        y = monthly_counts['count']
        
        # Fill area with alpha gradient
        ax.fill_between(x, 0, y, alpha=0.2, color=gradient_color)
        
        # Set clean white background with no grid
        ax.set_facecolor('white')
        
        # Explicitly turn off the grid
        ax.grid(False)
        
        # Remove all spines except bottom and left
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dddddd')
        ax.spines['bottom'].set_color('#dddddd')
        
        # Set a baseline at y=0
        ax.axhline(y=0, color='#bbbbbb', linestyle='-', alpha=0.3, linewidth=1)
        
        # Format y-axis to use integers only
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        
        # Format the title, labels with professional typography
        #title_font = {'fontsize': 22, 'fontweight': 'bold', 'fontfamily': 'sans-serif'}
        label_font = {'fontsize': 22, 'fontfamily': 'sans-serif'}
        
        #ax.set_title(f"Monthly Popularity of '{term}'", pad=20, **title_font)
        ax.set_xlabel('Date', **label_font)
        ax.set_ylabel('Number of Occurrences', **label_font)
        
        # Format x-axis dates to show year-month
        fig.autofmt_xdate(rotation=45)
        
        # Add annotations for peak points and collect content for those peak periods
        if len(monthly_counts) > 0:
            # Find top 3 points
            top_points = monthly_counts.nlargest(min(3, len(monthly_counts)), 'count')
            peak_months = {}
            
            # Add stylish annotations for peak points
            for i, (_, point) in enumerate(top_points.iterrows()):
                # Create fancy annotation
                ax.annotate(
                    f"{int(point['count'])}",
                    (point['date'], point['count']),
                    textcoords="offset points",
                    xytext=(0, 12),
                    ha='center',
                    fontweight='bold',
                    fontsize=12,
                    bbox=dict(
                        boxstyle="round,pad=0.4",
                        fc='white',
                        ec=gradient_color,
                        alpha=0.9,
                        linewidth=1.5
                    )
                )
                
                # Format date for display
                date_str = point['date'].strftime('%B %Y')
                
                # Store peak data
                peak_months[i+1] = {
                    'date': date_str,
                    'count': int(point['count']),
                    'yearmonth': point['yearmonth']
                }
                
                # Collect content snippets from this peak period
                year_month = point['yearmonth']
                month_df = df[df['yearmonth'] == year_month]
                
                # Extract snippets and URLs for this peak period
                snippets = []
                for _, row in month_df.iterrows():
                    if 'snippets' in row and isinstance(row['snippets'], list) and len(row['snippets']) > 0:
                        snippet_text = row['snippets'][0]  # Take first snippet
                    else:
                        snippet_text = row.get('title', 'No content available')
                    
                    snippet_dict = {
                        'title': row.get('title', 'No title'),
                        'snippet': snippet_text,
                        'url': row.get('linkToArchive', ''),
                        'timestamp': row.get('tstamp', '')
                    }
                    snippets.append(snippet_dict)
                
                # Store snippets for this peak period
                result['peak_data'][i+1] = {
                    'date': date_str,
                    'snippets': snippets[:10]  # Limit to 10 snippets per peak
                }
            
            result['peak_months'] = peak_months
        
        # Enhance overall appearance
        plt.tight_layout()
        
        # Save high-quality figure
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        result['month_chart'] = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
    except Exception as e:
        print(f"Error creating month chart: {str(e)}")
    
    # # Generate year chart with similar enhancements
    # try:
    #     # Extract year for grouping
    #     df['year'] = df['datetime'].dt.year
        
    #     # Group by year and count occurrences
    #     year_counts = df.groupby('year').size().reset_index(name='count')
    #     year_counts = year_counts.sort_values('year')
        
    #     # Create clean plot with no styles that might add grid lines
    #     plt.style.use('default')
        
    #     # Create figure with high resolution and aspect ratio
    #     fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
        
    #     # Define a nice color
    #     bar_color = '#3366cc'
        
    #     # Create bar chart with enhanced styling
    #     bars = ax.bar(
    #         year_counts['year'],
    #         year_counts['count'],
    #         color=bar_color,
    #         alpha=0.8,
    #         width=0.7,
    #         edgecolor=bar_color,
    #         linewidth=1.5
    #     )
        
    #     # Set clean white background with no grid
    #     ax.set_facecolor('white')
        
    #     # Explicitly turn off the grid
    #     ax.grid(False)
        
    #     # Remove top and right spines for cleaner look
    #     ax.spines['top'].set_visible(False)
    #     ax.spines['right'].set_visible(False)
    #     ax.spines['left'].set_color('#dddddd')
    #     ax.spines['bottom'].set_color('#dddddd')
        
    #     # Set a baseline at y=0
    #     ax.axhline(y=0, color='#bbbbbb', linestyle='-', alpha=0.3, linewidth=1)
        
    #     # Format y-axis to use integers only
    #     ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        
    #     # Format the title, labels with professional typography
    #     title_font = {'fontsize': 22, 'fontweight': 'bold', 'fontfamily': 'sans-serif'}
    #     label_font = {'fontsize': 14, 'fontfamily': 'sans-serif'}
        
    #     ax.set_title(f"Popularity of '{term}' by Year", pad=20, **title_font)
    #     ax.set_xlabel('Year', **label_font)
    #     ax.set_ylabel('Number of Occurrences', **label_font)
        
    #     # Format x-axis as years
    #     ax.set_xticks(year_counts['year'])
    #     ax.set_xticklabels([int(year) for year in year_counts['year']])
        
    #     # Add value labels on bars
    #     for bar in bars:
    #         height = bar.get_height()
    #         ax.text(
    #             bar.get_x() + bar.get_width()/2.,
    #             height + 1,
    #             f'{int(height)}',
    #             ha='center',
    #             va='bottom',
    #             fontweight='bold',
    #             fontsize=12,
    #             bbox=dict(
    #                 boxstyle="round,pad=0.3",
    #                 fc='white',
    #                 ec='#bbbbbb',
    #                 alpha=0.9
    #             )
    #         )
        
    #     # Set y-axis limit to give bars some headroom
    #     ax.set_ylim(0, max(year_counts['count']) * 1.15)
        
    #     # Enhance overall appearance
    #     plt.tight_layout()
        
    #     # Save high-quality figure
    #     buf = io.BytesIO()
    #     plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    #     buf.seek(0)
    #     result['year_chart'] = base64.b64encode(buf.getvalue()).decode('utf-8')
    #     plt.close()
    # except Exception as e:
    #     print(f"Error creating year chart: {str(e)}")
    
    return result

def analyze_search_term(term, start_year=2000, max_results=1000):
    """
    Main function to fetch data and create visualizations for a search term
    
    Parameters:
    -----------
    term : str
        The term to search for
    start_year : int
        The year to start searching from
    max_results : int
        Maximum number of results to fetch
        
    Returns:
    --------
    dict
        Dictionary containing the analysis results
    """
    try:
        # Fetch data from Arquivo.pt
        df = fetch_arquivo_data(term, start_year, max_results)
        
        if len(df) == 0:
            return {
                'year_chart': None,
                'month_chart': None,
                'peak_months': {},
                'peak_data': {},
                'total_results': 0,
                'error': "No results found for this search term."
            }
        
        # Create visualizations
        return create_visualizations(df, term)
    except Exception as e:
        return {
            'year_chart': None,
            'month_chart': None,
            'peak_months': {},
            'peak_data': {},
            'total_results': 0,
            'error': str(e)
        }