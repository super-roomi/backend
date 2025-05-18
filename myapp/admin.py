from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from .models import User, Question, Choice, QuestionAttempt, HardQuestion, HardQuestionAttempt

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'date_of_birth')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'date_of_birth', 'is_active', 'is_staff')

    def clean_password(self):
        return self.initial["password"]

class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'full_name', 'date_of_birth', 'is_staff')
    list_filter = ('is_staff',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'date_of_birth', 'phone_number')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'date_of_birth', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

# Question-related admin interfaces
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'created_at')
    inlines = [ChoiceInline]
    search_fields = ['question_text']

class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'created_at')
    search_fields = ['user__email', 'question__question_text']

# Hard Question admin interfaces
class HardQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'correct_answer', 'difficulty', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ['question_text', 'correct_answer']
    fieldsets = (
        (None, {'fields': ('question_text', 'correct_answer')}),
        ('Metadata', {'fields': ('difficulty',)}),
    )

class HardQuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'user_answer', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'created_at')
    search_fields = ['user__email', 'question__question_text', 'user_answer']
    readonly_fields = ('user', 'question', 'user_answer', 'is_correct', 'created_at')

admin.site.register(User, UserAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(QuestionAttempt, QuestionAttemptAdmin)
admin.site.register(HardQuestion, HardQuestionAdmin)
admin.site.register(HardQuestionAttempt, HardQuestionAttemptAdmin)