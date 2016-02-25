from req import ApiRequestHandler
from req import Service
from map import *
import tornado

class ApiSubmissionsHandler(ApiRequestHandler):
    @tornado.gen.coroutine
    def get(self):
        pass

class ApiSubmissionHandler(ApiRequestHandler):
    def check_submit(self, meta={}):
        err, data = yield from Service.Problem.get_problem(meta)
        if err:
            self.render(err)
            return False
        if int(meta['group_id']) == int(data['group_id']) and (map_group_power['submission_manage'] in self.current_group_power or int(data['visible']) > 0):
            return True
        if self.current_contest:
            err, contest_problem_list = yield from Service.Contest.get_contest_problem_list(self.current_contest)
            if int(meta['id']) in (int(x['id']) for x in contest_problem_list):
                return True
        self.render((403, 'Permission Denied'))
        return False

    def check_rejudge(self, meta={}):
        err, data = yield from Service.Submission.get_submission(meta)
        if err:
            self.render(err)
            return False
        err, data = yield from Service.Problem.get_problem({'id': data['problem_id']})
        if err:
            self.render(err)
            return False
        if int(meta['group_id']) == int(data['group_id']) and map_group_power['submission_manage'] in self.current_group_power:
            return True
        self.render((403, 'Permission Denied'))
        return False

    @tornado.gen.coroutine
    def get(self, id):
        meta = {}
        meta['id'] = id
        meta['group_id'] = self.current_group
        err, data = yield from Service.Submission.get_submission(meta)
        if err: self.render(err)
        else: self.render(data)

    @tornado.gen.coroutine
    def post(self, id, action=None):
        if action == 'submit':
            args = ['id', 'execute_type_id', 'code_file[file]', 'plain_code', 'plain_file_name']
            meta = self.get_args(args)
            meta['group_id'] = self.current_group
            if not (yield from self.check_submit(meta)):
                return
            meta['problem_id'] = meta['id']
            meta['user_id'] =  self.account['id']
            meta['ip'] = self.remote_ip
            err, res = yield from Service.Submission.post_submission(meta)
            if err: self.render(err)
            else: self.render(res)
        elif action == 'rejudge':
            meta = {}
            meta['id'] = id
            meta['group_id'] = self.current_group
            if not (yield from self.check_rejudge(meta)):
                return
            err, res = yield from Service.Submission.post_rejudge(meta)
            if err: self.render(err)
            else: self.render(res)
        else:
            self.render((404, 'Page Not Found'))


    
