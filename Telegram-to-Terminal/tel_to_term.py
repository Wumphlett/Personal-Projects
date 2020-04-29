import os
import sys
import yaml
import time
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler


class TelegramTerminal:
    def __init__(self):
        logging.basicConfig(filename=sys.path[0] + '/log.txt', level=logging.INFO, format='%(message)s')
        logging.info('Starting Telegram to Terminal')
        with open(sys.path[0] + '/config.yml', 'r') as ymlfile:
            config = yaml.safe_load(ymlfile)
            self.token = config['token']
            self.superuser = config['username']
            self.base_path = config['path']
            ymlfile.close()
        self.updater = Updater(token=self.token, use_context=True)
        self.init_dispatch()
        self.superuser = ''

    def init_dispatch(self):
        dispatcher = self.updater.dispatcher

        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        auth_handler = CommandHandler('auth', self.start)
        dispatcher.add_handler(auth_handler)

        running_handler = CommandHandler('running', self.running)
        dispatcher.add_handler(running_handler)

        run_handler = CommandHandler('run', self.run)
        dispatcher.add_handler(run_handler)

        stop_handler = CommandHandler('stop', self.stop)
        dispatcher.add_handler(stop_handler)

        log_handler = CommandHandler('log', self.log)
        dispatcher.add_handler(log_handler)

        dispatcher.add_handler(CallbackQueryHandler(self.call_back))
        dispatcher.add_error_handler(self.error)

    def start(self, update, context):
        with open(sys.path[0] + '/config.yml', 'r') as ymlfile:
            superuser = yaml.safe_load(ymlfile)['user-id']
            ymlfile.close()
        if update.message.from_user.id != superuser:
            msg = 'You do not have permission to access this terminal'
            context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        else:
            self.superuser = update.message.from_user.id
            keyboard = [
                [KeyboardButton('/running')],
                [KeyboardButton('/run'), KeyboardButton('/stop')],
                [KeyboardButton('/log'), KeyboardButton('/auth')]
            ]
            kb_markup = ReplyKeyboardMarkup(keyboard)
            context.bot.send_message(chat_id=update.message.chat_id, text='Welcome Superuser', reply_markup=kb_markup)

    def running(self, update, context):
        if update.message.from_user.id == self.superuser:
            output = os.popen('{}/bash_scripts/currently-running-tel'.format(self.base_path)).read()
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=output)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Permission Denied')

    def run(self, update, context):
        if update.message.from_user.id == self.superuser:
            keyboard = self.get_options()
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            update.message.reply_text('/run <script>', reply_markup=keyboard)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Permission Denied')

    def stop(self, update, context):
        if update.message.from_user.id == self.superuser:
            keyboard = self.get_options()
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            update.message.reply_text('/stop <script>', reply_markup=keyboard)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Permission Denied')

    def log(self, update, context):
        if update.message.from_user.id == self.superuser:
            keyboard = self.get_options()
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            update.message.reply_text('/log <script>', reply_markup=keyboard)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Permission Denied')

    def call_back(self, update, context):
        query = update.callback_query
        query.answer()
        command = '{} {}'.format(query.message.text.split()[0], query.data)
        query.edit_message_text(text=command)
        time.sleep(.5)
        dir_name = os.popen('grep -v grep {}/bash_scripts/1-config.txt | grep {}'.format(self.base_path, query.data))\
            .read().replace('\n', '', 1).split(':')[3]
        cmd_dict = {
            '/run': '{}/bash_scripts/{}'.format(self.base_path, query.data),
            '/stop': '{}/bash_scripts/{}-kill'.format(self.base_path, query.data),
            '/log': 'tail -n 20 {}/{}/log.txt'.format(self.base_path, dir_name)
        }
        cmd_return = os.popen(cmd_dict[query.message.text.split()[0]]).read()
        query.edit_message_text(text=cmd_return)

    def get_options(self):
        output = os.popen('grep -v grep {}/bash_scripts/1-config.txt | grep -v ^#'.format(self.base_path)).read()
        options = []
        for line in output.split('\n')[:-1]:
            options.append(InlineKeyboardButton(line.split(':')[2], callback_data=line.split(':')[2]))
        keyboard = []
        if len(options) % 2 == 0:
            for i in range(0, len(options), 2):
                keyboard.append([options[i], options[i+1]])
        else:
            for i in range(0, len(options)-1, 2):
                keyboard.append([options[i], options[i + 1]])
            keyboard.append([options[-1]])
        return InlineKeyboardMarkup(keyboard)

    def error(self, update, context):
        logging.warning('Error: {}'.format(context.error))


if __name__ == '__main__':
    terminal = TelegramTerminal()

    terminal.updater.start_polling()
    terminal.updater.idle()