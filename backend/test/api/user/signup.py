#!/usr/bin/env python3
import sys
import requests
import json
import unittest
import datetime
from util import TestCase
import common
import config

class TestApiUserSignup(TestCase):
    url = "%s/api/users/signup/"%(config.base_url,)

    def test_user_signup(self):
        ### if exist test account remove it
        data = {
            "account": config.user_test_account,
            "passwd": config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        if res.status_code == 200:
            admin_token = common.get_token({'account': config.user_admin_account, 'passwd': config.user_admin_password})

            


        ### miss email
        data = {
            "account": config.user_test_account,
            "passwd": config.user_test_password,
            "repasswd": config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'value of email: "None" should not be empty value',
            }
        }
        self.assertEqualR(res, expect_result)
        ### miss account
        data = {
            'email': config.user_test_email,
            'passwd': config.user_test_password,
            'rpasswd': config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'value of account: "None" should not be empty value',
            }
        }
        self.assertEqualR(res, expect_result)
        ### miss passwd
        data = {
            'email': config.user_test_email,
            'account': config.user_test_account,
            'rpasswd': config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'value of passwd: "None" should not be empty value',
            }
        }
        self.assertEqualR(res, expect_result)
        ### miss rpasswd
        data = {
            'email': config.user_test_email,
            'account': config.user_test_account,
            'passwd': config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'value of repasswd: "None" should not be empty value',
            }
        }
        self.assertEqualR(res, expect_result)
        ### passwd & rpasswd are not the same
        data = {
            'email': config.user_test_email,
            'account': config.user_test_account,
            'passwd': config.user_test_password,
            'repasswd': config.user_test_password + str(datetime.datetime.now()),
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'Confirm Two Password',
            }
        }
        self.assertEqualR(res, expect_result)
        ### sign 'test'
        data = {
            'email': config.user_test_email,
            'account': config.user_test_account,
            'passwd': config.user_test_password,
            'repasswd': config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 200,
            "body": {
                "msg": '',
            }
        }
        self.assertEqualR(res, expect_result)
        ### sign 'test' account again
        data = {
            'email': config.user_test_email + str(datetime.datetime.now()),
            'account': config.user_test_account,
            'passwd': config.user_test_password,
            'repasswd': config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'Account Exist',
            }
        }
        self.assertEqualR(res, expect_result)
        ### sign 'test' email again
        data = {
            'email': config.user_test_email,
            'account': config.user_test_account + str(datetime.datetime.now()),
            'passwd': config.user_test_password,
            'repasswd': config.user_test_password,
        }
        res = requests.post(self.url, data=data)
        res.connection.close()
        expect_result = {
            "status_code": 400,
            "body": {
                "msg": 'Email Exist',
            }
        }
        self.assertEqualR(res, expect_result)
        ### 'test' delete 'test'
        ### 'admin' delete 'test'
        pass


