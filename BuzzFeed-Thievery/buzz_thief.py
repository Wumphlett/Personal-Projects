import time
import requests
import tweepy
import yaml
import logging
from threading import Thread
from queue import Queue
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


class BuzzThief:
    def __init__(self):
        self.search_url = 'https://www.buzzfeed.com/search?q=tweets'
        with open('config.yml', 'r') as ymlfile:
            self.config = yaml.safe_load(ymlfile)
            ymlfile.close()
        self.queue = Queue()
        self.last_tweet = datetime.datetime.now() - datetime.timedelta(minutes=15)
        self.last_article = ''
        self.article_monitoring = Thread(target=self.monitor_feed, daemon=True)
        self.blacklist_monitoring = Thread(target=self.monitor_mentions, daemon=True)
        self.send_notification_tweets = Thread(target=self.send_tweets, daemon=True)
        chrome_options = Options()
        # chrome_options.add_argument('--headless')
        # chrome_options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=chrome_options, executable_path=self.config['chrome-driver-path'])
        logging.basicConfig(filename='log.txt', level=logging.INFO)

    def monitor_feed(self):
        wait = WebDriverWait(self.driver, 15)
        wait.until(lambda x: self.driver.execute_script('return document.readyState') == 'complete')

        if self.last_article == '':
            self.driver.get(self.search_url)
            self.last_article = self.driver.find_element_by_xpath(
                '//*[@id="mod-search-feed-1"]/div[1]/section/article[1]/a').get_attribute('href')
            if self.config['latest-article'].lower() == 'instant':
                logging.info('QUEUE:Adding ' + self.last_article + ' to queue')
                self.queue.put(self.last_article)

        while self.article_monitoring.is_alive():
            self.driver.get(self.search_url)
            articles = self.driver.find_elements_by_xpath('//*[@id="mod-search-feed-1"]/div[1]/section/article')
            for article in articles:
                article_url = article.find_element_by_xpath('.//a').get_attribute('href')
                if self.last_article == article_url:
                    break
                else:
                    self.queue.put(article_url)
                    logging.info('QUEUE:Adding ' + article_url + ' to queue')
                    self.last_article = article_url
            time.sleep(60)  # in seconds

    def monitor_mentions(self):
        keys_dict = self.config['twitter-auth-keys']
        auth = tweepy.OAuthHandler(keys_dict['Consumer Key'], keys_dict['Consumer Secret'])
        auth.set_access_token(keys_dict['Access Token'], keys_dict['Access Token Secret'])
        twitter = tweepy.API(auth)

        while self.blacklist_monitoring.is_alive():
            latest_halt_id = self.latest_blacklist_id()
            if not latest_halt_id.isdigit():
                latest_halt_id = '100000'

            mentions = twitter.mentions_timeline(latest_halt_id)
            mentions.reverse()
            for mention in mentions:
                tweet = mention._json
                if 'halt' in tweet['text'].lower():
                    blacklist_item = '\n@{}:{}'.format(tweet['user']['screen_name'], tweet['id_str'])
                    with open('blacklist.txt', 'a') as blacklist:
                        blacklist.write(blacklist_item)
                    logging.info('BLACK:User ' + tweet['user']['screen_name'] + ' added to blacklist')
                    blacklist.close()
                    if tweet.get('in_reply_to_status_id') is not None:
                        twitter.destroy_status(tweet['in_reply_to_status_id'])
            time.sleep(20)  # in seconds

    def send_tweets(self):
        support = 'https://www.buzzfeed.com/about/contact'

        keys_dict = self.config['twitter-auth-keys']
        auth = tweepy.OAuthHandler(keys_dict['Consumer Key'], keys_dict['Consumer Secret'])
        auth.set_access_token(keys_dict['Access Token'], keys_dict['Access Token Secret'])
        twitter = tweepy.API(auth)

        while self.send_notification_tweets.is_alive():
            if not self.queue.empty():
                article_url = self.queue.get()
                tweet_authors = []
                response = requests.get(article_url)
                for line in response.text.split('\n'):
                    if 'class="subbuzz-tweet__username' in line:
                        start = line.find('>') + 1
                        end = line.rfind('<')
                        tweet_authors.append(line[start:end])
                for author in tweet_authors:
                    while datetime.datetime.now() - self.last_tweet < datetime.timedelta(minutes=15):
                        time.sleep(10)
                    if self.check_black_list(author):
                        tweet_body = '{}, your tweet has been used by BuzzFeed likely without your consent. ' \
                                     '\nThe article can be found here; {}\nTo request removal of your tweet, contact ' \
                                     'them here; {}\nTo stop receiving these notifications, ' \
                                     'reply with the word halt.'.format(author, article_url, support)
                        logging.info('TWEET:' + 'Notification sent to ' + author + ' for ' + article_url)
                        twitter.update_status(tweet_body)
                        self.last_tweet = datetime.datetime.now()
                        time.sleep(900)  # at least 15 min between tweets to avoid bad bot flag
                self.queue.task_done()
            else:
                time.sleep(10)
                continue

    @staticmethod
    def check_black_list(handle):
        with open('blacklist.txt', 'r') as blacklist:
            for line in blacklist:
                if handle in line:
                    blacklist.close()
                    return False
            blacklist.close()
        return True

    @staticmethod
    def latest_blacklist_id():
        with open('blacklist.txt', 'r') as blacklist:
            for line in blacklist:
                pass
            last_line = line
        blacklist.close()
        last_id = last_line[last_line.find(':') + 1:]
        return last_id


if __name__ == '__main__':
    try:
        bt = BuzzThief()
        bt.article_monitoring.start()
        bt.blacklist_monitoring.start()
        bt.send_notification_tweets.start()
        bt.article_monitoring.join()
        bt.blacklist_monitoring.join()
        bt.send_notification_tweets.join()
    except Exception as e:
        logging.critical(str(e))
        raise SystemExit
    finally:
        bt.driver.quit()
        for log in bt.log_files:
            log.close()
