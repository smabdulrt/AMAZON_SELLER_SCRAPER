import csv
import json
import logging
import time

import scrapy
from scrapy import Request
from scrapy.exceptions import CloseSpider
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class SellercentralSpider(scrapy.Spider):
    name = 'sellercentral'
    start_urls = ['https://www.google.com/']
    options = webdriver.ChromeOptions()
    options.add_argument("user-data-dir=C:\Profile")
    options.add_argument("--start-maximized")
    from selenium.webdriver.remote.remote_connection import LOGGER
    LOGGER.setLevel(logging.WARNING)
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)

    custom_settings = {
        'FEED_URI': 'sellercentral.xlsx',
        'FEED_FORMAT': 'xlsx',
        'FEED_EXPORT_ENCODING': 'utf-8-sig',
        'FEED_EXPORTERS': {'xlsx': 'scrapy_xlsx.XlsxItemExporter'},
    }
    counter = 0
    headers = {
        'authority': 'sellercentral.amazon.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'anti-csrftoken-a2z': 'hAHBRcrb6pQH+PdTwcR3505rtubnd6lKLWsYionGVo5QAAAAAGLZJWM3MTNiZTIzZ'
                              'S1iZDZlLTRkM2MtOTQ4Yi0wMGRiNTZlMjY0YWI=',
        'content-type': 'application/json',
        'origin': 'https://sellercentral.amazon.com',
        'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/103.0.5060.114 Safari/537.36'
    }

    url = "https://sellercentral.amazon.com/orders-api/search?limit=200&offset={page}&sort=ship_by_asc&" \
          "date-range=last-14&fulfillmentType=fba&orderStatus=all&forceOrdersTableRefreshTrigger=false"
    csrf_token = "https://sellercentral.amazon.com/messaging/reviews?orderId={order_id}&marketplaceId=ATVPDKIKX0DER"
    request_review = "https://sellercentral.amazon.com/messaging/api/solicitations/{order_id}/productReviewAndSellerFeedback?marketplaceId=ATVPDKIKX0DER&isReturn=false"

    def parse(self, no_response, **kwargs):
        self.driver.get('https://sellercentral.amazon.com/orders-v3/fba/all?page=1')
        time.sleep(15)
        try:
            self.driver.find_element(By.CSS_SELECTOR, '[type="email"]').clear()
            self.driver.find_element(By.CSS_SELECTOR, '[type="email"]').send_keys('USERNAME')
            self.driver.find_element(By.CSS_SELECTOR, '[type="password"]').send_keys('PASSWORD')
            self.driver.find_element(By.CSS_SELECTOR, '[id="signInSubmit"]').click()
        except Exception as e:
            self.logger.info("Email Already Entered")
        try:
            if self.driver.find_element(By.CSS_SELECTOR, ".a-span12.a-text-left .auth-text-truncate").text:
                self.driver.find_element(By.CSS_SELECTOR, '[type="password"]').send_keys('PASSWORD')
                self.driver.find_element(By.CSS_SELECTOR, '[id="signInSubmit"]').click()
        except Exception as e:
            # self.logger.info(e)
            if self.driver.find_element(By.CSS_SELECTOR, '[data-test-id="tab-/fba/all"] span~span').text:
                self.logger.info("YOUR ALREADY LOGGED IN")
        input('Enter when you are done : ')
        yield Request('https://www.google.com/', self.logins)

    def logins(self, response):
        yield Request(self.url.format(page="1"),
                      cookies=self.driver.get_cookies(),
                      callback=self.pagination,
                      meta={'cookies': self.driver.get_cookies()})

    def pagination(self, response):
        pages = json.loads(response.text).get('total', '')
        if pages < 200:
            pages = 201
        for i in range(0, pages, 200):
            self.driver.refresh()
            time.sleep(5)
            yield Request(url=self.url.format(page=i),
                          cookies=self.driver.get_cookies(),
                          callback=self.parse_detail,
                          meta={'cookies': self.driver.get_cookies()})

    def parse_detail(self, response):
        json_data = json.loads(response.text)['orders']

        records = self.get_search_critaria_from_file()
        file_counter = records[0]['count']

        for order in json_data:
            if self.counter <= int(file_counter):
                market = order.get('homeMarketplaceId', '')
                print(self.csrf_token.format(order_id=order['amazonOrderId']))
                print("Market", market)
                yield Request(url=self.csrf_token.format(order_id=order['amazonOrderId']),
                              cookies=response.meta['cookies'],
                              callback=self.parse_token,
                              headers=self.headers,
                              meta={'cookies': response.meta['cookies'], 'order_id': order['amazonOrderId']})
                self.counter += 1
            else:
                break

    def parse_token(self, response):
        token = response.headers.getlist('Anti-Csrftoken-A2Z')[0].decode("utf-8")
        self.headers['anti-csrftoken-a2z'] = token
        yield Request(
            url=self.request_review.format(order_id=response.meta['order_id']),
            cookies=response.meta['cookies'],
            callback=self.request_reviews,
            method='POST',
            headers=self.headers,
            body=json.dumps({}),
            meta={'order_id': response.meta['order_id']})

    def request_reviews(self, response):
        json_data = json.loads(response.text)
        if json_data.get('ineligibleReason', '') == 'REVIEW_REQUEST_OUTSIDE_TIME_WINDOW' and json_data.get('isSuccess',
                                                                                                           '') is False:
            pass
            # raise CloseSpider('bandwidth_exceeded')

        yield {
            'Order Id': response.meta['order_id'],
            'isSuccess': json_data.get('isSuccess', ''),
            'ineligibleReason': json_data.get('ineligibleReason', ''),
        }

    def get_search_critaria_from_file(self):
        with open(file='amazon_inputs.csv', mode='r', encoding='utf-8') as input_file:
            return list(csv.DictReader(input_file))
