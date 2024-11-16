import customtkinter as ctk
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Page
import pandas as pd
from threading import Thread
import ctypes
import sys
import re
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageTk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Hide console on Windows
if sys.platform == "win32":
    ctypes.windll.kernel32.FreeConsole()

@dataclass
class VideoData:
    """Data structure for storing TikTok video information."""
    username: str
    likes: str
    comments: str
    favorites: str
    shares: str
    upload_date: str
    description: str
    music_text: str

class TikTokScraperApp(ctk.CTk):
    """
    A GUI application for scraping TikTok videos using Playwright.
    
    This application allows users to:
    - Input TikTok cookies for authentication
    - Start/stop scraping
    - Filter videos based on dropshipping-related keywords
    - Save results to Excel
    """
    
    # Class constants
    WINDOW_SIZE = "700x500"
    WINDOW_TITLE = "TikTok Angrybird"
    OUTPUT_FILE = "tiktok_video_data.xlsx"
    
    # Keywords for dropshipping detection
    DROPSHIPPING_KEYWORDS = [
        "shop", "link in bio", "stock", 
        "sale", "discount", "order",
        "store", "retail", "add to cart",
        "checkout", "shipping", "offer",
        "guaranteed", "cash", "get yours",
        "limited edition", "deal", "buy",
        "price", "profit", "gift"
    ]

    def __init__(self) -> None:
        """Initialize the TikTok scraper application."""
        super().__init__()

        self.title(self.WINDOW_TITLE)
        self.geometry(self.WINDOW_SIZE)

        # Instance variables
        self.stop_flag: bool = False
        self.scraper_thread: Optional[Thread] = None
        self.logged_in_message_shown: bool = False

        self._setup_ui()
        self._load_icon()

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        # Cookie input section
        self.cookie_label = ctk.CTkLabel(self, text="Enter Cookie:")
        self.cookie_label.pack(pady=(20, 5))
        
        self.cookie_entry = ctk.CTkTextbox(self, height=50)
        self.cookie_entry.pack(fill="x", padx=20, pady=(0, 20))

        # Buttons
        self.load_button = ctk.CTkButton(
            self, 
            text="Load cookie from file", 
            command=self.load_from_file
        )
        self.load_button.pack(pady=10)

        self.start_button = ctk.CTkButton(
            self, 
            text="Start Scraping", 
            command=self.start_scraping
        )
        self.start_button.pack(pady=10)
        
        self.stop_button = ctk.CTkButton(
            self, 
            text="Stop Scraping", 
            command=self.stop_scraping, 
            state="disabled"
        )
        self.stop_button.pack(pady=10)
        
        # Checkbox for filtering
        self.check_variable = ctk.IntVar(value=1)
        self.check_button = ctk.CTkCheckBox(
            self, 
            text='Check if video is dropshipping related',
            variable=self.check_variable,
            offvalue=0,
            onvalue=1
        )
        self.check_button.pack(pady=10)

        # Log output section
        self.log_label = ctk.CTkLabel(self, text="Logs:")
        self.log_label.pack(pady=(20, 5))
        
        self.log_output = ctk.CTkTextbox(self, height=200, wrap="word")
        self.log_output.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _load_icon(self) -> None:
        """Load the application icon."""
        try:
            self.iconbitmap("icon.ico")
        except Exception as e:
            logger.warning(f"Failed to load icon: {e}")

    def log_message(self, message: str, level: str = "INFO") -> None:
        """
        Log a message to both the GUI and the logger.
        
        Args:
            message: The message to log
            level: The logging level (INFO, ERROR, etc.)
        """
        log_msg = f"[{level}] {message}\n"
        self.log_output.insert("end", log_msg)
        self.log_output.see("end")
        
        if level == "ERROR":
            logger.error(message)
        else:
            logger.info(message)

    def start_scraping(self) -> None:
        """Start the scraping process in a separate thread."""
        cookie = self.cookie_entry.get("1.0", "end").strip()
        if not cookie:
            self.log_message("Cookie cannot be empty", "ERROR")
            return

        self.log_message("Starting TikTok scraping...")
        self.stop_flag = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        self.scraper_thread = Thread(target=self.run_scraper, args=(cookie,))
        self.scraper_thread.start()

    def stop_scraping(self) -> None:
        """Stop the scraping process."""
        self.log_message("Stopping TikTok scraping...")
        self.stop_flag = True
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def run_scraper(self, cookie: str) -> None:
        """
        Run the TikTok scraper using Playwright.
        
        Args:
            cookie: The TikTok cookie for authentication
        """
        cookies = [
            {"name": cookie.split('=')[0].strip(), "value": cookie.split('=')[1].strip(), "domain": ".tiktok.com", "path": "/", "httpOnly": True, "secure": True}
            for cookie in cookie.split(';')
        ]
        video_records: List[Dict[str, str]] = []

        with sync_playwright() as p:
            try:
                browser = p.firefox.launch(headless=False, args=["--disable-gpu"])
                context = browser.new_context(
                    permissions=[]
                )
                page = context.new_page()
                page.context.add_cookies(cookies)
                page.goto("https://www.tiktok.com")
                
                if not self.logged_in_message_shown:
                    self.check_logged_in_username(page)

                # page.wait_for_selector('button[type="button"]:has-text("Decline")', timeout=20000)
                # page.click('button[type="button"]:has-text("Decline")')
                page.wait_for_selector('strong[data-e2e="like-count"]', timeout=10000)
                detected_usernames: Set[str] = set()
                check = self.check_variable.get()

                while not self.stop_flag:
                    self.log_message("Detecting video information...")
                    username_elements = page.query_selector_all('h3[data-e2e="video-author-uniqueid"]')
                    like_count_elements = page.query_selector_all('strong[data-e2e="like-count"]')
                    comment_count_elements = page.query_selector_all('strong[data-e2e="comment-count"]')
                    favorite_count_elements = page.query_selector_all('button[aria-label*="Favorites"]')
                    share_count_elements = page.query_selector_all('strong[data-e2e="share-count"]')
                    upload_date_elements = page.query_selector_all('a.e1g2yhv81')
                    description_elements = page.query_selector_all('h1[data-e2e="video-desc"]')
                    music_text_elements = page.query_selector_all('div.css-pvx3oa-DivMusicText')
                    video_data: Dict[str, VideoData] = {}

                    for i in range(len(username_elements)):
                        description = description_elements[i].inner_text() if i < len(description_elements) else "N/A"
                        if check and not any(keyword in description for keyword in self.DROPSHIPPING_KEYWORDS):
                            continue
                        username = username_elements[i].inner_text()
                        like_count = like_count_elements[i].inner_text() if i < len(like_count_elements) else "N/A"
                        comment_count = comment_count_elements[i].inner_text() if i < len(comment_count_elements) else "N/A"
                        favorite_count = favorite_count_elements[i].inner_text() if i < len(favorite_count_elements) else "N/A"
                        share_count = share_count_elements[i].inner_text() if i < len(share_count_elements) else "N/A"
                        upload_date = upload_date_elements[i].inner_text().split('·')[1].strip() if i < len(upload_date_elements) else "N/A"
                        
                        music_text = music_text_elements[i].inner_text() if i < len(music_text_elements) else "N/A"
                        video_data[username] = VideoData(
                            username=username,
                            likes=like_count,
                            comments=comment_count,
                            favorites=favorite_count,
                            shares=share_count,
                            upload_date=upload_date,
                            description=description,
                            music_text=music_text,
                        )

                    new_usernames = set(video_data.keys()) - detected_usernames

                    if new_usernames:
                        for username in new_usernames:
                            data = video_data[username]
                            log_msg = f"[LOG] {username} - Date: {data.upload_date} - {data.description}\n"
                            self.log_message(log_msg)
                            video_records.append({
                                'Uploader': username,
                                'Upload Date': data.upload_date,
                                'Description': data.description,
                                'Likes': data.likes,
                                'Comments': data.comments,
                                'Favorites': data.favorites,
                                'Shares': data.shares,
                                'Music Text': data.music_text,
                            })
                        detected_usernames.update(new_usernames)

                        # Save to Excel
                        df = pd.DataFrame(video_records)
                        df.to_excel(self.OUTPUT_FILE, index=False)
                        self.log_message(f"Data saved to '{self.OUTPUT_FILE}'")

                    page.wait_for_timeout(3000)
                    page.keyboard.press("End")
                    page.wait_for_timeout(10000)

                browser.close()
                self.log_message("Scraping stopped.")
                
            except PlaywrightTimeoutError:
                self.log_message("Timeout reached while waiting for elements on TikTok.", "ERROR")
            except Exception as e:
                self.log_message(f"Error: {e}", "ERROR")

    def check_logged_in_username(self, page: Page) -> None:
        """
        Check and display the logged-in username from the page content.
        
        Args:
            page: The Playwright page object
        """
        try:
            content = page.content()
            match = re.search(r',"nickName":"(.*?)"', content)
            if match:
                username = match.group(1)
                self.log_message(f"Logged in as {username}")
                self.logged_in_message_shown = True
            else:
                self.log_message("Could not detect username", "ERROR")
        except Exception as e:
            self.log_message(f"Error checking username: {e}", "ERROR")
    
    def load_from_file(self) -> None:
        """Load cookie data from a file."""
        try:
            with open("cookie.txt", "r") as f:
                cookie = f.read().strip()
                self.cookie_entry.delete("1.0", "end")
                self.cookie_entry.insert("1.0", cookie)
                self.log_message("Cookie loaded successfully")
        except FileNotFoundError:
            self.log_message("cookie.txt not found", "ERROR")
        except Exception as e:
            self.log_message(f"Error loading cookie: {e}", "ERROR")

if __name__ == "__main__":
    try:
        app = TikTokScraperApp()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Application crashed: {e}")
        raise