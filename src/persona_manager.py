# src/persona_manager.py
"""
Manages persona activation, isolation mode, and resets.
"""

active_personas = {
    "Cyclo": True,
    "Emo": True,
    "Prim": True,
    "Spri": True,
    "Governor": True  # Governor is treated as a special persona
}

isolation_mode = False
isolated_persona = None

def remove_persona(persona):
    """
    Deactivates a persona. If that leaves only one
    from the four main (Cyclo/Emo/Prim/Spri), we enter isolation mode.
    Governor cannot be removed.
    We also prevent removing all four main personas entirely.
    """
    global isolation_mode, isolated_persona

    # Never remove Governor
    if persona == "Governor":
        return

    if persona in active_personas:
        active_personas[persona] = False

    # Count how many of the four main personas remain active
    main_active = [p for p in ["Cyclo", "Emo", "Prim", "Spri"] if active_personas[p]]

    # If zero remain, revert this removal (can't remove all)
    if len(main_active) == 0:
        # revert
        active_personas[persona] = True
        return

    # If exactly one remains, we enter isolation mode with that persona
    if len(main_active) == 1:
        isolation_mode = True
        isolated_persona = main_active[0]

def add_persona(persona):
    """
    Reactivates a persona. If more than one main persona
    is active, we exit isolation mode.
    """
    global isolation_mode, isolated_persona
    if persona in active_personas:
        active_personas[persona] = True

    # Recount how many main personas are active
    main_active = [p for p in ["Cyclo", "Emo", "Prim", "Spri"] if active_personas[p]]

    if len(main_active) > 1:
        # Exit isolation if more than one
        isolation_mode = False
        isolated_persona = None

def reset_personas():
    """
    Resets all personas (including Governor) to active,
    and turns off isolation mode.
    """
    global isolation_mode, isolated_persona
    isolation_mode = False
    isolated_persona = None
    for p in active_personas:
        active_personas[p] = True

def isolate_persona(persona):
    """
    Directly isolate a single persona, ignoring the rest.
    Governor won't be isolated in that sense.
    """
    global isolation_mode, isolated_persona
    if persona == "Governor":
        return

    if persona in active_personas:
        isolation_mode = True
        isolated_persona = persona
        for p in ["Cyclo", "Emo", "Prim", "Spri"]:
            active_personas[p] = (p == persona)

def get_active_personas():
    """
    Returns all active 'main' personas (Cyclo, Emo, Prim, Spri),
    ignoring Governor in the normal list. If isolation is in effect,
    returns just the isolated one.
    """
    global isolation_mode, isolated_persona
    if isolation_mode and isolated_persona:
        return [isolated_persona]
    return [p for p in ["Cyclo", "Emo", "Prim", "Spri"] if active_personas[p]]

def is_isolation_mode():
    return isolation_mode
