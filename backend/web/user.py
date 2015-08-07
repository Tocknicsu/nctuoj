from req import RequestHandler
from req import reqenv
from req import Service


class WebUsersHandler(RequestHandler):
    @reqenv
    def get(self):
        if not self.map_power['user_manage'] in self.account['power']:
            self.write_error(403)
            return
        err, meta = yield from Service.User.get_users_info()
        self.Render('./users/users.html', data=meta)

    @reqenv
    def post(self):
        pass

class WebUserHandler(RequestHandler):
    """ single user data """
    @reqenv
    def get(self, id=None, action=None):
        if id == None:
            id = self.account["id"]
        err, meta = yield from Service.User.get_user_advanced_info(id)
        self.Render('./users/user.html', data=meta)

    """ update user data """
    @reqenv
    def post(self, id=None, action=None):
        pass

class WebUserSignHandler(RequestHandler):
    @reqenv
    def get(self, action):
        print(action)
        if action == "signin":
            self.Render('./users/user_signin.html')
        elif action == "signout":
            Service.User.SignOut(self)
            self.redirect('/')
        elif action == "signup":
            self.Render('./users/user_signup.html')
        else:
            self.write_error(404)

    @reqenv
    def post(self, action): 
        if action == "signin":
            args = ['account', 'passwd']
            meta = self.get_args(args)
            err, id = yield from Service.User.SignIn(meta, self)
            if err:
                self.Render('./users/user_signin.html')
            else:
                self.redirect('/')
        elif action == "signout":
            Service.User.SignOut(self)
            self.redirect('/')
        elif action == "signup":
            args = ['email', 'account', 'passwd', 'repasswd', 'school_id', 'student_id']
            meta = self.get_args(args)
            passwd = meta['passwd']
            err, id = yield from Service.User.SignUp(meta)
            if err:
                self.Render('./users/user_signup.html')
            else:
                meta['passwd'] = passwd
                err, id = yield from Service.User.SignIn(meta, self)
                self.redirect('/')
        else:
            self.write_error(404)
