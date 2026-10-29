import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from build_presentation import build
from evaluate_benchmark import evaluate
from review_app import save_label, record_hash
from westminster_leads.classifier import classify
from westminster_leads.digest import select
from westminster_leads.geography import distance_km, postcode_centre
from westminster_leads.storage import Store


def sample():
    return {'record': {'reference':'TEST/FULL','description':'Roof replacement','source_url':'https://idoxpa.westminster.gov.uk/online-applications/','provenance':'london_datahub'}, 'trades':None,'contact_route':None}


def fields():
    return {'index':['0'],'reference':['TEST/FULL'],'reviewer':['Test reviewer'],'attested':['yes'],
            'trade':['Roofing'],'contact':['portal']}


class CompletionTests(unittest.TestCase):
    def test_review_attestation_hash_and_no_prediction_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'labels.json';path.write_text(json.dumps([sample()]))
            bad=fields();bad.pop('attested')
            with self.assertRaises(ValueError):save_label(path,bad)
            self.assertIsNone(json.loads(path.read_text())[0]['trades'])
            save_label(path,fields())
            labelled=json.loads(path.read_text())[0]
            self.assertEqual(labelled['reviewed_record_sha256'],record_hash(labelled['record']))
            with patch('evaluate_benchmark.classify',return_value={'relevant_trades':['Roofing'],'contact_route':'portal'}):
                result=evaluate([labelled],'rules',require_human=True)
            self.assertEqual(result['micro']['f1'],1)
            self.assertEqual(result['label_provenance'],'human-attested')
            self.assertTrue(result['warnings'])
            labelled['record']['description']='Changed after review'
            with self.assertRaises(ValueError):evaluate([labelled],'rules',require_human=True)

    def test_review_negative_validation_and_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'labels.json';path.write_text(json.dumps([sample()]))
            bad=fields();bad['contact']=['agent']
            with self.assertRaises(ValueError):save_label(path,bad)
            bad=fields();bad['no_trades']=['yes']
            with self.assertRaises(ValueError):save_label(path,bad)
            negative=fields();negative.pop('trade');negative.update(no_trades=['yes'],contact=['excluded'])
            save_label(path,negative)
            labelled=json.loads(path.read_text())[0]
            self.assertEqual(labelled['trades'],[]);self.assertIsNone(labelled['contact_route'])

    def test_radius_filter_and_postcode_lookup(self):
        point={'lat':51.5,'lon':-.1}
        self.assertEqual(distance_km(point,point),0)
        self.assertAlmostEqual(distance_km({'lat':0,'lon':0},{'lat':0,'lon':1}),111.195,places=2)
        r=sample()['record'];r.update(decision='Approved',coordinates=point)
        c=classify(r)
        self.assertEqual(len(select([(r,c)],centre=point,radius_km=1)),1)
        self.assertEqual(select([(r|{'coordinates':{'lat':52.,'lon':-.1}},c)],centre=point,radius_km=1),[])
        self.assertEqual(select([(r|{'coordinates':None},c)],centre=point,radius_km=1),[])
        response=Mock(status_code=200);response.json.return_value={'result':{'latitude':51.5,'longitude':-.1}}
        postcode_centre.cache_clear()
        with patch('westminster_leads.geography.requests.get',return_value=response) as get:
            self.assertEqual(postcode_centre('SW1A 1AA'),point)
            postcode_centre('SW1A 1AA');get.assert_called_once()
        postcode_centre.cache_clear()
        with self.assertRaises(ValueError):postcode_centre('https://evil.invalid')

    def test_mocked_llm_schema_cost_and_contact_validation(self):
        result=classify(sample()['record'])
        result['estimated_cost_usd']=None
        body={'choices':[{'message':{'content':json.dumps(result)}}], 'model':'test-model', 'usage':{'prompt_tokens':100,'completion_tokens':50}}
        response=Mock();response.json.return_value=body
        with patch.dict('os.environ',{'LEADS_LLM_API_KEY':'test-only','LEADS_INPUT_USD_PER_MILLION':'1','LEADS_OUTPUT_USD_PER_MILLION':'2'}), patch('westminster_leads.classifier.requests.post',return_value=response) as post:
            actual=classify(sample()['record'],'openai')
            self.assertAlmostEqual(actual['estimated_cost_usd'],.0002)
            messages=post.call_args.kwargs['json']['messages']
            self.assertEqual(messages[1]['role'],'user')
            result['contact_route']='agent'
            response.json.return_value=body|{'choices':[{'message':{'content':json.dumps(result)}}]}
            with self.assertRaises(ValueError):classify(sample()['record'],'openai')

    def test_slide_deck_uses_real_count_and_discloses_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);r=sample()['record'];store.upsert(r);store.classify(r['reference'],classify(r));store.close()
            target=Path(tmp)/'slides.html'
            result=build(tmp,target)
            self.assertEqual(result['records'],1);self.assertEqual(result['slides'],7)
            self.assertIn('not yet measured',target.read_text())
            self.assertIn('secondary',target.read_text().lower())



class BackupTests(unittest.TestCase):
    def test_restore_database_state_and_preserve_existing_backup(self):
        from backup_data import backup
        from zipfile import ZipFile
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'dataset';store=Store(directory)
            r=sample()['record'];store.upsert(r);store.classify(r['reference'],classify(r))
            state={'completed_until':'2026-10-29T10:00:00+00:00','bootstrap_weeks':4}
            store.save_sync_state(state);store.close()
            output=Path(tmp)/'backup.zip';backup(directory,output)
            restored=Path(tmp)/'restored'
            with ZipFile(output) as archive:archive.extractall(restored)
            store=Store(restored)
            self.assertEqual(store.sync_state(),state)
            self.assertEqual(list(store.records())[0][0]['reference'],'TEST/FULL')
            self.assertIsNotNone(list(store.records())[0][1]);store.close()
            before=output.read_bytes()
            with self.assertRaises(FileExistsError):backup(directory,output)
            self.assertEqual(output.read_bytes(),before)

if __name__ == '__main__':unittest.main()
