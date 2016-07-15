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





def makePretty(myList):
    """ 
    This function takes in a list of dictionaries, where each dictionary represents an input/output
    It modifies variable names and descriptions to be more human readable. 

    """
    for myDict in myList:
        if 'name' in myDict.keys():
            myDict['name'] = myDict['name'].replace("_"," ").title()
        if 'desc' in myDict.keys():
            myDict['desc'] = myDict['desc'][0].upper()+myDict['desc'][1:]

