# twitterAuth
# usage :
# oauth = TwitterAuth(consumer_secret, consumer_key)
# oauth.request_token() # for request token
# oauth.do_request() # if you want to implement other request just use this one and wrap arround
# twitter using header based authorization
# we need care about Authorization header payload
import time
from base64 import b64encode
from urllib.parse import quote, parse_qs
from urllib.request import Request, urlopen
from hmac import new as hmac
from hashlib import sha1

class TwitterAuth():
    
    # constructor init parameter is consumer secret and consumer key
    def __init__(self, consumer_secret, consumer_key):
        self.consumer_secret = consumer_secret
        self.consumer_key = consumer_key
        
        # list of dictionary of twitter rest api url
        # access via dicionary get will return url of rest api
        # ex: twitter_rest_api.get('api_authenticate')
        self.twitter_rest_api = {'api_authenticate':'https://api.twitter.com/oauth/authenticate',
            'api_request_token':'https://api.twitter.com/oauth/request_token',
            'api_access_token':'https://api.twitter.com/oauth/access_token',
            'api_statuses_user_timeline':'https://api.twitter.com/1.1/statuses/user_timeline.json',
            'api_account_verify_credentials':'https://api.twitter.com/1.1/account/verify_credentials.json'}

    # parameter
    # url_request : api url for request ex https://api.twitter.com/oauth/request_token
    # oauth_token : access token for accessing api this step should be after request granting from user to application
    # oauth_token_secret : access token will concate with consumer secret for generating signing key
    # oauth_callback : required if request oauth token and oauth token sercret, this callback should be same with application callback on api provider
    # request_method can be POST/GET
    # use_headers_auth False/True, depend on provider restriction
    # if use_headers_auth True headers will send with Authorization payload
    # additional_params should be pair key and val as dictionary and will put on payload request
    def do_request(self, url_request='', request_method='GET',
        oauth_token='', oauth_token_secret='',
        oauth_callback='', use_headers_auth=False, additional_params={}):

        oauth_nonce = str(time.time()).replace('.', '')
        oauth_timestamp = str(int(time.time()))

        params = {'oauth_consumer_key':self.consumer_key,
            'oauth_nonce':oauth_nonce,
            'oauth_signature_method':'HMAC-SHA1',
            'oauth_timestamp':oauth_timestamp,
            'oauth_version':'1.0'}

        # if validate callback
        # and request token and token secret
        if(oauth_callback != ''):
            params['oauth_callback'] = oauth_callback

        # if request with token
        if(oauth_token != ''):
            params['oauth_token'] = oauth_token
            
        # if additional parameter exist
        # append to parameter
        for k in additional_params:
            params[k] = additional_params.get(k)

        # create signing key
        # generate oauth_signature
        # key structure oauth standard is [POST/GET]&url_request&parameter_in_alphabetical_order
        params_str = '&'.join(['%s=%s' % (self.percent_quote(k), self.percent_quote(params[k])) for k in sorted(params)])
        message = '&'.join([request_method, self.percent_quote(url_request), self.percent_quote(params_str)])

        # Create a HMAC-SHA1 signature of the message.
        # Concat consumer secret with oauth token secret if token secret available
        # if token secret not available it's mean request token and token secret
        key = '%s&%s' % (self.percent_quote(self.consumer_secret), self.percent_quote(oauth_token_secret)) # Note compulsory "&".
        signature = hmac(key.encode('UTF-8'), message.encode('UTF-8'), sha1)
        digest_base64 = b64encode(signature.digest()).decode('UTF-8')
        params["oauth_signature"] = digest_base64

        # if use_headers_auth
        headers_payload = {}
        if use_headers_auth:
            headers_str_payload = 'OAuth ' + ', '.join(['%s="%s"' % (self.percent_quote(k), self.percent_quote(params[k])) for k in sorted(params)])
            headers_payload['Authorization'] = headers_str_payload

            # if POST method add urlencoded
            if request_method == 'POST':
                headers_payload['Content-Type'] = 'application/x-www-form-urlencoded'
                
            headers_payload['User-Agent'] = 'HTTP Client'
            
        # generate param to be passed into url
        params_str = '&'.join(['%s=%s' % (k, self.percent_quote(params[k])) for k in sorted(params)])
        
        # if method GET append parameter to url_request with ? params_request_str
        # and set params_request_str to None
        # if using get method
        # all parameter should be exposed into get parameter in alphabetical order
        if request_method == 'GET':
            url_request += '?' + params_str
            params_str = None
            
        # if method POST encode data to standard iso
        # post using header based method
        elif request_method == 'POST':
            # encode to standard iso for post method
            params_str = params_str.encode('ISO-8859-1')
        
        # request to provider with
        # return result
        try:
            req = Request(url_request, data=params_str, headers=headers_payload, method=request_method)
            res = urlopen(req)
            return res.readall()
        except Exception as e:
            print(e)
            return None

    # simplify request token
    # get request token
    # required oauth_callback
    def request_token(self, oauth_callback):
        res = self.do_request(url_request=self.twitter_rest_api.get('api_request_token'),
            request_method='POST',
            oauth_callback=oauth_callback,
            use_headers_auth=True)

        # mapping to dictionary
        # return result as dictioanary
        if res:
            return self.qs_to_dict(res.decode('UTF-8'))
            

        # default return is None
        return None

    # request authentication url
    # requred parameter is oauth_token
    # will return request_auth_url for granting permission
    def request_auth_url(self, oauth_token):
        if oauth_token:
            return '?'.join((self.twitter_rest_api.get('api_authenticate'), '='.join(('oauth_token', self.percent_quote(oauth_token)))))
            
        # default value is None
        return None
        
    # request access token
    # parameter oauth_verifier and oauth_token is required 
    def request_access_token(self, oauth_token, oauth_verifier):
        if oauth_token and oauth_verifier:
            res = self.do_request(url_request=self.twitter_rest_api.get('api_access_token'),
                request_method='POST',
                oauth_token=oauth_token,
                oauth_token_secret='',
                oauth_callback='',
                use_headers_auth=True,
                additional_params={'oauth_verifier':oauth_verifier})
                
            # mapping to dictionary
            # return result as dictioanary
            if res:
                return self.qs_to_dict(res.decode('UTF-8'))
                
        # default return none
        return None
        
    # parse query string into dictionary
    # parameter is query string key=valuy&key2=value2
    def qs_to_dict(self, qs_string):
        res = parse_qs(qs_string)
        data_out = {}
        for k in res:
            data_out[k] = res[k][0]
        
        return data_out
        
    # get statuses user timeline
    # Returns a collection of the most recent Tweets posted by the user indicated by the screen_name or user_id parameters.
    # read twitter rest api for more params optional
    # optional params={'user_id':'117257387', 'screen_name':'_mru_', 'since_id':'',
    #   'count':'', 'max_id':'', 'trim_user':'', 'exclude_replies':'', 'contributor_details':'', 'include_rts':''}
    # oauth_token and oauth_token_secret is required
    def request_statuses_user_timeline(self, oauth_token, oauth_token_secret, params={}):
    
        res = self.do_request(url_request=self.twitter_rest_api.get('api_statuses_user_timeline'),
                request_method='GET',
                oauth_token=oauth_token,
                oauth_token_secret=oauth_token_secret,
                oauth_callback='',
                use_headers_auth=True,
                additional_params=params)
                
        return res.decode('UTF-8')
    
    # oauth_token, oauth_token_secret is required
    # read twitter rest api for more detail about params
    # param optional
    # ex: param = {'include_entities':'true|false', 'skip_status':'true|false', 'include_email':'true|false'}
    def request_account_verify_credentials(self, oauth_token, oauth_token_secret, params={}):
    
        res = self.do_request(url_request=self.twitter_rest_api.get('api_account_verify_credentials'),
                request_method='GET',
                oauth_token=oauth_token,
                oauth_token_secret=oauth_token_secret,
                oauth_callback='',
                use_headers_auth=True,
                additional_params=params)
                
        return res.decode('UTF-8')

    # percent_quote
    # quote url as percent quote
    def percent_quote(self, text):
        return quote(text, '~')

