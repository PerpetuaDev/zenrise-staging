"""Bokun native REST client.

Auth is HMAC-SHA1 over date + access key + method + path. The transport is
injectable so the build's data layer can be tested without network access.
Credentials must never reach logs or error messages.
"""
import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = 'https://api.bokun.io'
DEFAULT_ENV = os.path.join(os.path.expanduser('~'), '.bokun-api.env')


class BokunError(Exception):
    pass


def load_credentials(path=None):
    """(access_key, secret_key) from the environment, else from the env file.

    The environment is checked first so CI can supply them as secrets: a runner
    has no ~/.bokun-api.env, and writing the file just to read it back would put
    the credentials on disk in the workspace.
    """
    env_ak = os.environ.get('BOKUN_ACCESS_KEY')
    env_sk = os.environ.get('BOKUN_SECRET_KEY')
    if env_ak and env_sk:
        return env_ak, env_sk
    path = path or DEFAULT_ENV
    values = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    except OSError as e:
        raise BokunError(f'cannot read Bokun credentials at {path}: {e.strerror}')
    try:
        return values['BOKUN_ACCESS_KEY'], values['BOKUN_SECRET_KEY']
    except KeyError as missing:
        raise BokunError(f'{path} is missing {missing}')


def sign(secret, date, access_key, method, path):
    msg = (date + access_key + method + path).encode()
    return base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha1).digest()).decode()


def _urllib_transport(method, url, headers, body):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except OSError as e:
        raise BokunError(f'network error calling Bokun: {e}')


class BokunClient:
    def __init__(self, access_key, secret, transport=None):
        self._ak = access_key
        self._sk = secret
        self._transport = transport or _urllib_transport

    def _call(self, method, path, body=None):
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        headers = {
            'X-Bokun-Date': date,
            'X-Bokun-AccessKey': self._ak,
            'X-Bokun-Signature': sign(self._sk, date, self._ak, method, path),
            'Accept': 'application/json',
            'Content-Type': 'application/json;charset=UTF-8',
        }
        payload = json.dumps(body).encode() if body is not None else None
        status, raw = self._transport(method, BASE + path, headers, payload)
        if not 200 <= status < 300:
            # Deliberately excludes headers: they carry the access key.
            raise BokunError(f'Bokun {method} {path} returned {status}')
        try:
            return json.loads(raw)
        except ValueError:
            raise BokunError(f'Bokun {method} {path} returned unparseable JSON')

    def get(self, path):
        return self._call('GET', path)

    def post(self, path, body):
        return self._call('POST', path, body)


def from_env(path=None, transport=None):
    ak, sk = load_credentials(path)
    return BokunClient(ak, sk, transport=transport)
