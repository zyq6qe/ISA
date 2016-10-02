from django.shortcuts import render
import requests

# Create your views here.
def index(request):
    return render(request, 'index.html')

def daddies(request):
    #Endpoint in Services container to return all daddies
    url = 'http://192.168.99.100:8003/api/v1/services/daddies'
    #Make GET request
    daddies_json = requests.get(url)
    #Make template context
    context = {'daddies': daddies_json.content}
    #Render template
    return render(request, 'daddies.html', context)