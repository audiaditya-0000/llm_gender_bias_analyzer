import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
from services.gender_swap import render_scenario

def run_tests():
    template1 = "The {PC_NOUN} walks toward the gate.\n{PC_SUBJECT} opens it.\nThe guard speaks to {PC_OBJECT}."
    assert render_scenario(template1, "male") == "The man walks toward the gate.\nHe opens it.\nThe guard speaks to him.", "Test 1 Male failed"
    assert render_scenario(template1, "female") == "The woman walks toward the gate.\nShe opens it.\nThe guard speaks to her.", "Test 1 Female failed"

    template2 = "The {PC_NOUN} sees a woman.\nThe woman tells {PC_OBJECT} about her brother."
    assert render_scenario(template2, "male") == "The man sees a woman.\nThe woman tells him about her brother.", "Test 2 Male failed"
    assert render_scenario(template2, "female") == "The woman sees a woman.\nThe woman tells her about her brother.", "Test 2 Female failed"

    template3 = "The {PC_NOUN} remembers that {PC_POSSESSIVE} brother was killed."
    assert render_scenario(template3, "male") == "The man remembers that his brother was killed.", "Test 3 Male failed"
    assert render_scenario(template3, "female") == "The woman remembers that her brother was killed.", "Test 3 Female failed"

    template4 = "The {PC_NOUN} blamed {PC_REFLEXIVE}."
    assert render_scenario(template4, "male") == "The man blamed himself.", "Test 4 Male failed"
    assert render_scenario(template4, "female") == "The woman blamed herself.", "Test 4 Female failed"

    template5 = "The brother entered the room.\nThe sister waited outside.\nThe father was angry."
    assert render_scenario(template5, "male") == template5, "Test 5 Male failed"
    assert render_scenario(template5, "female") == template5, "Test 5 Female failed"

    print("Gender swap tests passed!")

if __name__ == "__main__":
    run_tests()
    import unittest
    from test_reliability import TestInterRaterReliability
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestInterRaterReliability)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("All test suites passed successfully!")
