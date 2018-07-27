from django import forms
from django.core.files.images import get_image_dimensions

from apps.bank.models import Account
from apps.registration.models import UserProperty, UserPropertyValue
from apps.registration.utils import (ClearableImageInput, field_for_property, set_initial_from_valueobject,
                                     update_property)

from .models import ActiveUser, Attendee


class TournamentForm(forms.ModelForm):

    class Meta:
        model = ActiveUser
        fields = ["active"]

    def __init__(self, *args, **kwargs):
        super(TournamentForm, self).__init__(*args, **kwargs)
        self.fields['active'].queryset = Attendee.objects.filter(active_user=self.instance)
        self.fields['active'].label_from_instance = lambda o : o.tournament

class SkinForm(forms.ModelForm):

    class Meta:
        model = Attendee

        fields = ["ui_skin"]

class ProfileForm(forms.Form):

    first_name = forms.CharField(max_length=200)
    last_name = forms.CharField(max_length=200)
    avatar = forms.ImageField(required=False, label="Profile Picture", help_text="If you want, you can set a profile picture for for the IYPT CC")

    allowed_ranges = [(u'\u0020', u'\u0020'),  # space
              (u'\u0027', u'\u0027'),  # apostrophe
              (u'\u0041', u'\u005a'),  # A - Z
              (u'\u0061', u'\u007a'),  # a - z
              (u'\u00c0', u'\u00d6'),  # A grave - Ö, no times
              (u'\u00d8', u'\u00dd'),  # O stroke - Y acute, no th
              (u'\u00df', u'\u00f6'),  # szlig - ö, no division
              (u'\u00f8', u'\u0131'),  # o stroke - dotless i, no ligature
              (u'\u0134', u'\u017e'),  # J circumflex - z caron i, no long S
              (u'\u0200', u'\u021b'),  # slovenian croatian romanian
              (u'\u1e00', u'\u1e9a'),  # A ring - a half ring, no long s
              (u'\u1ea0', u'\u1ef9'),  # A dot below - y tilde, no welsh LL
              (u'\u002d', u'\u002d'),  # hyphen-minus -
              (u'\u2010', u'\u2010'),  # unicode hyphen
              ]

    def __init__(self, activeUser, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].initial = activeUser.user.first_name
        self.fields['last_name'].initial = activeUser.user.last_name

    def _char_check(self, s):

        errors = []
        for c in s:
            valid = False
            for r in self.allowed_ranges:
                if r[0] <= c <= r[1]:
                    valid = True
            if not valid:
                errors.append(c)
        return errors

    def allowed_chars(self):
        chars = []
        for r in self.allowed_ranges:
            for c in range(ord(r[0]),ord(r[1])+1):
                chars.append({'s':chr(c),'i':c,'h':'%04x'%c})
        return chars

    def clean_first_name(self):
        data = self.cleaned_data['first_name']

        errors = self._char_check(data)
        if len(errors) > 0:
            raise forms.ValidationError("Contains characters (%s), which are not allowed."%(", ".join(errors)))

        # Always return a value to use as the new cleaned data, even if
        # this method didn't change it.
        return data

    def clean_last_name(self):
        data = self.cleaned_data['last_name']

        errors = self._char_check(data)
        if len(errors) > 0:
            raise forms.ValidationError("Contains characters (%s), which are not allowed."%(", ".join(errors)))

        # Always return a value to use as the new cleaned data, even if
        # this method didn't change it.
        return data

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']

        if avatar:
            try:
                w, h = get_image_dimensions(avatar)

                # validate dimensions
                max_width = max_height = 150
                if w != h:
                    raise forms.ValidationError(u'Please use an image that is '
                                                'square')

                if w > max_width or h > max_height:
                    raise forms.ValidationError(u'Please use an image that is '
                                                '%s x %s pixels or smaller.' % (max_width, max_height))

                # validate content type
                main, sub = avatar.content_type.split('/')
                if not (main == 'image' and sub in ['jpeg', 'jpeg', 'gif', 'png']):
                    raise forms.ValidationError(u'Please use a JPEG, '
                                                'GIF or PNG image.')

                # validate file size
                if len(avatar) > (20 * 1024):
                    raise forms.ValidationError(u'Avatar file size may not exceed 20k.')

            except AttributeError:
                """
                Handles case when we are updating the user profile
                and do not supply a new avatar
                """
                pass

        return avatar

class UserPropertyForm(forms.Form):

    #first_name = forms.CharField(max_length=200)
    #last_name = forms.CharField(max_length=200)

    def __init__(self, activeUser, *args, **kwargs):
        super(UserPropertyForm, self).__init__(*args, **kwargs)

        for up in UserProperty.objects.all():
            field = field_for_property(up)

            try:
                upv = UserPropertyValue.objects.filter(user=activeUser, property=up).last()
                if upv:
                    set_initial_from_valueobject(field, up.type, upv)
            except:
                pass

            self.fields["user-property-%d" % up.id] = field


        #self.fields['first_name'].initial = activeUser.user.first_name
        #self.fields['last_name'].initial = activeUser.user.last_name

    def save(self, request):

        for up in UserProperty.objects.all():

            value = self.cleaned_data["user-property-%d" % up.id]

            upv = None
            try:
                upv = UserPropertyValue.objects.filter(user=request.user.profile, property=up).last()
            except:
                pass

            update_property(request, up, upv, value, "user-property-%s", UserPropertyValue, {"user":request.user.profile,
                                                       "author":request.user.profile})


class AccountAddressForm(forms.ModelForm):

    class Meta:
        model = Account
        fields = ("address", )

        widgets = {'address':forms.Textarea}
