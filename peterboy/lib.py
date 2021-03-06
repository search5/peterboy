import xml.sax
from functools import wraps

import paginate
from flask import request, abort, url_for

from peterboy.database import db_session
from peterboy.models import Client, TokenCredential, PeterboyNotebook

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
        return paginate.make_html_tag('li', paginate.make_html_tag('a', a_tag),
                                      **{"class": "page-item active"})
    return paginate.make_html_tag("li", a_tag, **{"class": "page-item"})


class TomboyXMLHandler(xml.sax.ContentHandler):
    def __init__(self):
        super()
        self.transform = []
        self.startTag = {"list": "<ul>",
                         "list-item": '<li>',
                         "bold": "<strong>", "italic": "<em>",
                         "size:huge": "<span style=\"font-size:xx-large\">",
                         "size:large": "<span style=\"font-size:large\">",
                         "size:small": "<span style=\"font-size:small\">",
                         "strikethrough": "<strike>",
                         "monospace": '<span style="font-family:monospace">',
                         "highlight": "<span class=\"highlight\">",
                         "link:internal": "<a class=\"internal\">",
                         "link:url": "<a class=\"url\">"}
        self.endTag = {"list": "</ul>", "list-item": "</li>",
                       "bold": "</strong>", "italic": "</em>",
                       "size:huge": "</span>", "size:large": "</span>",
                       "size:small": "</span>", "monospace": "</span>",
                       "strikethrough": "</strike>", "highlight": "</span>",
                       "link:internal": "</a>", "link:url": "</a>"}

    def startElement(self, name, attrs):
        new_tag = self.startTag.get(name, "")
        self.transform.append(new_tag)

    def characters(self, content):
        if self.transform[-1] == '<a class="url">':
            self.transform[-1] = '<a style="color:#3465A4" href="{}">'.format(content)
        elif self.transform[-1] == '<a class="internal">':
            self.transform[-1] = '<a style="color:#204A87" href="#{}">'.format(content)
        elif self.transform[-1] == '<span class="highlight">':
            self.transform[-1] = '<span style="background:yellow">'.format(content)

        self.transform.append(content)

    def endElement(self, name):
        self.transform.append(self.endTag.get(name, ""))


class HTMLToTomboy(xml.sax.ContentHandler):
    def __init__(self):
        super()
        self.transform = []
        self.startTag = ""
        self.result = ""

    def startElement(self, name, attrs):
        if name == "doc":
            return

        if name == "span":
            # 서체 스타일 및 크기 조정
            if attrs["style"] == "font-weight: bold;":
                self.startTag = "bold"
            elif attrs["style"] == "font-weight: italic;":
                self.startTag = "italic"
            elif attrs["style"] == "text-decoration-line: line-through;":
                self.startTag = "strikethrough"
            elif attrs["style"] == "background-color: yellow;":
                self.startTag = "highlight"
            elif attrs["style"] == "font-family: monospace;":
                self.startTag = "monospace"
            elif attrs["style"] == "font-size: small;":
                self.startTag = "size:small"
            elif attrs["style"] == "font-size: medium;":
                return
            elif attrs["style"] == "font-size: large;":
                self.startTag = "size:large"
            elif attrs["style"] == "font-size: xx-large;":
                self.startTag = "size:huge"
        elif name == "a":
            if attrs["href"].startswith("#"):
                self.startTag = "link:internal"
            else:
                self.startTag = "link:url"
        # else:
        #     self.startTag = name
        elif name == "ul":
            self.startTag = "list"
        elif name == "li":
            self.startTag = "list-item"

        self.transform.append("<{}>".format(self.startTag))

    def characters(self, content):
        self.transform.append(content)

    def endElement(self, name):
        if name == "doc":
            return

        tag_match = {"ul": "list", "li": "list-item"}

        if name in ("ul", "li"):
            self.transform.append("</{}>".format(tag_match[name]))
        else:
            self.transform.append("</{}>".format(self.startTag))

    def endDocument(self):
        self.result = "".join(self.transform)

        while True:
            nested_list_start_pos = self.result.find("<list><list>")
            if nested_list_start_pos < 0:
                break

            nested_list_end_pos = self.result.find("</list>", nested_list_start_pos)

            before_fragment = self.result[:nested_list_start_pos + 6]

            nested_list_fragment = self.result[nested_list_start_pos + 6:nested_list_end_pos + 7]

            after_fragment = self.result[nested_list_end_pos + 7:]

            new_fragment = "{}{}{}{}{}".format(before_fragment, "<list-item>", nested_list_fragment, "</list-item>", after_fragment)

            self.result = new_fragment


def notebook_names(notebook_name):
    records = db_session.query(PeterboyNotebook.note_id)

    if notebook_name != "untagged":
        notebook_name = "system:notebook:{}".format(notebook_name)

    if notebook_name:
        records = records.filter(PeterboyNotebook.notebook_name == notebook_name)

    return records
