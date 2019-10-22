from functools import wraps

from flask import request, abort

from peterboy.models import Client, TokenCredential

NOTE_DATETIMESTAMP = "%Y-%m-%dT%H:%M:%S.%f+09:00"


def new_client(user_id):
    return Client(
        user_id=user_id,
        client_id='anyone',
        client_secret='anyone',
        default_redirect_uri='oob',
    )


def authorization2dict(header):
    auth_header = header[1:].split(",")
    resp = {}

    for item in auth_header:
        first_equal = item.find("=")
        resp[item[:first_equal]] = item[first_equal + 1:][1:-1]

    return resp


def authorize_check(error=True):
    def authorize_inner(f):
        @wraps(f)
        def check(*args, **kwargs):
            token_credential = None

            if 'Authorization' in request.headers:
                authorization = authorization2dict(
                    request.headers['Authorization'])
                token_credential = TokenCredential.query.filter(
                    TokenCredential.oauth_token == authorization['oauth_token']).first()

            kwargs[
                'token_user'] = token_credential.user if token_credential else None

            if error:
                abort(500)

            return f(*args, **kwargs)

        return check

    return authorize_inner
