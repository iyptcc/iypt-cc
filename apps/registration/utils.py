from datetime import datetime
from io import BytesIO

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from django.forms.widgets import ClearableFileInput
from django.utils.html import conditional_escape
from django_countries import countries
from django_countries.fields import LazyTypedChoiceField
from django_select2.forms import Select2MultipleWidget, Select2Widget
from pytz import timezone

from apps.account.models import ParticipationRole
from apps.bank.models import PropertyFee
from apps.dashboard.datetimefield import DateTimeFieldNonTZ
from apps.dashboard.datetimepicker import DateTimePicker
from apps.team.models import TeamRole

from .models import AttendeeProperty, AttendeePropertyValue, Property, PropertyValue, UserProperty, UserPropertyValue
from .pdfid.pdfid import PDFiD


class PropertyClearableInput(ClearableFileInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        if value != None:
            if hasattr(value, "instance"):
                if value.instance != None:
                    if type(value.instance) == AttendeePropertyValue:
                        typ = 'a'
                        user = value.instance.attendee.id
                    else:
                        typ = 'u'
                        user = value.instance.user.id

                    try:
                        url = value.url.split('/')[-1]
                    except:
                        url = ""

                    context['widget'].update({
                        "property_type": typ,
                        "property_user":user,
                        "property_id":value.instance.id,
                        "property_url": url
                    })
            else:
                print("PropertyClearableInput: nonbound existing value: %s"%value)

        return context

class ClearablePermissionFileInput(PropertyClearableInput):

    template_name = 'widget/clearable_file_input.html'

class ClearableImageInput(PropertyClearableInput):

    template_name = 'widget/clearable_image_input.html'

def pdf_validator(value):

    if value is None:
        return None

    if hasattr(value, 'temporary_file_path'):
        file = value.temporary_file_path()
    else:
        if hasattr(value, 'read'):
            file = BytesIO(value.read())
        else:
            file = BytesIO(value['content'])

    dom = PDFiD(file)

    ispdf = False
    for k,v in dom.firstChild.attributes.items():
        if k == 'IsPDF':
            if v == 'True':
                ispdf = True

    if ispdf:
        for kw in dom.firstChild.firstChild.childNodes:
            #print(kw.attributes.items())
            pass
    if not ispdf:
        raise ValidationError(
            '%(value)s is not a of filetype pdf',
            params={'value': value}, )


def field_for_property(property, suffix=""):
    label = property.name
    t = property.type
    if suffix:
        label = "%s (%s)"%(label, suffix)

    help_text=""
    if hasattr(property, "data_utilisation"):
        if property.data_utilisation != None:
            help_text = property.data_utilisation

    commargs = {"help_text":help_text,
                "label":label,
                "required": False}

    if t == UserProperty.DATETIME:
        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            opts["timeZone"] = property.tournament.timezone
        except:
            pass
        field = DateTimeFieldNonTZ(widget=DateTimePicker(format='%Y-%m-%dT%H:%M%z',options=opts), **commargs)
    elif t == UserProperty.DATE:
        field = forms.DateField(widget=DateTimePicker(format='%Y-%m-%d', options={
            "format": "YYYY-MM-DD"}), **commargs)
    elif t == UserProperty.INT:
        field = forms.IntegerField(**commargs)
    elif t == UserProperty.STRING:
        field = forms.CharField(**commargs)
    elif t == UserProperty.IMAGE:
        field = forms.ImageField(widget=ClearableImageInput(), **commargs)
    elif t == UserProperty.PDF:
        field = forms.FileField(widget=ClearablePermissionFileInput(),validators=[pdf_validator], **commargs)
    elif t == UserProperty.TEXT:
        field = forms.CharField(widget=forms.Textarea, **commargs)
    elif t == UserProperty.GENDER:
        field = forms.ChoiceField(choices=((None,'----'),('female',"female"),('male','male')),
                                  widget=Select2Widget, **commargs)
    elif t == UserProperty.BOOLEAN:
        field = forms.NullBooleanField(**commargs)
    elif t == UserProperty.BOOLEAN_TRUE:
        field = forms.BooleanField(widget=forms.CheckboxInput, **commargs)
    elif t == UserProperty.PREFERRED_NAME:
        field = forms.CharField(**commargs)
    elif t == UserProperty.PREFERRED_NAME_SHORT:
        field = forms.CharField(max_length=12, **commargs)
    elif t == UserProperty.CHOICE:
        cp = property
        if hasattr(property,"user_property"):
            if property.user_property != None:
                cp = property.user_property
        choices = tuple(cp.propertychoice_set.all().values_list("id","name"))
        choices = ((None,"------"),)+choices
        field = forms.ChoiceField(choices=choices, widget=Select2Widget, **commargs)
    elif t == UserProperty.MULTIPLE_CHOICE:
        cp = property
        if hasattr(property, "user_property"):
            if property.user_property != None:
                cp = property.user_property
        choices = tuple(cp.propertychoice_set.all().values_list("id", "name"))
        field = forms.MultipleChoiceField(choices=choices, widget=Select2MultipleWidget,**commargs)
    elif t == UserProperty.CONFLICT_ORIGINS:
        if hasattr(property, "tournament"):
            if property.tournament != None:
                choices = tuple(property.tournament.origin_set.all().values_list("id", "name"))
                field = forms.MultipleChoiceField(choices=choices, widget=Select2MultipleWidget, **commargs)
        else:
            raise AttributeError("Conflicting Origins can only be used on Attendee Properties")
    elif t == UserProperty.COUNTRY:
        field = LazyTypedChoiceField(choices=[(None,'----')]+list(countries), widget=Select2Widget , **commargs)
    elif t == UserProperty.PROBLEM:
        problems = []
        for p in property.tournament.problem_set.all():
            problems.append((p.number,"%d. %s"%(p.number, p.title)))
        choices = ((None, "------"),) + tuple(problems)
        field = forms.ChoiceField(choices=choices, widget=Select2Widget, **commargs)
    else:
        raise NotImplementedError("Missing field for property type: %s" % t)

    return field

def set_initial_from_valueobject(field, t, valueo):

    chs = valueo.choices_value.values_list("id", flat=True)
    if t == Property.CHOICE:
        if len(chs):
            field.initial = chs[0]
    elif t == Property.MULTIPLE_CHOICE:
        field.initial = list(map(str,chs))
    elif t == Property.CONFLICT_ORIGINS:
        field.initial = list(valueo.conflict_origins.values_list("id", flat=True))
    else:
        value = getattr(valueo, valueo.field_name[t])
        if type(value) == datetime:
            try:
                zoned = value.astimezone(timezone(valueo.attendee.tournament.timezone))
            except:
                zoned = value
            field.initial = zoned
        else:
            field.initial = value

def update_property(request, property, pv, value, field_format, new_class, new_params, copy_image=False, prelim=False):

    t = property.type
    up = property
    try:
        if property.user_property:
            t = property.user_property.type
            up = property.user_property
    except:
        pass

    if new_class == AttendeePropertyValue:
        if prelim:
            new_params.update({"confirmed":False})
            #print("updated params")
            #print(new_params)

    if t in [Property.MULTIPLE_CHOICE, Property.CHOICE]:
        update = True
        if pv:
            cur = pv.choices_value.all().values_list("id", flat=True)
            if set([int(v) for v in value]) == set(cur):
                update = False

        if update:
            apv = new_class.objects.create(**new_params, property=property)
            cur_choices = up.propertychoice_set.filter(pk__in=value)
            apv.choices_value.add(*cur_choices)
    elif t in [Property.IMAGE, Property.PDF]:
        f = request.FILES.get(field_format % property.id, None)
        if copy_image and value!=False and f==None:
            fp = open(value.path, 'rb')
            f = ContentFile(fp.read(),"copied-%s"%value.name.split('/')[-1])
            update = True
        else:
            update = True
            if f == None:
                if value != False:
                    update = False

        if update:
            params = {PropertyValue.field_name[property.type]:f}
            new_class.objects.create(**new_params, property=property, **params)
    elif t in [Property.CONFLICT_ORIGINS]:
        update = True
        if pv:
            cur = pv.conflict_origins.all().values_list("id", flat=True)
            if set([int(v) for v in value]) == set(cur):
                update = False

        if update:
            apv = new_class.objects.create(**new_params, property=property)
            cur_choices = property.tournament.origin_set.filter(pk__in=value)
            apv.conflict_origins.add(*cur_choices)
    else:
        if property.type == Property.PROBLEM:
            if value == '':
                value = None
            else:
                value = int(value)
        if not pv or value != getattr(pv, pv.field_name[property.type]):
            apv = new_class.objects.create(**new_params, property=property)
            apv.__setattr__(apv.field_name[property.type], value)
            apv.save()

def delete_teamrole(tm):

    # check if attendee holds old team role with other team
    only_here = True
    for tms in tm.attendee.teammember_set.all():
        if (tms != tm) and (tms.role == tm.role):
            only_here = False
    if only_here:
        for pr in tm.role.participation_roles.all():
            tm.attendee.roles.remove(pr)

def persons_data(attendees, hidden=False):
    if len(attendees) == 0:
        return ([],[])
    trn = attendees.first().tournament
    aps = []
    if hidden:
        apoq = AttendeeProperty.objects.filter(tournament=trn).prefetch_related("required", "optional")
    else:
        apoq = AttendeeProperty.user_objects.filter(tournament=trn).prefetch_related("required", "optional")

    apos = []
    for ap in apoq:
        apos.append({"name": ap.name, "object": ap, "required": set(ap.required.all().values_list("id", flat=True)),
                     "optional": set(ap.optional.all().values_list("id", flat=True)), "type": ap.type})
    for ap in apos:
        aps.append(ap["name"])

    atts={}

    for att in attendees.all().prefetch_related("roles"):
        at = {"attendee": att, "id": att.id,'juror':False}
        if hasattr(att,"juror"):
            if att.juror != None:
                at["juror"] = True
        dat = []
        att_roles = set(att.roles.values_list("id",flat=True))
        for ap in apos:
            dat_p={"value":None,"needed":True, "required":False, "optional":False}
            if len(att_roles & ap["required"]):
                ls = " (req.)"
                dat_p["required"]=True
            elif len(att_roles & ap["optional"]):
                ls = " (opt.)"
                dat_p["optional"]=True
            elif ap['object'].hidden == True:
                ls = " (hidd.)"
                dat_p["optional"]=True
            else:
                dat_p["needed"]=False
                dat.append(dat_p)
                continue

            try:
                dep_ap = ap["object"].required_if
                depcheck = att.attendeepropertyvalue_set.filter(property=dep_ap).last().bool_value
                if depcheck == True:
                    dat_p["required"]=True
                    dat_p["optional"]=False
            except:
                pass


            try:
                apv = att.attendeepropertyvalue_set.filter(property=ap["object"]).last()
                chs = apv.choices_value.values_list("name", flat=True)
                if ap["object"].type == AttendeeProperty.CHOICE:
                    if len(chs):
                        dat_p["value"] = chs[0]
                elif ap["object"].type == AttendeeProperty.MULTIPLE_CHOICE:
                    dat_p["list"] = list(chs)
                elif ap["object"].type == AttendeeProperty.IMAGE:
                    dat_p["image"] = {"id":apv.id,"url":apv.image_value.url.split("/")[-1]}
                elif ap["object"].type == AttendeeProperty.PDF:
                    dat_p["file"] = {"id":apv.id,"url":apv.file_value.url.split("/")[-1]}
                elif ap["object"].type == AttendeeProperty.CONFLICT_ORIGINS:
                    dat_p["list"] = list(apv.conflict_origins.values_list("name", flat=True))
                else:
                    val = getattr(apv, apv.field_name[ap["type"]])
                    if val is not None:
                        if type(val) == datetime:
                            try:
                                zoned = val.astimezone(timezone(apv.attendee.tournament.timezone))
                            except:
                                zoned = val
                            dat_p["value"] = "%s" % zoned
                        else:
                            dat_p["value"] = "%s" % val

            except:
                pass

            dat.append(dat_p)

        at["data"] = dat
        atts[att.id] = at

    return (atts, aps)

def get_members(trn, team, apoq = None):
    aps = []
    if not apoq:
        apoq = AttendeeProperty.user_objects.filter(tournament=trn).prefetch_related("required","optional")

    apos = []
    for ap in apoq:
        apos.append({"name":ap.name,"object":ap, "required": set(ap.required.all().values_list("id",flat=True)),
                     "optional": set(ap.optional.all().values_list("id",flat=True)),"type":ap.type})
    for ap in apos:
        aps.append(ap["name"])

    limits = {}
    for tr in TeamRole.objects.filter(tournament=trn):
        if tr.members_min:
            limits[tr] = {"value":0}

    members = []
    tlj_pen = 0
    tlj_acc = 0
    missing = 0
    optional = 0
    for tm in team.teammember_set.all().prefetch_related("role","attendee__roles","attendee__juror"):
        member = {"attendee": tm.attendee, "role": tm.role, "proles":tm.attendee.roles.all(), "id": tm.id, "accepted": False, "manager":tm.manager, "juror":tm.attendee.roles.filter(type=ParticipationRole.JUROR).exists()}
        try:
            pj = tm.attendee.active_user.possiblejuror_set.get(tournament=trn)
            member["juror"] = True
            if pj.approved_by != None:
                member["accepted"] = True
        except:
            pass
        if tm.role not in limits:
            limits[tm.role] = {"value":0}
        limits[tm.role]["value"] += 1
        if hasattr(tm.attendee,"juror"):
            if tm.attendee.juror != None:
                member["accepted"] = True
        if tm.role.type == TeamRole.LEADER and member["juror"]:
            if member["accepted"]:
                tlj_acc += 1
            else:
                tlj_pen += 1
        dat = []
        att_roles = set(tm.attendee.roles.values_list("id",flat=True))
        for ap in apos:
            dat_p={"value":None,"needed":True, "required":False, "optional":False}
            if len(att_roles & ap["required"]):
                ls = " (req.)"
                dat_p["required"]=True
            elif len(att_roles & ap["optional"]):
                ls = " (opt.)"
                dat_p["optional"]=True
            else:
                dat_p["needed"]=False
                dat.append(dat_p)
                continue

            try:
                dep_ap = ap["object"].required_if
                if dep_ap:
                    depcheck = tm.attendee.attendeepropertyvalue_set.filter(property=dep_ap).last().bool_value
                    if depcheck == True:
                        dat_p["required"]=True
                        dat_p["optional"] = False
            except:
                pass

            apv = None
            apv_unc = None
            try:
                apv_unc = tm.attendee.attendeepropertyvalue_set(manager="unconfirmed").filter(property=ap["object"]).last()
                if apv_unc.confirmed:
                    apv=apv_unc
                else:
                    apv = tm.attendee.attendeepropertyvalue_set.filter(
                        property=ap["object"]).last()

                    dat_p["prelim"] = "%s" % (getattr(apv_unc, apv_unc.field_name[ap["type"]]))
                chs = apv.choices_value.values_list("name", flat=True)
                if ap["object"].type == AttendeeProperty.CHOICE:
                    if len(chs):
                        dat_p["value"] = chs[0]
                elif ap["object"].type == AttendeeProperty.MULTIPLE_CHOICE:
                    dat_p["list"] = chs
                elif ap["object"].type == AttendeeProperty.IMAGE:
                    dat_p["image"] = {"id":apv.id,"url":apv.image_value.url.split("/")[-1]}
                elif ap["object"].type == AttendeeProperty.PDF:
                    dat_p["file"] = {"id":apv.id,"url":apv.file_value.url.split("/")[-1]}
                elif ap["object"].type == AttendeeProperty.CONFLICT_ORIGINS:
                    dat_p["list"] = apv.conflict_origins.values_list("name", flat=True)
                else:
                    val = getattr(apv, apv.field_name[ap["type"]])
                    if val != None:
                        if type(val) == datetime:
                            try:
                                zoned = val.astimezone(timezone(trn.timezone))
                            except:
                                zoned = val
                            dat_p["value"] = "%s" % zoned
                        else:
                            dat_p["value"]="%s" % val

            except Exception as e:
                #print(e)
                pass

            #print(dat_p)

            if dat_p["required"] and dat_p["value"] == None:
                missing += 1
            if dat_p["optional"] and dat_p["value"] == None:
                optional += 1

            dat.append(dat_p)

        member["data"] = dat
        members.append(member)

    for key, val in limits.items():
        if key.members_max and val["value"] > key.members_max:
            limits[key]["exceed"]=True
        if key.members_min and val["value"] < key.members_min:
            limits[key]["undercut"]=True
    min_jurors = trn.registration_teamleaderjurors_required
    if not team.is_competing:
        min_jurors = trn.registration_teamleaderjurors_required_guest

    try:
        tl_max_limit = TeamRole.objects.get(tournament=trn,type=TeamRole.LEADER).members_max
    except:
        tl_max_limit = None
    accjr = TeamRole(pk=-2,name="accepted TL Jurors",members_min=min_jurors, members_max=tl_max_limit)
    penjr = TeamRole(pk=-3,name="pending TL Jurors",members_min=min_jurors, members_max=tl_max_limit)
    if min_jurors > 0:
        limits[accjr] = {"value":tlj_acc}
        if tlj_acc < min_jurors:
            limits[accjr]["undercut"]=True
        if tlj_pen > 0:
            limits[penjr] = {"value": tlj_pen}
            if tlj_pen > 0:
                limits[penjr]["exceed"]=True

    return (members, aps, limits, (missing,optional))

def application_propertyvalues(tournament, role, activeUser):

    missing_profile = []

    attrs = []

    if activeUser.user.first_name != "":
        attrs.append({"name": "First Name", 'value': activeUser.user.first_name, "type": Property.STRING, "set":True})
    else:
        attrs.append({"name": "First Name", 'value': None, "type": Property.STRING, "set": False})
        missing_profile.append({"name":"First Name"})

    if activeUser.user.last_name != "":
        attrs.append({"name": "Last Name", 'value': activeUser.user.last_name, "type": Property.STRING, "set":True})
    else:
        attrs.append({"name": "Last Name", 'value': None, "type": Property.STRING, "set": False})
        missing_profile.append({"name":"Last Name"})

    for ap in AttendeeProperty.user_objects.filter(Q(tournament=tournament),
                                                   Q(apply_required=role)):

        #print(ap)
        t = ap.user_property.type
        up = ap.user_property

        valueo = None
        try:
            valueo = UserPropertyValue.objects.filter(user=activeUser, property=up).last()
        except:
            pass

        attr = {"name": ap.name, 'property': up, 'list': None, 'value': None, "type": up.type, "set": False,
                "apv": valueo}

        if valueo:
            attr["set"] = True
            chs = valueo.choices_value.values_list("name", flat=True)
            if t == Property.CHOICE:
                if len(chs):
                    attr["value"] = chs[0]
            elif t == Property.MULTIPLE_CHOICE:
                attr["list"] = chs
            elif t == Property.CONFLICT_ORIGINS:
                attr["list"] = valueo.conflict_origins.values_list("name", flat=True)
            else:
                value = getattr(valueo, valueo.field_name[t])
                if value == None:
                    attr["set"] = False
                    missing_profile.append(up)
                elif type(value) == datetime:
                    try:
                        zoned = value.astimezone(timezone(tournament.timezone))
                    except:
                        zoned = value
                    attr["value"] = zoned

                    #print(type(attr["value"]))
                    #print(attr["value"])
                else:
                    attr["value"] = value
        else:
            missing_profile.append(up)

        attrs.append(attr)

    return{'attrs':attrs,
           'missing':missing_profile}
