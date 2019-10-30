from uuid import uuid4

from authlib.flask.oauth1 import AuthorizationServer
from authlib.flask.oauth1.sqla import create_query_client_func, \
    register_authorization_hooks
from flask import render_template, request
from flask.views import MethodView
from oauthlib.oauth1 import OAuth1Error

from peterboy.database import db_session
from peterboy.models import User, Client, TokenCredential, \
    TemporaryCredential, TimestampNonce

server = None


def init_oauth_url(wsgi):
    global server
    query_client = create_query_client_func(db_session, Client)
    server = AuthorizationServer(wsgi, query_client=query_client)
    register_authorization_hooks(
        server, db_session,
        token_credential_model=TokenCredential,
        temporary_credential_model=TemporaryCredential,
        timestamp_nonce_model=TimestampNonce,
    )


class IssueToken(MethodView):
    def post(self):
        return server.create_token_response(request)


class OAuthorize(MethodView):
    def get(self):
        try:
            req = server.check_authorization_request()
            return render_template('oauth/authorize.html', req=req)
        except OAuth1Error as error:
            return render_template('oauth/error.html', error=error)

    def post(self):
        granted = request.form.get('granted')
        if granted:
            grant_user = User.query.get(int(granted))
            if not grant_user.current_sync_guid:
                grant_user.current_sync_guid = str(uuid4())
        else:
            grant_user = None

        try:
            return server.create_authorization_response(request, grant_user)
        except OAuth1Error as error:
            return render_template('oauth/error.html', error=error)


class OAuthRequestToken(MethodView):
    def post(self):
        return server.create_temporary_credentials_response()
