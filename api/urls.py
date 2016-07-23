from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^login$', "api.views.login"),
    url(r'^getPokes$', "api.views.getPokemons"),
    url(r'^getStops$', "api.views.getPokestops"),
    url(r'^moreData$', "api.views.hasMoreData"),
    url(r'^updateScan$', "api.views.updateScan"),
    url(r'^$', "api.views.load_frontend")
)
