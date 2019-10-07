

class PVSystem:

    def __init__(self, site_tuple, SL_instance):
        self.error_type = None # update on the fly (default set to None)
        self.site_tuple = site_tuple
        self.capacity = getattr(site_tuple, "Capacity")
        self.eastings = getattr(site_tuple, "Eastings")
        self.northings = getattr(site_tuple, "Northings")
        self.system_type = getattr(site_tuple, "system_type")
        self.SL_instance = SL_instance

    def decommissioned(self):
        # set error_type
        self.error_type = "decommissioned"
        # get error value
        import pdb; pdb.set_trace()
        error = self.SL_instance.return_error(self.error_type, self.system_type)


        return