# testing outh request token
oauth = TwitterAuth('YOUR CONSUMER SECRET', 'YOUR CONSUMER KEY')
#res = oauth.request_token(oauth_callback='http://127.0.0.1:8888/p/authenticate/twitter')
#print(res)
#print(oauth.request_auth_url(res.get('oauth_token')))
#oauth_token=0DfoVA1fBB119ZTc6Z2K0PqZXvPfIMRZ&oauth_verifier=wQJ335O6w4WOJmOl8W5092HYCzdeC48n
#access_token = oauth.request_access_token('0DfoVA1fBB119ZTc6Z2K0PqZXvPfIMRZ', 'wQJ335O6w4WOJmOl8W5092HYCzdeC48n')
#print(access_token)
#print(oauth.request_statuses_user_timeline('117257387-5q81kt6bLQe5vwNhVIxn8mjkLpf4MDcwgpHiGvAn', 'EDvwqziHQLp67RTFOKjmlWf05JVYIxFn6tYdVj2JFOC2D', params={'screen_name':'_mru_', 'count':'2'}))
#print(oauth.request_account_verify_credentials('117257387-5q81kt6bLQe5vwNhVIxn8mjkLpf4MDcwgpHiGvAn', 'EDvwqziHQLp67RTFOKjmlWf05JVYIxFn6tYdVj2JFOC2D'))