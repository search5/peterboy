import xml.sax
from functools import wraps

import paginate
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


def paginate_link_tag(item):
    """
    Create an A-HREF tag that points to another page usable in paginate.
    """
    item['attrs'] = {'class': 'page-link'}
    a_tag = paginate.Page.default_link_tag(item)

    if item['type'] == 'current_page':
        return paginate.make_html_tag('li', paginate.make_html_tag('a', a_tag), **{"class": "page-item active"})
    return paginate.make_html_tag("li", a_tag, **{"class": "page-item"})


class TomboyXMLHandler(xml.sax.ContentHandler):
    def __init__(self):
        super()
        self.transform = []
        self.startTag = {"list": "<ul>", "list-item": "<li>",
                         "bold": "<strong>", "italic": "<em>",
                         "size:huge": "<h1 style=\"display: inline-block\">",
                         "size:large": "<h2 style=\"display: inline-block\">",
                         "size:small": "<small>",
                         "strikethrough": "<strike>", "monospace": "<pre>",
                         "highlight": "<span class=\"highlight\">",
                         "link:internal": "<a class=\"internal\">",
                         "link:url": "<a class=\"url\">"}
        self.endTag = {"list": "</ul>", "list-item": "</li>",
                       "bold": "</strong>", "italic": "</em>",
                       "size:huge": "</h1>", "size:large": "</h2>",
                       "size:small": "</small>",
                       "strikethrough": "</strike>", "highlight": "</span>",
                       "link:internal": "</a>", "link:url": "</a>"}

    def startElement(self, name, attrs):
        self.transform.append(self.startTag.get(name, ""))

    def characters(self, content):
        if self.transform[-1] == '<a class="url">':
            self.transform[-1] = '<a class="url" href="{}">'.format(content)

        self.transform.append(content)

    def endElement(self, name):
        self.transform.append(self.endTag.get(name, ""))
