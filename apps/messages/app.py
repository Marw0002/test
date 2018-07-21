from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import url
from django.views.generic import RedirectView

from oscar.core.application import Application
from oscar.core.loading import get_class

from oscar.apps.messages.views import *

class DjangoMessagesConfig(AppConfig):
    name = 'django_messages'
    verbose_name = _('Messages')

class MessagesApplication(Application):
    name='messages'
	
    inbox = get_class('messages.views', 'InboxView')
    trash = get_class('messages.views', 'TrashView')	

    def get_urls(self):
        urls = [

            #url(r'^$', RedirectView.as_view(permanent=True, url='inbox/'), name='messages_redirect'),
            url(r'^inbox/$', self.inbox.as_view(), name='messages_inbox'),
            #url(r'^outbox/$', outbox, name='messages_outbox'),
            #url(r'^compose/$', compose, name='messages_compose'),
            #url(r'^compose/(?P<recipient>[\w.@+-]+)/$', compose, name='messages_compose_to'),
            #url(r'^reply/(?P<message_id>[\d]+)/$', reply, name='messages_reply'),
            #url(r'^view/(?P<message_id>[\d]+)/$', view, name='messages_detail'),
            #url(r'^delete/(?P<message_id>[\d]+)/$', delete, name='messages_delete'),
            #url(r'^undelete/(?P<message_id>[\d]+)/$', undelete, name='messages_undelete'),
            url(r'^trash/$', self.trash.as_view() , name='messages_trash'),
            ]		
           
        return self.post_process_urls(urls)
	

application = MessagesApplication()
