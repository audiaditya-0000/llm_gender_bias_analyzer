import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
from services.gender_swap import render_scenario

def test_pc_noun_and_pronouns():
    template = "The {PC_NOUN} walks toward the gate.\n{PC_SUBJECT} opens it.\nThe guard speaks to {PC_OBJECT}."
    
    male = render_scenario(template, "male")
    assert male == "The man walks toward the gate.\nHe opens it.\nThe guard speaks to him."
    
    female = render_scenario(template, "female")
    assert female == "The woman walks toward the gate.\nShe opens it.\nThe guard speaks to her."

def test_third_party_gender_unchanged():
    template = "The {PC_NOUN} sees a woman.\nThe woman tells {PC_OBJECT} about her brother."
    
    male = render_scenario(template, "male")
    assert male == "The man sees a woman.\nThe woman tells him about her brother."
    
    female = render_scenario(template, "female")
    assert female == "The woman sees a woman.\nThe woman tells her about her brother."

def test_third_party_relationship_unchanged():
    template = "The {PC_NOUN} remembers that {PC_POSSESSIVE} brother was killed."
    
    male = render_scenario(template, "male")
    assert male == "The man remembers that his brother was killed."
    
    female = render_scenario(template, "female")
    assert female == "The woman remembers that her brother was killed."

def test_reflexive():
    template = "The {PC_NOUN} blamed {PC_REFLEXIVE}."
    
    male = render_scenario(template, "male")
    assert male == "The man blamed himself."
    
    female = render_scenario(template, "female")
    assert female == "The woman blamed herself."

def test_no_global_substitution():
    template = "The brother entered the room.\nThe sister waited outside.\nThe father was angry."
    
    male = render_scenario(template, "male")
    assert male == template
    
    female = render_scenario(template, "female")
    assert female == template

def test_adjective():
    template = "A {PC_ADJECTIVE} {PC_NOUN} arrives."
    
    male = render_scenario(template, "male")
    assert male == "A male man arrives."
    
    female = render_scenario(template, "female")
    assert female == "A female woman arrives."
