"""Synthetic tests; no real chats, credentials, or database access."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from import_weflow import convert
from common import inspect


def message(id=1, **kw):
    return dict(localId=id, createTime=1738713600+id, localType=1,
                isSend=0, senderUsername='demo_friend', content='虚构测试文字', **kw)


def page(messages=None, **kw):
    messages = messages if messages is not None else [message()]
    return dict(success=True, talker='demo_friend', count=len(messages),
                hasMore=False, messages=messages) | kw


class ImportTests(unittest.TestCase):
    def test_order_quotes_system_and_no_account_metadata(self):
        a=message(3, quote={'content':'引用\n保持换行','sender':'private_id'})
        b=message(1);b.update(localType=10000,isSend=None)
        c=message(2);c.update(isSend=1,content='  原样文字\n',localType=3,mediaLocalPath='private_path')
        rows,warnings=convert([page([a,b,c])],3)
        self.assertEqual([r['sender'] for r in rows],['系统','我','好友'])
        self.assertEqual(rows[1]['content'],'  原样文字\n')
        self.assertEqual(rows[2]['quote_content'],'引用\n保持换行')
        self.assertIsNone(rows[1]['readable_resource'])
        self.assertFalse(inspect(rows,'main')['errors'])
        self.assertNotIn('private_',json.dumps(rows))

    def test_repeated_content_is_not_deduplicated(self):
        a,b=message(1),message(2);b['createTime']=a['createTime']
        rows,_=convert([page([a,b])],2)
        self.assertEqual(len(rows),2)

    def test_valid_pages(self):
        rows,_=convert([page([message(1)],hasMore=True),page([message(2)])],2)
        self.assertEqual(len(rows),2)

    def test_reject_bad_scope_and_incomplete_data(self):
        bad=[page(hasMore=True),page(talker='group@chatroom'),page(count=2),
             page([message(),message()]),page(success=False)]
        for p in bad:
            with self.subTest(p=p), self.assertRaises(ValueError): convert([p],len(p['messages']))
        with self.assertRaises(ValueError): convert([page()],2)
        with self.assertRaises(ValueError): convert([page(hasMore=True),page(talker='other')],2)

    def test_reject_invalid_fields(self):
        for key,value in [('createTime',1738713600000),('isSend',True),('senderUsername','other'),
                          ('content',None),('quote',[]),('localId',0),('localType','1')]:
            p=page();p['messages'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):convert([p],1)

    def test_unknown_and_unavailable_quote(self):
        a=message();a.update(localType=49,replyToMessageId='missing')
        rows,w=convert([page([a])],1)
        self.assertEqual(rows[0]['source_type_code'],49)
        self.assertEqual(rows[0]['quote_status'],'unknown')
        self.assertEqual(w['compound_message_not_expanded'],1)

    def test_cli_preserves_source_and_refuses_overwrite(self):
        script=Path(__file__).resolve().parents[1]/'scripts/import_weflow.py'
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json';out=Path(tmp)/'out.jsonl'
            source.write_text(json.dumps(page()),encoding='utf-8');before=source.read_bytes()
            args=[sys.executable,'-B',str(script),str(source),'--expected-count','1','--output',str(out)]
            first=subprocess.run(args,capture_output=True)
            self.assertEqual(first.returncode,0,first.stderr)
            written=out.read_bytes()
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(out.read_bytes(),written)


if __name__=='__main__': unittest.main()
