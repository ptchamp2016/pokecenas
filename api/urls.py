from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^login$', "api.views.login"),
    url(r'^getPokes$', "api.views.getPokemons"),
    url(r'^$', "api.views.load_frontend")
)
