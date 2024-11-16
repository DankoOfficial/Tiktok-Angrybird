"""
TikTok AngryBird Frontend Application

Uses Streamlit-based frontend for analyzing Tiktok video data.
It includes features for data visualization, filtering, and keyword analysis.
Created by DankoOfficial (https://github.com/DankoOfficial) & alexx
"""

from typing import Dict, List
from datetime import datetime
from io import BytesIO
from os import getenv, path
from re import findall

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from requests import get, RequestException

EXCEL_FILENAME = 'tiktok_video_data.xlsx'
MAX_DISPLAY_ROWS = 50
MAX_DATA_ROWS = 75
MAX_TOP_HASHTAGS = 10
AI_MODEL = 'mixtral-8x7b-32768' # https://console.groq.com/docs/models

COLUMN_UPLOADER = 'Uploader'
COLUMN_LIKES = 'Likes'
COLUMN_COMMENTS = 'Comments'
COLUMN_SHARES = 'Shares'

load_dotenv()

client = Groq(api_key=getenv('API_KEY'))

def load_data() -> pd.DataFrame:
    """
    Load and preprocess TikTok video data from Excel file.
    
    Returns:
        pd.DataFrame: Processed DataFrame containing TikTok video data
    """
    if not path.exists(EXCEL_FILENAME):
        st.error("Data file not found. Ensure backend script has run to collect data.")
        return pd.DataFrame()

    try:
        data = pd.read_excel(EXCEL_FILENAME, engine='openpyxl')
        numeric_columns = ["Likes", "Comments", "Shares"]
        for col in numeric_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int)
        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def extract_hashtags(data: pd.DataFrame) -> pd.DataFrame:
    """
    Extract hashtags from video descriptions.
    
    Args:
        data (pd.DataFrame): Input DataFrame containing video data
        
    Returns:
        pd.DataFrame: DataFrame with extracted hashtags
    """
    if 'Description' not in data.columns:
        st.warning("No 'Description' column found in data.")
        return pd.DataFrame()
    
    try:
        data['Hashtags'] = data['Description'].apply(
            lambda x: findall(r'#\w+', str(x)) if pd.notnull(x) else []
        )
        hashtag_data = data.explode('Hashtags')
        return hashtag_data[hashtag_data['Hashtags'].notna()]
    except Exception as e:
        st.error(f"Error extracting hashtags: {str(e)}")
        return pd.DataFrame()

def convert_df_to_excel(df: pd.DataFrame) -> BytesIO:
    """
    Convert DataFrame to Excel file in memory.
    
    Args:
        df (pd.DataFrame): DataFrame to convert
        
    Returns:
        BytesIO: Excel file in memory
    """
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Error converting to Excel: {str(e)}")
        return BytesIO()

def format_data(data: pd.DataFrame, max_rows: int = MAX_DISPLAY_ROWS) -> str:
    """
    Format DataFrame rows into a readable string.
    First row has detailed format as example, remaining rows are concise.
    
    Args:
        data (pd.DataFrame): Input DataFrame
        max_rows (int): Maximum number of rows to format
        
    Returns:
        str: Formatted string representation of data
    """
    try:
        formatted_lines = []
        for index, row in data.head(max_rows).iterrows():
            formatted_line = (
                f"{index}|{row['Uploader']}|{row['Upload Date']}|"
                f"{row['Description']}|{row['Likes']}|{row['Comments']}|"
                f"{row['Shares']}|{row['Favorites']}|{row['Music Text']}"
            )
            formatted_lines.append(formatted_line)
        return formatted_lines
    except Exception as e:
        st.error(f"Error formatting data: {str(e)}")
        return ""

