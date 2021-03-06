import json
import logging
import types
import datetime
import collections
import tornado.template
import tornado.gen
import tornado.web
import tornado.websocket
import datetime
import inspect
import re
from map import *
import config
import markdown as markdown
from urllib.parse import quote

def md(s):
    if s is None: s = ''
    return markdown.markdown(s, extensions=['markdown.extensions.nl2br'])

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)

class Service:
    pass

class RequestHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        try:
            self.get_argument('json')
            self.res_json = True

        except tornado.web.HTTPError:
            self.res_json = False

    def log(self, msg):
        if not self.acct:
            id = 0
        else:
            id = self.acct['id']
        class_name = self.__class__.__name__
        caller_function = inspect.stack()[1].function
        caller_lineno = inspect.stack()[1].lineno
        caller_filename = inspect.stack()[1].filename
        msg = '<USER %d / %s@%s@%s@%s> %s' % (id, caller_filename, caller_lineno, self.__class__.__name__, caller_function, str(msg))
        logging.debug(msg)

    def get_args(self, name):
        meta = {}
        for n in name:
            try:
                if n[-2:] == "[]":
                    meta[n[:-2]] = self.get_arguments(n)
                elif n[-6:] == "[file]":
                    n = n[:-6]
                    meta[n] = self.request.files[n][0]
                else:
                    meta[n] = self.get_argument(n)
            except:
                meta[n] = None
        return meta

    @tornado.gen.coroutine
    def prepare(self):
        try:
            self.current_group = int(re.search(r'.*/groups/(\d+).*', self.request.uri).groups(1)[0])
        except:
            self.current_group = 0
        self.map_power = map_power
        self.map_group_power = map_group_power
        self.map_group_type = map_group_type
        self.map_lang = map_lang
        err, self.map_execute_types = yield from Service.Execute.get_execute_type()
        err, self.map_verdict_types = yield from Service.Verdict.get_verdict_type()
        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip
        self.remote_ip = remote_ip
        print("[%s] %s %s"%(self.request.method, self.request.uri, self.remote_ip))




class ApiRequestHandler(RequestHandler):
    def render(self, msg=""):
        if isinstance(msg, tuple): code, msg = msg
        else: code = 200
        self.set_status(code)
        self.finish(json.dumps({
                'msg': msg
            },
            cls=DatetimeEncoder))
        return
    @tornado.gen.coroutine
    def prepare(self):
        yield super().prepare()
        self.account = {}
        token = (self.get_args(['token']))['token']
        if token == None:
            self.account['id'] = 0
        else:
            err, data = yield from Service.User.get_user_basic_info_by_token({'token': token})
            if err:
                self.account['id'] = 0
            else:
                self.account = data
        if self.request.method != 'GET':
            if self.account['id'] == 0 and self.request.uri not in config.API_URI_WITHOUT_SIGNIN:
                self.render((403, 'Permission Denied'))
                return
        id = self.account['id']
        err, self.registered_contest = yield from Service.User.get_user_contest({'id': id})
        err, self.current_contest = yield from Service.User.get_user_current_contest({'id': id})
        err, self.account['power'] = yield from Service.User.get_user_power_info({'id': id})
        err, self.group = yield from Service.User.get_user_group_info({'id': id})
        err, self.inpublic_group = yield from Service.User.get_user_inpublic_group({'id': id})
        err, self.current_group_power = yield from Service.Group.get_group_user_power({
            'user_id': id, 
            'group_id': self.current_group
        })

        in_group = self.current_group in (x['id'] for x in self.group)
        ### if the user not in the group and doesn't try add to group then return 403
        if not in_group and self.current_group != 0 and not re.search(r'^/api/groups/\d+/\d+/$', self.request.uri):
            self.render((403, 'Permission Denied'))
            return
            

