from django.contrib import admin

from .models import ChairFeedback, ChairFeedbackGrade, Feedback, FeedbackGrade

admin.site.register(Feedback)
admin.site.register(FeedbackGrade)
admin.site.register(ChairFeedback)
admin.site.register(ChairFeedbackGrade)
