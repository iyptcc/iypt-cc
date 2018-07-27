from django.template import TemplateDoesNotExist
from jinja2 import BaseLoader, Environment, Undefined

from .models import Pdf, Template


def _get_next_pdfname(tournament,prefix):
    vnum = 0
    try:
        pdfnames = Pdf.objects.filter(name__startswith=tournament.slug+'/'+prefix).values_list("name", flat=True)
        for pdfname in pdfnames:
            num = int(pdfname.split('-v')[-1])
            if num > vnum:
                vnum = num
    except:
        pass

    return vnum+1

class TeXLoader(BaseLoader):

    def __init__(self, tournament, *args, **kwargs):
        super(TeXLoader, self).__init__(*args, **kwargs)

        self.tournament = tournament

    def get_source(self, env, template_name):
        try:
            #print("look for %s in trn: %s"%(template_name, self.tournament))
            t = Template.objects.get(name=template_name, tournament=self.tournament)
            template_src = t.templateversion_set.last().src
            if t.parent:
                source = env.block_start_string + ' extends "'+t.parent.name+'" ' + env.block_end_string + '\n' + template_src
            else:
                source = template_src

            return source, None, lambda: False
        except:  # Template.DoesNotExist:
            raise TemplateDoesNotExist(msg='template {} not in db'.format(template_name))

def tex_static():
    pass

REPLACEMENTS = {
    "§": "\\textsection{}",
    "$": "\\textdollar{}",
    "LaTeX": "\\LaTeX \\ ",
    " TeX": " \\TeX \\ ",
    "€": "\\euro",
    "'": "\\textquotesingle ",
    #"\n": "\\\\",
    #"\\\\\n\\\\": "\\\\\\ \n\\\\"
    }

ESCAPES = ("&", "{", "}", "%", '[', ']', '#', '_')

def texify(value):
    '''
    escapes/replaces special character with appropriate latex commands
    '''
    tex_value = []
    # escape special symbols
    for char in str(value):
        tex_value.append("%s" % ("\\%s" % char if char in ESCAPES else char))
    tex_value = "".join(tex_value)
    # replace symbols / words with latex commands
    for key, value in REPLACEMENTS.items():
        tex_value = tex_value.replace(key, value)
    # make newlines texable
    print("texvalue")
    parts = tex_value.strip().split("\n")
    tex_value = []
    for idx,p in enumerate(parts):
        if len(p.strip()) == 0:
            tex_value.append("\\ \\\\")
        else:
            tex_value.append(p)
            tex_value.append("\\\\")

    print(tex_value)
    return "%s" % "\n".join(tex_value[:-1])



def render_template(template_id, context):
    print(template_id)
    template = Template.objects.get(id=template_id)

    env = Environment(
        loader=TeXLoader(template.tournament),
        block_start_string='(%',
        block_end_string='%)',
        variable_start_string='((',
        variable_end_string='))',
        comment_start_string='(#',
        comment_end_string='#)',
        cache_size=0,
        autoescape=False,
        undefined=Undefined,
        extensions=['jinja2.ext.do', ]
    )

    env.globals.update({
        'static': tex_static
    })

    env.filters['texify'] = texify

    tmpl = env.get_template(template.name)

    src = tmpl.render(context)
    return src
