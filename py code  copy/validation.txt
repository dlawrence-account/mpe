# mpe/code/mpe/validation.py
def validate_triple(triple):
    """Ensure triple is exactly three numeric values."""
    if len(triple) != 3:
        raise ValueError("Triple must have exactly 3 values.")
    return tuple(float(x) for x in triple)
