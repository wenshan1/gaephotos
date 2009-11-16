from uliweb.form import *
from uliweb.i18n import ugettext_lazy as _

#Form.layout_class = Form.CSSLayout

class RegisterForm(Form):
    form_buttons = Submit(value=_('Register'), _class="button")
    form_title = _('Register')
    
    username = StringField(label=_('Username:'), required=True)
    password = PasswordField(label=_('Password:'), required=True)
    password1 = PasswordField(label=_('Password again:'), required=True)
#    email = StringField(label=_('Email:'))
    next = HiddenField()
    
    def form_validate(self, all_data, request):
        if all_data.password != all_data.password1:
            raise ValidationError, 'Passwords are not matched'
    

class LoginForm(Form):
    form_buttons = Submit(value=_('Login'), _class="button")
    form_title = _('Login')
    
    username = StringField(label=_('Username:'), required=True)
    password = PasswordField(label=_('Password:'), required=True)
    rememberme = BooleanField(label=_('Remember Me'))
    next = HiddenField()
    
class ChangePasswordForm(Form):
    form_buttons = Submit(value=_('Save'), _class="button")
    form_title = _('Change Password')
    
    oldpassword = PasswordField(label=_('Old Password:'), required=True)
    password = PasswordField(label=_('Password:'), required=True)
    password1 = PasswordField(label=_('Password again:'), required=True)
    action = HiddenField(default='changepassword')

    def form_validate(self, all_data, request):
        if all_data.password != all_data.password1:
            raise ValidationError, 'Passwords are not matched'

    def validate_oldpassword(self, data, request):
        if not request.user.check_password(data):
            raise ValidationError, 'Password is not right.'