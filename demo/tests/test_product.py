import copy
import json
import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import validate_config, evaluate_trace, ValidationError, UNITS
from server import Store, generate
from persistence import backup, restore
from test_core import good_trace


class ProductTests(unittest.TestCase):
    def test_languages_counts_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            original=Store(Path(folder)/'original.sqlite3')
            original.save('students',{'id':'S-BILINGUAL','label':'Sample','grade':'Secondary','diagnostic':{}})
            for language in ('en','zh'):
                for count in (2,3,4):
                    package=generate(original,'S-BILINGUAL','demo',validate_config({'language':language,'question_count':count}))
                    self.assertEqual(len(package['plan']['nodes']),count*2)
                    self.assertEqual(len(package['proposal']['question_ids']),count)
                    self.assertEqual(len(package['schedule']),count)
                    self.assertEqual(package['plan']['language'],language)
                    self.assertIn('解方程' if language=='zh' else 'Solve',package['plan']['nodes'][0]['prompt'])
            snapshot=backup(original)
            restored=Store(Path(folder)/'restored.sqlite3')
            self.assertEqual(restore(restored,{'confirmed':True,'backup':snapshot})['merged'],7)
            self.assertEqual(restore(restored,{'confirmed':True,'backup':snapshot})['merged'],0)
            self.assertEqual(len(restored.packages()),6)
            self.assertNotEqual(restored.packages()[0]['student_token'],original.packages()[0]['student_token'])
            changed=restored.get('students','S-BILINGUAL');changed['label']='Changed';restored.save('students',changed)
            with self.assertRaises(ValidationError):restore(restored,{'confirmed':True,'backup':snapshot})
            self.assertEqual(restored.get('students','S-BILINGUAL')['label'],'Changed')

    def test_backup_retains_trace_revisions(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'source.sqlite3');store.save('students',{'id':'S','label':'S','grade':'Secondary','diagnostic':{}})
            p=generate(store,'S','demo',validate_config({}));p['status']='evaluated';store.save('packages',p)
            trace=good_trace(p);result=evaluate_trace(p,trace)
            with store.connect() as db:
                values=(p['id'],1,json.dumps(trace),json.dumps(result))
                db.execute('INSERT INTO traces VALUES (?,?,?,?)',values);db.execute('INSERT INTO trace_history VALUES (?,?,?,?)',values)
            restored=Store(Path(folder)/'target.sqlite3');restore(restored,{'confirmed':True,'backup':backup(store)})
            self.assertEqual(restored.evaluations('S'),[result])

    def test_unit_and_language_constraints(self):
        self.assertEqual(len(UNITS),1)
        for bad in ({'unit_id':'unregistered'},{'language':'fr'},{'question_count':5},{'question_count':4,'max_pages':3}):
            with self.assertRaises(ValidationError):validate_config(bad)


if __name__=='__main__':unittest.main()
