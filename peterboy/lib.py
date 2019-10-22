from functools import wraps

from flask import request, abort, url_for

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


def get_token_credential():
    if 'Authorization' in request.headers:
        authorization = authorization2dict(
            request.headers['Authorization'])
        token_credential = TokenCredential.query.filter(
            TokenCredential.oauth_token == authorization['oauth_token']).first()
        return token_credential
    return


def authorize_pass(f):
    @wraps(f)
    def check(*args, **kwargs):
        token_credential = get_token_credential()

        kwargs['token_user'] = token_credential.user if token_credential else None

        return f(*args, **kwargs)
    return check


def authorize_error(f):
    @wraps(f)
    def check(*args, **kwargs):
        token_credential = get_token_credential()

        if not token_credential:
            abort(500)
        else:
            kwargs['token_user'] = token_credential.user

        return f(*args, **kwargs)
    return check


def create_ref(api_name, web_route_name, **kwargs):
    return {
        "api-ref": url_for(api_name, **kwargs, _external=True),
        "href": url_for(web_route_name, **kwargs)
    }
