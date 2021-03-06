from django.shortcuts import render
from django.http import JsonResponse, Http404, HttpResponse
from django.utils.http import urlquote
from django.contrib.auth.hashers import check_password, make_password
import requests
import os
import hmac
import json
from services.settings import ENTITIES_URL, SECRET_KEY
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from elasticsearch import Elasticsearch
from kafka import KafkaProducer


def get_users_from_models(request):
    # Call users endpoint in Model container
    # url = 'http://sugar_entities:8000/api/v1/users/'
    url = ENTITIES_URL + 'api/v1/users/'
    # Make GET
    r = requests.get(url)
    # Format response as json
    users_json = r.json()
    # Return json response
    return JsonResponse(users_json, content_type='application/json')


def get_user_from_models(request, pk):
    # Call users endpoint in Model container
    # url = 'http://sugar_entities:8000/api/v1/users/' + pk + '/'
    url = ENTITIES_URL + 'api/v1/users/' + urlquote(pk) + '/'
    # Make GET
    r = requests.get(url)
    # Format response as json
    user_json = r.json()
    # Return json response
    return JsonResponse(user_json, content_type='application/json')


def get_babies_from_models(request):
    # Call users endpoint in Model container
    # url = 'http://sugar_entities:8000/api/v1/users/'
    url = ENTITIES_URL + 'api/v1/users/'
    # Make GET
    r = requests.get(url)
    # Format response as json
    babies_json = r.json()
    babies_json['result'] = [user for user in babies_json['result'] if user['user_type'] == 'Baby']
    return JsonResponse(babies_json, content_type='application/json')


def get_baby_from_models(request, pk):
    # Call users endpoint in Model container
    url = ENTITIES_URL + 'api/v1/users/' + urlquote(pk) + '/'
    # Make GET
    r = requests.get(url)
    # Format response as json
    baby_json = r.json()
    if baby_json['user_type'] != 'Baby':
        raise Http404('Baby does not exist')
    return JsonResponse(baby_json, content_type='application/json')


def get_daddies_from_models(request):
    # Call users endpoint in Model container
    # url = 'http://sugar_entities:8000/api/v1/users/'
    url = ENTITIES_URL + 'api/v1/users/'
    # Make GET
    r = requests.get(url)
    # Format response as json
    daddy_json = r.json()
    daddy_json['result'] = [user for user in daddy_json['result'] if user['user_type'] == 'Daddy']
    return JsonResponse(daddy_json, content_type='application/json')


def get_daddy_from_models(request, pk):
    # Call users endpoint in Model container
    url = ENTITIES_URL + 'api/v1/users/' + urlquote(pk) + '/'
    # Make GET
    r = requests.get(url)
    # Format response as json
    daddy_json = r.json()
    if daddy_json['user_type'] != 'Daddy':
        raise Http404('Daddy does not exist')
    return JsonResponse(daddy_json, content_type='application/json')


# @csrf_exempt
# def create_date(request):
#     url = ENTITIES_URL + 'api/v1/dates/'
#     r = requests.post(url, request.POST)
#
#     return JsonResponse(r.json())


def get_dates(request):
    url = ENTITIES_URL + 'api/v1/dates/'
    r = requests.get(url)
    return JsonResponse(r.json(), content_type='application/json')

def index_dates_at_startup(request):
    kp = KafkaProducer(bootstrap_servers='kafka:9092')

    url = ENTITIES_URL + 'api/v1/dates/'
    r = requests.get(url)
    body_data = json.loads(r.content.decode('utf8'))
    for date in body_data['result']:
        kp.send('new-listings-topic', json.dumps(date).encode('utf-8'))



@csrf_exempt
def create_user(request):
    url = ENTITIES_URL + 'api/v1/users/'
    data = request.POST.copy()
    data['password'] = make_password(data['password'])
    r = requests.post(url, data)
    jsonresponse = str(r.content, encoding='utf8')
    final_json = json.loads(jsonresponse)
    return JsonResponse(final_json, content_type='application/json')

@csrf_exempt
def create_date(request):
    url = ENTITIES_URL + 'api/v1/dates/'
    r = requests.post(url, request.POST)
    jsonresponse = str(r.content, encoding='utf8')
    final_json = json.loads(jsonresponse)
    kp = KafkaProducer(bootstrap_servers='kafka:9092')
    kp.send('new-listings-topic', json.dumps(final_json).encode('utf-8'))
    return JsonResponse(final_json, content_type='application/json')


@csrf_exempt
@require_POST
def authenticate(request):
    url = ENTITIES_URL + 'api/v1/authenticators/' + urlquote(request.POST['authenticator'])
    r = requests.get(url)
    auth = r.json()
    return JsonResponse({'result': 'authenticator' in auth}, content_type='application/json')


@csrf_exempt
@require_POST
def login(request):
    # Call authenticators endpoint
    user_url = ENTITIES_URL + 'api/v1/users/username/' + urlquote(request.POST['username'])
    r = requests.get(user_url)
    user = r.json()

    # Check password, change this to hashes before turning in!!!
    if not check_password(request.POST['password'], user['password']):
        raise Http404('Invalid login')

    # If authenticator for user already exists, delete the other one
    del_url = ENTITIES_URL + 'api/v1/authenticators/user/' + urlquote(user['id'])
    r = requests.delete(del_url)

    # Create the authenticator the user will user
    authenticator = {
        'user': user['id'],
        'authenticator': hmac.new(key=SECRET_KEY.encode('utf-8'), msg=os.urandom(32), digestmod='sha256').hexdigest()
    }
    auth_url = ENTITIES_URL + 'api/v1/authenticators/'

    # Save authenticator in the database
    r = requests.post(auth_url, data=authenticator)
    auth_json = r.json()

    return JsonResponse(auth_json, content_type='application/json')


@csrf_exempt
def search(request):
    es = Elasticsearch(['es'])
    results = es.search(index='listing_index', body={'query': {'query_string': {'query': request.GET['search']}}, 'size': 10})
    search_results = {
        'result': [hit['_source'] for hit in results['hits']['hits']],
    }
    return JsonResponse(search_results)
