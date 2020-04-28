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

        log_handler = CommandHandler('log', self.log)
        dispatcher.add_handler(log_handler)

        run_handler = CommandHandler('run', self.run)
        dispatcher.add_handler(run_handler)

        stop_handler = CommandHandler('stop', self.stop)
        dispatcher.add_handler(stop_handler)

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
        output = os.popen('{}/bash_scripts/currently-running-tel'.format(self.base_path)).read()

        context.bot.send_message(chat_id=update.effective_chat.id, text=output)

    def log(self, update, context):
        if len(context.args) < 1:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Provide a script name fragment')
            return
        output = os.popen('grep -v grep {}/bash_scripts/1-config.txt | grep {}'.format(self.base_path, context.args[0]))
        script = output.read()
        script = script.replace('\n', '', 1)
        if script == '' or script.count('\n') > 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Invalid argument, does not specify script')
        else:
            if script.split(':')[2] == 'telegram':
                output = 'Cannot view the log of the bot from the bot while the bot is running'
            else:
                output = os.popen('tail -n 20 {}/{}/log.txt'.format(self.base_path, script.split(':')[3])).read()
            context.bot.send_message(chat_id=update.effective_chat.id, text=output)

    def run(self, update, context):
        if len(context.args) < 1:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Provide a script name fragment')
            return
        output = os.popen('grep -v grep {}/bash_scripts/1-config.txt | grep {}'.format(self.base_path, context.args[0]))
        script = output.read()
        script = script.replace('\n', '', 1)
        if script == '' or script.count('\n') > 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Invalid argument, does not specify script')
        else:
            os.system('{}/bash_scripts/{}'.format(self.base_path, script.split(':')[2]))
            output = 'Running script {}'.format(script.split(':')[2])
            context.bot.send_message(chat_id=update.effective_chat.id, text=output)

    def stop(self, update, context):
        if len(context.args) < 1:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Provide a script name fragment')
            return
        output = os.popen('grep -v grep {}/bash_scripts/1-config.txt | grep {}'.format(self.base_path, context.args[0]))
        script = output.read()
        script = script.replace('\n', '', 1)
        if script == '' or script.count('\n') > 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Invalid argument, does not specify script')
        else:
            os.system('{}/bash_scripts/{}-kill'.format(self.base_path, script.split(':')[2]))
            output = 'Running script {}-kill'.format(script.split(':')[2])
            context.bot.send_message(chat_id=update.effective_chat.id, text=output)


if __name__ == '__main__':
    terminal = TelegramTerminal()

    terminal.updater.start_polling()
    terminal.updater.idle()
