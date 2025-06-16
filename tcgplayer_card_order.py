from collections import OrderedDict
import re
import time

import PyPDF2
from PySide6 import QtWidgets, QtCore, QtGui

from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

def get_lazy_loaded_content_selenium(url, wait_time=10):
    """
    Use Selenium to wait for lazy-loaded content, then parse with BeautifulSoup
    """
    # Setup Firefox options
    firefox_options = Options()
    firefox_options.add_argument("--headless")  # Run in background
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    firefox_options.add_argument("--width=1920")
    firefox_options.add_argument("--height=1080")
    
    # Optional: Set custom user agent
    firefox_options.set_preference("general.useragent.override", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
    
    # Optional: Disable images for faster loading (if you don't need them)
    # firefox_options.set_preference("permissions.default.image", 2)
    
    driver = webdriver.Firefox(options=firefox_options)

    try:
        # Load the page
        driver.get(url)
        
        # Wait for specific elements to load (adjust selector as needed)
        wait = WebDriverWait(driver, wait_time)
        
        # Example: Wait for images to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
        
        # Additional wait for lazy loading
        time.sleep(2)
        
        # Get the final HTML after all content is loaded
        html = driver.page_source
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        return soup
        
    finally:
        driver.quit()

def fetch_tcgplayer_image(soup):
    """
    Fetch product image from TCGPlayer URL and return as QPixmap
    
    Args:
        product_url (str): TCGPlayer product URL
        
    Returns:
        QPixmap: Image as QPixmap, or None if failed
    """
    try:
        # Request headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Get the product page
        # response = requests.get(product_url, headers=headers, timeout=10)
        # response.raise_for_status()
        
        # # Parse the HTML
        # soup = BeautifulSoup(response.content, 'html.parser')
        
        # TCGPlayer image selectors (try multiple approaches)
        image_url = None
        
        # Method 1: Look for specific TCGPlayer image classes
        selectors = [
            'img.product-image__image',
            'img[data-testid="product-image"]',
            '.product-image img',
            '.product-details img',
            'img[alt*="Product Image"]',
            '.primary-image img',
            'lazy-image__wrapper',
        ]
        
        for selector in selectors:
            # print(f"Trying selector: {selector}")
            img_tag = soup.select_one(selector)
            if img_tag:
                srcset = img_tag.get('srcset')
                pattern = r'(https://[^\s]+1000x1000\.jpg)\s+1000w'
                match = re.search(pattern, srcset)
                if match:
                    image_url = match.group(1)
                else:
                    # Fallback to src or data-src
                    image_url = img_tag.get('src') or img_tag.get('data-src')
                if image_url:
                    break
        
        # Method 2: Fallback - look for any image with product-like characteristics
        # if not image_url:
        #     for img in soup.find_all('img'):
        #         src = img.get('src') or img.get('data-src', '')
        #         alt = img.get('alt', '').lower()
                
        #         # Look for images that are likely product images
        #         if (any(keyword in src for keyword in ['product', 'card', 'image']) or
        #             any(keyword in alt for keyword in ['product', 'card', 'image']) or
        #             any(ext in src for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                    
        #             if 'tcgplayer' in src or src.startswith('/'):
        #                 image_url = src
        #                 break
        
        if not image_url:
            print("No product image found on the page")
            return None
        
        # Convert relative URL to absolute
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            image_url = 'https://www.tcgplayer.com' + image_url
        
        print(f"Found image URL: {image_url}")
        
        # Download the image
        img_response = requests.get(image_url, headers=headers, timeout=10)
        img_response.raise_for_status()
        
        # Create QPixmap from image data
        pixmap = QtGui.QPixmap()
        success = pixmap.loadFromData(img_response.content)
        
        if success:
            print(f"Successfully loaded image: {pixmap.width()}x{pixmap.height()}")
            return pixmap
        else:
            print("Failed to create QPixmap from image data")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def extract_order_details(pdf_path):
    order_details = []
    urls = OrderedDict()
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for (page_num, page) in enumerate(reader.pages):
            if '/Annots' in page:
                annotations = page['/Annots']
                
                for annotation in annotations:
                    annotation_obj = annotation.get_object()
                    
                    # Check if it's a link annotation
                    if annotation_obj.get('/Subtype') == '/Link':
                        # Check for URI action
                        if '/A' in annotation_obj:
                            action = annotation_obj['/A']
                            if '/URI' in action:
                                url = action['/URI']
                                # TODO, replace this with the actual text content if possible
                                urls[url] = url
                    if annotation_obj.get('/Subtype') == "/Text":
                        print(annotation_obj["/Contents"])
        print("Extracted URLs:")
        urls = [url for url in urls if 'productCatalog' in url]
        for url in urls:
            print(f"{url}")
        return urls

class OrderWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.urls = [] 

        self.setWindowTitle("TCGPlayer Order Details")
        self.setGeometry(100, 100, 800, 600)
        # TODO Add a QFileDialog to select the PDF file
        # TODO Add a progress bar while loading images
        # TODO Add some sort of checkbox to mark which items have been found
        # TODO Add a button to save the order details to excel sheet

        self.setupUi()

    def setupUi(self): 

        self.layout = QtWidgets.QVBoxLayout()

        fileLayout = QtWidgets.QHBoxLayout()
        fileLabel = QtWidgets.QLabel("TCGPlayer Order PDF:")
        fileLayout.addWidget(fileLabel)
        self.filePath = QtWidgets.QLineEdit()
        self.filePath.setReadOnly(True)
        fileLayout.addWidget(self.filePath)
        browseButton = QtWidgets.QPushButton("Browse")
        browseButton.clicked.connect(self._openPDFFile)
        fileLayout.addWidget(browseButton)
        fileLayout.setContentsMargins(10, 10, 10, 10)
        self.layout.addLayout(fileLayout)

        # Process
        processLayout = QtWidgets.QHBoxLayout() 
        processButton = QtWidgets.QPushButton("Process Order")
        processButton.clicked.connect(self.process_order)
        processLayout.addWidget(processButton)
        processLayout.setContentsMargins(10, 10, 10, 10)
        self.layout.addLayout(processLayout)

        self.order_list_widget = QtWidgets.QListWidget()
        self.order_list_widget.setIconSize(QtCore.QSize(200, 200))
        self.order_list_widget.setSpacing(10)
        

        container = QtWidgets.QWidget()

        self.layout.addWidget(self.order_list_widget)
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def populate_order_list(self):
        self.order_list_widget.clear()
        # Process the urls
        for url in self.urls:
            soup = get_lazy_loaded_content_selenium(url)

            pixmap = fetch_tcgplayer_image(soup)
            icon = QtGui.QIcon()
            if pixmap:
                icon = QtGui.QIcon(pixmap)
            list_widget_item = QtWidgets.QListWidgetItem(icon, url)
            if pixmap:
                # Doesn't seem to be working on macos. Need to test on windows
                tooltip = self.create_tooltip_with_large_icon(
                        pixmap, 
                        tooltip_text=url, 
                        icon_size=(1000, 1000)
                    )
                list_widget_item.setToolTip(tooltip)
            self.order_list_widget.addItem(QtWidgets.QListWidgetItem(icon, url))

    def _openPDFFile(self):
        """Open a file dialog to select the PDF file"""
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select TCGPlayer Order PDF", "", 
            "PDF Files (*.pdf);;All Files (*)", options=options
        )
        if file_path:
            self.filePath.setText(file_path)
            self.pdf_file = file_path

    def process_order(self):
        """Process the order by extracting details from the PDF"""
        pdf_path = self.pdf_file
        self.urls = extract_order_details(pdf_path)
        if not self.urls:
            QtWidgets.QMessageBox.warning(self, "No URLs Found", "No TCGPlayer product URLs found in the PDF.")
            return
        self.populate_order_list()

    def create_tooltip_with_large_icon(self, icon_path, tooltip_text="", icon_size=(128, 128)):
        """Create HTML tooltip with enlarged icon"""
        # Load and scale the pixmap
        pixmap = QtGui.QPixmap(icon_path).scaled(
            icon_size[0], icon_size[1], 
            QtCore.Qt.KeepAspectRatio, 
            QtCore.Qt.SmoothTransformation
        )
        
        # Convert pixmap to base64 for HTML embedding
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        image_data = buffer.data().toBase64().data().decode()
        buffer.close()
        
        # Create HTML tooltip
        html_tooltip = f'''
        <div>
            <img src="data:image/png;base64,{image_data}" style="display:block; margin:5px;">
            <p>{tooltip_text}</p>
        </div>
        '''
        return html_tooltip

def main():
    # Use the pixmap in your QLabel or other widget
    # label.setPixmap(pixmap)
    # Or scale it first:
    # scaled_pixmap = pixmap.scaled(300, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    # label.setPixmap(scaled_pixmap)
    path = "/Users/stephenlu/Downloads/TCGplayer Seller Portal.pdf"
    app = QtWidgets.QApplication([])
    window = OrderWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()