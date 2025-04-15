#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import tempfile
import uuid
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QTabWidget,
    QPushButton, QToolBar, QColorDialog, QAction, QFileDialog, 
    QDialog, QLineEdit, QListWidget, QHBoxLayout, QLabel, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtCore import QUrl, Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap

# ====================== CONFIGURATION ======================
SESSION_FILE = "browser_session.json"  # Where we save open tabs
BOOKMARKS_FILE = "bookmarks.json"     # Where we store bookmarks

# Our beautiful custom start page
DEFAULT_START_PAGE = """
<html>
<head><title>Welcome to PyBrowser</title>
<style>
    body { 
        font-family: 'Arial', sans-serif; 
        text-align: center; 
        margin-top: 50px;
        background: #f5f5f5;
    }
    .quick-links { 
        margin: 20px; 
    }
    button { 
        padding: 10px 15px; 
        margin: 5px; 
        cursor: pointer;
        background: #4285f4;
        color: white;
        border: none;
        border-radius: 4px;
    }
    input {
        padding: 10px;
        width: 300px;
        border-radius: 4px;
        border: 1px solid #ddd;
    }
</style>
</head>
<body>
    <h1>Welcome to PyBrowser!</h1>
    <div class="quick-links" id="quickLinks"></div>
    <input type="text" id="searchBox" placeholder="Search or enter URL">
    <button onclick="search()">Go</button>
    
    <script>
        function search() {
            let query = document.getElementById('searchBox').value;
            if (query.includes('.')) {
                if (!query.startsWith('http')) query = 'https://' + query;
                window.location.href = query;
            } else {
                window.location.href = `https://google.com/search?q=${encodeURIComponent(query)}`;
            }
        }
        
        // Load saved bookmarks
        if (localStorage.bookmarks) {
            let links = JSON.parse(localStorage.bookmarks);
            let html = '';
            links.forEach(link => {
                html += `<button onclick="window.location.href='${link.url}'">${link.title}</button>`;
            });
            document.getElementById('quickLinks').innerHTML = html;
        }
    </script>
</body>
</html>
"""

# ====================== ASCII ART BANNER ======================
def show_banner():
    banner = """
                              _______________    __  ___      ___    ____  
                             /_  __/ ____/   |  /  |/  /     /   |  /  _/  
                              / / / __/ / /| | / /|_/ /_____/ /| |  / /    
                             / / / /___/ ___ |/ /  / /_____/ ___ |_/ /     
                            /_/ /_____/_/  |_/_/  /_/     /_/  |_/___/     
                             server = https://discord.gg/recaptcha       
                             discord = NikhiL
    """
    print(banner)
    print("🚀 Starting PyBrowser - Your lightweight Python web browser\n")

# ====================== AD BLOCKER ======================
class AdBlocker(QWebEngineUrlRequestInterceptor):
    """Blocks annoying ads and trackers"""
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        blocked_domains = ["doubleclick.net", "adsense", "adservice", "googleadservices"]
        if any(ad in url for ad in blocked_domains):
            print(f"🔒 Blocked ad/tracker: {url}")
            info.block(True)

# ====================== BROWSER TAB ======================
class BrowserTab(QWidget):
    """Represents a single browser tab with its own session"""
    def __init__(self, url=None, incognito=False):
        super().__init__()
        self.incognito = incognito
        self.setup_ui(url)
        
    def setup_ui(self, url):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create unique profile for each tab (fresh session)
        profile_name = f"profile_{uuid.uuid4().hex}"
        storage_path = os.path.join(tempfile.gettempdir(), profile_name)
        
        self.profile = QWebEngineProfile(profile_name, self)
        if self.incognito:
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            self.profile.setHttpCacheType(QWebEngineProfile.NoCache)
        self.profile.setPersistentStoragePath(storage_path)
        
        # Set a modern user agent
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Add our ad blocker
        self.interceptor = AdBlocker()
        self.profile.setRequestInterceptor(self.interceptor)
        
        # Configure the web page
        self.page = QWebEnginePage(self.profile, self)
        self.setup_page_settings()
        
        # Create the browser view
        self.browser = QWebEngineView()
        self.browser.setPage(self.page)
        self.load_url(url)
        
        layout.addWidget(self.browser)
        self.setLayout(layout)
    
    def setup_page_settings(self):
        """Enable important browser features"""
        settings = self.page.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
    
    def load_url(self, url):
        """Load either a URL or our default start page"""
        if url and url.startswith("http"):
            self.browser.setUrl(QUrl(url))
        else:
            self.browser.setHtml(DEFAULT_START_PAGE)
    
    def url(self):
        """Get current URL"""
        return self.browser.url().toString()
    
    def title(self):
        """Get current page title"""
        return self.browser.page().title()
    
    def reload(self):
        """Refresh the current page"""
        self.browser.reload()

