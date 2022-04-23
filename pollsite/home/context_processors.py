from django.conf import settings # import the settings file

from home.models import HomePage

def base_context(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {
        'pages': HomePage.objects.all()[1:],
        'show_admin' : settings.SHOW_ADMIN,
        'admin_url' : settings.ADMIN_URL,
    }