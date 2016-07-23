from django.http import HttpResponse
import datetime
import json
import jpm_api
from django.template.response import TemplateResponse
import os

def json_custom_parser(obj):
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        dot_ix = 19
        return obj.isoformat()[:dot_ix]
    else:
        raise TypeError(obj)    
    
def load_frontend(request):
    return TemplateResponse(request, 'index.html', context={
        "GMAPS_API_KEY": os.environ.get('GMAPS_API_KEY', "Invalid")
	})

def login(request):
    location = request.POST.get('location', "Lisboa, Portugal")
    result = jpm_api.login(location=location)

    if(result == True):
        return HttpResponse(json.dumps({
            "status": "success",
            "data": result
        }, default=json_custom_parser), content_type='application/json', status=200)
    else:
        return HttpResponse(status=407)

def getPokemons(request):
    result = jpm_api.getPokemons()

    return HttpResponse(json.dumps({
            "status": "success",
            "data": result
        }, default=json_custom_parser), content_type='application/json', status=200)

def getPokestops(request):
    result = jpm_api.getLuredStops()

    return HttpResponse(json.dumps({
            "status": "success",
            "data": result
        }, default=json_custom_parser), content_type='application/json', status=200)

def hasMoreData(request):
    return HttpResponse(json.dumps({
            "status": "success",
            "data": jpm_api.hasMoreData()
        }, default=json_custom_parser), content_type='application/json', status=200)

def updateScan(request):
    location = request.POST.get('location', "Lisboa, Portugal")
    
    result = jpm_api.rescan(location)
    return HttpResponse(json.dumps({
            "status": "success",
            "data": result
        }, default=json_custom_parser), content_type='application/json', status=200)
