
import re
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotInteractableException

# GLOBALS
CHROME_DRIVER_PATH = "C:\\chromedriver\\chromedriver.exe"

DEFAULT_LABEL_ROW = 1

SHEETS_SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]


BASE_SITE = "https://www.tcgplayer.com/product/"

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
        if not self.JSON_KEYFILE:
            raise AttributeError("No JSON key file to load credentials with.")
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.JSON_KEYFILE, SHEETS_SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open(self.spreadsheet_name).worksheets()[self.spreadsheet_id]
        return sheet


class TCGPlayerSheetManager(BaseSheetDependencyInjectionManager):

    # This will be saved at the root of the project for your service account
    JSON_KEYFILE = "tcgplayertracker-fdff0beefc31.json"
    PRICE_COLUMN = "Current Price (per unit)"
    TOTAL_VALUE_COLUMN = "Total Value"
    SHEET_NAME = "TCG track"
    SHEET_ID = 1

    def getPriceColumn(self, record):
        """(int): Returns the index for the column for where to update the price"""
        keys = list(record.keys())
        return keys.index(self.PRICE_COLUMN) + 1

    def getTotalValueColumn(self, record):
        keys = list(record.keys())
        return keys.index(self.TOTAL_VALUE_COLUMN) + 1

    def getLinkToProduct(self, row):
        product_id = row['TCG Product ID']
        if not product_id:
            return None
        return "{}{}".format(BASE_SITE, str(product_id))

    def getPricingSection(self):
        """Returns class name for the pricing section"""
        return "price-guide__points"

    def getPricing(self, driver):
        section_name = TCGPlayerSheetManager.shared_instance().getPricingSection()
        price_point = driver.find_element(By.CLASS_NAME, section_name)
        # Get the first price as this is the market price
        # price_span_element = price_point.find_element(By.CLASS_NAME, "price")
        price_span_element = price_point.find_element(By.CLASS_NAME, "price-points__upper__price")
        price_text = price_span_element.get_attribute("innerHTML")
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


    def updatePricing(self, driver):
        print("Getting all records")
        records = self.sheet.get_all_records()
        for (i, record) in enumerate(records):
            # Row starts at 2
            row = i + 2 
            link = self.getLinkToProduct(record)
            if not link:
                continue
            print("Getting price for {}".format(self.getProductName(record)))
            driver.get(link)
            # Have the web driver wait until it loads the title
            element = WebDriverWait(driver, 20).until(
                EC.all_of(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "price-points__upper__price"))
                    # EC.presence_of_element_located((By.CLASS_NAME, "product-details__price-guide")), 
                    # EC.presence_of_element_located((By.CLASS_NAME, "price-points__rows")), 
                    # EC.presence_of_all_elements_located((By.CLASS_NAME, "price"))
                )
            )
            price = self.getPricing(driver)
            # If there are no sold price, set price to nothing
            if price != '-':
                priceFloat = float(price.lstrip("$"))
            print("Updating price: {}".format(price))
            column = self.getPriceColumn(record)
            self.sheet.update_cell(row, column, price)
            
            # Get the total value
            totalValue = self.getTotalValue(priceFloat, record)
            totalValueColumn = self.getTotalValueColumn(record)
            self.sheet.update_cell(row, totalValueColumn, totalValue)

def create_web_driver():
    """Creates the web driver to run the script for searching the site."""
    driver = webdriver.Firefox()
    return driver

def update_sheet(sheet, row, col, val):
    sheet.update_cell(row, col, val)

def update_sheet_records(rows=None):
    """Iterates through the records finding any shoes we have and will retrieve
    the pricing from stock X to update.

    Args:
        rows(list<int>): List of rows to specifically check
    """
    if rows is None:
        rows = []

    print("Loading web driver")
    driver = create_web_driver()
    print("Getting data from google sheet")
    manager = TCGPlayerSheetManager.shared_instance()
    manager.load()
    # sheet = manager.sheet
    manager.updatePricing(driver)

def main():
    update_sheet_records()

if __name__ == "__main__":
    main()