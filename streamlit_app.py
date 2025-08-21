import streamlit as st
import requests
import json
from datetime import datetime
import folium
from streamlit_folium import st_folium
import pandas as pd
import hashlib

# Page configuration
st.set_page_config(
    page_title="Inshorts News Reader",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
BASE_URL = "https://api.inshorts.abhi8290.in/api/v1/news"

def make_api_request(url):
    """Make API request with error handling"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None

def format_date(date_str):
    """Format ISO date string to readable format"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        return date_str

def get_article_id(article):
    """Get a consistent article ID"""
    return article.get('id') or article.get('url') or hashlib.md5(str(article.get('title', '')).encode()).hexdigest()[:8]

def display_news_article(article):
    """Display a single news article"""
    with st.container():
        st.markdown(f"""
        <div class="news-card">
            <div class="news-title">{article.get('title', 'No Title')}</div>
            <div class="news-meta">
                📅 {format_date(article.get('publication_date', ''))} | 
                📰 {article.get('source_name', 'Unknown')} | 
                🏷️ {', '.join(article.get('category', []))} |
                <span class="relevance-score">Score: {article.get('relevance_score', 0):.2f}</span>
            </div>
            <div class="news-description">{article.get('description', 'No description available')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Get consistent article ID
        article_id = get_article_id(article)
        
        # Create columns for buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            url = article.get('url')
            if url:
                read_key = f"read_{article_id}"
                if st.button("🔗 Read Full", key=read_key):
                    # Toggle the URL display
                    current_state = st.session_state.get('show_url_for', None)
                    if current_state == article_id:
                        st.session_state.show_url_for = None
                    else:
                        st.session_state.show_url_for = article_id
            else:
                st.write("URL: N/A")

        with col2:
            summary_key = f"summary_{article_id}"
            if st.button("🤖 AI Summary", key=summary_key):
                # Toggle the summary display
                current_state = st.session_state.get('show_summary_for', None)
                if current_state == article_id:
                    st.session_state.show_summary_for = None
                else:
                    st.session_state.show_summary_for = article_id

        # Display full article link if toggled on
        if st.session_state.get('show_url_for') == article_id and url:
            st.markdown(f'<div class="full-article-link"><a href="{url}" target="_blank" rel="noopener noreferrer">Open full article</a></div>', unsafe_allow_html=True)
        
        # Display AI summary if toggled on
        if st.session_state.get('show_summary_for') == article_id:
            summary = article.get('llm_summary', 'No AI summary available')
            if summary and summary != 'No AI summary available':
                st.markdown(f"""
                <div class="summary-box">
                    <div class="summary-title">AI Summary:</div>
                    {summary}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("No AI summary available for this article")

def initialize_session_state():
    """Initialize all session state variables"""
    session_defaults = {
        'articles': [],
        'show_url_for': None,
        'show_summary_for': None,
        'current_page': 1,
        'selected_category': None,
        'score_filter': 0.7,
        'search_query': "",
        'current_view': None
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def clear_articles_only():
    """Clear only articles, preserve UI state"""
    st.session_state.articles = []
    st.session_state.show_url_for = None
    st.session_state.show_summary_for = None

def main():
    st.title("📰 Inshorts News Reader")
    st.markdown("Browse news articles from various categories, search by location, or find specific content")

    # Initialize session state
    initialize_session_state()

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select News Type:",
        ["🔥 Trending News", "📂 Category News", "🎯 Search by Score", "📍 Location-based News", "🔍 Custom Search"]
    )
    
    # Only clear articles if view changes
    if st.session_state.current_view != page:
        clear_articles_only()
        st.session_state.current_view = page

    if page == "🔥 Trending News":
        st.header("🔥 Trending News")
        
        trending_windows = {"Last 6 Hours": "6h", "Last 24 Hours": "24h", "Last Week": "week"}
        selected_window_label = st.selectbox("Select Trending Window:", list(trending_windows.keys()))
        selected_window = trending_windows[selected_window_label]

        if st.button("🔄 Fetch Trending News", type="primary"):
            st.session_state.current_page = 1
            url = f"{BASE_URL}/trending?window={selected_window}"
            
            with st.spinner(f"Fetching trending news for {selected_window_label}..."):
                data = make_api_request(url)
                
                if data:
                    articles = data.get('data', {}).get('articles', [])
                    
                    if articles:
                        st.session_state.articles = articles
                        st.success(f"Found {len(articles)} trending articles for {selected_window_label}")
                    else:
                        st.session_state.articles = []
                        st.warning(f"No trending articles found for {selected_window_label}.")
                else:
                    st.session_state.articles = []
                    st.error("Failed to fetch trending news.")

    elif page == "📂 Category News":
        st.header("Browse News by Category")
        
        categories = [
            "DEFENCE", "EXPLAINERS", "FINANCE", "Feel_Good_Stories", "General",
            "Health___Fitness", "IPL", "IPL_2025", "Israel-Hamas_War", "Lifestyle",
            "Russia-Ukraine_Conflict", "automobile", "bollywood", "business", "city",
            "cricket", "crime", "education", "entertainment", "facts", "fashion",
            "football", "hatke", "miscellaneous", "national", "politics", "science",
            "sports", "startup", "technology", "travel", "world"
        ]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_category = st.selectbox(
                "Select Category:", 
                categories, 
                index=categories.index(st.session_state.selected_category) if st.session_state.selected_category in categories else 0
            )
        with col2:
            page_num = st.number_input("Page Number:", min_value=1, value=st.session_state.current_page)
        
        if st.button("📰 Get News", type="primary"):
            st.session_state.selected_category = selected_category
            st.session_state.current_page = page_num
            url = f"{BASE_URL}/category/{selected_category}?page={page_num}"
            
            with st.spinner(f"Fetching {selected_category} news..."):
                data = make_api_request(url)
                
                if data:
                    articles = data.get('data', {})
                    
                    if articles:
                        st.session_state.articles = articles
                        st.success(f"Found {len(articles)} articles in {selected_category}")
                    else:
                        st.session_state.articles = []
                        st.warning(f"No articles found for category: {selected_category}")
                else:
                    st.session_state.articles = []
                    st.error("Failed to fetch news articles")

    elif page == "🎯 Search by Score":
        st.header("Find News by Relevance Score")
        st.info("Higher relevance scores indicate more important or trending news")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            score = st.slider("Minimum Relevance Score:", 0.0, 1.0, st.session_state.score_filter, 0.1)
        with col2:
            page_num = st.number_input("Page Number:", min_value=1, value=st.session_state.current_page, key="score_page")
        
        if st.button("🎯 Search by Score", type="primary"):
            st.session_state.score_filter = score
            st.session_state.current_page = page_num
            url = f"{BASE_URL}/score/{score}?page={page_num}"
            
            with st.spinner(f"Searching articles with score ≥ {score}..."):
                data = make_api_request(url)
                
                if data:
                    articles = data.get('data', {})
                    
                    if articles:
                        st.session_state.articles = articles
                        st.success(f"Found {len(articles)} articles with relevance score ≥ {score}")
                        
                        # Show score distribution
                        scores = [article.get('relevance_score', 0) for article in articles]
                        df = pd.DataFrame({'Relevance Score': scores})
                        st.subheader("Score Distribution")
                        st.bar_chart(df['Relevance Score'].value_counts().sort_index())
                    else:
                        st.session_state.articles = []
                        st.warning(f"No articles found with relevance score ≥ {score}")
                else:
                    st.session_state.articles = []
                    st.error("Failed to fetch news articles")

    elif page == "📍 Location-based News":
        st.header("Location-based News Search")
        st.info("Find news articles from a specific geographic location")
        
        # Location input
        col1, col2, col3 = st.columns(3)
        with col1:
            latitude = st.number_input("Latitude:", value=19.697352, format="%.6f")
        with col2:
            longitude = st.number_input("Longitude:", value=73.865399, format="%.6f")
        with col3:
            radius = st.number_input("Radius (km):", min_value=1, max_value=1000, value=100)
        
        # Map for location selection
        st.subheader("📍 Select Location on Map")
        m = folium.Map(location=[latitude, longitude], zoom_start=10)
        folium.Marker([latitude, longitude], popup="Selected Location").add_to(m)
        folium.Circle([latitude, longitude], radius=radius*1000, popup=f"Search Radius: {radius}km").add_to(m)
        
        map_data = st_folium(m, height=300, width=700)
        
        # Update coordinates if map is clicked
        if map_data['last_clicked']:
            latitude = map_data['last_clicked']['lat']
            longitude = map_data['last_clicked']['lng']
            st.success(f"Location updated: {latitude:.6f}, {longitude:.6f}")
        
        if st.button("🌍 Get Local News", type="primary"):
            st.session_state.current_page = 1
            url = f"{BASE_URL}/nearby?lat={latitude}&lon={longitude}&radius={radius}"
            
            with st.spinner(f"Searching news within {radius}km of selected location..."):
                data = make_api_request(url)
                
                if data:
                    articles = data.get('data', {})
                    
                    if articles:
                        st.session_state.articles = articles
                        st.success(f"Found {len(articles)} local news articles")
                    else:
                        st.session_state.articles = []
                        st.warning("No local news found for the specified location")
                else:
                    st.session_state.articles = []
                    st.error("Failed to fetch local news")

    elif page == "🔍 Custom Search":
        st.header("Custom News Search")
        st.info("Search for specific news topics or from particular sources")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input(
                "Search Query:",
                value=st.session_state.search_query,
                placeholder="e.g., 'News Only from bihar from timesofindia'"
            )
        with col2:
            page_num = st.number_input("Page Number:", min_value=1, value=st.session_state.current_page, key="search_page")
        
        # Search examples
        with st.expander("💡 Search Examples"):
            st.markdown("""
            - `technology startup funding` - Technology and startup funding news
            - `covid vaccination india` - COVID vaccination news from India
            - `cricket world cup` - Cricket World Cup related news
            - `stock market sensex` - Stock market and Sensex news
            """)
        
        if st.button("🔍 Search News", type="primary") and search_query:
            st.session_state.search_query = search_query
            st.session_state.current_page = page_num
            import urllib.parse
            encoded_query = urllib.parse.quote(search_query)
            url = f"{BASE_URL}/search?q={encoded_query}&page={page_num}"
            
            with st.spinner(f"Searching for '{search_query}'..."):
                data = make_api_request(url)
                
                if data and data.get('success'):
                    articles = data.get('data', {}).get('articles', [])
                    meta = data.get('data', {}).get('meta', {})
                    
                    if articles:
                        st.session_state.articles = articles
                        st.success(f"Found {len(articles)} articles for '{search_query}'")
                        
                        # Show search metadata
                        if meta:
                            with st.expander("🔍 Search Details"):
                                st.json(meta)
                    else:
                        st.session_state.articles = []
                        st.warning(f"No articles found for '{search_query}'")
                else:
                    st.session_state.articles = []
                    st.error("Failed to search news articles")

    # Display articles from session state
    if st.session_state.articles:
        for article in st.session_state.articles:
            display_news_article(article)
    else:
        st.info("No articles to display. Please perform a search or select a category.")

if __name__ == "__main__":
    main()