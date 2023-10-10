import markdown, re
from urllib.parse import parse_qs
import config as cfg
from http import HTTPStatus, cookies
import os, sys

encode    = lambda dat: bytes(dat, "UTF-8")
decode    = lambda dat: str(dat, "UTF-8")

# HTML helpers

# shorthand key:
# c := content within the tag
# s := tag class
# h := href or src link
# i := indentation level
# a := full attribute string
# l := list to insert between subtags

# indent string c with i tabs and append newline
mk_t      = lambda c, i=0    : '\t'*i + f'{c}\n'
#def mk_t(c, i=0):
    #print("mk_t", i, c, file=sys.stderr)
    #return '\t'*i + f'{c}<br />'


# generalized attribute inserters
mk_dtattr = lambda t, c, a='', i=0: mk_t(f'<{t}{a}>{c}</{t}>', i)
mk_otattr = lambda t, a='', i=0: mk_t(f'<{t}{a} />', i)


# fallback class for generated HTML
cdfl = 'radius_default'

# for simple usage, take just the class
mk_dubtag = lambda t, c, s=cdfl, i=0: mk_dtattr(t, c, f' class="{s}"', i=i)

# no conent so just take tag and class
mk_onetag = lambda t, s=cdfl, i=0: mk_t(f'<{t} class="{s}" />', i=i)

# direct HTML tag makers
mk_h    = lambda v, c, s=cdfl, i=0: mk_dubtag("h" + str(v), c, s, i)
mk_li   = lambda            c, i=0: mk_dubtag("li", c, i)
_lihelp = lambda            l, i=0: '\n'.join([mk_li(_li, i) for _li in k])

# for blocks with indented content in  a\n\t\b\c form
_3linefmt = '{}\n{}\n{}'
mk_tblock = lambda a, b, c, i=0: _3linefmt.format(mk_t(a, i), mk_t(b, i+1), mk_t(c, i))

mk_ul   = lambda            l, i=0: mk_tblock("<ul>", _lihelp(l, i+1), "</ul>", i)


_afmt = ' href="{}" class="{}"'
mk_a    = lambda h, t, s=cdfl, i=0: mk_dtattr("a", t, _afmt.format(h, s), i)
mk_code = lambda    c, s=cdfl, i=0: mk_dubtag("code", c, s, i)

# x used for alt text attribute value
_imgfmt = ' src="{}" class="{}" alt="{}"'
mk_img  = lambda h, x, s=cdfl, i=0: mk_otattr("img", _imgfmt.format(h, s, x) , i)

# no default class for div: it's required as the first argument
_divfmt = '<div class="{}">'
mk_div  = lambda         s, c, i=0: mk_tblock(_divfmt.format(s), c, "</div>")


# pass h=1 for table header
mk_td   = lambda    c, s, h=0, i=0: mk_dubtag(f't{["d","h"][h]}', c, s, i)

_trhelp = lambda      l, s, h, i=0: '\n'.join([mk_td(_td, s, h, i) for _td in l])
mk_tr   = lambda      l, s, h, i=0: mk_tblock("<tr>", _trhelp(l, s, h, i+1), "</tr>", i)

_tbhelp = lambda         l, s, i=0: '\n'.join([mk_tr(_tr, s, j == 0, i) for j, _tr  in enumerate(l)])
mk_tbl  = lambda    l, s=cdfl, i=0: mk_tblock("<table>", _tbhelp(l, s, i), "</table>")

# compound HTML makers
mk_sep    = lambda         i=0: mk_t(f'<hr />', i)
mk_chrset = lambda         i=0: mk_t('<meta charset="UTF-8">', i)
mk_msgfmt = lambda     kv, i=0: mk_code(('{} = {} <br />').format(*kv), i)
mk_msgblk = lambda b, kvs, i=0: b + ''.join([mk_msgfmt(kv, i) for kv in kvs]) + b
# _stylefmt = '<link rel="stylesheet" type="text/css" href="{}"/>'
# mk_style  = lambda         i=0: mk_t(_stylefmt.format(cfg.style), i)
_stylefmt = '<link rel="stylesheet" type="text/css" href="style.css"/>'
#mk_style  = lambda         i=0: mk_t(_stylefmt, i)
mk_navbt  =  lambda  h, t, i=0: mk_a(t, h, 'nav')

