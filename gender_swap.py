"""
Shared gender-swap utility using explicit PC tokens.

Tokens:
{PC_NOUN}
{PC_SUBJECT}
{PC_OBJECT}
{PC_POSSESSIVE}
{PC_REFLEXIVE}
"""

import re

# Kept for backward compatibility with existing UI routes
BUILTIN_WORD_PAIRS: list[tuple[str, str]] = []
CUSTOM_PAIRS_FILE = "custom_word_pairs.json"

PC_FORMS = {
    "male": {
        "NOUN": "man",
        "SUBJECT": "he",
        "OBJECT": "him",
        "POSSESSIVE": "his",
        "REFLEXIVE": "himself",
        "ADJECTIVE": "male",
    },
    "female": {
        "NOUN": "woman",
        "SUBJECT": "she",
        "OBJECT": "her",
        "POSSESSIVE": "her",
        "REFLEXIVE": "herself",
        "ADJECTIVE": "female",
    },
}

def render_scenario(text: str, gender: str) -> str:
    """
    Renders a scenario template for the specified PC gender.
    Replaces explicit PC tokens with their gendered forms.
    Leaves all other text unchanged.
    """
    if gender not in PC_FORMS:
        raise ValueError(f"Invalid gender: {gender}")

    forms = PC_FORMS[gender]
    result = text

    for token, value in forms.items():
        placeholder = f"{{PC_{token}}}"
        
        # We need to replace the placeholder but capitalize if it's at the start of a sentence.
        # A sentence start is: beginning of string, or after a '.', '!', '?' followed by whitespace.
        # Also after a newline.
        
        def repl(match):
            prefix = match.group(1)
            # If prefix ends with sentence-ending punctuation + whitespace, or is just whitespace
            # and there's no other text before it (which we can't fully check with just a lookbehind
            # if it's variable length, but we can capture the preceding chars).
            # Actually, regex is easier:
            return prefix + value

        # Let's just do an iterative search and replace to handle capitalization properly.
        # Or we can just use a regex for the placeholder and check the index.
        pass

    # Better approach:
    # Find all {PC_...} tokens and replace them one by one.
    # If the token is the very first thing, or if the last non-whitespace character before it is . ! or ?, capitalize it.
    
    # We will do a regex sub with a function
    def replacer(match):
        full_string = match.string
        start_idx = match.start()
        token_name = match.group(1)
        
        if token_name not in forms:
            return match.group(0) # Not a recognized token, don't replace
            
        replacement = forms[token_name]
        
        # Check if we should capitalize
        # Walk backwards from start_idx to find the first non-whitespace char
        should_capitalize = False
        i = start_idx - 1
        while i >= 0 and full_string[i] in ' \t\n\r':
            if full_string[i] == '\n':
                # Newline is a strong indicator of a new sentence in these prompts
                should_capitalize = True
                break
            i -= 1
            
        if i < 0:
            should_capitalize = True
        elif not should_capitalize and full_string[i] in '.!?':
            should_capitalize = True
            
        if should_capitalize:
            return replacement.capitalize()
        return replacement

    result = re.sub(r'\{PC_([A-Z]+)\}', replacer, result)

    return result

