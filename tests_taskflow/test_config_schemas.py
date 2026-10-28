"""No unsupported config field can be silently ignored by the shared checkers."""
import tempfile
import unittest
from pathlib import Path
from muse_audit.taskflow.tasks import prepare_task,review_task
from muse_audit.taskflow.config_schemas import schemas,config_problem

class ConfigSchemaTests(unittest.TestCase):
    def run_check(self,kind,config,artifact_kind='text',data='Hi there.'):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'facts';source.write_text('supplied')
            t=prepare_task(Path(d)/'store','Produce a result',[{'id':'word_cap','kind':kind,'description':'Between 50 and 100 words','mode':'must_change','config':config}],[('facts',source,'facts.txt')],'result',artifact_kind)
            (Path(t['task_dir'])/'artifacts/result').write_text(data)
            return review_task(Path(d)/'store',t['task_id'],write_outputs=False)
    def test_reported_minimum_word_false_pass_is_unknown(self):
        receipt=self.run_check('markdown.word_limit',{'max_words':100,'min_words':50},'markdown')
        self.assertEqual(receipt['checks'][0]['status'],'UNKNOWN');self.assertEqual(receipt['decision'],'UNRESOLVED')
    def test_extra_field_abstains_for_every_supported_new_config(self):
        cases={'text.required_exact':{'text':'Hi'},'text.forbidden_exact':{'text':'secret'},'text.word_limit':{'max_words':100},
         'markdown.required_exact':{'text':'Hi'},'markdown.forbidden_exact':{'text':'secret'},'markdown.word_limit':{'max_words':100},
         'json.field_exact':{'field':'x','expected':7},'csv.columns':{'columns':['x']},'csv.rows_exact':{'source_id':'facts'},'csv.total_cap':{'column':'x','max_value':100}}
        for kind,config in cases.items():
            with self.subTest(kind=kind):
                config={**config,'not_supported':True}
                artifact_kind='markdown' if kind.startswith('markdown.') else 'json' if kind.startswith('json.') else 'csv' if kind.startswith('csv.') else 'text'
                receipt=self.run_check(kind,config,artifact_kind)
                self.assertEqual(receipt['checks'][0]['status'],'UNKNOWN')
    def test_types_missing_fields_and_bool_integer_are_not_accepted(self):
        for kind,config in [('text.word_limit',{'max_words':True}),('markdown.word_limit',{'max_words':-1}),('json.field_exact',{'field':'x'}),('csv.columns',{'columns':['x','x']}),('csv.total_cap',{'column':'x','max_value':float('inf')})]:
            with self.subTest(kind=kind):self.assertIsNotNone(config_problem(kind,config))
    def test_catalog_is_exact_and_not_mutable_by_callers(self):
        catalog=schemas();self.assertEqual(len(catalog),10)
        self.assertTrue(all(s['additionalProperties'] is False for s in catalog.values()))
        catalog['text.word_limit']['properties']['min_words']={}
        self.assertNotIn('min_words',schemas()['text.word_limit']['properties'])
if __name__=='__main__':unittest.main()
