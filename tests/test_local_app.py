"""Boundary and import tests using fictional examples only."""
import base64
import copy
import http.client
import io
import json
from pathlib import Path
import sys
import threading
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from local_app import prepare, make_server, ROOT


def file(name, data):
    return {'name': name, 'data': base64.b64encode(data).decode()}


class DataTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / 'examples/sample_messages.jsonl').read_bytes()
        self.rows = [json.loads(line) for line in self.raw.decode().splitlines()]

    def test_jsonl_preserves_content_and_counts(self):
        result = prepare({'format': 'jsonl', 'expected_count': len(self.rows), 'files': [file('messages.jsonl', self.raw)]})
        self.assertEqual(result['rows'], self.rows)
        self.assertFalse(result['report']['errors'])
        self.assertEqual(len(result['report']['input_sha256'][0]['sha256']), 64)

    def test_json_array(self):
        result = prepare({'format': 'json', 'files': [file('messages.json', json.dumps(self.rows).encode())]})
        self.assertEqual(result['rows'], self.rows)
        self.assertFalse(result['report']['expected_count_checked'])

    def test_weflow_requires_count_and_preserves_quote(self):
        request = {'format': 'weflow', 'files': [file('001.json', (ROOT / 'examples/weflow_response.sample.json').read_bytes())]}
        with self.assertRaises(ValueError):
            prepare(request)
        request['expected_count'] = 4
        result = prepare(request)
        self.assertEqual(len(result['rows']), 4)
        self.assertFalse(result['report']['errors'])

    def test_zip_separates_forwarded_without_extracting(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('01/messages_2025-01.jsonl', self.raw)
            z.writestr('03/forwarded_messages.jsonl', 'not parsed')
            z.writestr('../../unrelated.txt', 'not extracted')
        result = prepare({'format': 'zip', 'files': [file('data.zip', archive.getvalue())]})
        self.assertEqual(result['rows'], self.rows)
        self.assertIn('forwarded_messages.jsonl', result['report']['excluded_files'])

    def test_duplicates_order_and_count_fail_without_deletion(self):
        changed = [self.rows[-1]] + self.rows + [self.rows[-1]]
        result = prepare({'format': 'json', 'expected_count': 999, 'files': [file('test.json', json.dumps(changed).encode())]})
        self.assertEqual(result['rows'], changed)
        self.assertGreater(result['report']['errors']['duplicate_rows'], 0)
        self.assertGreater(result['report']['errors']['time_out_of_order'], 0)
        self.assertEqual(result['report']['errors']['expected_count_mismatch'], 1)

    def test_invalid_json_and_forwarded_fail(self):
        for data in [b'{"content":1,"content":2}', b'{"timestamp":NaN}', b'\n']:
            with self.assertRaises(ValueError):
                prepare({'format':'jsonl','files':[file('test.jsonl',data)]})
        with self.assertRaises(ValueError):
            prepare({'format':'jsonl','files':[file('forwarded_messages.jsonl',self.raw)]})
        rows = copy.deepcopy(self.rows)
        rows[0]['parent_message_index'] = 2
        with self.assertRaises(ValueError):
            prepare({'format':'json','files':[file('test.json',json.dumps(rows).encode())]})


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_loopback_origin_token_and_file_boundary(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        self.assertEqual(self.request('GET', '/', headers={'Host':'attacker.test'})[0], 403)
        self.assertEqual(self.request('GET', '/../../private_data/secrets.json')[0], 404)
        self.assertEqual(self.request('POST','/api/inspect','{}')[0], 403)
        self.assertEqual(self.request('POST','/api/inspect','{}',{'Origin':'https://other.test','X-Local-Token':self.server.token})[0], 403)
        status, data = self.request('GET','/api/bootstrap')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)['prompts']), 3)

    def test_browser_contract(self):
        payload={'format':'weflow','expected_count':4,'files':[file('001.json',(ROOT/'examples/weflow_response.sample.json').read_bytes())]}
        status,data=self.request('POST','/api/inspect',json.dumps(payload),{'Origin':'http://'+self.server.authority,'X-Local-Token':self.server.token,'Content-Type':'application/json'})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(data)['report']['records'],4)


if __name__ == '__main__':
    unittest.main()
