from req import ApiRequestHandler
from req import Service
import tornado
from map import *


class ApiExecuteTypesHandler(ApiRequestHandler):
    def check_edit(self, meta={}):
        if map_power['execute_manage'] not in self.account['power']:
            self.render((403, 'Permission Denied'))
            return False
        return True
    @tornado.gen.coroutine
    def get(self):
        err, data = yield from Service.Execute.get_execute_list()
        if err: self.render(err)
        else: self.render(data)

    @tornado.gen.coroutine
    def post(self):
        if not self.check_edit(): 
            return
        args = ["description", "lang", "command[]", "cm_mode"]
        meta = self.get_args(args)
        meta["setter_user_id"] = self.account['id']
        err, data = yield from Service.Execute.post_execute(meta)
        if err: self.render(err)
        else: self.render({"id": data})

class ApiExecuteTypesPriorityHandler(ApiRequestHandler):
    def check_edit(self):
        if map_power['execute_manage'] not in self.account['power']:
            self.render((403, 'Permission Denied'))
            return False
        return True
    @tornado.gen.coroutine
    def post(self):
        if not self.check_edit(): return
        args = ['priority[]', 'id[]']
        meta = self.get_args(args)
        print('META: ', meta)
        meta['priority'] = dict(zip([int(x) for x in meta['id']], [int(x) for x in meta['priority']]))
        err, res = yield from Service.Execute.post_execute_priority(meta)
        if err: self.render(err)
        else: self.render(res)

class ApiExecuteTypeHandler(ApiRequestHandler):
    def check_edit(self, meta):
        if map_power['execute_manage'] not in self.account['power']:
            self.render((403, 'Permission Denied'))
            return False
        err, data = yield from Service.Execute.get_execute(meta)
        if err:
            self.render(err)
            return False
        return True

    @tornado.gen.coroutine
    def get(self, id):
        meta = {}
        meta['id'] = id
        err, data = yield from Service.Execute.get_execute(meta)
        if err: self.render(err)
        else: self.render(data)

    @tornado.gen.coroutine
    def put(self, id):
        check_meta = {}
        check_meta['id'] = id
        if not (yield from self.check_edit(check_meta)):
            return
        args = ["description", "lang", "command[]", "cm_mode"]
        meta = self.get_args(args)
        meta["setter_user_id"] = self.account['id']
        meta['id'] = id
        err, data = yield from Service.Execute.put_execute(meta)
        if err: self.error(err)
        else: self.render({"id": data})

    @tornado.gen.coroutine
    def delete(self, id):
        check_meta = {}
        check_meta['id'] = id
        if not (yield from self.check_edit(check_meta)):
            return
        meta = check_meta
        err, data = yield from Service.Execute.delete_execute(meta)
        if err: self.render(err)
        else: self.render(data)
