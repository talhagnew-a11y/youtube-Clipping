import importlib.util
import json
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]/'payload/venv/Lib/site-packages/shortsflow'
spec=importlib.util.spec_from_file_location('source_under_test',BASE/'source_info.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
URL='https://www.youtube.com/watch?v=wBVbxswlJ4A'

def webpage(license_text='Creative Commons Attribution license (reuse allowed)',link='https://creativecommons.org/licenses/by/3.0/'):
    row={'metadataRowRenderer':{'title':{'simpleText':'License'},'contents':[{'runs':[{'text':license_text,'navigationEndpoint':{'urlEndpoint':{'url':link}}}]}]}}
    return '<script>var ytInitialPlayerResponse = '+json.dumps({'videoDetails':{'title':'10 Useful Tips','author':'Original Creator'}})+';</script><script>var ytInitialData = '+json.dumps({'contents':[row]})+';</script>'

class Response:
    def __init__(self,text='',data=None):self.text=text;self.data=data
    def raise_for_status(self):pass
    def json(self):return self.data

class Lookup(unittest.TestCase):
    def test_actual_youtube_license_reference(self):
        data=source.fetch(URL,get=lambda *a,**k:Response(webpage(link='/t/creative_commons')),extract=lambda url:{})
        self.assertTrue(data['is_cc'])
        self.assertEqual(data['license_url'],'https://www.youtube.com/t/creative_commons')

    def test_links_and_host_restrictions(self):
        self.assertEqual(source.canonical_url('https://youtu.be/wBVbxswlJ4A?t=12'),URL)
        self.assertEqual(source.canonical_url('https://www.youtube.com/shorts/wBVbxswlJ4A'),URL)
        for bad in ['https://127.0.0.1/private','https://youtube.com.evil.example/watch?v=wBVbxswlJ4A','file:///secret','https://www.youtube.com/playlist?list=abc','https://example.com/?url='+URL]:
            with self.assertRaises(ValueError):source.canonical_url(bad)

    def test_exact_source_license_and_creator(self):
        data=source.fetch(URL,get=lambda *a,**k:Response(webpage()),extract=lambda url:self.fail('Unneeded extractor called'))
        self.assertEqual(data['author'],'Original Creator')
        self.assertEqual(data['license_url'],'https://creativecommons.org/licenses/by/3.0/')
        self.assertTrue(data['is_cc'])
        self.assertEqual(data['source_url'],URL)

    def test_unrelated_cc_link_does_not_license_video(self):
        page=webpage('Standard YouTube License','https://example.com/terms')
        page+='<a href="https://creativecommons.org/licenses/by/4.0/">Music attribution</a>'
        data=source.fetch(URL,get=lambda *a,**k:Response(page),extract=lambda url:{})
        self.assertFalse(data['is_cc'])
        self.assertEqual(data['license_url'],'')

    def test_no_license_version_is_invented(self):
        data=source.fetch(URL,get=lambda *a,**k:Response(webpage(link='')),extract=lambda url:{})
        self.assertTrue(data['is_cc'])
        self.assertEqual(data['license_url'],'')

    def test_metadata_fallback_has_no_permission_assumption(self):
        def get(url,**kw):return Response(data={'title':'Fallback title','author_name':'Fallback creator'}) if 'oembed' in url else Response('unavailable')
        data=source.fetch(URL,get=get,extract=lambda url:{})
        self.assertEqual(data['author'],'Fallback creator')
        self.assertFalse(data['is_cc'])
        self.assertEqual(data['license_url'],'')

    def test_private_or_unavailable_does_not_make_up_fields(self):
        def fail(*a,**k):raise OSError('unavailable')
        with self.assertRaises(ValueError):source.fetch(URL,get=fail,extract=fail)

if __name__=='__main__':unittest.main(verbosity=2)