STYLE="""
<style>
body {
		margin: 0 auto;
		width: 80%;
}
</style>

""".strip()
def mk_style():
    return STYLE


class Rocket:
    """
    Rocket: Radius user request context (responsible for authentication)
            Limited external read access to users table

    ...

    Attributes
    ----------
    path_info : str
        Absolute path requested by user

    queries : dict
        Dictionary of parsed URL queries (passsed by '?key1=value1&key2=value2' suffix)

    session : Session
        The current valid session token if it exists or None


    """

    # Eventually, toggle CGI or WSGI
    def read_body_args_wsgi(self):
        if self.method == "POST":
	        return  parse_qs(self.env['wsgi.input'].read(self.len_body()))
        else:
            return {None: '(no body)'}


    def __init__(self, env, start_res):
        self.env   = env
        self._start_res = start_res
        self.path_info = self.env.get("PATH_INFO", "/")
        self.queries   = parse_qs(self.env.get("QUERY_STRING", ""))
        self._msg       = "(silence)"
        self.headers   = []
        # enable page formatter selection
        # right now we just make the header and footer for HTML
        # and user the identity function by default
        self.format    = lambda x: x
        self.body_args  = self.read_body_args_wsgi()

    def __repr__(self):
        return f'Rocket({self.method},{self.path_info},{self.queries},{str(self.headers)},{self._msg},{self.body_args})'

    def __str__(self):
        return repr(self)


    def msg(self, msg):
        self._msg = msg


    def len_body(self):
        return int(self.env.get('CONTENT_LENGTH', "0"))

    @property
    def method(self):
        return self.env.get('REQUEST_METHOD', "GET")

    def format_html(self, doc):
        # generate a reproduction of the original header without too much abstraction for initial version

        # general constants

        # Prepare logo
        logo_div_doc  = ''
        logo_div_doc += mk_img(cfg.logo, '[The Balance] logo', 'balance_logo')
        logo_div_doc += mk_h('1', cfg.title, 'title')
        logo_div_gen  =  lambda: mk_div('logo', logo_div_doc)

        # Prepare nav
        nav_kvs = cfg.nav_buttons
        nav_btn_gen =    lambda: ''.join([mk_navbt(pair[1], pair[0]) for pair in nav_kvs])
        nav_div_gen =    lambda: f'<hr />{mk_div("nav", nav_btn_gen())}{mk_sep()}\n'

        # Prepare footer
        msgdoc  = []
        msgdoc += [('appname',  cfg.appname)]
        msgdoc += [('version',  cfg.version)]
        msgdoc += [('source',   cfg.source)]
        # Concatenate all components to complete this format operation
        output = ''
        output += mk_style()
        output += mk_chrset()
        output += logo_div_gen()
        output += nav_div_gen()
        output += doc
        output += mk_msgblk(mk_sep(), msgdoc)

        return output

    def respond(self, code, content):
        # Given total correctness of the server
        # all user requests end up here
        self.headers += [('Content-Type', 'text/html')]
        document = self.format_html(content)
        print(f'respond {code.phrase} {self.headers} {document}')
        self._start_res(f'{code.value} {code.phrase}', self.headers)
        return [encode(document)]

def handle_md(rocket, md_path):
    with open(md_path, 'r', newline='') as f:
        content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])
        return rocket.respond(HTTPStatus.OK, content)

def handle_try_md(rocket):
    #md_path = f'{cfg.dataroot}{rocket.path_info}'

    md_path = f'docs/{rocket.path_info}'
    if os.access(md_path, os.R_OK):
        return handle_md(rocket, md_path)
    else:
        return rocket.respond(HTTPStatus.NOT_FOUND, 'HTTP 404 NOT FOUND')

def application(env, SR):
    rocket = Rocket(env, SR)
    return handle_try_md(rocket)
