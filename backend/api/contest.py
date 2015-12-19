from req import ApiRequestHandler
from req import Service
from map import *
import tornado

class ApiContestsHandler(ApiRequestHandler):
    @tornado.gen.coroutine
    def get(self):
        pass

    @tornado.gen.coroutine
    def post(self):
        pass
    
class ApiContestHandler(ApiRequestHandler):
    def check_view(self, meta):
        err, data = yield from Service.Contest.get_contest(meta)
        if err:
            self.render(500, err)
            return False
        if int(meta['group_id']) == int(data['group_id']) and (map_group_power['contest_manage'] in self.current_group_power or int(data['visible']) > 0):
            return True
        self.render(403, 'Permission Denied')
        return False

    def check_edit(self, meta):
        if map_group_power['contest_manage'] not in self.current_group_power:
            self.render(403, 'Permission Denied')
            return False
        if int(meta['id']) != 0:
            err, data = yield from Service.Contest.get_contest(meta)
            if err:
                self.render(500, err)
                return False
            if int(data['group_id']) != int(meta['group_id']):
                self.render(403, 'Permission Denied')
                return False
        return True

    @tornado.gen.coroutine
    def get(self, id):
        meta = {}
        meta['id'] = id
        meta['group_id'] = self.current_group
        if not (yield from self.check_view(meta)):
            return
        err, data = yield from Service.Contest.get_contest(meta)
        if err:
            self.render(500, err)
            return
        self.render(200, data)
        return


    @tornado.gen.coroutine
    def post(self, id, action=None):
        check_meta = {}
        check_meta['id'] = id
        check_meta['group_id'] = self.current_group
        if action == None:
            if not (yield from self.check_edit(check_meta)):
                return
            args = ['visible', 'title', 'description', 'register_start', 'register_end', 'start', 'freeze', 'end', 'type']
            meta = self.get_args(args)
            meta['id'] = id
            meta['group_id'] = self.current_group
            meta['setter_user_id'] = self.account['id']
            err, data = yield from Service.Contest.post_contest(meta)
            if err: self.render(500, err)
            else: self.render(200, data)
        elif action == 'register':
            if not (yield from self.check_view(check_meta)):
                return
            meta = check_meta
            meta['user_id'] = self.account['id']
            err, res = yield from Service.Contest.register(meta)
            if err: self.render(500, err)
            else: self.render(200, res)
        elif action == 'unregister':
            if not (yield from self.check_view(check_meta)):
                return
            meta = check_meta
            meta['user_id'] = self.account['id']
            err, res = yield from Service.Contest.unregister(meta)
            if err: self.render(500, err)
            else: self.render(200, res)
        else:
            self.render(404, 'Permission Denied')
        return

    @tornado.gen.coroutine
    def delete(self, id):
        check_meta = {}
        check_meta['id'] = id
        check_meta['group_id'] = self.current_group
        if not (yield from self.check_edit(check_meta)):
            return
        meta = check_meta
        err, res = yield from Service.Contest.delete_contest(meta)
        if err: self.render(500, err)
        else: self.render(200, res)
        return

class ApiContestProblemsHandler(ApiRequestHandler):
    def check_view(self, meta):
        err, data = yield from Service.Contest.get_contest(meta)
        if err:
            self.render(500, err)
            return False
        if int(data['group_id']) == 1 and int(data['visible']) == 2:
            return True
        if map_group_power['contest_manage'] in self.current_group_power or int(data['visible']) != 0:
            return True
        self.render(403, 'Permission Denied')
        return False

    def check_edit(self, meta):
        if map_group_power['contest_manage'] not in self.current_group_power:
            self.render(403, 'Permission Denied')
            return False
        for problem in meta['problems']:
            err, data = yield from Service.Problem.get_problem({'id': problem})
            if err:
                self.render(500, err+' ID: %s'%(str(problem)))
                return False
            if int(data['group_id']) != int(meta['group_id']):
                self.render(403, 'Permission Denied ID: %s'%(str(problem)))
                return False
        if int(meta['id']) != 0:
            err, data = yield from Service.Contest.get_contest(meta)
            if err:
                self.render(500, err)
                return False
        return True
    @tornado.gen.coroutine
    def get(self, id):
        meta = {}
        meta['id'] = id
        meta['group_id'] = self.current_group
        if not (yield from self.check_view(meta)):
            return
        err, res = yield from Service.Contest.get_contest_problem_list(meta)
        if err: self.render(500, err)
        else: self.render(200, res)
        return

    @tornado.gen.coroutine
    def post(self, id):
        args = ['problems[]', 'scores[]']
        meta = self.get_args(args)
        meta['id'] = id
        meta['group_id'] = self.current_group
        check_meta = {}
        check_meta['id'] = id
        check_meta['group_id'] = self.current_group
        check_meta['problems'] = meta['problems']
        if not (yield from self.check_edit(check_meta)):
            return
        err, res = yield from Service.Contest.post_contest_problem(meta)
        if err: self.render(500, err)
        else: self.render(200, res)
        return

class ApiContestSubmissionsHandler(ApiRequestHandler):
    def check_view(self, meta):
        err, current_contest = yield from Service.Contest.get_current_contest()
        err, data = yield from Service.Contest.get_contest(meta)
        if err:
            self.render(500, err)
            return False
        # if int(meta['group_id']) == int(data['group_id']) and (map_group_power['contest_manage'] in self.current_group_power or (int(meta['id']) in current_contest and int(self.current_contest['id']) in current_contest)):
        if int(meta['group_id']) == int(data['group_id']):
            return True
        self.render(403, 'Permission Denied')
        return False
    
    @tornado.gen.coroutine
    def get(self, id):
        meta = {}
        meta['id'] = id
        meta['group_id'] = self.current_group
        meta['user_id'] = self.account['id']
        meta['current_group_power'] = self.current_group_power
        if not (yield from self.check_view(meta)):
            return
        err, data = yield from Service.Contest.get_contest_submission_list(meta)
        if err: self.render(500, err)
        else: self.render(200, data)

class ApiContestScoreboardHandler(ApiRequestHandler):
    @tornado.gen.coroutine
    def get(self, id):
        meta = {}
        meta['id'] = id
        meta['current_group_power'] = self.current_group_power
        err, data = yield from Service.Contest.get_contest_submissions_scoreboard(meta)
        if err: self.render(500, err)
        else: self.render(200, data)
