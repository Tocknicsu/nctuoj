from service.base import BaseService
from req import Service
import config

class GroupService(BaseService):
    def __init__(self, db, rs):
        super().__init__(db, rs)

        GroupService.inst = self

    def get_group_list(self, data={}):
        required_args = ['page', 'count']
        err = self.check_required_args(required_args, data)
        res, res_cnt = yield from self.db.execute('SELECT * FROM groups ORDER BY id LIMIT %s OFFSET %s;', (data['count'], int(data['page']-1)*int(data['count']),))
        return (None, res)


    def get_group_list_count(self):
        res = self.rs.get('group_list_count')
        if res: return (None, res)
        res, res_cnt = yield from self.db.execute('SELECT COUNT(*) FROM groups;')
        self.rs.set('group_list_count', res[0]['count'])
        return (None, res[0]['count'])

    def get_group(self, data={}):
        required_args = ['id']
        err = self.check_required_args(required_args, data)
        if err: return (err, None)
        res = self.rs.get('group@%s'%(str(data['id'])))
        if res is None:
            res, res_cnt = yield from self.db.execute('SELECT * FROM groups WHERE id=%s;', (data['id'],))
            res = res[0]
            self.rs.set('group@%s'%(str(data['id'])), res)
        err, res['members'] = yield from self.get_group_member_list(data)
        return (None, res)

    def get_group_member_list(self, data={}):
        required_args = ['id']
        err = self.check_required_args(required_args, data)
        if err: return (err, None)
        res = self.rs.get('group@%s@user'%(str(data['id'])))
        if res: return (None, res)
        res, res_cnt = yield from self.db.execute('SELECT u.* FROM map_group_user as g, users as u WHERE g.user_id=u.id AND g.group_id=%s ORDER BY u.id;', (data['id'], ))
        for x in res:
            err, x['group_power'] = yield from Service.User.get_user_group_power_info(x['id'], data['id'])
            x.pop('passwd')
        self.rs.set('group@%s@user'%(str(data['id'])), res)
        return (None, res)

    def post_group(self, data={}):
        required_args = ['id', 'name', 'description']
        err = self.check_required_args(required_args, data)
        if err: return (err, None)
        self.rs.delete('group@%s@user'%(str(data['id'])))
        if int(data['id']) == 0:
            data.pop('id')
            sql, param = self.gen_insert_sql('groups', data)
            id = (yield from self.db.execute(sql, param))[0][0]['id']
        else:
            id = data.pop('id')
            sql, param = self.gen_update_sql('groups', data)
            yield from self.db.execute(sql+' WHERE id=%s', param+(id,))
            self.rs.delete('group@%s'%(str(id)))
        return (None, id)

    def post_group_user(self, data={}):
        required_args = ['user_id', 'group_id']
        err = self.check_required_args(required_args, data)
        if err: return (err, None)
        data.pop('power')
        sql, param = self.gen_insert_sql('map_group_user', data)
        id, res_cnt = yield from self.db.execute(sql, param)
        print(sql, param, res_cnt)
        if id is None:
            return ('Already in', None)
        id = id[0]['id']
        self.rs.delete('group@%s@user'%(str(data['group_id'])))
        return (None, id)

    def delete_group_user(self, data={}):
        required_args = ['user_id', 'group_id']
        err = self.check_required_args(required_args, data)
        if err: return (err, None)
        res, res_cnt = yield from self.db.execute('DELETE FROM map_group_user WHERE user_id=%s AND group_id=%s RETURNING id;', (data['user_id'], data['group_id'],))
        print('RES: ',res)
        if res_cnt == 0:
            return ("User isn't in this group", None)
        else: 
            self.rs.delete('group@%s@user'%(str(data['group_id'])))
            return (None, res[0]['id'])

    def delete_group(self, data={}):
        required_args = ['id']
        err = self.check_required_args(required_args, data)
        if err: return (err, None)
        res, res_cnt = yield from self.db.execute('DELETE FROM groups WHERE id=%s RETURNING id;', (data['id'],))
        if res_cnt == 0:
            return ('No ID exist', None)
        else:
            self.rs.delete('group@%s'%(str(data['id'])))
            self.rs.delete('group@%s@user'%(str(data['id'])))
            return (None, res[0]['id'])
