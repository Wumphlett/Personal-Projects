import os
import sys
import time
import requests
import signal
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
        with open(sys.path[0] + '/config.yml', 'r') as ymlfile:
            self.config = yaml.safe_load(ymlfile)
            ymlfile.close()
        self.queue = Queue()
        self.last_tweet = datetime.datetime.now() - datetime.timedelta(minutes=5)
        self.last_article = ''
        self.article_monitoring = Thread(target=self.monitor_feed, daemon=True)
        self.blacklist_monitoring = Thread(target=self.monitor_mentions, daemon=True)
        self.send_notification_tweets = Thread(target=self.send_tweets, daemon=True)
        chrome_options = Options()
        chrome_options.add_argument('--incognito')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=chrome_options, executable_path=self.config['chrome-driver-path'])
        logging.basicConfig(filename=sys.path[0] + '/log.txt', level=logging.INFO, format='%(message)s')
        init_time = datetime.datetime.now().strftime('%H:%M:%S')
        mode = 'instant' if self.config['latest-article'] == 'instant' else 'latest'
        logging.info('START({}):Starting Bot in Mode: {}'.format(init_time, mode))

    def monitor_feed(self):
        try:
            wait = WebDriverWait(self.driver, 15)
            wait.until(lambda x: self.driver.execute_script('return document.readyState') == 'complete')

            if self.last_article == '':
                self.driver.get(self.search_url)
                self.last_article = self.driver.find_element_by_xpath(
                    '//*[@id="mod-search-feed-1"]/div[1]/section/article[1]/a').get_attribute('href')
                now = datetime.datetime.now().strftime('%H:%M:%S')
                logging.info('QUEUE({}):Latest article upon start up is {}'.format(now, self.last_article.split('/')[-1]))
                if self.config['latest-article'].lower() == 'instant':
                    now = datetime.datetime.now().strftime('%H:%M:%S')
                    logging.info('QUEUE({}):Adding {} to queue'.format(now, self.last_article.split('/')[-1]))
                    self.queue.put(self.last_article)

            while self.article_monitoring.is_alive():
                self.driver.get(self.search_url)
                articles = self.driver.find_elements_by_xpath('//*[@id="mod-search-feed-1"]/div[1]/section/article')
                aux = articles[0].find_element_by_xpath('.//a').get_attribute('href')
                articles = [article.find_element_by_xpath('.//a').get_attribute('href') for article in articles]
                if self.last_article not in articles:  # deleted last article check
                    self.last_article = articles[0]
                    continue
                for article_url in articles:
                    if self.last_article == article_url:
                        self.last_article = aux
                        now = datetime.datetime.now().strftime('%H:%M:%S')
                        logging.info('ERROR({}): Last article deleted, setting last to {}'.format(now, articles[0]))
                        break
                    else:
                        self.queue.put(article_url)
                        now = datetime.datetime.now().strftime('%H:%M:%S')
                        logging.info('QUEUE({}):Adding {} to queue'.format(now, article_url.split('/')[-1]))
                now = datetime.datetime.now().strftime('%H:%M:%S')
                logging.info('QUEUE({}):Completed article check'.format(now, self.last_article.split('/')[-1]))
                time.sleep(900)  # in seconds
        except Exception:
            exc_time = datetime.datetime.now().strftime('%H:%M:%S')
            logging.exception('({}):EXCEPTION'.format(exc_time))
            os.system('kill -10 {}'.format(os.getpid()))
            return

    def monitor_mentions(self):
        try:
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
                        with open(sys.path[0] + '/blacklist.txt', 'a') as blacklist:
                            blacklist.write(blacklist_item)
                        now = datetime.datetime.now().strftime('%H:%M:%S')
                        logging.info('BLACK({}):User {} added to blacklist'.format(now, tweet['user']['screen_name']))
                        blacklist.close()
                        if tweet.get('in_reply_to_status_id') is not None:
                            or_tweet = twitter.get_status(tweet['in_reply_to_status_id'])._json['text']
                            if tweet['user'] == or_tweet[:or_tweet.index(',')]:
                                twitter.destroy_status(tweet['in_reply_to_status_id'])
                now = datetime.datetime.now().strftime('%H:%M:%S')
                logging.info('BLACK({}):Completed blacklist check'.format(now, self.last_article.split('/')[-1]))
                time.sleep(900)  # in seconds
        except Exception:
            exc_time = datetime.datetime.now().strftime('%H:%M:%S')
            logging.exception('({}):EXCEPTION'.format(exc_time))
            os.system('kill -10 {}'.format(os.getpid()))
            return

    def send_tweets(self):
        try:
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
                    now = datetime.datetime.now().strftime('%H:%M:%S')
                    logging.info('TWEET({}):Sending {} tweets for {}'.format(now, str(len(tweet_authors)),
                                                                             article_url.split('/')[-1]))
                    for num, author in enumerate(tweet_authors):
                        while datetime.datetime.now() - self.last_tweet < datetime.timedelta(minutes=5):
                            time.sleep(10)
                        if self.check_black_list(author):
                            if author in tweet_authors[:num]:
                                now = datetime.datetime.now().strftime('%H:%M:%S')
                                logging.info('TWEET({}):Duplicate Author ({}), skipping'.format(now, author))
                                continue
                            tweet_body = '{}, your tweet has been used by BuzzFeed likely without your approval' \
                                         '\nThe article can be found here; {}\nTo request removal of your tweet, contact ' \
                                         'them here; {}\nTo stop receiving these notifications, ' \
                                         'reply with the word halt'.format(author, article_url, support)
                            twitter.update_status(tweet_body)
                            now = datetime.datetime.now().strftime('%H:%M:%S')
                            logging.info('TWEET({}):Notification ({}) sent to {} for {}'
                                         .format(now, str(num + 1), author, article_url.split('/')[-1]))
                            self.last_tweet = datetime.datetime.now()
                            time.sleep(300)  # at least 5 min between tweets to avoid bad bot flag
                    self.queue.task_done()
                else:
                    time.sleep(10)
                    continue
        except Exception:
            exc_time = datetime.datetime.now().strftime('%H:%M:%S')
            logging.exception('({}):EXCEPTION'.format(exc_time))
            os.system('kill -10 {}'.format(os.getpid()))
            return

    @staticmethod
    def check_black_list(handle):
        with open(sys.path[0] + '/blacklist.txt', 'r') as blacklist:
            for line in blacklist:
                if handle in line:
                    blacklist.close()
                    return False
            blacklist.close()
        return True

    @staticmethod
    def latest_blacklist_id():
        with open(sys.path[0] + '/blacklist.txt', 'r') as blacklist:
            for line in blacklist:
                pass
            last_line = line
        blacklist.close()
        last_id = last_line[last_line.find(':') + 1:]
        return last_id


def sig_kill(sig_code, frame):
    sig_now = datetime.datetime.now().strftime('%H:%M:%S')
    logging.info('SIGNL({}):Received Signal Code {}'.format(sig_now, sig_code))
    exit_code = 0 if sig_code == 15 else 1
    raise SystemExit(exit_code)


if __name__ == '__main__':
    bt = BuzzThief()
    try:
        signal.signal(signal.SIGTERM, sig_kill)
        signal.signal(signal.SIGUSR1, sig_kill)
        bt.article_monitoring.start()
        bt.blacklist_monitoring.start()
        bt.send_notification_tweets.start()
        bt.article_monitoring.join()
        bt.blacklist_monitoring.join()
        bt.send_notification_tweets.join()
    except SystemExit as se:
        exit_time = datetime.datetime.now().strftime('%H:%M:%S')
        if se.code == 0:
            logging.info('EXIT ({}):Normal System Exit'.format(exit_time))
        else:
            logging.critical('EXIT ({}):Exit Due To Exception'.format(exit_time))
        bt.driver.quit()
        sys.exit(se.code)
    finally:
        sys.exit(0)
