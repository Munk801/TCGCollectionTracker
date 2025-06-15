
import argparse
import os
import re
import sys
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotInteractableException

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# GLOBALS
CHROME_DRIVER_PATH = "C:\\chromedriver\\chromedriver.exe"

DEFAULT_LABEL_ROW = 1

SHEETS_SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]


BASE_SITE = "https://www.tcgplayer.com/product/"
PRODUCT_ID_REGEX = r"product/(\d+)"

class BaseSheetDependencyInjectionManager(object):

    JSON_KEYFILE = ""
    SHEET_NAME = ""
    SHEET_ID = 0

    _INSTANCE = None

    def __init__(self, spreadsheet_name, sheet_id, label_row=1):
        self.spreadsheet_name = spreadsheet_name
        self.spreadsheet_id = sheet_id
        self.label_row = label_row
        self._sheet = self.load()

    @property
    def sheet(self):
        return self._sheet

    @classmethod
    def shared_instance(cls):
        if cls._INSTANCE is None:
            name = cls.SHEET_NAME
            sheet_id = cls.SHEET_ID
            cls._INSTANCE = cls(name, sheet_id)
        return cls._INSTANCE

    def getColumnForValue(self):
        return 100

    def load(self):
        """Creates and authorizes a client and returns the google sheet.
        """
        json_keyfile = self.findJSONKeyFile()
        if not json_keyfile:
            raise AttributeError("No JSON key file to load credentials with.")
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, SHEETS_SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open(self.spreadsheet_name).worksheets()[self.spreadsheet_id]
        return sheet
    
    def findJSONKeyFile(self):
        """Finds the JSON key file for the service account.

        Returns:
            str: The path to the JSON key file.
        """
        files = os.listdir('.')
        for file in files:
            # print(f"File: {file}")
            if re.match(self.JSON_KEYFILE, file):
                return file
        return None


