from django.conf import settings # import the settings file

from home.models import HomePage

def base_context(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {
        'pages': HomePage.objects.all()[1:],
        'wss':settings.SOCKET_ENCRYPTION,
        'show_admin' : settings.SHOW_ADMIN,
        'admin_url' : settings.ADMIN_URL,
        'bot_msg_prefix' : settings.BOT_MSG_PREFIX,
        'darkmode': request.session.get('dark'),
    }