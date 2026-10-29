import unittest
from westminster_leads.classifier import classify
from westminster_leads.digest import granted


class LeadQualityTests(unittest.TestCase):
    def test_combined_type_does_not_make_lbc_primary_permission(self):
        base = {'reference': '26/00001/LBC', 'application_type': 'Full planning & listed building consent',
                'decision': 'Approved', 'description': 'Extension at roof level'}
        self.assertFalse(granted(base))
        self.assertTrue(granted(base | {'reference': '26/00001/FULL'}))
        self.assertFalse(granted(base | {'reference': '26/00001/FULL', 'status': 'Application Under Consideration'}))
        self.assertFalse(granted(base | {'reference': '26/00001/FULL', 'description': 'Retrospective extension'}))
        self.assertFalse(granted(base | {'reference': '26/00001/FULL', 'application_type': 'Removal/Variation of a condition'}))

    def test_location_is_not_landscaping(self):
        for text in ('Installation of air conditioning in the rear garden', 'Heat pump in garden at basement level'):
            result = classify({'reference': 'TEST', 'description': text})
            self.assertNotIn('Landscaping', result['relevant_trades'])
        self.assertIn('Landscaping', classify({'reference': 'TEST', 'description': 'Garden renovation with new paving'})['relevant_trades'])

    def test_ventilation_is_not_kitchen_refit(self):
        for text in ('Installation of kitchen extract plant at roof level', 'Bathroom vent at rear elevation', 'Doors between kitchen/dining room and vault'):
            self.assertNotIn('Kitchens & Bathrooms', classify({'reference': 'TEST', 'description': text})['relevant_trades'])
        self.assertIn('Kitchens & Bathrooms', classify({'reference': 'TEST', 'description': 'Replacement kitchen and bathrooms'})['relevant_trades'])


if __name__ == '__main__':
    unittest.main()
