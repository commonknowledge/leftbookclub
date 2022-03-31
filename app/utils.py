def flatten_list(the_list):
    """
    Takes a 2D list and returns a 1D list
    """
    return [item for sublist in the_list for item in sublist]