# ====================== BOOKMARKS MANAGER ======================
class BookmarksDialog(QDialog):
    """Handles saving and organizing bookmarks"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Bookmarks")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_bookmark)
        
        # Input fields for new bookmarks
        hbox = QHBoxLayout()
        self.url_input = QLineEdit(placeholderText="Enter URL (e.g., https://example.com)")
        self.title_input = QLineEdit(placeholderText="Custom title (optional)")
        add_btn = QPushButton("➕ Add")
        add_btn.clicked.connect(self.add_bookmark)
        remove_btn = QPushButton("🗑️ Remove")
        remove_btn.clicked.connect(self.remove_bookmark)
        
        hbox.addWidget(self.url_input)
        hbox.addWidget(self.title_input)
        hbox.addWidget(add_btn)
        hbox.addWidget(remove_btn)
        
        layout.addLayout(hbox)
        layout.addWidget(self.list)
        
        self.setLayout(layout)
        self.load_bookmarks()
    
    def load_bookmarks(self):
        """Load saved bookmarks from file"""
        self.list.clear()
        if os.path.exists(BOOKMARKS_FILE):
            try:
                with open(BOOKMARKS_FILE, "r") as f:
                    bookmarks = json.load(f)
                    for b in bookmarks:
                        self.list.addItem(f"📌 {b['title']} - {b['url']}")
            except Exception as e:
                print(f"⚠️ Error loading bookmarks: {e}")
    
    def save_bookmarks(self, bookmarks):
        """Save bookmarks to file"""
        with open(BOOKMARKS_FILE, "w") as f:
            json.dump(bookmarks, f, indent=2)
    
    def get_bookmarks(self):
        """Get current bookmarks list"""
        if os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, "r") as f:
                return json.load(f)
        return []
    
    def add_bookmark(self):
        """Add a new bookmark"""
        url = self.url_input.text().strip()
        title = self.title_input.text().strip() or url
        
        if not url:
            QMessageBox.warning(self, "Oops", "Please enter a URL!")
            return
            
        if not url.startswith("http"):
            url = "https://" + url
        
        bookmarks = self.get_bookmarks()
        bookmarks.append({"url": url, "title": title})
        self.save_bookmarks(bookmarks)
        self.load_bookmarks()
        
        # Clear inputs
        self.url_input.clear()
        self.title_input.clear()
        
        QMessageBox.information(self, "Success", "Bookmark added!")
    
    def remove_bookmark(self):
        """Remove selected bookmark"""
        current = self.list.currentRow()
        if current >= 0:
            bookmarks = self.get_bookmarks()
            bookmarks.pop(current)
            self.save_bookmarks(bookmarks)
            self.load_bookmarks()
    
    def open_bookmark(self, item):
        """Open bookmark in new tab"""
        url = item.text().split(" - ")[-1]
        self.parent().add_tab(url)

# ====================== MAIN BROWSER WINDOW ======================
class WebApp(QMainWindow):
    """Main browser application window"""
    def __init__(self, start_url=None):
        super().__init__()
        self.dark_mode = False
        self.incognito = False
        
        # Setup the UI
        self.setup_ui()
        
        # Load previous session
        self.load_session()
        
        # Open initial tab
        if start_url:
            self.add_tab(start_url)
        else:
            self.add_tab()
    
    def setup_ui(self):
        """Initialize the main window UI"""
        self.setWindowTitle("PyBrowser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_ui)
        self.setCentralWidget(self.tabs)
        
        # Create toolbar with actions
        self.setup_toolbar()
    
    def setup_toolbar(self):
        """Create and configure the browser toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # New Tab Button
        new_tab_act = QAction(QIcon.fromTheme("tab-new"), "New Tab (Ctrl+T)", self)
        new_tab_act.setShortcut("Ctrl+T")
        new_tab_act.triggered.connect(lambda: self.add_tab())
        self.toolbar.addAction(new_tab_act)
        
        # Private Tab Button
        new_private_act = QAction(QIcon.fromTheme("private-browsing"), "Private Tab (Ctrl+Shift+T)", self)
        new_private_act.setShortcut("Ctrl+Shift+T")
        new_private_act.triggered.connect(self.add_private_tab)
        self.toolbar.addAction(new_private_act)
        
        # Close Tab Button
        close_tab_act = QAction(QIcon.fromTheme("tab-close"), "Close Tab (Ctrl+W)", self)
        close_tab_act.setShortcut("Ctrl+W")
        close_tab_act.triggered.connect(self.close_current_tab)
        self.toolbar.addAction(close_tab_act)
        
        # Refresh Button
        refresh_act = QAction(QIcon.fromTheme("view-refresh"), "Refresh (F5)", self)
        refresh_act.setShortcut("F5")
        refresh_act.triggered.connect(self.refresh_tab)
        self.toolbar.addAction(refresh_act)
        
        self.toolbar.addSeparator()
        
        # Bookmarks Button
        bookmark_act = QAction(QIcon.fromTheme("bookmark-new"), "Bookmarks (Ctrl+D)", self)
        bookmark_act.setShortcut("Ctrl+D")
        bookmark_act.triggered.connect(self.show_bookmarks)
        self.toolbar.addAction(bookmark_act)
        
        # Dark Mode Toggle
        dark_mode_act = QAction(QIcon.fromTheme("color-management"), "Dark Mode", self)
        dark_mode_act.setCheckable(True)
        dark_mode_act.triggered.connect(self.toggle_dark_mode)
        self.toolbar.addAction(dark_mode_act)
    
    def add_tab(self, url=None, incognito=False):
        """Add a new browser tab"""
        if not url:
            current_tab = self.current_tab()
            if current_tab and current_tab.url() != "about:blank":
                url = current_tab.url()
        
        tab = BrowserTab(url, incognito)
        
        # Connect signals to update UI when page changes
        tab.browser.titleChanged.connect(lambda title, tab=tab: self.update_tab_title(tab))
        tab.browser.iconChanged.connect(lambda icon, tab=tab: self.update_tab_icon(tab, icon))
        
        # Add to tab widget
        index = self.tabs.addTab(tab, "Loading...")
        self.tabs.setTabIcon(index, QIcon.fromTheme("text-html"))
        self.tabs.setCurrentIndex(index)
        
        # If no URL provided, show our custom start page
        if not url:
            tab.browser.setHtml(DEFAULT_START_PAGE)
    
    def add_private_tab(self):
        """Add a new private browsing tab"""
        self.add_tab(incognito=True)
    
    def current_tab(self):
        """Get the currently active tab"""
        return self.tabs.currentWidget()
    
    def close_tab(self, index):
        """Close tab at specified index"""
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            widget.deleteLater()
            self.tabs.removeTab(index)
        else:
            # Don't allow closing the last tab
            QMessageBox.information(self, "Can't close", "You need at least one tab open!")
    
    def close_current_tab(self):
        """Close the currently active tab"""
        self.close_tab(self.tabs.currentIndex())
    
    def refresh_tab(self):
        """Reload the current tab"""
        if current := self.current_tab():
            current.reload()
    
    def update_tab_title(self, tab):
        """Update tab title when page title changes"""
        index = self.tabs.indexOf(tab)
        title = tab.title()[:20]  # Trim long titles
        if title:
            self.tabs.setTabText(index, title)
    
    def update_tab_icon(self, tab, icon):
        """Update tab icon when page icon changes"""
        index = self.tabs.indexOf(tab)
        self.tabs.setTabIcon(index, icon)
    
    def update_ui(self):
        """Update UI elements based on current state"""
        pass  # Could add status updates here
    
    def toggle_dark_mode(self, checked):
        """Toggle between light and dark theme"""
        self.dark_mode = checked
        if checked:
            self.setStyleSheet("""
                QMainWindow, QDialog {
                    background-color: #333;
                    color: #eee;
                }
                QToolBar {
                    background-color: #444;
                    border: none;
                }
                QTabBar::tab {
                    background: #555;
                    color: #fff;
                    padding: 5px;
                }
                QTabBar::tab:selected {
                    background: #777;
                }
            """)
        else:
            self.setStyleSheet("")
    
    def show_bookmarks(self):
        """Show the bookmarks manager dialog"""
        dialog = BookmarksDialog(self)
        dialog.exec_()
    
    def load_session(self):
        """Load previously saved session (open tabs)"""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    session = json.load(f)
                    for url in session.get("urls", []):
                        self.add_tab(url)
            except Exception as e:
                print(f"⚠️ Error loading session: {e}")
    
    def save_session(self):
        """Save current session (open tabs) to file"""
        urls = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab and tab.url() not in ["about:blank", ""]:
                urls.append(tab.url())
        
        with open(SESSION_FILE, "w") as f:
            json.dump({"urls": urls}, f, indent=2)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_session()
        super().closeEvent(event)

# ====================== MAIN APPLICATION ======================
if __name__ == "__main__":
    # Show our awesome banner
    show_banner()
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Try to load custom style if available
    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("ℹ️ No custom style.qss found - using default styling")
    except Exception as e:
        print(f"⚠️ Error loading stylesheet: {e}")
    
    # Get starting URL from command line or user input
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("🌍 Enter starting URL (or press Enter for home page): ").strip() or None
    
    # Create and show main window
    window = WebApp(url)
    window.show()
    
    # Run the application
    sys.exit(app.exec_())
