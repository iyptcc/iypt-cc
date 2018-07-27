from django import forms


class DateTimeFieldNonTZ(forms.DateTimeField):

    def prepare_value(self, value):
        return value
