from uk_bin_collection.get_bin_data import AbstractGetBinDataClass as agbdc

import json
from unittest import mock
from requests.models import Response

def mocked_requests_get(*args,**kwargs):
    class MockResponse:
        def __init__(self,json_data,status_code,raise_error_type):
            self.text=json_data;self.status_code=status_code
            if raise_error_type is not None:self.raise_for_status=self.raise_error(raise_error_type)
            else:self.raise_for_status=lambda:None
        def raise_error(self,errorType):
            if errorType=='HTTPError':raise agbdc.requests.exceptions.HTTPError()
            elif errorType=='ConnectionError':raise agbdc.requests.exceptions.ConnectionError()
            elif errorType=='Timeout':raise agbdc.requests.exceptions.Timeout()
            elif errorType=='RequestException':raise agbdc.requests.exceptions.RequestException()
            return errorType
    if args[0]=='aurl':return MockResponse('test_data',200,None)
    elif args[0]=='HTTPError.json':return MockResponse({},999,'HTTPError')
    elif args[0]=='ConnectionError.json':return MockResponse({},999,'ConnectionError')
    elif args[0]=='Timeout.json':return MockResponse({},999,'Timeout')
    elif args[0]=='RequestException.json':return MockResponse({},999,'RequestException')
    elif args[0]=='not.json':return MockResponse('not json',200,None)
    return MockResponse(None,404,'HTTPError')

@mock.patch('requests.get', side_effect=mocked_requests_get)
def test_get_data(mock_get):
    page_data = agbdc.get_data('aurl')
    assert(page_data.text =="test_data")

def test_output_json():
    bin_data = {"bin": ""}
    output = agbdc.output_json(bin_data)
    assert type(output) == str
    assert output == '{\n    "bin": ""\n}'