class TCGPlayerSheetManager(BaseSheetDependencyInjectionManager):

    # This will be saved at the root of the project for your service account
    JSON_KEYFILE = "tcgplayertracker.*\.json"
    PRICE_COLUMN = "Current Price (per unit)"
    TOTAL_VALUE_COLUMN = "Total Value"
    TCG_PRODUCT_ID_COLUMN = "TCG Product ID"
    SERIES_COLUMN = "Series"
    PRODUCT_NAME_COLUMN = "Product Name"
    TCG_LINK_COLUMN = "TCG Link"
    UNIT_PRICE_COLUM = "Current Price (per unit)"
    TOTAL_PRICE_COLUMN = "Total Value"
    SHEET_NAME = "TCG track"
    SHEET_ID = 1
    PRODUCT_FILTERS = {
        "Condition": "Near Mint",
    }
    COLUMN_OFFSET = 1  # Offset for the column index since gspread is 1-indexed

    def getTCGLinkColumn(self, record):
        """(int): Returns the index for the column for where to update the TCG link"""
        keys = list(record.keys())
        return keys.index(self.TCG_LINK_COLUMN) + 1

    def getSetNameColumn(self, record):
        """(int): Returns the index for the column for where to update the set name"""
        keys = list(record.keys())
        return keys.index(self.SERIES_COLUMN) + 1
    
    def getProductNameColumn(self, record): 
        """(int): Returns the index for the column for where to update the product name"""
        keys = list(record.keys())
        return keys.index(self.PRODUCT_NAME_COLUMN) + 1

    def getPriceColumn(self, record):
        """(int): Returns the index for the column for where to update the price"""
        keys = list(record.keys())
        return keys.index(self.PRICE_COLUMN) + 1

    def getTotalValueColumn(self, record):
        keys = list(record.keys())
        return keys.index(self.TOTAL_VALUE_COLUMN) + 1
    
    def getTCGProductIDColumn(self, record):
        """(int): Returns the index for the column for where to update the TCG Product ID"""
        keys = list(record.keys())
        return keys.index(self.TCG_PRODUCT_ID_COLUMN) + 1
    
    def getProductIDFromLink(self, record):
        # If the ID doesn't exist, check if the link is already there
        # another way
        link = record['TCG Link']
        print("Link: {}".format(link))
        if not link:
            return None
        match = re.search(PRODUCT_ID_REGEX, link)
        if not match:
            return None
        product_id = match.group(1)
        print("Found Product ID: {}".format(product_id))
        return product_id
        # Update the product ID in the sheet
        # self.sheet.update_cell(row, self.getTCGProductIDColumn(record), product_id)

    def getLinkToProduct(self, record, row):
        """Gets the link to the product on TCGPlayer.  
        If the link already  exist, it will try to find the product ID
        """
        product_id = record['TCG Product ID']
        if not product_id:
            return None

        return "{site}{product_id}".format(
            site=BASE_SITE, 
            product_id=str(product_id),
        )

    def getPricingSection(self):
        """Returns class name for the pricing section"""
        return "price-guide__points"
    
    def getProductHeaderSection(self):
        return "product-details__header"
    
    def getProductSubHeaderSection(self):
        return "product-details__name__sub-header"
    
    def getProductTitleSection(self):
        return "product-details__name"

    def getPricing(self, driver):
        section_name = TCGPlayerSheetManager.shared_instance().getPricingSection()
        price_point = driver.find_element(By.CLASS_NAME, section_name)
        # Get the first price as this is the market price
        # price_span_element = price_point.find_element(By.CLASS_NAME, "price")
        price_span_element = price_point.find_element(By.CLASS_NAME, "price-points__upper__price")
        price_text = price_span_element.get_attribute("innerHTML")
        return price_text 
    
    def getSetName(self, driver):
        # section_name = TCGPlayerSheetManager.shared_instance().getProductSubHeaderSection()
        # product_header = driver.find_element(By.CLASS_NAME, section_name)
        # product_name_section = TCGPlayerSheetManager.shared_instance().getProductTitleSection()
        # product_title_element = product_header.find_element(By.CLASS_NAME, product_name_section)
        span = driver.find_element(By.CSS_SELECTOR, '[data-testid="lblProductDetailsSetName"]')
        innerHTML = span.get_attribute('innerHTML')
        return innerHTML

    def getProductFullName(self, driver):
        section_name = TCGPlayerSheetManager.shared_instance().getProductHeaderSection()
        product_header = driver.find_element(By.CLASS_NAME, section_name)
        # Get the first price as this is the market price
        # price_span_element = price_point.find_element(By.CLASS_NAME, "price")
        product_name_section = TCGPlayerSheetManager.shared_instance().getProductTitleSection()
        product_title_element = product_header.find_element(By.CLASS_NAME, product_name_section)
        price_text = product_title_element.get_attribute("innerHTML")
        return price_text 

    def getProductName(self, record):
        return "{} {} {}".format(
            record['Game'],
            record['Series'], 
            record['Product Name']
        )

    def getQuantity(self, record):
        return int(record["Number"])

    def getTotalValue(self, price, record):
        return "${:.2f}".format(price * self.getQuantity(record))

    def hasPricingElement(self, driver):
        section_name = TCGPlayerSheetManager.shared_instance().getPricingSection()
        price_point = driver.find_element(By.CLASS_NAME, section_name)
        # Get the first price as this is the market price
        # price_span_element = price_point.find_element(By.CLASS_NAME, "price")
        price_span_element = price_point.find_element(By.CLASS_NAME, "price-points_upper__price")
        price_text = price_span_element.get_attribute("innerHTML")
    
    def loadUrlWithAdditionalQueryParams(self, driver, url):
        # Get the current URL after any redirects/changes
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        # Parse the URL
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        
        # Add new parameters
        params.update(self.PRODUCT_FILTERS)
        # Rebuild the URL
        new_query = urlencode(params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        print(f"Modified URL: {new_url}") 
        # Navigate to the modified URL
        driver.get(new_url)

    def batchUpdatePricing(self, record, row):
        requests = []
        values = list(record.values())
        lengthValues = len(record.values())
        
        # Convert to A1 notation
        end_col = chr(ord('A') + lengthValues - 1)
        range_name = f"A{row}:{end_col}{row}"
        
        requests.append({
            'range': range_name,
            'values': [values]
        })
        
        if requests:
            print("Batch Updating with requests: {}".format(requests))
            self.sheet.batch_update(requests, value_input_option='USER_ENTERED')

    def updatePricing(self, driver, start_row=None):
        print("Getting all records")
        records = self.sheet.get_all_records()
        # print("Records: {}".format(records))
        for (i, record) in enumerate(records):
            # Skip the first record
            # Row starts at 2
            row = i + 2
            if start_row and row < start_row:
                print("Skipping row {} as it is before the start row {}".format(row, start_row))
                continue
            # If the link doesn't exist, check if it exists in another column
            product_id = self.getProductIDFromLink(record)
            if not record['TCG Product ID']:
                record['TCG Product ID'] = product_id
            link = self.getLinkToProduct(record, row)
            if not link:
                continue
            print("Getting price for {}".format(self.getProductName(record)))
            driver.get(link)
            if "Single" in record['Game']:
                # Reload the url with additional options
                self.loadUrlWithAdditionalQueryParams(driver, link)

            # Have the web driver wait until it loads the title
            element = WebDriverWait(driver, 20).until(
                EC.all_of(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "price-points__upper__price"))
                    # EC.presence_of_element_located((By.CLASS_NAME, "product-details__price-guide")), 
                    # EC.presence_of_element_located((By.CLASS_NAME, "price-points__rows")), 
                    # EC.presence_of_all_elements_located((By.CLASS_NAME, "price"))
                )
            )
            if not record['TCG Link']:
                record['TCG Link'] = driver.current_url
                # self.sheet.update_cell(row, self.getTCGLinkColumn(record), driver.current_url)

            product_name = self.getProductFullName(driver)
            # print("Product Name: {}".format(product_name))
            if record['Product Name'] != product_name:
                record['Product Name'] = product_name
                column = self.getProductNameColumn(record)
                print("Updating product name: {} at row {} column {}".format(product_name, row, column))
                # self.sheet.update_cell(row, column, product_name)

            set_name = self.getSetName(driver)
            if record['Series'] != set_name:
                record['Series'] = set_name
                column = self.getSetNameColumn(record)
                print("Updating set name: {} at row {} column {}".format(set_name, row, column))
                # self.sheet.update_cell(row, column, set_name)
            # print("Set Name: {}".format(set_name))

            price = self.getPricing(driver)
            # If there are no sold price, set price to nothing
            if price != '-':
                priceFloat = float(price.replace("$", "").replace(",", ""))
            # price = price.strip("$")
            print("Updating price: {}".format(price))
            column = self.getPriceColumn(record)
            if record[self.UNIT_PRICE_COLUM] != price:
                record[self.UNIT_PRICE_COLUM] = price
                # Update the price in the sheet
            # self.sheet.update_cell(row, column, price)
            
            # Get the total value
            totalValue = self.getTotalValue(priceFloat, record)
            # totalValue = totalValue.strip("$")
            totalValueColumn = self.getTotalValueColumn(record)
            if record[self.TOTAL_PRICE_COLUMN] != totalValue:
                record[self.TOTAL_PRICE_COLUMN] = totalValue

            self.batchUpdatePricing(record, row)
            # self.sheet.update_cell(row, totalValueColumn, totalValue)

            # If we ran through 30 products, close the driver to avoid memory issues
            if i % 30 == 0:
                print("Closing web driver to avoid memory issues")
                driver.quit()
                print("Recreating web driver")
                driver = create_web_driver()

        # Quit the driver after all records are processed
        driver.quit()

def create_web_driver():
    """Creates the web driver to run the script for searching the site."""
    driver = webdriver.Firefox()
    return driver

def update_sheet(sheet, row, col, val):
    sheet.update_cell(row, col, val)

def update_sheet_records(start_row=None):
    """Iterates through the records finding any shoes we have and will retrieve
    the pricing from stock X to update.

    Args:
        rows(list<int>): List of rows to specifically check
    """
    print("Loading web driver")
    driver = create_web_driver()
    print("Getting data from google sheet")
    manager = TCGPlayerSheetManager.shared_instance()
    manager.load()
    # sheet = manager.sheet
    manager.updatePricing(driver, start_row=start_row)

def main():
    parser = argparse.ArgumentParser(description='Process spreadsheet data')
    
    # Optional argument with default value
    parser.add_argument(
        '--start-row', 
        type=int, 
        default=1, 
        help='Row number to start processing from (default: 1)'
    )
    
    args = parser.parse_args()
    update_sheet_records(start_row=args.start_row)

if __name__ == "__main__":
    main()