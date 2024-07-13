from bootstrap3_datetime.widgets import DateTimePicker as OrigDateTimePicker


class DateTimePicker(OrigDateTimePicker):

    class Media:
        js = (
            "moment/min/moment.min.js",
            "moment-timezone/builds/moment-timezone-with-data.min.js",
            "bootstrap-datetimepicker/build/js/bootstrap-datetimepicker.min.js",
        )
        css = {
            "all": (
                "bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.min.css",
            ),
        }

    js_template = """
<script>
    (function defer() {
          if (window.jQuery) {
                $(function(){
                    $("#%(picker_id)s:has(input:not([readonly],[disabled])) > input").datetimepicker(%(options)s);
                });
          } else {
               setTimeout(function() { defer() }, 50);
          }
    })();
</script>"""

    def _format_value(self, value):
        """This function name was changed in Django 1.10 and removed in 2.0."""
        return self.format_value(value)
