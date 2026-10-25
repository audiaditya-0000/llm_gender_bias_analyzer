import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from services.gender_swap import render_scenario
from services.gender_salient_scenarios import GENDER_SALIENT_SCENARIOS

print(f"Loaded {len(GENDER_SALIENT_SCENARIOS)} gender-salient scenarios.")

for idx, scen in enumerate(GENDER_SALIENT_SCENARIOS, 1):
    male_rendered = render_scenario(scen["scenario_text"], "male")
    female_rendered = render_scenario(scen["scenario_text"], "female")
    
    # Assertions
    assert male_rendered != female_rendered, f"Scenario {idx} did not change between genders!"
    assert "{PC_" not in male_rendered, f"Unreplaced token in male scenario {idx}: {male_rendered}"
    assert "{PC_" not in female_rendered, f"Unreplaced token in female scenario {idx}: {female_rendered}"
    assert scen["scenario_text"].strip().endswith("must now decide how to respond."), f"Ending sentence missing in {idx}"
    
    print(f"[{idx}/10] '{scen['title']}' validated successfully.")

print("\nALL 10 GENDER-SALIENT SCENARIOS PASSED VALIDATION!")
