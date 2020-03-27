import os, io, time
import requests
import tweepy
import yaml
from multiprocessing import Process
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_latest_article(url):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_options, executable_path=config_driver())
    driver.get(url)

    file_name = get_temp_html()
    with io.open(file_name, 'w', encoding='utf-8') as latest:
        latest.write(driver.page_source)
    latest.close()

    html_line = ''
    with io.open(file_name, 'r', encoding='utf-8') as latest:
        for line in latest:
            if 'class="xs-block xs-overflow-hidden"' in line:
                html_line = line
                break
    latest.close()
    os.remove(file_name)
    start = html_line.find('href="') + len('href="')
    html_line = html_line[start:]
    end = html_line.find('"')
    latest_url = html_line[:end]

    return latest_url


def get_buzzfeed_handles(url):
    if not url:
        return
    response = requests.get(url)

    file_name = get_temp_html()
    with io.open(file_name, 'w+', encoding='utf-8') as f:
        f.write(response.text)
        f.close()

    handles = []
    with io.open(file_name, 'r', encoding='utf-8') as f:
        for line in f:
            if 'subbuzz-tweet__username' in line:
                start = line.find('>') + 1
                end = line.rfind('<')
                handles.append(line[start:end])
    f.close()
    os.remove(file_name)
    return handles


def send_tweet(handles, article):
    support = 'https://www.buzzfeed.com/about/contact'
    keys_dict = config_keys()
    auth = tweepy.OAuthHandler(keys_dict['Consumer Key'], keys_dict['Consumer Secret'])
    auth.set_access_token(keys_dict['Access Token'], keys_dict['Access Token Secret'])
    twitter = tweepy.API(auth)
    for handle in handles:
        if check_black_list(handle):
            tweet_body = '{}, your tweet has been used by BuzzFeed likely without your consent. ' \
                         '\nThe article can be found here; {}\nTo request removal of your tweet, contact ' \
                         'them here; {}\nTo stop receiving these notifications, ' \
                         'reply with the word halt.'.format(handle, article, support)
            twitter.update_status(tweet_body)
            time.sleep(6)


def monitor_feed(search_url):
    latest_article_url = ''
    send_now = config_latest()
    while True:
        next_latest_url = get_latest_article(search_url)
        if next_latest_url != latest_article_url and send_now:
            latest_article_url = next_latest_url
            send_tweet(get_buzzfeed_handles(latest_article_url), latest_article_url)
        elif next_latest_url != latest_article_url:
            latest_article_url = next_latest_url
            send_now = True
        time.sleep(60)  # in seconds


def monitor_mentions():
    keys_dict = config_keys()
    auth = tweepy.OAuthHandler(keys_dict['Consumer Key'], keys_dict['Consumer Secret'])
    auth.set_access_token(keys_dict['Access Token'], keys_dict['Access Token Secret'])
    twitter = tweepy.API(auth)

    while True:
        latest_halt_id = latest_blacklist_id()
        if latest_halt_id == 'status id' or '' or None: latest_halt_id = 10000

        mentions = twitter.mentions_timeline(latest_halt_id)
        mentions.reverse()
        for mention in mentions:
            tweet = mention._json
            if 'halt' in tweet['text'].lower():
                blacklist_item = '\n@{}:{}'.format(tweet['user']['screen_name'], tweet['id_str'])
                with open('blacklist.txt', 'a') as blacklist:
                    blacklist.write(blacklist_item)
                blacklist.close()
                if tweet.get('in_reply_to_status_id') is not None:
                    twitter.destroy_status(tweet['in_reply_to_status_id'])
        time.sleep(20)  # in seconds


def get_temp_html():
    date_time = datetime.now()
    file_name = 'html_encoding/' + date_time.strftime('%m-%d-%Y_%H-%M-%S') + '.html'
    return file_name


def check_black_list(handle):
    with open('blacklist.txt', 'r') as blacklist:
        for line in blacklist:
            if handle in line:
                blacklist.close()
                return False
        blacklist.close()
    return True


def latest_blacklist_id():
    with open('blacklist.txt') as blacklist:
        for line in blacklist:
            pass
        last_line = line
    blacklist.close()
    last_id = last_line[last_line.find(':') + 1:]
    return last_id


def config_driver():
    with open('config.yml', 'r') as ymlfile:
        config = yaml.safe_load(ymlfile)
    driver = config['chrome-driver-path']
    ymlfile.close()
    return driver


def config_keys():
    with open('config.yml', 'r') as ymlfile:
        config = yaml.safe_load(ymlfile)
    keys = config['twitter-auth-keys']
    ymlfile.close()
    return keys


def config_latest():
    with open('config.yml', 'r') as ymlfile:
        config = yaml.safe_load(ymlfile)
    send_on = config['latest-article'].lower()
    if send_on == 'latest':
        send_now = False
    elif send_on == 'instant':
        send_now = True
    else:
        send_now = None
    return send_now


if __name__ == '__main__':
    buzzfeed_search_url = 'https://www.buzzfeed.com/search?q=tweets'

    Process(target=monitor_feed, args=(buzzfeed_search_url,)).start()
    Process(target=monitor_mentions).start()
