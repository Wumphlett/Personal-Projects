import os
import sys
import yaml
import time
import logging
import subprocess
from telegram.ext import Updater, CommandHandler


class TelegramTerminal:
    def __init__(self):
        logging.basicConfig(filename=sys.path[0] + '/log.txt', level=logging.INFO)
        with open(sys.path[0] + '/config.yml', 'r') as ymlfile:
            config = yaml.safe_load(ymlfile)
            self.token = config['token']
            self.superuser = config['username']
            self.base_path = config['path']
            ymlfile.close()
        self.updater = Updater(token=self.token, use_context=True)
        self.init_dispatch()

    def init_dispatch(self):
        dispatcher = self.updater.dispatcher

        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        running_handler = CommandHandler('running', self.running)
        dispatcher.add_handler(running_handler)

    @staticmethod
    def start(update, context):
        with open(sys.path[0] + '/config.yml', 'r') as ymlfile:
            superuser = yaml.safe_load(ymlfile)['username']
            ymlfile.close()
        if update.message.from_user.username != superuser:
            msg = 'You do not have permission to access this terminal'
        else:
            msg = 'Welcome Superuser'
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    def running(self, update, context):
        out = subprocess.Popen(['{}/currently-running'.format(self.base_path)],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

        stdout, stderr = out.communicate()
        print(stdout)
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


if __name__ == '__main__':
    terminal = TelegramTerminal()

    terminal.updater.start_polling()
    terminal.updater.idle()