class WebRequestHandler(RequestHandler):
    def set_secure_cookie(self, name, value, expires_days=30, version=None, **kwargs):
        kwargs['httponly'] = True
        super().set_secure_cookie(name, value, expires_days, version, **kwargs)

    def write_error(self, err, **kwargs):
        print("write error")
        try: status_code, err = err
        except: status_code = err; err = ''
        if status_code == 403 and self.account['id'] == 0:
            self.redirect("/users/signin/?next_url=%s" % quote(self.request.uri[1:], safe=''))
            print(self.request.uri)
            return
        kwargs['err'] = err
        self.set_status(status_code)
        self.render('./err/'+str(status_code)+'.html', **kwargs)

    def render(self, templ, **kwargs):
        kwargs['md'] = md
        kwargs['map_power'] = self.map_power
        kwargs['map_group_power'] = self.map_group_power
        kwargs['map_group_type'] = self.map_group_type
        kwargs['map_lang'] = self.map_lang
        kwargs['map_visible'] = map_visible
        kwargs['map_execute_types'] = self.map_execute_types
        kwargs['map_verdict_types'] = self.map_verdict_types
        kwargs['account'] = self.account
        try:
            kwargs['title'] = str(self.title) + " | NCTUOJ"
        except:
            kwargs['title'] = "NCTUOJ"
        kwargs['group'] = self.group
        kwargs['inpublic_group'] = self.inpublic_group
        kwargs['current_contest'] = self.current_contest
        kwargs['registered_contest'] = self.registered_contest
        kwargs['current_group'] = self.current_group
        kwargs['current_group_power'] = self.current_group_power
        kwargs['current_group_active'] = self.current_group_active
        # print("This function in req.py's render: ", kwargs)
        super().render('./web/template/'+templ, **kwargs)

    @tornado.gen.coroutine
    def prepare(self):
        yield super().prepare()
        ### No group => 0
        ### No user => 0 (guest)
        try:
            self.current_group_active = re.search(r'/groups/\d+/(\w+)/.*', self.request.uri).groups(1)[0]
        except:
            self.current_group_active = "bulletins"

        self.account = {}
        try:
            token = self.get_secure_cookie('token').decode()
            err, data = yield from Service.User.get_user_basic_info_by_token({'token': token})
            if err:
                id = 0
                self.clear_cookie('token')
            else:
                id = data['id']
                self.account = data
        except:
            id = 0
            self.clear_cookie('token')
        if id == 0:
            self.account['token'] = ""
        
        self.account["id"] = id
        err, self.registered_contest = yield from Service.User.get_user_contest({'id': id})
        err, self.current_contest = yield from Service.User.get_user_current_contest({'id': id})
        err, self.account['power'] = yield from Service.User.get_user_power_info({'id': id})
        err, self.group = yield from Service.User.get_user_group_info({'id': id})
        err, self.inpublic_group = yield from Service.User.get_user_inpublic_group({'id': id})
        err, self.current_group_power = yield from Service.Group.get_group_user_power({
            'user_id': id,
            'group_id': self.current_group
        })

        """ if the user not in the group render(403) """
        in_group = self.current_group in (x['id'] for x in self.group)
        if not in_group and self.current_group != 0:
            self.write_error(403)
            return
        
        """ if a person in contest """
        """
        if self.current_contest:
            err, contest_group_power = yield from Service.User.get_user_group_power_info(id, self.current_contest['group_id'])
            if len(contest_group_power) == 0:
                if re.search(r'/groups/\d+/*', self.request.uri) is not None and re.search(r'/groups/\d+/contests/(\w*)/', self.request.uri) is None:
                    self.redirect('/groups/%s/contests/%s/'%(str(self.current_contest['group_id']), str(self.current_contest['id'])))
        """

class StaticFileHandler(tornado.web.StaticFileHandler):
    @tornado.gen.coroutine
    def prepare(self):
        super().prepare()
        self.account = {}
        try:
            token = self.get_secure_cookie('token').decode()
            err, data = yield from Service.User.get_user_basic_info_by_token({'token': token})
            if err:
                id = 0
                self.clear_cookie('token')
            else:
                id = data['id']
                self.account = data
        except:
            id = 0
            self.clear_cookie('token')
        if id == 0:
            self.account['token'] = ""
        self.account['id'] = id


        

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def reqenv(func):
    @tornado.gen.coroutine
    def wrap(self,*args,**kwargs):
        ret = func(self,*args,**kwargs)
        if isinstance(ret,types.GeneratorType):
            ret = yield from ret
        return ret
    return wrap


