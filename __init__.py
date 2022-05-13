#-----------------------------------------------------------
# Copyright (C) 2020 Pablo Nuñez
#-----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#---------------------------------------------------------------------

def classFactory(iface):
    
    from .main_survey import Main_Plugin
    return Main_Plugin(iface)

