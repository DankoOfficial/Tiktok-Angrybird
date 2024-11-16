# TikTok AngryBird 🦅
![Screenshot_18](https://github.com/user-attachments/assets/42e7229e-035e-4b73-8dbc-de44c14e0a2c)

A powerful TikTok video analysis tool that combines data scraping and visualization capabilities. This project consists of a desktop scraper application and a web-based analytics dashboard.

## Features
![Screenshot_17](https://github.com/user-attachments/assets/30f8204a-ea95-4668-bc9c-36b436b8ba82)

### Desktop Scraper (main.py)
- 🔐 Cookie-based authentication for TikTok access
- 🤖 Automated video data collection using Playwright
- 🎯 Smart filtering for dropshipping-related content
- 💾 Excel export functionality
- 🖥️ User-friendly GUI built with CustomTkinter

  ![Screenshot_19](https://github.com/user-attachments/assets/39e2e6aa-8571-443e-b001-eab3c183897b)


### Analytics Dashboard (frontend.py)
- 📊 Interactive data visualizations with Plotly
- 🏷️ Hashtag analysis and engagement metrics
- 🤖 AI-powered data insights using Groq API
- 📈 Trend analysis and competition tracking
- 🔍 Advanced filtering and search capabilities

## Requirements

### Backend (main.py)
```
customtkinter
playwright
pandas
Pillow
```

### Frontend (frontend.py)
```
streamlit
pandas
plotly
groq
python-dotenv
xlsxwriter
```

## Installation

1. Clone this repository
2. Install the required packages:
```bash
pip install -r requirements.txt
```
3. Install Playwright browsers:
```bash
playwright install firefox
```

## Setup

1. Create a `.env` file in the project root
2. Add your Groq API key:
```
API_KEY=your_groq_api_key_here
```

## Usage

### Running the Scraper
1. Run `python main.py`
2. Enter your TikTok cookie in the input field
3. Choose whether to filter for dropshipping content
4. Click "Start Scraping"

### Running the Analytics Dashboard
1. Ensure you have scraped data (tiktok_video_data.xlsx should exist)
2. Run `streamlit run frontend.py`
3. Access the dashboard at http://localhost:8501

## Features in Detail

### Data Collection
- Video metadata (likes, comments, shares)
- Upload dates and descriptions
- Music information
- Engagement metrics

### Analysis Capabilities
- Hashtag popularity tracking
- Engagement rate calculations
- Content trend identification
- AI-powered insights
- Competition analysis

## Security Notes
- Never share your TikTok cookies
- Store API keys securely in .env file
- Use the tool responsibly and in accordance with TikTok's terms of service

## Contributing
Feel free to submit issues and enhancement requests!

## Credits
Created by DankoOfficial (https://github.com/DankoOfficial) & alexx

## License
This project is licensed under the MIT License - see the LICENSE file for details
