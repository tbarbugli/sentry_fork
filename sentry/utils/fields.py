from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^sentry\.utils\.fields\.URLTextField"])

from django.db.models import TextField

class URLTextField(TextField):
    '''
    Drop in replacement for the URLField, with support for really long urls
    '''
    def __init__(self, verbose_name=None, name=None, verify_exists=True, **kwargs):
        kwargs.pop('max_length', None)
        self.verify_exists = verify_exists
        TextField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.URLField, 'verify_exists': self.verify_exists}
        defaults.update(kwargs)
        return super(TextField, self).formfield(**defaults)