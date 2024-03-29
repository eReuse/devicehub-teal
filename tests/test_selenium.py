# Generated by Selenium IDE
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options


class TestSelenium:
    def setup_method(self, method):
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Firefox(
            options=options, executable_path=r'./bin/geckodriver'
        )
        self.vars = {}

    def teardown_method(self, method):
        self.driver.quit()

    def test_selenium(self):
        # setup
        self.driver.get("http://localhost:5000/login/")
        self.driver.set_window_size(1920, 1063)

        # login
        self.driver.find_element(By.ID, "yourEmail").click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(By.ID, "id_password").send_keys("1234")
        self.driver.find_element(By.ID, "yourEmail").send_keys("user@dhub.com")
        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.driver.implicitly_wait(3)

        # select the first lot and get the ID of it
        self.driver.find_element(By.LINK_TEXT, "Temporary Lots").click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(
            By.CSS_SELECTOR, "#temporal-lots-nav > li:nth-child(2) span"
        ).click()
        self.driver.implicitly_wait(3)
        lot_id = self.driver.current_url.split("/")[5]

        # go to unassigned
        # self.driver.find_element(By.CSS_SELECTOR, ".nav-item:nth-child(5) span").click()
        self.driver.find_element(By.CSS_SELECTOR, ".nav-item:nth-child(7) span").click()
        self.driver.implicitly_wait(3)

        # select the first device

        self.driver.find_element(
            By.CSS_SELECTOR, "tr:nth-child(1) .deviceSelect"
        ).click()
        self.driver.implicitly_wait(3)

        # add to new selenium_lot
        self.driver.find_element(By.ID, "btnLots").click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(By.ID, lot_id).click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(By.ID, "ApplyDeviceLots").click()
        time.sleep(3)
        element = self.driver.find_element(By.ID, "ApplyDeviceLots")
        time.sleep(3)
        actions = ActionChains(self.driver)
        time.sleep(3)
        actions.move_to_element(element).perform()
        time.sleep(3)
        element = self.driver.find_element(By.CSS_SELECTOR, "body")
        time.sleep(3)
        actions = ActionChains(self.driver)
        time.sleep(3)
        # actions.move_to_element(element, 0, 0).perform()
        actions.move_to_element(element).perform()
        time.sleep(3)
        self.driver.find_element(By.ID, "SaveAllActions").click()
        time.sleep(3)

        # go to selenium lot
        self.driver.find_element(By.LINK_TEXT, "Temporary Lots").click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(
            By.CSS_SELECTOR, "#temporal-lots-nav > li:nth-child(2) span"
        ).click()
        self.driver.implicitly_wait(3)

        # select the first device
        self.driver.find_element(By.CSS_SELECTOR, ".deviceSelect").click()

        # remove to new selenium_lot
        self.driver.find_element(By.ID, "btnLots").click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(By.ID, lot_id).click()
        self.driver.implicitly_wait(3)
        self.driver.find_element(By.ID, "ApplyDeviceLots").click()
        time.sleep(3)
        self.driver.find_element(By.ID, "SaveAllActions").click()
        time.sleep(3)

        # self.driver.find_element(By.CSS_SELECTOR, ".nav-item:nth-child(5) span").click()
        self.driver.find_element(By.CSS_SELECTOR, ".nav-item:nth-child(7) span").click()
        self.driver.implicitly_wait(3)

        # logout
        # self.driver.find_element(By.CSS_SELECTOR, ".d-md-block:nth-child(2)").click()
        self.driver.find_element(By.CSS_SELECTOR, ".d-md-block:nth-child(2)").click()
        self.driver.find_element(
            By.CSS_SELECTOR, "li:nth-child(9) > .dropdown-item > span"
        ).click()
        # self.driver.find_element(By.CSS_SELECTOR, ".d-md-block").click()
        # self.driver.implicitly_wait(3)
        # self.driver.find_element(By.LINK_TEXT, "Sign Out").click()
