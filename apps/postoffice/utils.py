from django.template import TemplateDoesNotExist
from jinja2 import BaseLoader, Environment, Undefined

from .models import Template


class MailLoader(BaseLoader):

    def __init__(self, tournament, *args, **kwargs):
        super(MailLoader, self).__init__(*args, **kwargs)

        self.tournament = tournament

    def get_source(self, env, template_name):
        try:
            #print("look for %s in trn: %s"%(template_name, self.tournament))
            if template_name.endswith("_subject"):
                t = Template.objects.get(name=template_name[:-8], tournament=self.tournament)
                template_src = t.templateversion_set.last().subject
            else:
                t = Template.objects.get(name=template_name, tournament=self.tournament)
                template_src = t.templateversion_set.last().src


            source = template_src

            return source, None, lambda: False
        except:  # Template.DoesNotExist:
            raise TemplateDoesNotExist(msg='template {} not in db'.format(template_name))


def render_template(template_id, context):
    print(template_id)
    template = Template.objects.get(id=template_id)

    env = Environment(
        loader=MailLoader(template.tournament),
        block_start_string='(%',
        block_end_string='%)',
        variable_start_string='((',
        variable_end_string='))',
        comment_start_string='(#',
        comment_end_string='#)',
        cache_size=0,
        autoescape=True,
        undefined=Undefined,
        extensions=['jinja2.ext.do', ]
    )

    env.globals.update({
        #'static': tex_static
    })

    tmpl = env.get_template(template.name)
    subtmpl = env.get_template("%s_subject"%template.name)

    srcs = []
    for elem in context:
        srcs.append((subtmpl.render(elem),tmpl.render(elem)))

    return srcs