def fetch_search_data(term: str) -> List[Dict]:
    """
    Fetch search data from the API.
    
    Args:
        term (str): Search term
        
    Returns:
        List[Dict]: List of search results
    """
    try:
        response = get(
            f"https://serptag.co.uk/api/global-key/?format=json&keyword={term}&lang=en",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Error processing search data: {str(e)}")
        return []

def answer_question(question: str, data: str) -> str:
    """
    Generate AI response to user questions about the data.
    
    Args:
        question (str): User's question
        data (pd.DataFrame): Data to analyze
        
    Returns:
        str: AI-generated response
    """
    try:
        prompt_message = {
            "role": "user",
            "content": (
                f"You are a data analyst. Always base your response strictly on the "
                f"data provided, using clear examples and logical reasoning. Provide "
                f"specific insights, identify patterns, and explain any trends or "
                f"anomalies. When relevant, offer actionable recommendations backed "
                f"by data. Prompt by the user: {question} Data: {data}"
            )
        }
        
        chat_completion = client.chat.completions.create(
            messages=[prompt_message],
            model=AI_MODEL
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"

def init_session_state():
    """Initialize Streamlit session state variables."""
    if "reload_data" not in st.session_state:
        st.session_state["reload_data"] = False
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

def create_visualization(hashtag_data: pd.DataFrame):
    """Create and display hashtag engagement visualization."""
    if not hashtag_data.empty:
        hashtag_engagement = hashtag_data.groupby('Hashtags').agg({
            COLUMN_LIKES: 'sum',
            COLUMN_COMMENTS: 'sum',
            COLUMN_SHARES: 'sum'
        }).reset_index()

        hashtag_engagement['Total Engagement'] = (
            hashtag_engagement[COLUMN_LIKES] + 
            hashtag_engagement[COLUMN_COMMENTS] + 
            hashtag_engagement[COLUMN_SHARES]
        )
        
        top_hashtags = hashtag_engagement.nlargest(MAX_TOP_HASHTAGS, 'Total Engagement')
        
        fig = px.bar(
            top_hashtags,
            x='Hashtags',
            y=[COLUMN_LIKES, COLUMN_COMMENTS, COLUMN_SHARES],
            title="Top 10 Hashtags by Engagement",
            labels={'value': 'Engagement Count', 'Hashtags': 'Hashtags'},
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No hashtags found in descriptions.")

def setup_sidebar(data: pd.DataFrame) -> pd.DataFrame:
    """Setup and handle sidebar filters."""
    st.sidebar.header("Filter Options")
    uploader_filter = st.sidebar.text_input("Uploader")
    min_likes = st.sidebar.number_input("Minimum Likes", min_value=0, value=0)
    min_comments = st.sidebar.number_input("Minimum Comments", min_value=0, value=0)
    sort_by = st.sidebar.selectbox("Sort By", ["Upload Date", "Likes", "Comments", "Favorites", "Shares"])
    sort_order = st.sidebar.radio("Sort Order", ["Ascending", "Descending"])

    filtered_data = data.copy()
    if uploader_filter:
        filtered_data = filtered_data[
            filtered_data[COLUMN_UPLOADER].str.contains(uploader_filter, case=False, na=False)
        ]
    
    filtered_data = filtered_data[filtered_data[COLUMN_LIKES] >= min_likes]
    filtered_data = filtered_data[filtered_data[COLUMN_COMMENTS] >= min_comments]
    filtered_data = filtered_data.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
    
    return filtered_data

def setup_chat_interface():
    """Setup and display the chat interface."""
    st.markdown(
        "<h3 style='margin: 0; padding: 0;'>[🤖] Chat with the TikTok Data Bot</h3>",
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <style>
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 0px;
            overflow-y: auto;
            padding: 0;
            margin: 0;
        }
        .user-message {
            color: #006400;
            background-color: #E0F2E0;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 5px;
        }
        .bot-message {
            color: #4B2E2E;
            background-color: #F0E5E5;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 5px;
        }
        h3 {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def display_chat_messages():
    """Display chat message history."""
    with st.container():
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(
                    f"<div class='user-message'><strong>🧑 [USER]:</strong> {message['content']}"
                    f"<br><small>{message['timestamp']}</small></div>",
                    unsafe_allow_html=True
                )
            elif message["role"] == "bot":
                st.markdown(
                    f"<div class='bot-message'><strong>🤖 [BOT]:</strong> {message['content']}"
                    f"<br><small>{message['timestamp']}</small></div>",
                    unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)

def submit_message():
    user_input = st.session_state["user_input"]
    if user_input:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format the data with explanation
        data = load_data()
        formatted_data = format_data(data)[:MAX_DATA_ROWS]
        data_explanation = f'Below is the TikTok video data. The first row shows a detailed example with labeled fields.\nAll subsequent rows follow this format: index|uploader|upload_date|description|likes|comments|shares|favorites|music_text\n\n{formatted_data}'
        response = answer_question(user_input, data_explanation)

        st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": timestamp})
        st.session_state.chat_history.append({"role": "bot", "content": response, "timestamp": timestamp})

        st.session_state["user_input"] = ""

def format_trend(trend):
    """Format trend value with color and arrow."""
    return f"<span style='color:green;'>⬆️ {trend}%</span>" if trend > 0 else f"<span style='color:red;'>⬇️ {trend}%</span>"

def format_competition(competition_index):
    """Format competition index with color."""
    color = "yellow" if competition_index >= 60 else "green"
    return f"<span style='color:{color};'>{competition_index}</span>"

def setup_trend_search():
    """Setup and handle trend search functionality."""
    st.subheader("Search Keyword Data")

    if "show_results" not in st.session_state:
        st.session_state["show_results"] = False

    search_term = st.text_input("Enter a keyword to search:", "")

    col1, col2 = st.columns(2)

    with col1:
        search_button = st.button("Search")

    with col2:
        clear_button = st.button("Clear Table")

    if search_button and search_term:
        search_results = fetch_search_data(search_term)
        if search_results:
            df = pd.DataFrame(search_results)

            df["Trend"] = df["trend"].apply(format_trend)
            df["Competition"] = df["competition_index"].apply(format_competition)
            
            df = df.rename(columns={
                "text": "Keyword",
                "volume": "Volume",
                "low_bid": "Low Bid",
                "high_bid": "High Bid"
            })

            display_df = df[["Keyword", "Volume", "Trend", "Competition", "Low Bid", "High Bid"]]
            
            st.session_state["show_results"] = True
            st.session_state["results_df"] = display_df
        else:
            st.write("No results found.")
            st.session_state["show_results"] = False

    if clear_button:
        st.session_state["show_results"] = False

    if st.session_state["show_results"]:
        st.markdown(
            st.session_state["results_df"].to_html(escape=False, index=False)
            .replace('<td>', '<td style="text-align: left;">', 1)
            .replace('<th>', '<th style="text-align: left;">', 1),
            unsafe_allow_html=True
        )

def get_base64_icon() -> str:
    """Convert icon.ico to base64 string."""
    try:
        import base64
        with open("icon.ico", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        # Return an empty string if icon file is not found
        return ""

def main():
    """Main function to run the Streamlit application."""
    # Get icon, if available
    icon_base64 = get_base64_icon()
    icon_html = f'<img src="data:image/x-icon;base64,{icon_base64}" class="app-icon">' if icon_base64 else ""
    
    st.markdown(
        f"""
        <style>
        @keyframes gradient {{
            0% {{
                background-position: 0% 50%;
            }}
            100% {{
                background-position: 200% 50%;
            }}
        }}
        .title-container {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 10px;
            margin-bottom: 20px;
        }}
        .app-icon {{
            width: 40px;
            height: 40px;
        }}
        .title-text {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(90deg, 
                #ffffff 0%,
                #2b2b2b 25%,
                #ffffff 50%,
                #2b2b2b 75%,
                #ffffff 100%
            );
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-fill-color: transparent;
            animation: gradient 3s linear infinite;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
            letter-spacing: -0.5px;
        }}
        .github-link {{
            display: inline-flex;
            align-items: center;
            text-decoration: none;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            padding: 8px 16px;
            border-radius: 12px;
            font-size: 0.9em;
            gap: 8px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            margin-left: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
            font-weight: 500;
        }}
        .github-link:hover {{
            background: rgba(0, 0, 0, 0.9);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        .github-icon {{
            width: 20px;
            height: 20px;
            opacity: 0.9;
            transition: all 0.3s ease;
            filter: brightness(0) invert(1);
        }}
        .github-link:hover .github-icon {{
            transform: rotate(360deg);
            opacity: 1;
        }}
        .github-text {{
            color: #ffffff;
            font-weight: 500;
            letter-spacing: 0.2px;
        }}
        .github-badge {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #1a1a1a 0%, #373737 100%);
            color: white;
            padding: 8px 15px;
            border-radius: 50px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
            transition: all 0.3s ease;
            z-index: 1000;
        }}
        .github-badge:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }}
        .github-badge img {{
            width: 20px;
            height: 20px;
            filter: brightness(0) invert(1);
        }}
        .github-badge a {{
            color: white !important;
            text-decoration: none !important;
            font-size: 0.9em;
            font-weight: 500;
        }}
        </style>
        <div class="title-container">
            {icon_html}
            <h1 class="title-text">TikTok AngryBird</h1>
            <a href="https://github.com/DankoOfficial" target="_blank" class="github-link">
                <img src="https://cdn-icons-png.flaticon.com/512/25/25231.png" class="github-icon">
                <span class="github-text">DankoOfficial</span>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    init_session_state()
    
    if st.button("Reload Data"):
        st.session_state["reload_data"] = True
    
    data = load_data()
    
    if not data.empty:
        st.write(f"Number of results: {len(data)}")
        
        filtered_data = setup_sidebar(data)
        st.dataframe(filtered_data)
        
        st.download_button(
            label="Download Filtered Data as Excel",
            data=convert_df_to_excel(filtered_data),
            file_name="filtered_tiktok_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        hashtag_data = extract_hashtags(filtered_data)
        create_visualization(hashtag_data)
        
        setup_trend_search()
        
        setup_chat_interface()
        display_chat_messages()
        st.text_input("Type your message here:", key="user_input", on_change=submit_message)
        
        st.markdown(
            """
            <style>
            .github-badge {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: linear-gradient(135deg, #1a1a1a 0%, #373737 100%);
                color: white;
                padding: 8px 15px;
                border-radius: 50px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                display: flex;
                align-items: center;
                gap: 8px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
                transition: all 0.3s ease;
                z-index: 1000;
            }}
            .github-badge:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
            }}
            .github-badge img {{
                width: 20px;
                height: 20px;
                filter: brightness(0) invert(1);
            }}
            .github-badge a {{
                color: white !important;
                text-decoration: none !important;
                font-size: 0.9em;
                font-weight: 500;
            }}
            </style>
            <div class="github-badge">
                <img src="https://cdn-icons-png.flaticon.com/512/25/25231.png">
                <a href="https://github.com/DankoOfficial" target="_blank">
                    Created by DankoOfficial
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.write("No data available. Run the backend script to generate data.")

if __name__ == "__main__":
    main()