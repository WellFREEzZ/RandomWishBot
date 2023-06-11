import os


class Config:
    def __init__(self):
        self.local_data = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)),
                                       'local_data')
        self.db_name = os.path.join(self.local_data, 'main.sqlite')
        self.bot_session_name = 'bot_release'
        self.bot_token = '5445680867:AAFVBfZd0DmcYcrHToP5daEXhHH7ahB-sFA'  # @botfather
        self.api_id = 9642740  # my.telegram.org/apps
        self.api_hash = 'cbef4484034fa81f1af50b65baaf1081'  # my.telegram.org/apps

        if not os.path.exists(self.local_data):
            os.makedirs(self.local_data)
        self.sep = '_|_'
        self.proxy = None  # PROXY in formate:
        # {
        #    'proxy_type': 'socks5',  # (mandatory) protocol to use (see above)
        #    'addr': '0.0.0.0',  # (mandatory) proxy IP address
        #    'port': 0000,  # (mandatory) proxy port number
        #    'username': 'username',  # (optional) username if the proxy requires auth
        #    'password': 'pass',  # (optional) password if the proxy requires auth
        # }
