def finditem(obj, key): 
	""" 
	Parameters: 
	Obj -- going to be a dictionary; 
	key -- key of a dictionary entry.
	Returns: item -- a value associated with a key

	This function will perform a deep search in a dictionary
	for a value associated with a key        
	"""
	if key in obj: 
		return obj[key]
	for k, v in obj.items():
	    if isinstance(v, dict):
	        item = finditem(v, key)
	        if item is not None:
	            return item
