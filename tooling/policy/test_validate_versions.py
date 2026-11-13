from __future__ import annotations
import importlib.util, unittest
from pathlib import Path
MODULE_PATH=Path(__file__).with_name('validate_versions.py')
SPEC=importlib.util.spec_from_file_location('apf_validate_versions',MODULE_PATH); assert SPEC and SPEC.loader
m=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_major_pin(self):
        self.assertEqual(m.major_from_pin('7.*.*'),7); self.assertEqual(m.major_from_pin('1.*.*-preview'),1)
    def test_reject_minor_or_latest(self):
        for value in ('7.2.*','7.2.0','latest','*'):
            with self.assertRaises(m.VersionGovernanceError): m.major_from_pin(value)
    def test_conflicting_major(self):
        profile={'assignments':[{'key':'a','definition':{'id':'/providers/Microsoft.Authorization/policyDefinitions/x','definition_version':'1.*.*'}},{'key':'b','definition':{'id':'/providers/Microsoft.Authorization/policyDefinitions/x','definition_version':'2.*.*'}}]}
        with self.assertRaises(m.VersionGovernanceError): m.profile_pins(profile)
    def test_hold_review(self):
        review={'policy_definition_id':'/providers/Microsoft.Authorization/policyDefinitions/x','assignment_keys':['a'],'current_pin':'7.*.*','current_effective_major':7,'observed_latest':'8.0.0','observed_latest_major':8,'status':'hold','decision':'keep_current_major'}
        summary=m.validate_review(Path('r.json'),review,{'/providers/microsoft.authorization/policydefinitions/x':7},{'a':'7.*.*'}); self.assertIn('status=hold',summary)
    def test_approved_target_must_match(self):
        review={'policy_definition_id':'/providers/Microsoft.Authorization/policyDefinitions/x','assignment_keys':['a'],'current_pin':'7.*.*','current_effective_major':7,'observed_latest':'8.0.0','observed_latest_major':8,'status':'approved','decision':'upgrade_major','target_pin':'9.*.*'}
        with self.assertRaises(m.VersionGovernanceError): m.validate_review(Path('r.json'),review,{'/providers/microsoft.authorization/policydefinitions/x':7},{'a':'7.*.*'})
if __name__=='__main__': unittest.main()
