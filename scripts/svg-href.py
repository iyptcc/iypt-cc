from lxml import etree
import sys

# usage
# python svg-href.py ../apps/registration/templates/registration/registration_graph_raw.svg ../apps/registration/templates/registration/registration_graph.svg ../apps/registration/templates/registration/inc/next_action.html ../apps/registration/templates/registration/inc/wait_action.html


with open(sys.argv[1]) as f:
    content = f.read()

content = content.replace("<br>","<br/>").replace('class="label"', 'class="svglabel"').replace(".label",".svglabel")

root = etree.fromstring(content)

refmap = {
"name" : {"path":"account:profile"},
"profile" : {"path":"account:profile"},
"apply_experiencedjuror" : {"path":"registration:apply_preselected_participationrole","attrs":["tournament.slug", "tournament.roles.ju"]},
"apply_possiblejuror" : {"path":"registration:apply_possiblejuror","attrs":["tournament.slug"]},
"apply_teamleaderjuror" : {"path":"registration:apply_preselected_teammember","attrs":["tournament.slug", "tournament.team_roles.leader"]},
"data" : {"path":"registration:attendeeproperty"},
"associate_experiencedjuror" : {"path":"registration:associate_to_team","attrs":["tournament.slug"]},
"setpw" : {"path":"registration:manageable_teams"},
"apply_ioc" : {"path":"registration:"},
"apply_manager" : {"path":"registration:apply_team","attrs":["tournament.slug"]},
"associate_role" : {"path":"registration:associate_to_team","attrs":["tournament.slug"]},
"participate" : {"path":"registration:"},
"apply_teammember" : {"path":"registration:apply_preselected_teammember","attrs":["tournament.slug", "tournament.team_roles.member"]},
"apply_teamleader" : {"path":"registration:apply_preselected_teammember","attrs":["tournament.slug", "tournament.team_roles.leader"]},
"associate_visitor" : {"path":"registration:apply_visitor_teammember","attrs":["tournament.slug","'visitor'"]},
"apply_role" : {"path":"registration:apply_preselected_participationrole","attrs":["tournament.slug", "tournament.roles.vi"]},
"apply_loc" : {"path":"registration:apply_participationrole","attrs":["tournament.slug"]},
}

ns = {'svg':'http://www.w3.org/2000/svg',
      'xhtml':'http://www.w3.org/1999/xhtml'}
gs = root.findall(".//svg:g[@class='node']",namespaces=ns)

def makelink(div,url):
    # if not stage.startswith("wait_"):
    link = etree.Element("div")

    div.tag = "a"
    div.addprevious(link)
    link.insert(0, div)

    # print(div.attrib)
    for k, v in div.attrib.items():
        link.set(k, v)
        del div.attrib[k]

        if "attrs" in url:
            div.set("href", "{% url '" + url["path"] + "' " + " ".join(url["attrs"]) + " %}")
        else:
            div.set("href", "{% url '" + url["path"] + "' %}")  # print(etree.tostring(g))

    # print("---")

aa = []
wa = []

for g in gs[:]:
    div = g.find('.//xhtml:div', namespaces=ns)
    stage = g.get("id")
    #print(stage)

    name = " ".join(" ".join(list(div.itertext())).split())
    dic = []

    if stage in refmap:
        if refmap[stage]["path"] != "registration:":
            dic.append("'path':'%s'"%refmap[stage]["path"])
            makelink(div,refmap[stage])

            aa.append("{% if '" + stage + "' in available_actions %}")
            aa.append('<a href="{% url "'+refmap[stage]["path"]+'" ' + " ".join(refmap[stage].get("attrs",[])) + ' %}" class ="btn btn-warning">')
            aa.append(name)
            aa.append("</a>{% endif %}")

    elif stage.startswith("active_"):
        makelink(div, {"path":"account:tournament"})

    g.set("id",'{{ tournament.slug }}%s'%stage)

    wa.append(" {% if '" + stage + "' in wait_actions %} \n")
    wa.append(' <span class ="label label-primary">')
    wa.append(name)
    wa.append(" </span>&nbsp; \n {% endif %} ")

aa.append("{% if '" + "active_teammember" + "' in available_actions %}")
aa.append('<a href="{% url "account:tournament" %}" class ="btn btn-success">')
aa.append("set active tournament")
aa.append("</a>{% endif %}")

with open(sys.argv[2],'wb+') as f:
    f.write(etree.tostring(root))

with open(sys.argv[3],'wb+') as f:
    for al in aa:
        f.write((al+'\n').encode())

with open(sys.argv[4],'wb+') as f:
    for al in wa:
        f.write((al).encode())
