#!/usr/bin/env python
""" This module is used to assist in obtaining a login session
    for AWS especially when using MFA
"""

from __future__ import print_function

import ConfigParser
import argparse
import json
import os
import pickle
import re
import sys
import time
from datetime import datetime
from dateutil import tz

import keyring
import boto3
import pyotp

def eprint(*args, **kwargs):
    """ Error print to stderr """
    print(*args, file=sys.stderr, **kwargs)


class aws_login_helper:
    """ Class to assist in login! """
    def __init__(self):

        self.aws_profiles = self.load_aws_profiles(
            os.path.expanduser("~/.aws/credentials"))
        self.aws_session = None
        self.keyring = keyring.get_keyring()
        self.session_name = None

    def list_profiles(self):
        """ Print out profiles that exist """
        baseprofile = self.aws_profiles.keys()
        baseprofile.sort()

        eprint("Available profiles & roles")
        for profile in baseprofile:
            eprint("  %s" % (profile))

    def set_keyring(self, mykeyring):
        """ Allow a specific keyring to be used """
        self.keyring = mykeyring.copy()

    def load_aws_profiles(self, filename):
        """ Load the AWS profiles from ~/.aws/config """
        iniconfig = ConfigParser.ConfigParser()
        iniconfig = ConfigParser.ConfigParser()
        iniconfig.readfp(open(filename))

        result = {}
        for section in iniconfig.sections():
            section = section.lower()
            result[section] = {}
            for item in iniconfig.items(section):
                result[section][item[0].upper()] = item[1]

        return result

    def set_token_key(self, profile):
        """ Store the mfa token hash in keyring """
        profile = profile.lower()
        # Start with given profile name
        if self.aws_profiles.get(profile):
            if self.aws_profiles[profile].get('MFA_SERIAL'):
                mfa_arn = self.aws_profiles[profile].get('MFA_SERIAL')
            else:
                eprint('You must set mfa_serial in the aws credentials first')
                return False
        else:
            eprint('Error: profile not found')
            return False

        print ("Enter the MFA key for %s: " % (mfa_arn))
        key = sys.stdin.readline().strip()

        if len(key) < 0:
            eprint('Invalid key entered')
        else:
            self.keyring.set_password(mfa_arn, mfa_arn, key)
            print ("Key set for %s" % mfa_arn)

    def get_profile_creds(self):
        """ Get the credentials for the profile """
        profile = self.session_name.lower()

        # Start with given profile name
        if not self.aws_profiles.get(profile):
            eprint('Error: Profile doesnt exist')
        else:
            profile_req = self.aws_profiles[profile]
            creds = profile_req.copy()

            if creds.get('SOURCE_PROFILE'):
                # Look for source profile keys
                profile_source = self.aws_profiles[creds['SOURCE_PROFILE']]
                creds['AWS_ACCESS_KEY_ID'] = \
                    profile_source['AWS_ACCESS_KEY_ID']
                creds['AWS_SECRET_ACCESS_KEY'] =  \
                    profile_source['AWS_SECRET_ACCESS_KEY']

            if creds.get('MFA_SERIAL'):
                totpkey = self.keyring.get_password(
                    creds['MFA_SERIAL'], creds['MFA_SERIAL'])
                if not totpkey:
                    eprint("Error: Can't get key for mfa %s" % creds['MFA_SERIAL'])
                    return False

                exp = 30 - (datetime.now().second % 30)
                if exp < 2:
                    time.sleep(exp+1)
                    exp = 30 - (datetime.now().second % 30)

                creds['TokenExpires'] = exp
                creds.update({
                    'tokencreds': {
                        'SerialNumber':creds['MFA_SERIAL'],
                        'TokenCode':self.get_topt(totpkey)
                    }})

            self.creds = creds

    def aws_login(self, profile):
        """ Login with STS if using mfa, otherwise just set
            the keys in creds
        """
        if self.aws_profiles.get(profile):
            self.session_name = profile
        else:
            eprint("Error: Profile %s doesn't exist" % profile)
            return False

        # creds will be the access key pair passed to boto3
        self.get_profile_creds()
        creds = self.creds

        self.aws_session = None
        cachetry = self.cache_load()
        if cachetry:
            return True

        session = boto3.Session(
            aws_access_key_id=creds['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=creds['AWS_SECRET_ACCESS_KEY'])

        if creds.get('ROLE_ARN'):
            # Assume Role
            creds['tokencreds']['RoleArn'] = creds['ROLE_ARN']
            creds['tokencreds']['Rolesession_name'] = "assumerole"
            sts = session.client('sts')
            sessiontoken = sts.assume_role(**creds['tokencreds'])
            self.aws_session = sessiontoken['Credentials']

        elif creds.get('MFA_SERIAL'):
            # Session Token
            sts = session.client('sts')
            sessiontoken = sts.get_session_token(**creds['tokencreds'])
            self.aws_session = sessiontoken['Credentials']

        else:
            # Regular Profile
            self.aws_session = {
                'AccessKeyId':creds['AWS_ACCESS_KEY_ID'],
                'SecretAccessKey':creds['AWS_SECRET_ACCESS_KEY']
            }

        self.cache_save()
        return True

    def print_topt_from_profile(self, profile):
        """ Print the one time code for MFA """
        if self.aws_profiles.get(profile):
            self.session_name = profile
        else:
            eprint("Error: Profile %s doesn't exist" % profile)
            return False

        # creds will be the access key pair passed to boto3
        self.get_profile_creds()
        token = self.creds['tokencreds']
        print (
            "[%s] (Expires: %ss): %s" %
            (profile, self.creds['TokenExpires'], token['TokenCode'])
        )

    def get_boto_creds(self):
        """ Return a dict of creds that can be passed to boto3 """
        botocreds = {}

        if not self.aws_session:
            return {}

        botovars = {
            'AccessKeyId': 'aws_access_key_id',
            'SecretAccessKey': 'aws_secret_access_key',
            'SessionToken': 'aws_session_token'}

        for key, value in botovars.items():
            if self.aws_session.get(key):
                botocreds[value] = self.aws_session.get(key)

        return botocreds

    def cache_load(self):
        """ Attempt to load from cache """
        if not os.path.isdir('/tmp/awscreds/'):
            os.mkdir('/tmp/awscreds/')

        if os.path.isfile('/tmp/awscreds/' + self.session_name):
            with open('/tmp/awscreds/' + self.session_name, 'r') as credload:
                chkinfo = pickle.loads(credload.read())
                if chkinfo.get('SecretAccessKey'):
                    if chkinfo.get('Expiration'):
                        now = datetime.now(tz.tzoffset('UTC', 0))
                        if chkinfo['Expiration'] < now:
                            return False

                else:
                    return False
        else:
            return False

        self.aws_session = chkinfo
        return True

    def cache_save(self):
        """ Save creds to cache """
        if os.path.isdir('/tmp/awscreds'):
            with open('/tmp/awscreds/' + self.session_name, 'w') as credsave:
                pickle.dump(self.aws_session, credsave)

    def cache_clear(self):
        """ Clear any existing cache for this session """
        if os.path.isfile('/tmp/awscreds/' + self.session_name):
            os.remove('/tmp/awscreds/' + self.session_name)

    def get_topt(self, mykey):
        """ Get the one time code for MFA """
        urlcheck = re.findall('\?secret=(.*)', mykey)
        if len(urlcheck) > 0:
            secret = urlcheck[0]
        else:
            secret = mykey

        return pyotp.TOTP(secret).now()

    def output_bash_login(self, profilename):
        """ Output bash exports that will set AWS Environment """
        logintry = self.aws_login(profilename)
        if logintry:

            exportvars = {
                'AccessKeyId': 'AWS_ACCESS_KEY_ID',
                'SecretAccessKey': 'AWS_SECRET_ACCESS_KEY',
                'SessionToken': 'AWS_SESSION_TOKEN'}

            print("unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN "
                  "AWS_SESSION_TOKEN AWS_DEFAULT_REGION AWS_DEFAULT_PROFILE")

            print ("export AWS_DEFAULT_PROFILE=\"%s\"" % (profilename))
            for key, value in exportvars.iteritems():
                if self.aws_session.get(key):
                    print ("export %s=\"%s\"" % (value, self.aws_session[key]))

    def output_bash_logout(self):
        """ Output bash exports that will unset AWS Environment """
        self.session_name = os.environ.get('AWS_DEFAULT_PROFILE')
        if self.session_name:
            self.cache_clear()

        print("unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN "
              "AWS_SESSION_TOKEN AWS_DEFAULT_REGION AWS_DEFAULT_PROFILE")

def main():
    """ Main Function """
    awslogin = aws_login_helper()

    # this is the top level parser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-k', metavar="keychain", default=False,
        help='Specify OSX keychain file')

    p_action = parser.add_mutually_exclusive_group(required=True)
    p_action.add_argument(
        '-l', help='List available profiles', action='store_true')
    p_action.add_argument(
        '-t', metavar="profile", default=False,
        help='Display MFA token')
    p_action.add_argument(
        '-b', metavar="profile", default=False,
        help='Login for bash environment')
    p_action.add_argument(
        '-B', action='store_true', default=False,
        help='Logout for bash environment')
    p_action.add_argument(
        '-m', metavar="profile", default=False,
        help='Store MFA key for profile')

    args = vars(parser.parse_args())

    if args['k']:
        if os.path.isfile(args['k']):
            awslogin.keyring.keychain = args['k']

    if args['l']:
        awslogin.list_profiles()
    elif args['B']:
        awslogin.output_bash_logout()
    elif args['t']:
        awslogin.print_topt_from_profile(args['t'])
    elif args['b']:
        awslogin.output_bash_login(args['b'])
    elif args['m']:
        awslogin.set_token_key(args['m'])

if __name__ == "__main__":
    main()
